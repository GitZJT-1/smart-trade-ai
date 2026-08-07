#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_google_vision.py — Google Cloud Vision OCR 引擎

用于俄/英工程图纸和合同的高精度 OCR，替代 Tesseract/OCR.space 的低准确度链路。
Google Cloud Vision 在俄语西里尔文字、混合排版、小字密集场景远超开源引擎。

特点:
  - 自动检测凭证（GOOGLE_APPLICATION_CREDENTIALS / GOOGLE_API_KEY）
  - 支持图片（PNG/JPG/TIF）和 PDF 输入
  - document_text_detection → 结构化输出（paragraphs/words + bounding poly + confidence）
  - 俄语语言提示 → 西里尔字母识别准确度显著提升
  - 单个请求处理，无需多引擎交叉验证

用法:
  # 单图 OCR
  python ocr_google_vision.py drawing.png --lang-hint ru

  # PDF 多页 OCR
  python ocr_google_vision.py contract.pdf --lang-hint ru --out ocr_out/

  # 从 stdin 接收图片 base64（管道模式）
  python ocr_google_vision.py --stdin --lang-hint ru

输出:
  <out>/ocr_google_vision.txt  逐页全文
  <out>/fields.json           提取字段（复用 ocr_pdf.py 的字段提取逻辑）
  <out>/verify_list.txt       待核清单

依赖:
  google-cloud-vision >= 3.0（pip install google-cloud-vision）

认证（二选一）:
  1) 服务账号 JSON（推荐）: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
  2) API Key: 在 ~/AppData/Local/hermes/.env 设置 GOOGLE_API_KEY=...
     （API Key 模式功能受限：无结构化文档输出，仅返回纯文本）
"""

import argparse
import base64
import json
import os
import re
import sys
import traceback
from io import BytesIO

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─── 尝试导入 google-cloud-vision ───
try:
    from google.cloud import vision
    HAS_GOOGLE_CLOUD = True
except ImportError:
    HAS_GOOGLE_CLOUD = False

try:
    import fitz  # pymupdf — PDF 渲染用
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── 认证检测 ───
ENV_FILE = os.path.expanduser(r"~\AppData\Local\hermes\.env")

def detect_auth():
    """检测可用认证方式：服务账号 JSON > API Key > 无"""
    # 1) 服务账号 JSON（最完整）
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds and os.path.isfile(creds):
        return "service_account", creds

    # 2) API Key（功能受限）
    key = None
    if os.path.exists(ENV_FILE):
        try:
            for line in open(ENV_FILE, encoding="utf-8", errors="replace"):
                if line.strip().startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
        except OSError:
            pass
    if key:
        return "api_key", key

    return None, None


def ocr_via_service_account(image_bytes, lang_hint=None):
    """使用服务账号 JSON 认证的完整 Vision API（document_text_detection）"""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)

    # 语言提示（俄语 → 西里尔识别提升显著）
    ctx = None
    if lang_hint:
        ctx = vision.ImageContext(language_hints=[lang_hint])

    response = client.document_text_detection(image=image, image_context=ctx)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    annotation = response.full_text_annotation
    result = {
        "full_text": annotation.text,
        "pages": [],
        "method": "service_account",
    }

    for page in annotation.pages:
        page_data = {"width": page.width, "height": page.height, "blocks": []}
        for block in page.blocks:
            block_data = {
                "type": str(block.block_type),
                "paragraphs": [],
            }
            for para in block.paragraphs:
                para_data = {
                    "text": "",
                    "words": [],
                    "confidence": getattr(para, "confidence", 0),
                }
                for word in para.words:
                    word_text = "".join(
                        s.text for s in word.symbols
                    ) if word.symbols else ""
                    word_conf = getattr(word, "confidence", 0)
                    para_data["text"] += word_text + " "
                    para_data["words"].append({
                        "text": word_text,
                        "confidence": word_conf,
                    })
                para_data["text"] = para_data["text"].strip()
                block_data["paragraphs"].append(para_data)
            page_data["blocks"].append(block_data)
        result["pages"].append(page_data)

    return result


def ocr_via_api_key(image_bytes, lang_hint=None):
    """
    使用 API Key 认证的 Vision API（REST，仅 textDetection）。
    API Key 模式下 Google 不返回 document_text_detection 结构化结果。
    """
    import urllib.request
    import urllib.error

    b64 = base64.b64encode(image_bytes).decode("ascii")
    body = {
        "requests": [{
            "image": {"content": b64},
            "features": [{"type": "TEXT_DETECTION", "maxResults": 1}],
        }]
    }
    if lang_hint:
        body["requests"][0]["imageContext"] = {"languageHints": [lang_hint]}

    req = urllib.request.Request(
        f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Vision API HTTP {e.code}: {e.read().decode()}")

    resp_obj = data.get("responses", [{}])[0]
    if "error" in resp_obj:
        raise RuntimeError(f"Vision API error: {resp_obj['error']}")

    texts = resp_obj.get("textAnnotations", [])
    full_text = texts[0]["description"] if texts else ""
    return {
        "full_text": full_text,
        "pages": [],
        "method": "api_key",
    }


def ocr_image(image_bytes, lang_hint="ru"):
    """统一入口：根据认证方式自动选路径"""
    auth_type, auth_value = detect_auth()

    if auth_type is None:
        raise RuntimeError(
            "未配置 Google Cloud 认证。请二选一：\n"
            "  1) export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json\n"
            "  2) 在 ~/AppData/Local/hermes/.env 设置 GOOGLE_API_KEY=..."
        )

    if auth_type == "service_account":
        return ocr_via_service_account(image_bytes, lang_hint)
    else:
        GOOGLE_API_KEY = auth_value
        return ocr_via_api_key(image_bytes, lang_hint)


def ocr_pdf(pdf_path, lang_hint="ru", dpi=200):
    """OCR PDF 每一页（渲染 PNG → Google Vision）"""
    if not HAS_PYMUPDF:
        raise RuntimeError("pymupdf 未安装，无法处理 PDF（uv pip install pymupdf）")

    doc = fitz.open(pdf_path)
    results = []
    for i in range(doc.page_count):
        page = doc[i]
        # 先尝试直接提取文字（文字型页）
        txt = page.get_text().strip()
        if txt and len(txt) > 100:
            results.append({
                "page": i + 1,
                "type": "text",
                "text": txt,
            })
        else:
            # 渲染为 PNG 后 OCR
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            ocr = ocr_image(img_bytes, lang_hint)
            results.append({
                "page": i + 1,
                "type": "ocr",
                "text": ocr["full_text"],
                "method": ocr["method"],
            })
        print(f"  [页 {i+1}/{doc.page_count}] {results[-1]['type']} ({len(results[-1]['text'])} 字符)", file=sys.stderr)
    doc.close()
    return results


def ocr_file(file_path, lang_hint="ru", dpi=200):
    """自动识别文件类型（PDF / 图片）"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return ocr_pdf(file_path, lang_hint, dpi)

    # 图片文件
    with open(file_path, "rb") as f:
        img_bytes = f.read()

    # TIF 可能需要 pillow 转 PNG（Google Vision 不支持所有 TIF 变体）
    if ext in (".tif", ".tiff"):
        if not HAS_PIL:
            raise RuntimeError("pillow 未安装，无法处理 TIF（uv pip install pillow）")
        img = Image.open(BytesIO(img_bytes))
        if img.mode in ("CMYK", "RGBA", "P", "LA"):
            img = img.convert("RGB")
        buf = BytesIO()
        img.save(buf, "PNG")
        img_bytes = buf.getvalue()

    result = ocr_image(img_bytes, lang_hint)
    return [{"page": 1, "type": "ocr", "text": result["full_text"], "method": result["method"]}]


# ─── 字段提取（复用 ocr_pdf.py 的逻辑）───
def normalize_amount(s):
    s = s.strip().replace("\u00a0", " ")
    s = re.sub(r"\s+", "", s)
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


FIELD_PATTERNS = [
    ("spec_no",      r"(?:Спецификация|SPECIFICATION)\s*№?\s*\"?\s*(\d{10})\b",
                     r"\b(\d{10})\b",                                 "spec",     "规格书号"),
    ("contract_no",  r"К\s*[лд]оговору\s*№\s*\"?\s*(\d{10,})",
                     r"\b(\d{16,})\b",                                "contract", "合同号"),
    ("tender",       r"Tender\s*[№#]?\s*(\d{4,}\/\d+)",
                     r"\b(\d{7,8}\/\d+)\b",                           None,       "招标号"),
    ("total",        r"(?:Итого\s*сумма\s*без\s*НДС|Total\s*amount[^:\n]*)\s*[:.]?\s*([\d][\d\s.,]*)",
                     r"(\d{1,3}(?:\s?\d{3})+[,.]\d{2})",              "amount",   "总金额"),
    ("currency",     r"\b(CNY|RUB|USD|EUR)\b",
                     r"(?:Валюта|Currency)[^\n]{0,30}?(?<![A-Za-z])([A-Z]{3})\b", None, "币种"),
    ("delivery",     r"Условия\s*поставки[^\n]{0,80}?((?:DAP|CIF|FOB|EXW|CPT|CIP|DPU|DDP)\s*[\w.\- ]{0,30})",
                     r"\b(DAP|CIF|FOB|EXW|CPT|CIP|DPU|DDP)\s*[\w.\- ]{0,20}", None, "交货条款"),
    ("payment",      r"(?:Условия\s*платежа|Payment\s*terms)[:\s.\-/]*([^\n]{0,80})",
                     None,                                            None,       "付款条款"),
    ("delivery_date", r"Срок\s*поставки[^\d]{0,60}(\d{1,2}\.\d{1,2}\.\d{4})",
                     None,                                            "date",     "交货期"),
    ("contract_date", r"(?:К\s*[лд]оговору[^\n]{0,60}?|от|dated|Дата)[^\d\n]{0,12}(\d{1,2}\.\d{1,2}\.\d{4})",
                     r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b",                "date",     "合同日期"),
    ("supplier",     r"((?:Поставщик|Supplier|Продавец|Seller)[^\n]{0,120})",
                     None,                                            "low",      "供应商"),
    ("buyer",        r"((?:Покупатель|Buyer)[^\n]{0,120})",
                     None,                                            "low",      "买家"),
    ("manufacturer", r"(Завод\s*изготовитель[^\n]{0,100})",
                     None,                                            "low",      "制造商"),
]


def check_fmt(field, value):
    if field == "low":
        return False, "低置信度（OCR 噪声），需 vision/人工精修"
    if field == "contract":
        digits = re.sub(r"\D", "", value)
        return len(digits) >= 16, f"合同号通常 16-20 位，实际 {len(digits)} 位"
    if field == "spec":
        digits = re.sub(r"\D", "", value)
        return len(digits) == 10, f"规格书号应为 10 位，实际 {len(digits)} 位"
    if field == "amount":
        v = normalize_amount(value)
        return v is not None, f"金额无法解析: {value!r}"
    if field == "date":
        return bool(re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}", value)), f"日期格式异常: {value!r}"
    return True, ""


def extract_fields(full_text):
    fields, sources, verify = {}, {}, []
    for name, pat, fallback, fmt, desc in FIELD_PATTERNS:
        m = re.search(pat, full_text, re.IGNORECASE)
        used_fb = False
        if not m and fallback:
            m = re.search(fallback, full_text, re.IGNORECASE)
            used_fb = True
        if not m:
            verify.append(f"[缺失] {desc} ({name}) — 未在文本中找到")
            continue
        value = m.group(1).strip()
        ok, note = True, ""
        if fmt:
            ok, note = check_fmt(fmt, value)
        fields[name] = value
        if fmt == "low":
            verify.append(f"[低置信度] {desc} ({name}) 整行={value!r} — 请 vision/人工精修")
        elif not ok:
            verify.append(f"[格式可疑] {desc} ({name}) 值={value!r} — {note}")
        elif name in ("contract_no", "spec_no", "total", "delivery_date", "contract_date"):
            src = "兜底模式" if used_fb else "主模式"
            verify.append(f"[需核对] {desc} ({name}) 值={value!r} (来源={src})")
    return fields, verify


# ─── MAIN ───
def main():
    ap = argparse.ArgumentParser(description="Google Cloud Vision OCR")
    ap.add_argument("input", nargs="?", help="文件路径（图片或PDF），--stdin 时忽略")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 读取 base64 图片数据")
    ap.add_argument("--lang-hint", default="ru", help="语言提示，默认 ru, 多语言用逗号分隔")
    ap.add_argument("--out", help="输出目录（保存 ocr_full.txt 等）")
    ap.add_argument("--dpi", type=int, default=200, help="PDF 渲染 DPI（默认 200）")
    ap.add_argument("--check-auth", action="store_true", help="仅检测认证状态后退出")
    args = ap.parse_args()

    # ── 认证检测模式 ──
    if args.check_auth:
        auth_type, auth_value = detect_auth()
        if auth_type:
            print(f"[OK] 认证方式: {auth_type}")
            if auth_type == "service_account":
                print(f"     凭证文件: {auth_value}")
            else:
                print(f"     API Key: {auth_value[:6]}...")
            print(f"     google-cloud-vision: {'已安装' if HAS_GOOGLE_CLOUD else '未安装'}")
            print("     运行 uv pip install google-cloud-vision 安装")
        else:
            print("[X] 未配置认证")
            print("    方式1: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
            print("    方式2: 在 .env 设置 GOOGLE_API_KEY=...")
            print(f"    配置文件位置: {ENV_FILE}")
        return

    # ── 依赖检查 ──
    if not HAS_GOOGLE_CLOUD:
        print("错误: google-cloud-vision 未安装", file=sys.stderr)
        print("运行: uv pip install google-cloud-vision", file=sys.stderr)
        sys.exit(1)

    # ── 输入源 ──
    if args.stdin:
        b64_data = sys.stdin.read().strip()
        image_bytes = base64.b64decode(b64_data)
        pages = [{
            "page": 1,
            "type": "ocr",
            "text": ocr_image(image_bytes, args.lang_hint)["full_text"],
        }]
    elif args.input:
        pages = ocr_file(args.input, args.lang_hint, args.dpi)
    else:
        print("错误: 请指定输入文件或使用 --stdin", file=sys.stderr)
        sys.exit(1)

    # ── 输出 ──
    full_text = "\n\n".join(
        f"==== 第{p['page']}页（{p['type']} via Google Vision）====\n{p['text']}"
        for p in pages
    )

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        txt_path = os.path.join(args.out, "ocr_google_vision.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"[输出] 全文 → {txt_path}")

        # 字段提取（合同场景）
        fields, verify = extract_fields(full_text)
        fields_path = os.path.join(args.out, "fields.json")
        with open(fields_path, "w", encoding="utf-8") as f:
            json.dump({
                "fields": fields,
                "n_pages": len(pages),
                "engine": "google_cloud_vision",
            }, f, ensure_ascii=False, indent=2)
        print(f"[输出] 字段 → {fields_path}")

        if verify:
            verify_path = os.path.join(args.out, "verify_list.txt")
            with open(verify_path, "w", encoding="utf-8") as f:
                f.write("== Google Vision OCR 待核清单 ==\n")
                f.write("（Google Vision 准确度远超 Tesseract，通常仅长数字需核对）\n\n")
                for v in verify:
                    f.write(v + "\n")
            print(f"[输出] 待核清单 → {verify_path}")

        print("\n==== 提取字段 ====")
        for k in ("contract_no", "spec_no", "tender", "total", "currency",
                  "delivery", "payment", "delivery_date", "contract_date",
                  "supplier", "buyer", "manufacturer"):
            v = fields.get(k)
            if v:
                print(f"  {k}: {v}")
    else:
        print(full_text)


if __name__ == "__main__":
    main()

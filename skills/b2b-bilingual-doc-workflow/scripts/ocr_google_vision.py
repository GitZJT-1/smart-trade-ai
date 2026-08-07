#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_google_vision.py — Gemini Vision OCR 引擎

利用 Gemini 2.0 Flash 的视觉能力做高精度 OCR，替代 Tesseract/OCR.space。
Gemini Vision 对俄语西里尔文字、工程图纸混合排版识别远超开源引擎。

特点:
  - 单 API Key 认证（~/.hermes/.env 中 GOOGLE_API_KEY=...）
  - 支持图片（PNG/JPG/TIF）和 PDF 输入
  - 俄语语言提示 → 西里尔字母识别准确度显著提升
  - 不依赖 GCP 绑卡/服务账号（Cloud Vision 不支持 API Key，Gemini 支持）

用法:
  python ocr_google_vision.py drawing.png --lang-hint ru
  python ocr_google_vision.py contract.pdf --lang-hint ru --out ocr_out/
  python ocr_google_vision.py --check-auth

输出:
  <out>/ocr_gemini.txt    逐页全文
  <out>/fields.json       提取字段（合同场景）
  <out>/verify_list.txt   待核清单

依赖:
  无需额外 pip 包（仅用 urllib + base64 标准库）
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
import urllib.error
from io import BytesIO

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import fitz  # pymupdf — PDF 渲染
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── 通用配置 ───
ENV_FILE = os.path.expanduser(r"~\AppData\Local\hermes\.env")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-001:generateContent"
OCR_PROMPT = """Extract ALL text from this Russian engineering drawing. 
Return every word, number, and symbol exactly as it appears — preserve Cyrillic characters, GOST/ДСТУ standards, dimensions, material grades, and title block data.
Do NOT translate. Do NOT summarize. Output raw text only.
For the title block, pay special attention to: Масса (weight), Масштаб (scale), Обозначение (part number), Наименование (name), материал (material).
For assembly detail tables (спецификация), extract all rows: Поз (position), Обозначение, Наименование, Кол (quantity)."""


def detect_auth():
    """检测认证方式：GOOGLE_API_KEY > GOOGLE_APPLICATION_CREDENTIALS"""
    key = None
    if os.path.exists(ENV_FILE):
        try:
            for line in open(ENV_FILE, encoding="utf-8", errors="replace"):
                if line.strip().startswith("GOOGLE_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
        except OSError:
            pass
    if key and key.strip():
        return "api_key", key.strip()

    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds and os.path.isfile(creds):
        return "service_account", creds

    return None, None


def ocr_page_gemini(image_bytes, api_key, lang_hint="ru", mime="image/png"):
    """单页 Gemini Vision OCR"""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    body = {
        "contents": [{
            "parts": [
                {"text": OCR_PROMPT},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]
        }]
    }
    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API HTTP {e.code}: {body[:500]}")

    # Gemini 返回结构: candidates[0].content.parts[0].text
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini 无返回结果: {json.dumps(data, ensure_ascii=False)[:300]}")
    finish = candidates[0].get("finishReason", "UNKNOWN")
    text = "".join(
        p.get("text", "") for p in candidates[0].get("content", {}).get("parts", [])
    )
    return text, finish


def ocr_pdf(pdf_path, api_key, lang_hint="ru", dpi=200):
    """OCR PDF 每一页"""
    if not HAS_PYMUPDF:
        raise RuntimeError("pymupdf 未安装（uv pip install pymupdf）")

    doc = fitz.open(pdf_path)
    results = []
    for i in range(doc.page_count):
        page = doc[i]
        txt = page.get_text().strip()
        if txt and len(txt) > 100:
            results.append({"page": i + 1, "type": "text", "text": txt})
        else:
            pix = page.get_pixmap(dpi=dpi)
            text, finish = ocr_page_gemini(pix.tobytes("png"), api_key, lang_hint)
            results.append({"page": i + 1, "type": "ocr", "text": text, "finish": finish})
        print(f"  [页 {i+1}/{doc.page_count}] {results[-1]['type']} ({len(results[-1]['text'])} 字符)", file=sys.stderr)
    doc.close()
    return results


def ocr_file(file_path, api_key, lang_hint="ru", dpi=200):
    """自动识别文件类型（PDF / 图片）"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return ocr_pdf(file_path, api_key, lang_hint, dpi)

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    if ext in (".tif", ".tiff"):
        if not HAS_PIL:
            raise RuntimeError("pillow 未安装（uv pip install pillow）")
        img = Image.open(BytesIO(img_bytes))
        if img.mode in ("CMYK", "RGBA", "P", "LA"):
            img = img.convert("RGB")
        buf = BytesIO()
        img.save(buf, "PNG")
        img_bytes = buf.getvalue()

    text, finish = ocr_page_gemini(img_bytes, api_key, lang_hint)
    return [{"page": 1, "type": "ocr", "text": text, "finish": finish}]


# ─── 字段提取（复用 ocr_pdf.py 逻辑）───
def normalize_amount(s):
    s = s.strip().replace("\u00a0", " ")
    s = re.sub(r"\s+", "", s)
    s = s.replace(",", ".")
    try: return float(s)
    except ValueError: return None

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
    if field == "low": return False, "低置信度，需人工精修"
    if field == "contract":
        d = re.sub(r"\D", "", value)
        return len(d) >= 16, f"合同号 16-20 位，实际 {len(d)} 位"
    if field == "spec":
        d = re.sub(r"\D", "", value)
        return len(d) == 10, f"规格书号 10 位，实际 {len(d)} 位"
    if field == "amount":
        v = normalize_amount(value)
        return v is not None, f"金额无法解析: {value!r}"
    if field == "date":
        return bool(re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}", value)), f"日期格式异常: {value!r}"
    return True, ""

def extract_fields(full_text):
    fields, verify = {}, []
    for name, pat, fallback, fmt, desc in FIELD_PATTERNS:
        m = re.search(pat, full_text, re.IGNORECASE)
        used_fb = False
        if not m and fallback:
            m = re.search(fallback, full_text, re.IGNORECASE)
            used_fb = True
        if not m:
            verify.append(f"[缺失] {desc} ({name}) — 未找到")
            continue
        value = m.group(1).strip()
        ok, note = True, ""
        if fmt: ok, note = check_fmt(fmt, value)
        fields[name] = value
        if fmt == "low":
            verify.append(f"[低置信度] {desc} ({name}) = {value!r}")
        elif not ok:
            verify.append(f"[格式可疑] {desc} ({name}) = {value!r} — {note}")
        elif name in ("contract_no","spec_no","total","delivery_date","contract_date"):
            src = "兜底" if used_fb else "主"
            verify.append(f"[需核对] {desc} ({name}) = {value!r} ({src})")
    return fields, verify


# ─── MAIN ───
def main():
    ap = argparse.ArgumentParser(description="Gemini Vision OCR")
    ap.add_argument("input", nargs="?", help="文件路径")
    ap.add_argument("--lang-hint", default="ru")
    ap.add_argument("--out", help="输出目录")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--check-auth", action="store_true")
    args = ap.parse_args()

    if args.check_auth:
        auth_type, auth_value = detect_auth()
        if auth_type:
            print(f"[OK] Gemini Vision — {auth_type}: {auth_value[:8]}...")
        else:
            print("[X] 未配置认证")
            print(f"    在 {ENV_FILE} 设置 GOOGLE_API_KEY=...")
        return

    if not args.input:
        print("指定输入文件或 --check-auth", file=sys.stderr)
        sys.exit(1)

    auth_type, auth_value = detect_auth()
    if auth_type is None:
        print(f"错误: 未配置 GOOGLE_API_KEY。在 {ENV_FILE} 添加 GOOGLE_API_KEY=...", file=sys.stderr)
        sys.exit(1)

    pages = ocr_file(args.input, auth_value, args.lang_hint, args.dpi)
    full_text = "\n\n".join(
        f"==== 第{p['page']}页（{p['type']} via Gemini Vision{(' [' + p['finish'] + ']') if p.get('finish') else ''}）====\n{p['text']}"
        for p in pages
    )

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        txt_path = os.path.join(args.out, "ocr_gemini.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"[输出] 全文 → {txt_path}")

        fields, verify = extract_fields(full_text)
        fields_path = os.path.join(args.out, "fields.json")
        with open(fields_path, "w", encoding="utf-8") as f:
            json.dump({"fields": fields, "n_pages": len(pages), "engine": "gemini_vision"}, f, ensure_ascii=False, indent=2)
        print(f"[输出] 字段 → {fields_path}")

        if verify:
            vp = os.path.join(args.out, "verify_list.txt")
            with open(vp, "w", encoding="utf-8") as f:
                f.write("== Gemini Vision OCR 待核清单 ==\n\n")
                for v in verify: f.write(v + "\n")
            print(f"[输出] 待核 → {vp}")

        print("\n==== 提取字段 ====")
        for k in ("contract_no","spec_no","tender","total","currency",
                  "delivery","payment","delivery_date","contract_date",
                  "supplier","buyer","manufacturer"):
            if fields.get(k): print(f"  {k}: {fields[k]}")
    else:
        print(full_text)


if __name__ == "__main__":
    main()

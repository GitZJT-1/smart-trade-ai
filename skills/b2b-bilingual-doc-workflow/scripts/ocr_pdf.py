#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_pdf.py — 合同/规格书 PDF → 全文 + 关键字段提取 + 待核清单

覆盖 SKILL A1-A2 全流程：
  1. 遍历【所有页】：get_text() 非空=文字页直取；空=300dpi 渲染 PNG
  2. 扫描页 → 调用 PP-OCRv5（.venv-paddleocr，GPU 线级 OCR，西里尔）
  3. 关键字段锚点正则提取（俄/英），主模式 + 特征数字兜底，
     俄语逗号小数点、千分位空格归一化
  4. 数字格式校验，不合法进待核清单
  5. 输出 verify_list.txt —— 供 vision 交叉校验 / 人工校对

用法:
  .venv-skill/Scripts/python.exe scripts/ocr_pdf.py <合同.pdf> --out <输出目录>

输出:
  <out>/ocr_full.txt      逐页全文（含页码标记）
  <out>/pages/page_NN.png 扫描页渲染图（vision 核对用）
  <out>/fields.json       提取字段 + 来源页
  <out>/verify_list.txt   待核对清单
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPOCR_PY = os.path.join(SKILL_DIR, ".venv-paddleocr", "Scripts", "python.exe")
PPOCR_SCRIPT = os.path.join(SKILL_DIR, "scripts", "ocr_ppocrv5.py")

# ---------- 关键字段锚点（俄英双语） ----------
# 双栏扫描件 OCR 噪声大（"К логопору" 这类变体），原则：
#   1) 宽松锚点 + 特征数字兜底（合同号 / 10 位规格书号本身即强特征）
#   2) 金额/日期/条款类提取"就近数字"，不要求锚点后紧跟
#   3) 供应商/买家 OCR 不可靠 → 整行提取 + 低置信度标记，留待 vision/人工
FIELD_PATTERNS = [
    ("spec_no",      r"(?:Спецификация|SPECIFICATION)\s*№?\s*\"?\s*(\d{10})\b",
                     r"\b(\d{10})\b",                                 "spec",     "规格书号"),
    ("contract_no",  r"К\s*[лд]оговору\s*№\s*\"?\s*(\d{10,})",
                     r"\b(\d{16,})\b",                                "contract", "合同号"),
    ("tender",       r"Tender\s*[№#]?\s*(\d{4,}\/\d+)",
                     r"\b(\d{7,8}\/\d+)\b",                           None,       "招标号"),
    ("total",        r"(?:Итого\s*сумма\s*без\s*НДС|Total\s*amount[^:\n]*)\s*[:.]?\s*([\d][\d\s.,]*)",
                     r"(\d{1,3}(?:\s?\d{3})+[,.]\d{2})",              "amount",   "总金额(不含增值税)"),
    ("currency",     r"\b(CNY|RUB|USD|EUR)\b",
                     r"(?:Валюта|Currency)[^\n]{0,30}?(?<![A-Za-z])([A-Z]{3})\b", None, "币种"),
    ("delivery",     r"Условия\s*поставки[^\n]{0,80}?((?:DAP|CIF|FOB|EXW|CPT|CIP|DPU|DDP)\s*[\w.\- ]{0,30})",
                     r"\b(DAP|CIF|FOB|EXW|CPT|CIP|DPU|DDP)\s*[\w.\- ]{0,20}", None, "交货条款(Incoterms)"),
    ("payment",      r"(?:Условия\s*платежа|Payment\s*terms)[:\s.\-/]*([^\n]{0,80})",
                     None,                                            None,       "付款条款"),
    ("delivery_date", r"Срок\s*поставки[^\d]{0,60}(\d{1,2}\.\d{1,2}\.\d{4})",
                     None,                                            "date",     "交货期"),
    ("contract_date", r"(?:К\s*[лд]оговору[^\n]{0,60}?|от|dated|Дата)[^\d\n]{0,12}(\d{1,2}\.\d{1,2}\.\d{4})",
                     r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b",                "date",     "合同日期"),
    ("supplier",     r"((?:Поставщик|Supplier|Продавец|Seller)[^\n]{0,120})",
                     None,                                            "low",      "供应商(低置信度,整行提取)"),
    ("buyer",        r"((?:Покупатель|Buyer)[^\n]{0,120})",
                     None,                                            "low",      "买家(低置信度,整行提取)"),
    ("manufacturer", r"(Завод\s*изготовитель[^\n]{0,100})",
                     None,                                            "low",      "制造商(低置信度,整行提取)"),
]


def normalize_amount(s):
    """俄语数字归一化: '53 000,00' → 53000.00; '106,00' → 106.00"""
    s = s.strip().replace("\u00a0", " ")
    s = re.sub(r"\s+", "", s)          # 去掉千分位空格
    s = s.replace(",", ".")            # 俄语逗号=小数点
    try:
        return float(s)
    except ValueError:
        return None


def check_fmt(field, value):
    """数字格式校验，返回 (ok, 说明)"""
    if field == "low":
        return (False, "低置信度（OCR 噪声），需 vision/人工精修")
    if field == "contract":
        digits = re.sub(r"\D", "", value)
        return (len(digits) >= 16, f"合同号通常 16-20 位数字（NLMK 样例 18 位），实际 {len(digits)} 位")
    if field == "spec":
        digits = re.sub(r"\D", "", value)
        return (len(digits) == 10, f"规格书号应为 10 位数字，实际 {len(digits)} 位")
    if field == "amount":
        v = normalize_amount(value)
        return (v is not None, f"金额无法解析为数字: {value!r}")
    if field == "date":
        return (bool(re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}", value)), f"日期格式异常: {value!r}")
    return (True, "")


def extract_fields(full_text):
    """从全文提取字段。返回 (fields, sources, verify_list)"""
    fields, sources, verify = {}, {}, []
    for name, pat, fallback, fmt, desc in FIELD_PATTERNS:
        m = re.search(pat, full_text, re.IGNORECASE)
        used_fb = False
        if not m and fallback:
            m = re.search(fallback, full_text, re.IGNORECASE)
            used_fb = True
        if not m:
            verify.append(f"[缺失] {desc} ({name}) — 未在文本中找到锚点")
            continue
        value = m.group(1).strip()
        page_m = re.search(r"====\s*第(\d+)页\s*====", full_text[:m.start()])
        page = int(page_m.group(1)) if page_m else 1
        ok, note = True, ""
        if fmt:
            ok, note = check_fmt(fmt, value)
        fields[name] = value
        sources[name] = page
        if fmt == "low":
            verify.append(f"[低置信度] {desc} ({name}) 整行={value!r} 页码={page} — OCR 噪声大，请 vision/人工精修")
        elif not ok:
            verify.append(f"[格式可疑] {desc} ({name}) 值={value!r} — {note}")
        elif name in ("contract_no", "spec_no", "total", "delivery_date", "contract_date"):
            src = "兜底模式" if used_fb else "主模式"
            verify.append(f"[需核对] {desc} ({name}) 值={value!r} 页码={page} (来源={src}) — 长数字 OCR 易错，请 vision 交叉校验")
    return fields, sources, verify


def ocr_scan_pages(pngs_by_page, out_dir, device="gpu:0"):
    """扫描页批量 OCR：一次调用 PP-OCRv5 处理整个页面目录。

    pngs_by_page: {页码: png路径}。返回 {页码: 文本}。
    """
    if not pngs_by_page:
        return {}
    tmp = tempfile.mkdtemp(prefix="ocr_pdf_")
    try:
        # 把页面渲染图拷到临时目录（ocr_ppocrv5.py 按文件名排序处理）
        for page_no, png in pngs_by_page.items():
            dst = os.path.join(tmp, f"page_{page_no:02d}.png")
            import shutil
            shutil.copy(png, dst)

        cmd = [PPOCR_PY, PPOCR_SCRIPT, tmp, "--out", os.path.join(tmp, "out"),
               "--lang", "ru", "--device", device]
        r = subprocess.run(cmd, capture_output=True, timeout=1800)
        full = os.path.join(tmp, "out", "ocr_full.txt")
        if not os.path.exists(full):
            err = r.stderr.decode("utf-8", errors="replace")[-800:]
            return {p: f"[PP-OCRv5 失败]\n{err}" for p in pngs_by_page}

        text = open(full, encoding="utf-8").read()
        # 按 "===== page_NN.png（...）=====" 标记切分回各页
        result = {}
        parts = re.split(r"=====\s*(page_\d+\.png)\s*（[^）]*）=====", text)
        # parts = [前置, name1, 内容1, name2, 内容2, ...]
        for i in range(1, len(parts), 2):
            name = parts[i]
            body = parts[i + 1] if i + 1 < len(parts) else ""
            m = re.match(r"page_(\d+)\.png", name)
            if m:
                result[int(m.group(1))] = body.strip()
        # 补全缺失页（渲染了但 OCR 脚本没输出）
        for page_no in pngs_by_page:
            if page_no not in result:
                result[page_no] = "[OCR 无输出]"
        return result
    except Exception as e:
        return {p: f"[PP-OCRv5 异常: {e}]" for p in pngs_by_page}
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="合同 PDF 多页 OCR + 字段提取")
    ap.add_argument("pdf", help="合同 PDF 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--device", default="gpu:0", help="PP-OCRv5 推理设备")
    args = ap.parse_args()

    import fitz  # pymupdf
    pages_dir = os.path.join(args.out, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    doc = fitz.open(args.pdf)
    n_pages = doc.page_count
    print(f"[PDF] {args.pdf} — 共 {n_pages} 页")

    # 第一遍：文字页直取，扫描页渲染
    page_text = {}       # 页码 -> 文本
    scan_pngs = {}       # 页码 -> png路径（扫描页）
    for i in range(n_pages):
        page = doc[i]
        txt = page.get_text().strip()
        if txt:
            page_text[i + 1] = txt
            print(f"[页 {i+1}] 文字型，直接提取 ({len(txt)} 字符)")
        else:
            pix = page.get_pixmap(dpi=args.dpi)
            png = os.path.join(pages_dir, f"page_{i+1:02d}.png")
            pix.save(png)
            scan_pngs[i + 1] = png
    doc.close()

    # 第二遍：扫描页统一走 PP-OCRv5
    if scan_pngs:
        print(f"[OCR] {len(scan_pngs)} 张扫描页 → PP-OCRv5 (device={args.device}) ...")
        ocr_result = ocr_scan_pages(scan_pngs, args.out, args.device)
        for page_no, txt in ocr_result.items():
            page_text[page_no] = txt
            print(f"[页 {page_no}] 扫描型 → PP-OCRv5 ({len(txt)} 字符)")

    # 组装全文（按页码排序）
    full_parts = []
    for page_no in sorted(page_text):
        kind = "文字型" if page_no not in scan_pngs else "扫描型"
        full_parts.append(f"==== 第{page_no}页（{kind}）====\n{page_text[page_no]}")
    full_text = "\n\n".join(full_parts)

    text_path = os.path.join(args.out, "ocr_full.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"[输出] 全文 → {text_path}")

    fields, sources, verify = extract_fields(full_text)

    fields_path = os.path.join(args.out, "fields.json")
    with open(fields_path, "w", encoding="utf-8") as f:
        json.dump({"fields": fields, "sources": sources,
                   "n_pages": n_pages, "ocr_pages": sorted(scan_pngs)},
                  f, ensure_ascii=False, indent=2)
    print(f"[输出] 字段 → {fields_path}")

    verify_path = os.path.join(args.out, "verify_list.txt")
    with open(verify_path, "w", encoding="utf-8") as f:
        f.write("== 待核对清单（人工 / vision_analyze 逐页核对）==\n")
        for v in verify:
            f.write(v + "\n")
        if scan_pngs:
            f.write("\n== 扫描页渲染图（vision 核对用）==\n")
            for p in sorted(scan_pngs):
                f.write(f"第{p}页: {scan_pngs[p]}\n")
    print(f"[输出] 待核清单 → {verify_path}")

    print("\n==== 提取字段汇总 ====")
    for k in ("contract_no", "spec_no", "tender", "total", "currency",
              "delivery", "payment", "delivery_date", "contract_date",
              "supplier", "buyer", "manufacturer"):
        v = fields.get(k)
        if v:
            print(f"  {k}: {v}")
    print(f"\n[完成] 扫描页 {len(scan_pngs)} 张，待核条目 {len(verify)} 条 → 请按 verify_list.txt 用 vision 交叉校验")


if __name__ == "__main__":
    main()

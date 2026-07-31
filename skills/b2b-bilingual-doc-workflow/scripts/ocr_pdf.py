#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_pdf.py — 合同/规格书 PDF → 全文 + 关键字段提取 + 待核清单

覆盖 SKILL A1-A2 全流程：
  1. 遍历【所有页】：get_text() 非空=文字页直取；空=300dpi 渲染 PNG + Tesseract OCR
  2. 语言包自探测：rus / ukr / eng 缺失自动降级并明示
  3. 关键字段锚点正则提取（俄/英），主模式 + 特征数字兜底，
     俄语逗号小数点、千分位空格归一化
  4. 数字格式校验（合同号 19 位、规格书号 10 位等），不合法进待核清单
  5. 输出 verify_list.txt —— 供 vision 交叉校验 / 人工校对的关键字段清单

用法:
  python ocr_pdf.py <合同.pdf> --out <输出目录> [--langs rus+eng] [--dpi 300]

输出:
  <out>/ocr_full.txt      逐页全文（含页码标记）
  <out>/pages/page_01.png 扫描页渲染图（vision 核对用）
  <out>/fields.json       提取字段 + 置信度 + 来源页
  <out>/verify_list.txt   待核对清单（人工 / vision 交叉校验）
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\Tesseract-OCR\tessdata"
DEFAULT_LANGS = "rus+eng"

# ---------- 关键字段锚点（俄英双语） ----------
# 双栏扫描件 OCR 噪声大（"К логопору" 这类变体），原则：
#   1) 宽松锚点 + 特征数字兜底（19 位合同号 / 10 位规格书号本身即强特征）
#   2) 金额/日期/条款类提取"就近数字"，不要求锚点后紧跟
#   3) 供应商/买家 OCR 不可靠 → 整行提取 + 低置信度标记，留待 vision/人工
# (字段名, 主模式, 兜底模式, 校验函数, 说明)
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


def available_langs(requested):
    """探测 tessdata 中实际可用的语言包，自动降级"""
    have = {f[:-len(".traineddata")] for f in os.listdir(TESSDATA) if f.endswith(".traineddata")}
    want = [l.strip() for l in requested.split("+") if l.strip()]
    usable = [l for l in want if l in have]
    missing = [l for l in want if l not in have]
    if not usable:
        usable = ["eng"] if "eng" in have else []
    return usable, missing


def ocr_png(png_path, langs):
    """单页 OCR。中文路径必须 --tessdata-dir（TESSDATA_PREFIX 中文用户名乱码）"""
    cmd = [TESSERACT, png_path, "stdout", "-l", "+".join(langs), "--psm", "3",
           "--tessdata-dir", TESSDATA]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        return r.stdout.decode("utf-8", errors="replace")
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"[OCR 失败: {e}]\n"


def main():
    ap = argparse.ArgumentParser(description="合同 PDF 多页 OCR + 字段提取")
    ap.add_argument("pdf", help="合同 PDF 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--langs", default=DEFAULT_LANGS, help="OCR 语言，+ 连接，默认 rus+eng")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    import fitz  # pymupdf
    os.makedirs(os.path.join(args.out, "pages"), exist_ok=True)

    usable, missing = available_langs(args.langs)
    lang_note = f"可用语言: {'+'.join(usable)}"
    if missing:
        lang_note += f" | 缺失: {','.join(missing)}（已降级，俄语将转写为拉丁字母，需人工校对）"
    print(f"[语言] {lang_note}")

    doc = fitz.open(args.pdf)
    n_pages = doc.page_count
    print(f"[PDF] {args.pdf} — 共 {n_pages} 页")

    full_text, ocr_pages = [], []
    for i in range(n_pages):
        page = doc[i]
        txt = page.get_text().strip()
        if txt:
            full_text.append(f"==== 第{i+1}页（文字型）====\n{txt}")
            print(f"[页 {i+1}] 文字型，直接提取 ({len(txt)} 字符)")
        else:
            pix = page.get_pixmap(dpi=args.dpi)
            png = os.path.join(args.out, "pages", f"page_{i+1:02d}.png")
            pix.save(png)
            ocr_pages.append((i + 1, png))
            t = ocr_png(png, usable)
            full_text.append(f"==== 第{i+1}页（扫描型）====\n{t}")
            print(f"[页 {i+1}] 扫描型 → 300dpi 渲染 + OCR ({len(t)} 字符)")
    doc.close()

    text_path = os.path.join(args.out, "ocr_full.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))
    print(f"[输出] 全文 → {text_path}")

    fields, sources, verify = extract_fields("\n\n".join(full_text))

    fields_path = os.path.join(args.out, "fields.json")
    with open(fields_path, "w", encoding="utf-8") as f:
        json.dump({"fields": fields, "sources": sources, "lang_note": lang_note,
                   "n_pages": n_pages, "ocr_pages": [p for _, p in ocr_pages]},
                  f, ensure_ascii=False, indent=2)
    print(f"[输出] 字段 → {fields_path}")

    verify_path = os.path.join(args.out, "verify_list.txt")
    with open(verify_path, "w", encoding="utf-8") as f:
        f.write("== 待核对清单（人工 / vision_analyze 逐页核对）==\n")
        for v in verify:
            f.write(v + "\n")
        if ocr_pages:
            f.write("\n== 扫描页渲染图（vision 核对用）==\n")
            for p, png in ocr_pages:
                f.write(f"第{p}页: {png}\n")
    print(f"[输出] 待核清单 → {verify_path}")

    print("\n==== 提取字段汇总 ====")
    for k in ("contract_no", "spec_no", "tender", "total", "currency",
              "delivery", "payment", "delivery_date", "contract_date",
              "supplier", "buyer", "manufacturer"):
        v = fields.get(k)
        if v:
            print(f"  {k}: {v}")
    print(f"\n[完成] 扫描页 {len(ocr_pages)} 张，待核条目 {len(verify)} 条 → 请按 verify_list.txt 用 vision 交叉校验")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_fields.py — 从 OCR 全文提取合同关键字段（独立工具）

用法:
  python extract_fields.py <ocr_full.txt 或任意文本> [--out fields.json]

输出:
  fields.json: {"fields": {...}, "sources": {...}, "verify": [...]}
  字段: contract_no / spec_no / tender / total / currency / delivery /
        payment / delivery_date / contract_date / supplier / buyer / manufacturer

与 ocr_pdf.py 内的锚点表一致；本脚本用于对已生成的 ocr_full.txt 重复提取/调参。
"""
import argparse
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (字段名, 主模式, 兜底模式, 校验函数, 说明) — 与 ocr_pdf.py 保持一致
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
    s = s.strip().replace("\u00a0", " ")
    s = re.sub(r"\s+", "", s)
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def check_fmt(field, value):
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
    fields, sources, verify = {}, {}, []
    for name, pat, fallback, fmt, desc in FIELD_PATTERNS:
        m = re.search(pat, full_text, re.IGNORECASE)
        used_fb = False
        if not m and fallback:
            m = re.search(fallback, full_text, re.IGNORECASE)
            used_fb = True
        if not m:
            verify.append(f"[缺失] {desc} ({name}) — 未找到锚点")
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
            verify.append(f"[低置信度] {desc} ({name}) 整行={value!r} 页码={page}")
        elif not ok:
            verify.append(f"[格式可疑] {desc} ({name}) 值={value!r} — {note}")
        elif name in ("contract_no", "spec_no", "total", "delivery_date", "contract_date"):
            src = "兜底模式" if used_fb else "主模式"
            verify.append(f"[需核对] {desc} ({name}) 值={value!r} 页码={page} (来源={src})")
    return fields, sources, verify


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="OCR 全文文件")
    ap.add_argument("--out", default="fields.json")
    args = ap.parse_args()
    with open(args.text, encoding="utf-8") as f:
        text = f.read()
    fields, sources, verify = extract_fields(text)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"fields": fields, "sources": sources, "verify": verify},
                  f, ensure_ascii=False, indent=2)
    print("== 字段 ==")
    for k, v in fields.items():
        print(f"  {k}: {v}")
    print(f"== 待核对 {len(verify)} 条 ==")
    for v in verify:
        print(f"  {v}")
    print(f"[OK] → {args.out}")


if __name__ == "__main__":
    main()

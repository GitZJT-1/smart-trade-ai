#!/usr/bin/env python3
"""
doc_writers.py — 从 order.json 生成单据（套 NLMK 俄英双语模板）

生成三份（版式按 b2b-bilingual-doc-workflow 记录的 NLMK 26BY008 真实结构）：
  invoice  → 发票 docx（俄英双语，即商业发票 CI；形式发票 PI 同版式+有效期+标题）
  packing  → 箱单 docx（13 段 + 4行×7列表格）
  customs  → 报关单 xls（中国海关标准版式，近似——真实报关建议套 .xls 模板）

用法：
  python doc_writers.py all <order.json> [--config companies.yaml] [--outdir 目录]
  python doc_writers.py invoice <order.json> [--config ...] [--out ...]
  python doc_writers.py packing <order.json> ...
  python doc_writers.py customs  <order.json> ...

依赖：python-docx、xlwt、pyyaml（可选）、标准库。
"""
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import xlwt

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ── 数据加载 ──────────────────────────────────────────────────────


def load_order(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_config(path):
    if not path or not HAS_YAML:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_seller(order, config):
    sid = order.get("seller_id")
    if sid and config.get("sellers"):
        return config["sellers"].get(sid, {})
    return {}


def resolve_buyer(order, config):
    bid = order.get("buyer_id")
    if bid and config.get("buyers"):
        return config["buyers"].get(bid, {})
    return {}


def currency_symbol(cur):
    return {"CNY": "￥", "USD": "$", "EUR": "€", "RUB": "₽"}.get((cur or "USD").upper(), (cur or "USD"))


# ── 发票 / 商业发票（俄英双语 docx）───────────────────────────────


def generate_invoice(order, config, out_path):
    seller = resolve_seller(order, config)
    buyer = resolve_buyer(order, config)
    terms = order.get("terms", {}) or {}
    cur = terms.get("currency", "USD")
    sym = currency_symbol(cur)

    doc = Document()
    table = doc.add_table(rows=0, cols=5)
    table.style = "Table Grid"

    def add_merged(text, bold=False, size=10):
        row = table.add_row().cells
        merged = row[0]
        for c in row[1:]:
            merged = merged.merge(c)
        p = merged.paragraphs[0]
        r = p.add_run(text)
        r.bold = bold
        r.font.size = Pt(size)
        return merged

    # R0 供应商
    add_merged(f"Suppler/ Поставщик/ {seller.get('name_en', '')}", bold=True)
    if seller.get("address"):
        add_merged(f"{seller.get('address')}", size=9)
    # R2 买家（俄+英）
    buyer_line = buyer.get("name_ru", "") or buyer.get("name_en", "")
    if buyer.get("name_en") and buyer.get("name_ru"):
        buyer_line = f"{buyer.get('name_ru')} / {buyer.get('name_en')}"
    add_merged(f"Buyer/ Покупатель/ {buyer_line}", bold=True)
    if buyer.get("address"):
        add_merged(f"{buyer.get('address')}", size=9)
    # R3 交货条款 + 原产国
    dest = terms.get("destination", "") or terms.get("port_of_destination", "")
    add_merged(f"Terms of delivery /Условия поставки/ {terms.get('incoterm', '')} {dest}   |   "
               f"Country of origin: China /Страна происхождения: Китай", size=9)
    # R4 付款条款
    add_merged(f"Terms of Payment: {terms.get('payment', 'T/T')} /Условия оплаты: Т/Т", size=9)

    # 表头行（5 列）
    headers = ["Marks & numbers//\nНаименование и номера",
               "Number & kind of packages, description of goods//\nКоличество и вид упаковок, описание товара",
               "Quantity//\nКоличество",
               "Unit price//\nЦена",
               "Amount//\nСумма"]
    hrow = table.add_row().cells
    for i, h in enumerate(headers):
        hrow[i].text = ""
        r = hrow[i].paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(8)

    # 商品行
    for it in order.get("items", []):
        desc = it.get("description_ru") or it.get("description_en") or it.get("description_cn")
        if it.get("standard"):
            desc = f"{desc} {it.get('standard')}"
        cells = table.add_row().cells
        cells[0].text = it.get("hs_code", "")
        cells[1].text = desc
        cells[2].text = f"{it.get('quantity')} {it.get('unit', '')}".strip()
        up = it.get("unit_price")
        am = it.get("amount")
        cells[3].text = f"{sym}{up:,.2f}" if up is not None else ""
        cells[4].text = f"{sym}{am:,.2f}" if am is not None else ""

    # TOTAL 行
    total = sum(it.get("amount") or 0 for it in order.get("items", []))
    trow = table.add_row().cells
    t0 = trow[0]
    for c in trow[1:4]:
        t0 = t0.merge(c)
    t0.text = ""
    r = t0.paragraphs[0].add_run(f"TOTAL /ВСЕГО: {sym}{total:,.2f}")
    r.bold = True
    r.font.size = Pt(10)
    trow[4].text = f"{sym}{total:,.2f}"

    # 落款 + 日期
    add_merged(seller.get("name_en", ""), bold=True)
    add_merged(order.get("date", ""), size=9)

    doc.save(out_path)
    return out_path


# ── 箱单（俄英双语 docx）──────────────────────────────────────────


def generate_packing_list(order, config, out_path):
    seller = resolve_seller(order, config)
    buyer = resolve_buyer(order, config)
    terms = order.get("terms", {}) or {}
    dest = terms.get("destination", "") or terms.get("port_of_destination", "")

    doc = Document()
    buyer_ru = buyer.get("name_ru", "") or buyer.get("name_en", "")
    buyer_en = buyer.get("name_en", "")

    paragraphs = [
        seller.get("name_en", ""),
        seller.get("address", ""),
        "Packing List",
        "Упаковочный лист",
        "TO MESSRS/ К ГОСПОДАМ:",
        f"{buyer_ru} / {buyer_en}" if buyer_en and buyer_ru != buyer_en else buyer_ru,
        buyer.get("address", ""),
        f"Contract/ Договор No. {order.get('contract_no', '')}    Date /Дата: {order.get('date', '')}",
        f"Specification /Спецификация No. {order.get('spec_no', '')}",
        f"Terms of delivery:  {terms.get('incoterm', '')} {dest}    Country of origin:  China",
        f"Условия поставки: {terms.get('incoterm', '')} {dest}    Страна происхождения: Китай",
        seller.get("name_en", ""),
        order.get("date", ""),
    ]
    for txt in paragraphs:
        p = doc.add_paragraph()
        r = p.add_run(txt if txt else "")
        r.font.size = Pt(10)

    table = doc.add_table(rows=1, cols=7)
    table.style = "Table Grid"
    headers = ["Description of goods//Описание товаров", "Qty//Кол-во", "Unit//Единица измерения",
               "Package//Упаковка", "N.W.(kg)//Вес нетто", "G.W.(kg)//Вес брутто", "Volume/m3//Объём/м3"]
    for i, h in enumerate(headers):
        r = table.rows[0].cells[i].paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(8)

    items = order.get("items", [])
    for it in items:
        desc = it.get("description_ru") or it.get("description_en") or it.get("description_cn")
        qty = it.get("quantity", 0)
        unit = it.get("unit", "")
        nw = it.get("total_weight_kg") or it.get("weight_kg_per_unit")
        gw = round((nw or 0) * 1.05, 2) if nw else ""
        cells = table.add_row().cells
        for j, v in enumerate([desc, qty, unit, "", nw or "", gw or "", ""]):
            cells[j].text = str(v)

    # Total 行
    total_qty = sum(it.get("quantity", 0) for it in items)
    total_nw = sum(it.get("total_weight_kg") or it.get("weight_kg_per_unit") or 0 for it in items)
    cells = table.add_row().cells
    for j, v in enumerate(["Total//Всего", total_qty, "", "", round(total_nw, 2) or "", round(total_nw * 1.05, 2) if total_nw else "", ""]):
        cells[j].text = str(v)

    doc.save(out_path)
    return out_path


# ── 报关单（中国海关标准版式 xls，近似）────────────────────────────


def generate_customs(order, config, out_path):
    seller = resolve_seller(order, config)
    buyer = resolve_buyer(order, config)
    terms = order.get("terms", {}) or {}
    items = order.get("items", [])

    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("出口报关单", cell_overwrite_ok=True)
    title = xlwt.easyxf("font: bold on, height 280; align: horiz center, vert centre;")
    cell = xlwt.easyxf("font: height 200; align: horiz left, vert centre, wrap on;"
                       "borders: left thin, right thin, top thin, bottom thin;")
    lbl = xlwt.easyxf("font: height 200, bold on; align: horiz left, vert centre;"
                      "borders: left thin, right thin, top thin, bottom thin;")

    def w(r, c, v, style=cell):
        ws.write(r, c, v, style)

    w(0, 0, "中华人民共和国海关出口货物报关单", title)
    w(2, 0, "预录入编号", lbl); w(2, 2, "海关编号", lbl)
    w(4, 0, "收发货人", lbl); w(5, 0, f"{seller.get('name_cn', '')}{seller.get('uscc', '')}")
    w(4, 2, "出口口岸", lbl); w(4, 4, "出口日期", lbl); w(4, 6, "申报日期", lbl)
    w(6, 0, "生产销售单位", lbl); w(7, 0, f"{seller.get('name_cn', '')}{seller.get('uscc', '')}")
    w(10, 0, "贸易国(地区)", lbl); w(10, 2, "俄罗斯")
    w(11, 0, "运抵国(地区)", lbl); w(11, 2, "俄罗斯")
    w(12, 0, "成交方式", lbl); w(12, 2, terms.get("incoterm", "DAP"))
    w(14, 0, "合同协议号", lbl)
    w(15, 0, f"{order.get('contract_no', '')}/{order.get('spec_no', '')}")
    w(14, 4, "件数", lbl); w(14, 6, "毛重(kg)", lbl); w(14, 8, "净重(kg)", lbl)

    total_qty = sum(it.get("quantity", 0) for it in items)
    total_nw = sum(it.get("total_weight_kg") or 0 for it in items)
    w(15, 4, int(total_qty)); w(15, 6, round(total_nw * 1.05, 2)); w(15, 8, round(total_nw, 2))

    # 商品表头
    heads = ["项号", "商品编号", "商品名称、规格型号", "数量及单位", "最终目的国(地区)", "单价", "总价", "币制", "征免"]
    for c, h in enumerate(heads):
        w(20, c, h, lbl)

    r = 21
    for i, it in enumerate(items, 1):
        desc = it.get("description_cn") or it.get("description_en")
        w(r, 0, i); w(r, 1, it.get("hs_code", "")); w(r, 2, desc)
        w(r, 3, f"{it.get('quantity')}{it.get('unit', '')}")
        w(r, 4, "俄罗斯")
        w(r, 5, it.get("unit_price") or "")
        w(r, 6, it.get("amount") or "")
        w(r, 7, {"CNY": "人民币", "USD": "美元"}.get((terms.get("currency") or "USD").upper(), "美元"))
        w(r, 8, "照章")
        r += 1
    w(r, 0, "申报要素：以实际申报为准（品牌/材质/规格/用途等按货物实际情况申报）")

    wb.save(out_path)
    return out_path


# ── CLI ───────────────────────────────────────────────────────────


def main(argv):
    ap = argparse.ArgumentParser(description="从 order.json 生成单据（套 NLMK 俄英双语模板）")
    ap.add_argument("mode", choices=["all", "invoice", "packing", "customs"])
    ap.add_argument("order", help="order.json 路径")
    ap.add_argument("--config", default=None, help="companies.yaml 路径")
    ap.add_argument("--outdir", default=None, help="输出目录（默认 order.json 同目录）")
    ap.add_argument("--out", default=None, help="单文件输出路径")
    args = ap.parse_args(argv)

    order = load_order(args.order)
    config = load_config(args.config)
    outdir = Path(args.outdir) if args.outdir else Path(args.order).parent
    outdir.mkdir(parents=True, exist_ok=True)
    order_no = order.get("order_no", Path(args.order).stem)

    def out(ext):
        return str(Path(args.out) if args.out else outdir / f"{order_no}_{ext}")

    modes = ["invoice", "packing", "customs"] if args.mode == "all" else [args.mode]
    for m in modes:
        if m == "invoice":
            p = generate_invoice(order, config, out("invoice.docx"))
        elif m == "packing":
            p = generate_packing_list(order, config, out("packing.docx"))
        else:
            p = generate_customs(order, config, out("customs.xls"))
        print(f"✅ 已生成 {m}: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

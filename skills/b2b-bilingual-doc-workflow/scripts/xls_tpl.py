#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xls_tpl.py — .xls 旧格式模板读写工具库（import 用）+ CLI

铁律: .xls 旧格式 xlrd 只能读，写/改必须 xlutils.copy 保留原格式（openpyxl 不支持 .xls）。

用法（import）:
    import xls_tpl
    wb = xls_tpl.load_template("报关单模板.xls")     # rb，formatting_info=True
    wbw = xls_tpl.copy_rb(wb)                          # 可写副本
    xls_tpl.write_cells(wbw, 0, {(r, c): value, ...})  # sheet0 批量写
    xls_tpl.save(wbw, "out.xls")

用法（CLI）:
    python xls_tpl.py dump <模板.xls> [--sheet 0]   # 导出非空单元格坐标 → JSON
    python xls_tpl.py fill <模板.xls> <out.xls> <json>  # 按 {"sheet":0,"cells":{"r_c":value}}
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_template(path):
    """打开 xls 模板，保留格式信息。返回 xlrd book (rb)。"""
    import xlrd
    return xlrd.open_workbook(path, formatting_info=True)


def copy_rb(rb):
    """rb → 可写 wb（xlutils.copy）。"""
    import xlutils.copy
    return xlutils.copy.copy(rb)


def xf_to_style(rb, xf_index):
    """把 xlrd 的 XF 索引转成 xlwt XFStyle（保留字体/对齐/边框/数字格式）。

    关键：xlutils.copy 的 write 若不传 style 会用默认样式（Arial/左对齐/无边框）
    覆盖原单元格格式 —— 导致报关单"排版字体混乱"。写入前必须取原 XF 构造 style。
    """
    import xlwt
    xf = rb.xf_list[xf_index]

    style = xlwt.XFStyle()

    # 字体
    fnt = rb.font_list[xf.font_index]
    f = xlwt.Font()
    f.name = fnt.name
    f.height = fnt.height
    f.bold = fnt.weight >= 700
    f.italic = bool(fnt.italic)
    f.underline = fnt.underline_type
    f.struck_out = bool(fnt.struck_out)
    f.colour_index = fnt.colour_index
    f.escapement = fnt.escapement
    f.family = fnt.family
    f.charset = fnt.character_set
    style.font = f

    # 对齐（xlrd/xlwt 常量兼容：horz 0=general,1=left,2=center,3=right；vert 0=top,1=center,2=bottom）
    al = xf.alignment
    a = xlwt.Alignment()
    a.horz = al.hor_align
    a.vert = al.vert_align
    a.wrap = 1 if al.text_wrapped else 0
    a.rota = al.rotation
    a.indent = al.indent_level
    style.alignment = a

    # 边框
    bd = xf.border
    b = xlwt.Borders()
    b.left = bd.left_line_style
    b.right = bd.right_line_style
    b.top = bd.top_line_style
    b.bottom = bd.bottom_line_style
    b.left_colour = bd.left_colour_index
    b.right_colour = bd.right_colour_index
    b.top_colour = bd.top_colour_index
    b.bottom_colour = bd.bottom_colour_index
    style.borders = b

    # 数字格式（金额 0.00 等）
    try:
        fmt_key = xf.format_key
        fmt_str = rb.format_map.get(fmt_key).format_str if fmt_key in rb.format_map else None
        if fmt_str:
            style.num_format_str = fmt_str
    except Exception:
        pass

    # 背景填充
    try:
        if xf.background.pattern_colour_index or xf.background.fill_pattern:
            pat = xlwt.Pattern()
            pat.pattern = xf.background.fill_pattern
            pat.pattern_fore_colour = xf.background.pattern_colour_index
            pat.pattern_back_colour = xf.background.background_colour_index
            style.pattern = pat
    except Exception:
        pass

    return style


def write_cells(wbw, sheet_idx, cells, rb=None):
    """cells: {(row, col): value} 批量写入。row/col 0 基。

    rb: 源 xlrd book（load_template 的返回值）。传入后每个单元格写入时
    保留原格式（字体/对齐/边框/数字格式），避免默认样式覆盖。
    """
    ws = wbw.get_sheet(sheet_idx)
    src = rb.sheet_by_index(sheet_idx) if rb is not None else None
    for (r, c), v in cells.items():
        style = None
        if src is not None:
            style = xf_to_style(rb, src.cell_xf_index(r, c))
        ws.write(r, c, v, style)
    return ws


def save(wbw, out_path):
    wbw.save(out_path)


def dump_cells(path, sheet_idx=0):
    """遍历 sheet 全部单元格，返回 {sheet_idx: {row: {col: value}}}（非空）。"""
    import xlrd
    rb = xlrd.open_workbook(path, formatting_info=True)
    result = {}
    for si in range(rb.nsheets):
        ws = rb.sheet_by_index(si)
        cells = {}
        for r in range(ws.nrows):
            for c in range(ws.ncols):
                v = ws.cell_value(r, c)
                if v not in ("", None):
                    cells.setdefault(r, {})[c] = v
        if cells:
            result[si] = cells
    return result


def dump_cells_human(path, sheet_idx=0):
    """人类可读 dump：R{r}C{c}: {value}，用于模板结构档案。"""
    d = dump_cells(path, sheet_idx)
    lines = []
    for si, rows in d.items():
        lines.append(f"Sheet {si}（{len(rows)} 行非空）:")
        for r in sorted(rows):
            for c in sorted(rows[r]):
                lines.append(f"  R{r}C{c}: {rows[r][c]!r}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="xls 模板读写工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_dump = sub.add_parser("dump", help="导出非空单元格坐标")
    p_dump.add_argument("xls")
    p_dump.add_argument("--sheet", type=int, default=0)
    p_dump.add_argument("--json", action="store_true", help="JSON 输出")

    p_fill = sub.add_parser("fill", help="按坐标写入并另存")
    p_fill.add_argument("tpl", help="模板 xls")
    p_fill.add_argument("out", help="输出 xls")
    p_fill.add_argument("json", help='写值 JSON: {"sheet":0,"cells":{"5_0":"值","5_1":123}}')

    args = ap.parse_args()
    if args.cmd == "dump":
        if args.json:
            print(json.dumps(dump_cells(args.xls, args.sheet), ensure_ascii=False, indent=2))
        else:
            print(dump_cells_human(args.xls, args.sheet))
    elif args.cmd == "fill":
        spec = json.load(open(args.json, encoding="utf-8"))
        rb = load_template(args.tpl)
        wbw = copy_rb(rb)
        cells = {(int(k.split("_")[0]), int(k.split("_")[1])): v
                 for k, v in spec.get("cells", {}).items()}
        write_cells(wbw, spec.get("sheet", 0), cells)
        save(wbw, args.out)
        print(f"[OK] {args.out} 已写入 {len(cells)} 个单元格")


if __name__ == "__main__":
    main()

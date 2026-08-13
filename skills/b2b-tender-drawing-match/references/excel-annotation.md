# Excel 清单标注 — 已匹配项高亮

匹配+归档完成后，用户通常需要把原始 `.xls` 清单中已匹配的行用彩色底色标注出来，方便人工快速识别哪些项已有图纸、哪些待补。

## ⚠️ 核心陷阱：.xls 格式的 COM 写入不可靠

**通过 Excel COM 设置 `Interior.Color/ColorIndex` 后调用 `wb.Save()`，即时验证（同一 session 内回读）显示正确，但关闭 Excel 后重新打开 → 格式全部丢失。**

| 方案 | 读格式 | 着色 | 持久化 | 结论 |
|:-----|:------:|:----:|:------:|:-----|
| xlrd + xlutils + xlwt | ✓ | 部分 | ✗ | 不可靠 |
| COM 直接写 .xls | ✗（读格式不准） | ✓ | **✗ 保存后丢失** | 不可靠 |
| **COM 读格式 → COM 转 xlsx → openpyxl 着色** | ✓ | ✓ | **✓** | **推荐** |

## 推荐方案：COM 探色 → 转 xlsx → openpyxl 着色

### 步骤 1：用 COM 读取用户示例行的实际颜色

xlrd 的 `formatting_info=True` 对某些 Excel 版本的格式读取不完整（行间无差异时看不出颜色）。用 COM 直接读：

```python
import win32com.client

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
wb = excel.Workbooks.Open(full_path)
ws = wb.Sheets("Sheet2")

# 读示例行（用户手工标注的那一行）
example_row = 7  # Excel 1-indexed
for c in [1, 2]:  # Col A=1, B=2
    cell = ws.Cells(example_row, c)
    print(f"Color={cell.Interior.Color}, ColorIndex={cell.Interior.ColorIndex}, Bold={cell.Font.Bold}")

wb.Close(False)
excel.Quit()
```

常见标注色：`ColorIndex=43` → RGB `#92D050`（浅草绿），`ColorIndex=35` → 浅绿，`ColorIndex=50` → `RGB(153,204,0)`。

### 步骤 2：COM 转换 .xls → .xlsx

```python
excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

wb = excel.Workbooks.Open(xls_path)
wb.SaveAs(xlsx_path, FileFormat=51)  # 51 = xlOpenXMLWorkbook
wb.Close(False)
excel.Quit()
```

### 步骤 3：openpyxl 着色 + 粗体

```python
import openpyxl
from copy import copy

wb = openpyxl.load_workbook(xlsx_path)
ws = wb['Sheet2']

# 复制示例行的 fill 和 font
example_fill = copy(ws.cell(row=7, column=1).fill)  # #92D050 solid
example_font = copy(ws.cell(row=7, column=1).font)  # bold=True

# 对每个已匹配项着色 A/B 列
for item_no in matched_nos:  # set of int
    r = item_no + 5  # Sheet2: row 6 = item #1
    for c in [1, 2]:
        cell = ws.cell(row=r, column=c)
        cell.fill = copy(example_fill)
        cell.font = copy(example_font)

wb.save(xlsx_path)
```

### 步骤 4：验证

```python
wb = openpyxl.load_workbook(xlsx_path)
ws = wb['Sheet2']
target_rgb = 'FF92D050'

for item_no in matched_nos:
    r = item_no + 5
    fill_rgb = ws.cell(row=r, column=1).fill.fgColor.rgb
    bold = ws.cell(row=r, column=1).font.bold
    assert fill_rgb == target_rgb and bold, f"Item {item_no}: fill={fill_rgb} bold={bold}"
```

## 行号映射

| 清单 № | Sheet2 Excel 行（1-indexed） | openpyxl row |
|:------:|:---------------------------:|:----------:|
| 1 | 6 | 6 |
| 2 | 7 | 7 |
| N | N + 5 | N + 5 |
| 109 | 114 | 114 |

## 已匹配项来源

1. **`归档/` 目录下的子文件夹名**（数字即清单 №）— 最权威
2. **`_rename_plan.json`** — 包含所有重命名计划的 unique `no` 值
3. 二者取并集：`matched = set(folder_nums) | set(plan_nums)`

## 依赖

- `pywin32`（win32com）— 读格式 + 转 xlsx
- `openpyxl` — 着色写入
- 不需要 xlutils / xlwt（已被证实不可靠）

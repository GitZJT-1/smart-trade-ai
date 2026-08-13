# DOCX 技术手册生成模式（python-docx 直用）

2026-08-10 实战验证：为其他 Agent 生成可复刻的匹配引擎技术手册。以下为经过验证的 python-docx 模式。

## 为什么用 python-docx 直用而非 microsoft-word 包装器
`microsoft-word` skill 已声明 deprecated，指向 `docx` skill。直接用 `from docx import Document` 更可靠。

## 品牌配色
- 深蓝标题：`RGBColor(0x0B, 0x2A, 0x4A)` (#0B2A4A)
- 金色强调：`RGBColor(0xD4, 0xA8, 0x53)` (#D4A853)
- 正文：默认 Calibri 11pt

## 表格模式
```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_cell_shading(cell, color):
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color)
    cell._tc.get_or_add_tcPr().append(shading_elm)

# 表头：深蓝底 + 白字 + 粗体 9pt
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = h
    for run in cell.paragraphs[0].runs:
        run.font.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    set_cell_shading(cell, '0B2A4A')

# 数据行：交替底色 #E8EDF2
if r % 2 == 1:
    set_cell_shading(cell, 'E8EDF2')
```

## 代码块模式
```python
def add_code_block(doc, code_text):
    for line in code_text.strip().split('\n'):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(1)
        run = p.add_run(line)
        run.font.name = 'Consolas'
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
```

## 警告段落模式
```python
p = doc.add_paragraph()
run = p.add_run('⚠️ ' + text)
run.font.bold = True
run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
```

## 标题颜色统一
```python
def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x0B, 0x2A, 0x4A)
```

## 保存与验证
```python
# 保存路径：用户约定 → Desktop\工作报告\
output_path = r"C:\Users\周家同\Desktop\工作报告\{文件名}.docx"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
doc.save(output_path)

# 验证：read_file 回读，确认章节数 + 文件大小
# 不重跑 pytest（用户测试铁律）
```

## 完整依赖
- `python-docx`（`pip install python-docx`）
- 标准库：`os`, `datetime`
- 零外部依赖运行 python-docx 脚本

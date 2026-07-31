# scripts/ — 工具箱

| 脚本 | 用途 |
|---|---|
| `ocr_pdf.py` | 合同 PDF 多页 OCR（文字/扫描混合）+ 字段提取 + 待核清单（A1-A2） |
| `extract_fields.py` | 对已有 OCR 文本重复提取/调参字段（A2） |
| `xls_tpl.py` | .xls 模板读写（xlutils.copy 保格式；`xf_to_style` 保留原单元格格式） |
| `validate_3docs.py` | 三单一致性校验 + 结构化报告（A7，报告为交付物） |
| `dump_template.py` | 模板结构自动 dump（docx/xls → 结构档案，A3） |
| `env_check.py` | 环境自检（venv/tesseract/语言包/GOOGLE_API_KEY） |
| `glossary.json` | 115 条俄/乌→中机械冶金备件术语（B3 翻译辅助） |

运行环境：`uv venv --python 3.11 .venv-skill` + `uv pip install xlrd pandas python-docx pymupdf xlwt xlutils`
（Windows 中文路径下 tesseract 必须 `--tessdata-dir`；execute_code 沙箱与 venv 不同，一律用 venv python 执行）

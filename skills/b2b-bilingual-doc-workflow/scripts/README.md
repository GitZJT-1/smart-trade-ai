# scripts/ — 工具箱

| 脚本 | 用途 |
|---|---|
| `ocr_pdf.py` | 合同 PDF 多页 OCR（文字页直取 + 扫描页 PP-OCRv5）+ 字段提取 + 待核清单（A1-A2） |
| `ocr_paddle_vl.py` | PaddleOCR-VL 本地 GPU 整页文档结构化解析（Markdown/JSON，A1） |
| `ocr_ppocrv5.py` | PP-OCRv5 本地 GPU 线级 OCR（检测+识别，ru/uk 西里尔，B2.5/B4/C1） |
| `extract_fields.py` | 对已有 OCR 文本重复提取/调参字段（A2） |
| `xls_tpl.py` | .xls 模板读写（xlutils.copy 保格式；`xf_to_style` 保留原单元格格式） |
| `validate_3docs.py` | 三单一致性校验 + 结构化报告（A7，报告为交付物） |
| `dump_template.py` | 模板结构自动 dump（docx/xls → 结构档案，A3） |
| `env_check.py` | 环境自检（venv 依赖 / PaddleOCR GPU 引擎 / OCR.space） |
| `glossary.json` | 141 条俄/乌→中机械冶金备件术语（B3 翻译辅助） |

运行环境：
- 轻量脚本：`uv venv --python 3.11 .venv-skill` + `uv pip install xlrd pandas python-docx pymupdf xlwt xlutils`
- PaddleOCR 脚本：`.venv-paddleocr`（paddlepaddle-gpu + paddleocr[doc-parser]），需 NVIDIA GPU

（execute_code 沙箱与 venv 不同，一律用 venv python 执行）

---
name: b2b-tech-drawing
description: 工程图纸分析 — 从 PDF 图纸中自动提取材料、尺寸、公差等结构化生产信息
when_to_use:
  - "用户上传或提到工程图纸/技术图纸/铸造图纸/机械图纸"
  - "用户问「这是什么零件」「帮我看看这张图纸」「分析这张图纸」"
  - "客户发了 PDF 图纸要求报价"
  - "用户提到 GOST / ASTM / ISO / DIN / JIS 等工程标准"
triggers:
  - 图纸
  - 工程图
  - 技术图纸
  - 铸件图
  - 机械图
  - 零件图
  - GOST
  - ASTM
  - ISO 图纸
  - DIN 标准
  - 图纸报价
  - 分析图纸
  - 看看这张图
  - 帮我读图纸
  - technical drawing
  - engineering drawing
  - casting drawing
  - blueprint
  - mechanical drawing
category: 工具
version: 1.0.0
author: Foreign Trade Assistant
injection_prompt: |
  你是 b2b-tech-drawing 技能。用于分析客户发来的工程图纸 PDF，自动提取结构化生产信息。

  **处理流程**：
  1. 判断 PDF 类型——用 `read_file` 读 PDF，如果返回文字 < 50 字符 → 扫描件/图片型 PDF
  2. 调用 Python 工具分析图纸：
     ```
     python -c "
  from trade.tech_drawing import analyze_drawing
  import json
  result = analyze_drawing('{PDF文件路径}')
  print(json.dumps(result, ensure_ascii=False, indent=2))
  "
     ```
  3. 如果 LLM 分析失败（source = text_fallback）→ 展示原始文字内容给用户，建议人工审阅
  4. 如果 LLM 分析成功 → 按以下格式展示

  **输出格式**：
  ## 📐 零件信息
  - **名称**：xxx
  - **图号**：xxx
  - **材料**：xxx
  - **精度等级**：xxx
  - **适用标准**：xxx

  ## 📏 关键尺寸
  | 标注 | 数值 | 单位 |
  |------|------|------|
  | xxx  | xxx  | mm   |

  ## ⚙️ 技术要求
  - 公差：xxx
  - 表面处理：xxx
  - 热处理：xxx
  - 其他：xxx

  ## 💰 报价建议
  基于材料标准（如 GOST 977-88 → 对应中国 GB/T 11352 铸钢）、精度等级（12-7-0-0 铸件精度）、尺寸复杂度给出初步工艺路线和报价注意事项。

  **注意事项**：
  - 如果是扫描件且 LLM 不支持 vision，明确告知用户"该 PDF 为扫描图片，当前 LLM 不支持视觉识别，建议索要原始 CAD 文件或文字版 PDF"
  - 不编造任何尺寸数据，LLM 未识别出的字段标注「未识别」
  - 建议用户向客户索要原始 CAD 文件（DWG/DXF/STEP）以获得精确尺寸
---

# B2B Tech Drawing Analysis

从客户发来的工程图纸 PDF 中自动提取结构化信息，用于报价和生产。

## 输入

- 工程图纸 PDF 文件（文字层或扫描件均可）

## 输出

结构化 JSON + Markdown 格式报告，包含：
- 零件名称和图号
- 材料及标准
- 关键尺寸和公差
- 技术要求
- 报价建议

## 处理方式

- 文字层 PDF → 直接提取文字 → LLM 结构化分析
- 扫描件 PDF → 渲染为图片 → LLM Vision 识别（需模型支持）
- LLM 不可用时 → 回退展示原始文字内容

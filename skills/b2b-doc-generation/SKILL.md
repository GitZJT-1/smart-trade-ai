---
name: b2b-doc-generation
description: 商务文档生成 — 一键生成报价单/PI/合同/PPT（DOCX/XLSX/PPTX）
when_to_use:
  - "用户要求生成报价单 / PI / 合同 / 商业提案"
  - "一键生成 DOCX / XLSX / PPTX 格式文档"
  - "需要可下载的单证模板"
  - "用户提到「做一份报价」「生成合同」「导出 PPT」"
  - "不要用于：读取现有文档内容（用 b2b-document）"
triggers:
  - 生成文档
  - 创建文档
  - 制作文档
  - 生成PPT
  - 做一份报价
  - 做一份合同
  - 生成报价单
  - 生成合同
  - 生成提案
  - gen doc
  # ... (see skill_registry.py for full list)
category: 文档管理
version: 1.1.0
author: Foreign Trade Assistant
---
  你是 b2b-doc-generation 技能。用于**生成专业商务文档**（报价单/PI/合同/PPT/产品目录）。

  ════════════════════════════════════════
  核心原则
  ════════════════════════════════════════
  - **所有数据必须可追溯。** 每个数字、条款、产品规格必须标注来源（文件名+页码/行号）。
  - **优先使用客户真实数据。** 从 b2b-customer-mgmt 获取客户信息，从 b2b-document 提取源文件数据。
  - **格式优先于美观。** 商务文档的首要要求是可读性和合规性，其次才是视觉设计。
  - **生成后必须自检。** 用 openpyxl/python-docx/python-pptx 重新读取文件，确认关键字段非空。

  ════════════════════════════════════════
  文档类型与生成策略
  ════════════════════════════════════════

  ### DOCX — 报价单/合同/PI
  - 使用 python-docx 库
  - 必须包含：页眉（公司 Logo + 名称）、页脚（页码）、正文、签署区
  - 表格边框统一 0.5pt 灰色实线
  - 数字列右对齐，文本列左对齐
  - 金额列必须设置千分位格式（如 1,250,000）
  - 合同文档：段落间距 6pt，行距 1.5 倍
  - PI（形式发票）：包含银行信息区块、Incoterms、总金额大写

  ### XLSX — 价格表/产品目录/海关数据分析
  - 使用 openpyxl 库
  - Sheet 1 名称改为业务含义（如 "2026 Q3 Price List"）
  - 冻结首行（freeze_panes = 'A2'）
  - 表头行：深蓝底白字（PatternFill + Font color white + bold）
  - 数字格式：价格列 '#,##0.00'，百分比列 '0.0%'，日期列 'YYYY-MM-DD'
  - 自动列宽：基于内容最大长度 + 2 字符余量
  - 条件格式：A 级客户行绿色底，C 级客户行浅红底
  - 数据验证：价格列限制 >0，MOQ 列整数限制
  - 每列添加注释（Comment）标注数据来源

  ### PPTX — 提案/公司介绍/产品演示
  - 使用 python-pptx 库
  - 封面页：公司名 + 提案标题 + 日期
  - 每页最多 5 个要点（bullet points），字号 ≥18pt
  - 图表优先于表格（数据可视化 > 原始数据）
  - 统一字体：标题 Arial 28pt Bold，正文 Arial 18pt
  - 配色不超过 3 种（主色+辅色+强调色）
  - 图片必须保持原始比例，拉伸变形 = 不专业

  ════════════════════════════════════════
  数据溯源（强制）
  ════════════════════════════════════════
  生成文档后必须输出溯源表：

  | 文档位置 | 数据内容 | 来源文件 | 页码/行号 |
  |---------|---------|---------|----------|
  | A3 单元格 | 单价 $12.50 | price-list-2025.pdf | Page 3, Row 45-52 |
  | 第 4 段 | 公司介绍文本 | company-profile.md | 全文 |
  | Sheet 2 B5 | MOQ 200 | product-specs.xlsx | Sheet MOQ, Row 8 |

  ════════════════════════════════════════

-------|----------|----------|--------|
  | "注意到贵公司主营不锈钢板出口" | b2b-osint | 官网产品页 targetco.com/products | ✅ 高 |
  | "贵公司近年拓展了南美市场" | web_search | news.example.com/article | ⚠️ 间接 |
  | "如能与贵司深度合作" | - | AI 通用话术 | - |

  可信度定义:
    ✅ 高 = 直接来自官网/LinkedIn/公开数据/客户提供的文件
    ⚠️ 中 = 间接来源（行业报告/第三方描述/推测）
    ❌ 推测 = AI 基于上下文的合理推测，需人工核实
    - 无标注 = AI 通用话术，不涉及客户具体信息
---

```
Parties: Seller and Buyer legal names, addresses
Whereas: Background recitals
Article 1: Definitions
Article 2: Scope of Supply
Article 3: Pricing and Payment
Article 4: Delivery (Incoterms, lead time, shipping)
Article 5: Quality and Inspection
Article 6: Warranty
Article 7: Intellectual Property
Article 8: Confidentiality
Article 9: Force Majeure
Article 10: Termination
Article 11: Dispute Resolution
Article 12: Governing Law
Signature blocks
Annexes (if any)
```

### Phase 4: Populate with Data

Insert data with source citations:

```python
# XLSX cell with citation
cell.value = f"{price} USD/unit"
cell.comment = "📄 price-list-2025.pdf | Page: 3 | Row: 45-52"
```

### Phase 5: Verify Before Delivery

```python
# Re-read the generated document to verify
from openpyxl import load_workbook
wb_verify = load_workbook("output/quotation.xlsx")
ws_verify = wb_verify.active
print(f"Total rows: {ws_verify.max_row}")
print(f"Header: {ws_verify['A1'].value}")
# Confirm no empty critical cells in pricing columns
```

```python
# Verify PPTX
from pptx import Presentation
prs_verify = Presentation("output/proposal.pptx")
print(f"Total slides: {len(prs_verify.slides)}")
for i, slide in enumerate(prs_verify.slides, 1):
    title = slide.shapes.title.text if slide.shapes.title else "(no title)"
    print(f"Slide {i}: {title}")
```

### Phase 6: Save and Report

Save to the appropriate location:
- Quotations: `~/.trade/companies/{slug}/clients/{client}/quotes/`
- Proposals: `~/.trade/companies/{slug}/clients/{client}/proposals/`
- Contracts: `~/.trade/companies/{slug}/clients/{client}/contracts/`

Report to user:
```
✅ Quotation generated: {filename}
📄 Sources cited: 3 files
   - price-list-2025.pdf (Sheet: 1, Row: 45-52)
   - product-specs.xlsx (Sheet: MOQ, Row: 1-10)
   - client-history.docx (Paragraph: pricing terms)
```

## Incoterms Reference

| Term | Meaning | Risk Transfer | Cost Responsibility |
|------|---------|--------------|-------------------|
| EXW | Ex Works | Buyer assumes at seller's premises | Buyer pays all |
| FOB | Free on Board | Seller delivers on vessel | Seller pays to port |
| CIF | Cost Insurance Freight | Seller delivers to destination port | Seller pays all |
| DDP | Delivered Duty Paid | Seller delivers to buyer premises | Seller pays all |
| DAP | Delivered at Place | Seller delivers to named place | Seller pays to destination |

## Common Business Document Phrases

### Quotation Email Body
```
Subject: Quotation for {Product} — {Ref No.}

Dear {Name},

Thank you for your inquiry. Please find attached our quotation for {product/project}.

Key terms:
- Validity: {X} days
- Payment: {T/T 30% deposit, 70% before shipment}
- Lead Time: {X} weeks after deposit
- Port: {FOB Shanghai / CIF Hamburg}

We look forward to your feedback.

Best regards,
{Your Name}
{Company}
```

### Proposal Email Body
```
Subject: {Company} Proposal for {Project} — {Date}

Dear {Name},

Thank you for your time during our call on {date}. Per our discussion, please find attached our proposal addressing your requirements on {topic}.

Key highlights:
1. {Advantage 1}
2. {Advantage 2}
3. {Advantage 3}

Please don't hesitate to reach out if you have any questions.

Best regards,
{Your Name}
```

## Related Skills

- `b2b-document` — Extract raw data from source files
- `b2b-customer-mgmt` — Retrieve client context for customization
- `b2b-lead-generation` — Client analysis for proposal personalization

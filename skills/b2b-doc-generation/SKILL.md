---
name: b2b-doc-generation
description: 外贸单证生成 — 订单档案单一数据源，一键出报价单/PI/CI/装箱单/报关单/合同/提案（DOCX/XLSX/PPTX），UUID锚点价格回写 + 生成前阻断校验 + 客户硬匹配
when_to_use:
  - "用户要求生成外贸单证（报价单 / PI / CI / 装箱单 / 报关单 / 合同 / 商业提案）"
  - "一键生成 DOCX / XLSX / PPTX 格式文档"
  - "从询价单/合同出发，多份单证联动（改一处其余联动）"
  - "填好单价的报价单需要回写价格并出正式单据"
  - "用户提到「做一份报价」「生成PI」「出合同」「套模板做报关文件」「回写价格」"
  - "生成普通 Word/PPT 用 Hermes 内置 office skills 即可，不需要本技能"
  - "不要用于：读取文档内容（用 b2b-document）；俄/英双语合同/图纸的 OCR 提取与翻译（用 b2b-bilingual-doc-workflow）"
triggers:
  - 做报价单
  - 生成PI
  - 形式发票
  - 出合同
  - 外贸合同
  - 装箱单模板
  - 商业提案
  - 报价单模板
  - 出CI
  - 报关文件
  - 价格回写
  - 回写价格
  - 套模板
  - proforma invoice
  - quotation template
  - gen doc
  # ... (see skill_registry.py for full list)
category: 文档管理
version: 2.0.0
author: Foreign Trade Assistant
---

# 外贸单证生成（订单档案单一数据源 + 确定性引擎兜底）

## 定位

报价单 / PI / CI / 装箱单 / 报关单，本质是「**同一组订单数据的不同排版**」。
传统做法是每次从零手工抄，改一处要改四处，极易出错。

本 skill 的做法：
1. **先把订单数据沉淀成一份 order.json（唯一数据源）**
2. 所有单据都从这份档案生成，改一处其余联动
3. 四道确定性引擎兜底（不靠肉眼/AI 自查）：客户硬匹配、生成前阻断校验、UUID 锚点价格回写、结构校验

> 已吸收 trade-pipeline（外贸单证自动化）的四个核心工程模式，但保留你「套客户模板」的既有打法。

## 核心原则

- **单一数据源**：任何单据字段一律从 order.json 读，禁止生成过程中重新手抄/重填。
- **所有数据必须可追溯**：每个数字、条款、产品规格必须标注来源（文件名+页码/行号）。
- **不编造数据**：价格/数量/日期/合同号/税号逐字核对，不确定标 `[待补充]` 问用户。
- **客户匹配失败 = 硬阻断**：匹配不到客户就停下来问人，禁止猜（PI/CI 发错抬头 = 事故）。
- **生成正式单证前必跑 precheck**：error 阻断，warning 需确认。机器校验只查结构/一致性，查不了"发错客户/金额填错但看起来合法"——正式单证发给客户前仍需人工核对抬头/金额/税号。
- **格式优先于美观**：商务文档首要要求是可读性和合规性，其次才是视觉设计。
- **套模板优先**：用户提供了模板就用模板（复制+改字段保格式），不重建版式。

## scripts/ 工具箱（确定性引擎）

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `scripts/order_model.py` | 订单档案 init / recalc / dump（单一数据源核心） | 仅标准库 |
| `scripts/buyer_match.py` | 客户多级匹配 + 硬阻断 | pyyaml |
| `scripts/precheck.py` | 生成前阻断式校验引擎（12 规则） | pyyaml（可选） |
| `scripts/price_anchor.py` | 报价单 UUID 锚点 stamp / 价格回写 update | openpyxl |
| `scripts/doc_writers.py` | 从 order.json 生成发票/箱单/报关单（套 NLMK 俄英双语结构） | python-docx/xlwt |
| `scripts/html_to_pptx.py` | HTML 手册 → 可编辑 PPTX | python-pptx/bs4/lxml |

运行环境：系统 `python`（3.11+）已装 openpyxl + pyyaml，直接 `python scripts/xxx.py` 可跑，无需建 venv。

## 工作流总览

```
询价/合同 ──→ ① order.json（唯一数据源）
                    │
        ┌───────────┼───────────────┐
        ↓           ↓               ↓
   ② buyer_match  ③ precheck    ④ 各单据生成（套模板，读 order.json）
   (客户硬匹配)  (生成前校验)       报价单/PI/CI/装箱单/报关单/合同/PPT
        │           │               │
        └───── 阻断 ─┘       ⑤ price_anchor 价格回写（UUID 锚点）
                                → 重新出正式单据
```

### Phase 0：初始化台账（首次）

读 `assets/companies.yaml`。若 sellers 为空或仍为示例占位，先引导用户填写公司信息（中文名/英文名/地址/联系人/邮箱/税号），并录入客户台账（每个客户配 legal_names 全名 + aliases 别名）。客户台账是 buyer_match 的匹配源，别名越全匹配越准。已有客户（trade 后端 customer 表、b2b-customer-mgmt 档案）可导入。

### Phase 1：建立订单档案（单一数据源）

`python scripts/order_model.py init <order_no>` 生成空白骨架，或让 AI 从询价单/合同提取数据填入 order.json。

```json
{
  "order_no": "26LF4993",
  "seller_id": "luofei",
  "buyer_id": null,
  "buyer_raw_name": "ООО Метиз Трейдинг",
  "terms": { "incoterm": "DAP", "currency": "USD", "payment": "", "port_of_loading": "", "port_of_destination": "" },
  "items": [
    { "item_uuid": "8f3a1b2c", "description_cn": "六角螺栓", "description_en": "HEX HEAD BOLT",
      "standard": "DIN 933", "material": "8.8", "hs_code": "7318159090",
      "quantity": 1000, "unit": "pcs", "unit_price": null, "amount": null,
      "weight_kg_per_unit": null }
  ]
}
```

- item_uuid 由 init 生成，是价格回写的锚点，不要手工改。
- 报价阶段 unit_price / amount 留空（正常），客户确认后再回写。

### Phase 2：客户匹配（硬阻断）

```bash
python scripts/buyer_match.py assets/companies.yaml "ООО Метиз Трейдинг"
```

命中 → 输出 buyer_id 写进 order.json；未命中/歧义（退出码非 0）→ **停下来**列候选清单让用户选，或确认新客户（先补进 companies.yaml 再重跑）。匹配优先级：显式指定 → legal_names 精确 → aliases 精确 → 剥法律后缀核心名模糊（唯一命中才接受）。

### Phase 3：生成前校验（阻断式）

```bash
# 报价阶段（缺价是正常状态，只提示不阻断）
python scripts/precheck.py <order.json> --config assets/companies.yaml --stage quote
# 正式单证阶段（缺价升为 error，阻断）
python scripts/precheck.py <order.json> --config assets/companies.yaml --stage formal
```

- **error**（E001 买家未匹配 / E002 卖方未配置 / E004 数量非法 / E005 负价 / E006 金额≠数量×单价 / E008 术语非法）→ 阻断。
- **warning**（W001 缺价·正式阶段 / W002 目的港缺失 / W003 重量缺失 / W004 付款条款缺失）→ 默认阻断，`--skip-warnings` 放行。
- **info**（I001 产地证/质保书提醒）→ 不阻断。

报告落盘 `--report <订单>_precheck.md` 作为证据链随单证归档。

### Phase 4：生成报价单（套模板 + 埋 UUID）

按模板生成报价单后埋 UUID 锚点：`python scripts/price_anchor.py stamp <报价单.xlsx> <order.json>`，在报价单最右侧写入隐藏列 `__item_uuid__`（按品名匹配），客户之后怎么改行序都不影响回写。

### Phase 5：价格回写（UUID 锚点）

客户确认价格、业务员填好单价后：`python scripts/price_anchor.py update <报价单.xlsx> <order.json>`，靠 UUID 精确定位回写单价并重算 amount，落盘回 order.json。再跑一次 `precheck --stage formal`，通过后进入正式单据生成。

### Phase 6：生成正式单据（从 order.json 读）

用 writer 脚本生成，俄英双语结构按 NLMK 26BY008 真实模板：

```bash
# 一次生成发票 + 箱单 + 报关单
python scripts/doc_writers.py all <order.json> --config assets/companies.yaml --outdir <输出目录>
# 或单独生成
python scripts/doc_writers.py invoice <order.json> --config assets/companies.yaml
```

- 发票（invoice.docx）= 商业发票 CI；形式发票 PI 同版式，标题改 PROFORMA INVOICE + 加有效期。
- 箱单（packing.docx）、报关单（customs.xls）结构与 references 记录一致。
- 报关单是近似海关版式（从零画）；真实报关建议套你的 .xls 模板（详见 references/customs-declaration-templates.md 的 xlrd/xlutils 套模板流程）。
- 俄英双语客户走 b2b-bilingual-doc-workflow 的俄英模板细节。

### Phase 7：交付

交付物是单据本身（.xlsx/.docx，常见格式，不用 .md）。校验报告（precheck.md）作为证据链归档。正式 PI/CI 交付前**强制提醒人工核对买家抬头、金额、税号**。

---

## 文档类型与生成策略

### DOCX — 报价单/合同/PI
- 使用 python-docx；必须含页眉（Logo+名称）、页脚（页码）、正文、签署区
- 表格边框统一 0.5pt 灰色实线；数字列右对齐，文本列左对齐
- 金额列千分位格式（如 1,250,000）；合同段落间距 6pt、行距 1.5 倍
- PI 含银行信息区块、Incoterms、总金额大写

### XLSX — 价格表/产品目录/海关数据分析
- 使用 openpyxl；Sheet 名改业务含义；冻结首行 `freeze_panes='A2'`
- 表头深蓝底白字（PatternFill + Font white + bold）
- 数字格式：价格列 `#,##0.00`、百分比列 `0.0%`、日期列 `YYYY-MM-DD`
- 自动列宽（内容最大长度+2）；条件格式（A 级客户绿底/C 级红底）；数据验证（价格>0）
- 每列加 Comment 标注数据来源

### PPTX — 提案/公司介绍/产品演示
- 使用 python-pptx；封面页含公司名+标题+日期；每页 ≤5 要点、字号 ≥18pt
- 图表优先于表格；标题 Arial 28pt Bold、正文 18pt；配色 ≤3 种；图片保持原始比例

## 标准外贸单证字段清单（生成时必须包含）

### 商业发票 (Commercial Invoice)
- **A. 出口商信息**：公司名 / 地址 / 电话·邮箱·网站[可选]
- **B. 发票基本信息**：发票号 / 日期 / 合同号[可选] / 付款条款 / 贸易术语 / 起运港·目的港
- **C. 收货人信息**：公司名+地址+联系人+电话·邮箱
- **D. 运输信息**：运输方式 / 船名航次[可选·出货后补] / ETD·ETA
- **E. 货物明细表**：序号|品名|规格型号|HS编码|数量|单位|单价|币种|总金额；表尾含总件数/总毛重/总体积汇总行 + 金额合计（大小写）
- **F. 唛头**（无则写 N/M）
- **G. 银行信息**：开户行 / 账号 / SWIFT / 受益人（须与出口商一致）
- **H. 声明与签署**：签章区 + 声明文本[可选]

### 形式发票 (Proforma Invoice)
与商业发票结构相同，额外必填：**有效期（Valid Until）**；标题明确标注 "PROFORMA INVOICE"（无法律效力，仅供申请信用证/预付款）。

### 采购订单 (Purchase Order)
订单基本信息（PO号/日期/供应商编号/采购员/部门）→ 买卖双方信息 → 交货信息（地址/日期/运输/术语）→ 采购明细表（序号|品名|规格|数量|单位|单价|币种|总金额|交期）→ 金额汇总（小计/折扣[可选]/税率/税额/总额）→ 付款条款+备注 → 审批签字区。

### 原产地证 (Certificate of Origin)
CCPIT/CIQ 格式 12 字段：1.出口商 2.收货人[可选·To Order] 3.运输方式路线 4.目的国 5.签证机构专用(空) 6.唛头 7.包装件数及货物描述 8.HS编码 9.数量 10.发票号日期 11.出口商声明 12.签证机构证明。产地标准标记 "P"（完全获得）/"W"+HS（实质性改变）。

## 合同结构（DOCX）

Parties / Whereas / Article 1 Definitions / 2 Scope of Supply / 3 Pricing and Payment / 4 Delivery (Incoterms) / 5 Quality & Inspection / 6 Warranty / 7 IP / 8 Confidentiality / 9 Force Majeure / 10 Termination / 11 Dispute Resolution / 12 Governing Law / Signature blocks / Annexes。

## Incoterms 速查

| 术语 | 含义 | 风险转移 | 费用承担 |
|---|---|---|---|
| EXW | 工厂交货 | 卖方厂内 | 买方全包 |
| FOB | 船上交货 | 装运港上船 | 卖方至装运港 |
| CIF | 成本保险费运费 | 目的港 | 卖方全包至目的港 |
| DDP | 完税后交货 | 买方门口 | 卖方全包 |
| DAP | 目的地交货 | 指定地点 | 卖方至目的地 |

## 数据溯源（强制）

生成文档后输出溯源表：

| 文档位置 | 数据内容 | 来源文件 | 页码/行号 |
|---------|---------|---------|----------|
| A3 单元格 | 单价 $12.50 | price-list-2025.pdf | Page 3, Row 45-52 |
| Sheet2 B5 | MOQ 200 | product-specs.xlsx | Sheet MOQ, Row 8 |

## 常见商务邮件话术

### 报价邮件
```
Subject: Quotation for {Product} — {Ref No.}
Dear {Name},
Thank you for your inquiry. Please find attached our quotation.
Key terms: Validity {X} days | Payment {T/T 30% deposit, 70% before shipment} | Lead time {X} weeks | {FOB Shanghai / CIF Hamburg}
Best regards, {Name} / {Company}
```

### 提案邮件
```
Subject: {Company} Proposal for {Project} — {Date}
Dear {Name},
Thank you for your time on {date}. Please find our proposal addressing {topic}.
Key highlights: 1. {优势1} 2. {优势2} 3. {优势3}
Please don't hesitate to reach out with any questions.
```

## 发票号约定

`{年份}{公司代码}{合同号后4位}`，如 `26LF4993`（26=年份，LF=罗菲，4993=合同 4600114993 后四位）。唯一可追溯，无需序列库。

## references/ 索引

| 文件 | 内容 |
|---|---|
| customs-declaration-templates.md | 报关三件套（发票/箱单/报关单）套模板全流程 + NBSP/合并单元格/EasyOCR 俄语 OCR 坑 |
| docx-technical-manual-patterns.md | python-docx 品牌配色（深蓝 0B2A4A/金 D4A853）+ 表格/代码块/警告段落模式 |
| brochure-layout-patterns.md | 宣传册版式模式 |
| contract-supplement-scanned-pdf.md | 合同补充件扫描 PDF 处理 |
| supplier-registration-primetals.md | 供应商注册（Primetals） |
| html-to-pptx-session-20260715.md | HTML 手册转 PPTX 实战记录 |

## Pitfalls

- **客户名匹配失败必须停下问人**，禁止用"上次那个俄罗斯客户""类似订单"去猜 buyer_id。
- **金额一致性**：precheck 的 E006 会校验 amount = quantity × unit_price，手工抄的金额一错就露馅，别绕过它。
- **价格回写前必须先 stamp**：没埋 UUID 的报价单，update 会直接报"未找到隐藏列"。
- **docx 的 NBSP**：python-docx 存词间不换行空格 `\u00a0`，替换文本必须带 `\u00a0` 精确匹配，否则静默失败。
- **合并单元格 docx 表格**：改表格走 XML 层 `tbl.findall(w:tr)` → `tr.findall(w:tc)`，用 `tc.iter(w:t)` 读写，勿信 python-docx 的 row.cells 视图。
- **.xls 旧格式**：openpyxl 不支持 .xls，读用 xlrd、写用 xlwt/xlutils.copy 保格式。
- **中文/俄文路径**：OCR 相关（EasyOCR/OpenCV imread）不认中文路径，复制到 C:/temp/ 纯 ASCII 路径再处理。

## Related Skills

- `b2b-document` — 读取现有文档内容、提取原始数据
- `b2b-bilingual-doc-workflow` — 俄/英双语合同/图纸 OCR 提取与翻译、套俄英模板（本 skill 的俄语单证细节来源）
- `b2b-customer-mgmt` — 客户档案与 A/B/C 分级（客户台账来源之一）
- `b2b-lead-generation` — 客户分析用于提案个性化

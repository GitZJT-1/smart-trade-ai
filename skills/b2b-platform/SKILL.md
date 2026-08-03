---
name: b2b-platform
description: B2B 平台诊断 — 阿里国际站/MIC/独立站产品页分析与优化建议
when_to_use:
  - "分析阿里国际站 / 中国制造网 / TradeKey 产品页面"
  - "输出 B2B 平台产品优化建议"
  - "用户提到「阿里国际站」「中国制造网」「平台诊断」"
  - "不要用于：Amazon / eBay / Shopify（用各平台专用 skill）"
triggers:
  - 网站诊断
  - 平台诊断
  - 阿里国际站优化
  - 中国制造网
  - 独立站优化
  - 官网优化
  - 产品链接分析
  - 关键词优化
  - 阿里店铺
  - 平台上排名
  # ... (see skill_registry.py for full list)
category: 客户开发
version: 1.2.0
author: Foreign Trade Assistant
injection_prompt: |
  你是 b2b-platform 技能。用于**B2B 平台店铺全链路诊断与优化**（阿里国际站/MIC/独立站）。

  ════════════════════════════════════════
  铁律
  ════════════════════════════════════════
  - **行业对标必须用三级类目口径。** 禁止用一级/二级类目（如"工业设备"太宽泛，必须"物料搬运>>运输>>叉车"），否则对标数据完全失真。
  - **诊断归因不可混。** 商机转化率低 = 广告精准度问题（查词包+首页矩阵）；订单转化率低 = 业务承接能力问题（查报价SOP+响应速度）；L1+买家浓度低 = 词包清洗问题。
  - **严禁用行业经验估算数据。** 缺数据时标注"数据待补"或询问用户，绝不编造"行业平均约X%"。
  - **所有数值必须标注来源。** 同行均值/优秀值只能从平台官方「服务助手→服务报告→同行对比」页获取。

  ════════════════════════════════════════
  四维诊断框架
  ════════════════════════════════════════

  ### 维度一：经营诊断
  用 web_search 搜索店铺名 + 产品关键词，提取：
  - 曝光量 / 点击量 / 访客数（UV）的周环比趋势
  - 商机转化率（询盘+TM咨询 / 点击）vs 同行均值
  - 订单转化率（信保订单 / 商机数）vs 同行均值
  - L1+ 买家浓度（L1+买家数 / 总买家数）
  - 行业三级类目对标表（贵司 / 同行均值 / 同行优秀，三列必填）

  ### 维度二：P4P 直通车诊断
  词效分层规则（对每个活跃关键词打标）：
  - **A级词**（CTR>2.5% 且 30天有询盘）→ 加预算，提排名
  - **B级词**（CTR 0.5%-2.5%）→ 保持观察，优化匹配方式
  - **C级词**（CTR<0.5% 且 30天0询盘）→ 暂停，替换为买家意图词
  - **0购买词**（有点击无任何商机且月消耗>500元）→ 立即暂停，致命风险

  ### 维度三：旺铺前台诊断
  用 browser_navigate 访问店铺首页，检查：
  - 首屏 Banner 是否传递清晰价值主张（非"欢迎光临"类废话）
  - 产品分类是否按买家采购逻辑组织（非按内部产品线堆砌）
  - 公司介绍是否包含：工厂实拍/认证展示/产能数据/合作客户
  - 移动端适配（45%+ 流量来自移动端）

  ### 维度四：品牌广告诊断
  - 是否开通问鼎/顶展/全域聚量？各产品的 CTR 和商机贡献对比
  - 创意更新频率（建议 ≥2 周/次，月更底线）
  - 关键词屏蔽清单：月消耗>100元且0商机的词

  ════════════════════════════════════════
  五大问题模式匹配
  ════════════════════════════════════════
  先识别模式，再给行动。禁止跳过模式识别直接给建议。

  | 模式 | 特征 | 根因 | P0 行动 |
  |------|------|------|---------|
  | 流量充裕但漏斗失效 | 曝光正常，点击率低，商机极少 | 标题/主图/价格吸引力不足 | 优化前10产品标题+主图A/B测试 |
  | 广告断供型危机 | 曝光/点击大幅下滑 | 预算不足或竞价失败 | 补充P4P预算或切换智投 |
  | 高投入低效型 | 消耗高但商机极少 | 词包质量差/0购买词占比高 | 清洗词包，暂停C级词 |
  | 0购买词致命风险 | 单词月消耗>500元且0商机 | 词不匹配买家意图 | 立即暂停，替换为L1+买家搜索词 |
  | 降星预警型 | 服务分/按时发货率下滑 | 履约能力下降 | 检查近期订单履约+回复时效 |

  ════════════════════════════════════════
  输出格式
  ════════════════════════════════════════
  ```
  # {店铺名} 四维诊断报告
  ## 总体健康度：[绿/黄/红灯] + 核心KPI一览
  ## 维度一：经营诊断
  （行业三级类目对标表 + 趋势分析）
  ## 维度二：P4P 直通车诊断
  （词效分层表：A/B/C级词清单 + 预算调整建议）
  ## 维度三：旺铺前台诊断
  （8项检查清单 + 改进建议）
  ## 维度四：品牌广告诊断
  （品广产品健康度 + 创意优化建议）
  ## 问题模式：[匹配的模式] + 根因
  ## P0/P1/P2 行动路线图
  （每条含：负责人建议/截止时间/验证方式）
  ## 数据来源
  （所有数据的平台来源 + 截图说明）
  ```
---


```
Good: "High-Quality Stainless Steel Ball Valve DN50 PN16 for Industrial Use | ISO Certified"
Good: "Custom OEM [Product Type] Manufacturer | [X] Years Experience | Fast Delivery"
Bad:   "Product A001" (too short, no keywords)
Bad:   "Best Quality Low Price Factory Direct Supply Custom Wholesale Bulk Buy Now Discount" (keyword stuffing)
```

### Keyword Analysis

**For Each Major Keyword**:
1. **Search volume**: Is it commonly searched?
2. **Competition**: How many other sellers use it?
3. **Relevance**: Does it accurately describe your product?
4. **Specificity**: Is it too broad or too narrow?

**Keyword Categories**:

| Type | Examples | Use |
|------|---------|-----|
| **Product Type** | ball valve, circuit breaker, LED panel | Primary keyword in title |
| **Material** | stainless steel, aluminum, PVC | In title + description |
| **Application** | industrial, plumbing, automotive | In description |
| **Specification** | DN50, 12V, 100W | In title (if space allows) |
| **Buyer Intent** | manufacturer, factory, wholesale | In title (for B2B) |

### Product Description Analysis

**Check for**:
- Clear product features and specifications
- Product benefits (not just features)
- Technical parameters (dimensions, materials, certifications)
- Usage/application information
- Quality control/assurance mentions
- Trade terms (MOQ, lead time, payment terms)

**Description Structure (Recommended)**:

```
[HOOK — Address buyer pain point or need]

[PRODUCT OVERVIEW — What it is]
[KEY SPECIFICATIONS — Technical details in table format]
[MATERIALS & CONSTRUCTION — What it's made of and why it matters]
[APPLICATIONS — Where/how it's used]
[BENEFITS — Why choose this product over alternatives]
[CERTIFICATIONS — ISO, CE, RoHS, etc.]
[TRADE TERMS — MOQ, lead time, payment, shipping]
[COMPANY CREDIBILITY — Experience, factory info, service]
[CTA — Contact information/request quote]
```

### Image Analysis

**Check for**:
- Minimum 3-6 images per product
- Main image: clean, professional, white/light background
- Multiple angles (front, side, back, detail shots)
- Scale reference (person, ruler, coin for size)
- Application photos (product in use)
- Packaging images for export readiness
- Infographics showing key specifications
- Image resolution (minimum 800 x 800 px recommended)

**Image Best Practices**:
- Lead with a hero shot showing the complete product
- Include detail shots of key features/finish
- Show size comparison (common in B2B)
- Include factory production photos if applicable
- Video is increasingly important (product demo, factory tour)

## Phase 2: Store/Profile Analysis

### Store Elements to Analyze

| Element | What to Check | Impact |
|---------|---------------|--------|
| **Store Name** | Clear, professional, includes keywords | Branding + SEO |
| **Banner/Header** | Professional design, clear value proposition | First impression |
| **Company Introduction** | Experience, certifications, production capacity | Credibility |
| **Product Categories** | Logical organization, complete coverage | Navigation |
| **Response Rate** | Speed of reply to inquiries | Trust signal |
| **Transaction History** | Verified transactions, repeat buyers | Social proof |
| **Certifications** | ISO, CE, factory audits displayed | Quality assurance |

### Credibility Indicators

```
✅ Verified manufacturer status
✅ Trade Assurance membership
✅ On-site Check / Third-party inspection
✅ Years in business (verified)
✅ Transaction history (real buyers)
✅ Response rate > 90%
✅ Video content (factory tour)
✅ Client testimonials/reviews
❌ Missing: Any of the above = weakness to address
```

## Phase 3: Competitor Benchmarking

### How to Find Competitors

1. Search for main product keyword on the platform
2. Note the top-ranking sellers (first page)
3. Analyze their:
   - Product titles and keywords
   - Description length and structure
   - Image quality and quantity
   - Pricing (if visible)
   - Response time and communication
   - Certifications and credentials

### Competitor Analysis Template

```
Competitor: [Store/Company Name]
URL: [Link]

TITLES:
- [Competitor's title 1]
- [Competitor's title 2]
Gap vs. You: [What's missing or better in theirs]

IMAGES:
- Number of images: [X]
- Quality (1-5): [Rating] — [Strengths]
- Gap vs. You: [What's better in theirs]

DESCRIPTIONS:
- Length: [X] words
- Structure: [How they organize content]
- Key elements included: [List]
- Gap vs. You: [What's better in theirs]

PRICING:
- Visible: [Yes/No]
- Range: [If visible]
- Gap vs. You: [Positioning]

CERTIFICATIONS:
- [List displayed]
- Gap vs. You: [What's missing]

STRENGTHS TO BORROW:
1. [Specific tactic or element]
2. [Specific tactic or element]

ACTION ITEMS:
1. [Improvement based on competitor insight]
2. [Improvement based on competitor insight]
```

## Phase 4: Diagnostic Report & Improvement Plan

### Report Structure

```
# B2B Platform Store Diagnostic Report

## Executive Summary
[2-3 sentences: overall health score and key priority]

## Current Performance Issues
[Top 3-5 problems identified, ranked by impact]

## Detailed Analysis

### Product Titles
| Product | Current Title | Issues | Recommended Title |
|---------|--------------|--------|------------------|
| [Product 1] | [Title] | [Issue] | [New title] |
| [Product 2] | [Title] | [Issue] | [New title] |

### Keywords
| Keyword | Search Volume | Competition | Priority | Action |
|---------|--------------|-------------|---------|--------|
| [Keyword 1] | High/Med/Low | High/Med/Low | P1 | [Action] |

### Product Descriptions
| Product | Current Length | Structure Score | Action |
|---------|----------------|-----------------|--------|
| [Product 1] | [X] words | Good/Fair/Poor | [Rewrite/Expand/Restructure] |

### Images
| Product | Current Count | Quality | Missing | Action |
|---------|--------------|---------|---------|--------|
| [Product 1] | [X] | Good/Fair/Poor | [List] | [Add/PImprove] |

## Priority Action Plan

### P1 — Critical (Do This Week)
1. [Action item with specific steps]
2. [Action item with specific steps]

### P2 — Important (Do This Month)
1. [Action item]
2. [Action item]

### P3 — Nice to Have (Do This Quarter)
1. [Action item]
2. [Action item]

## Expected Outcomes
- [Metric] improvement: [Current] → [Expected]
- [Metric] improvement: [Current] → [Expected]
```

## Phase 5: Keyword Strategy

### Keyword Research Process

1. **Seed keywords**: Start with main product terms
2. **Expand**: Add variations (synonyms, related terms)
3. **Filter**: Remove irrelevant or extremely low-volume terms
4. **Prioritize**: Focus on high-relevance + moderate-competition terms

### Keyword Categories for B2B

| Category | Example | Placement |
|----------|---------|-----------|
| **Head terms** | valve, pump | Title (once) |
| **Product type** | ball valve, butterfly valve | Title + description |
| **Material** | stainless steel, brass | Title + description |
| **Specification** | DN50, 1/2 inch | Title (if space) |
| **Application** | industrial, plumbing | Description |
| **Buyer intent** | manufacturer, factory, wholesale | Title + description |
| **Long-tail** | ball valve for water treatment | Description |

### Title Optimization Rules

1. **First 30 characters matter most** — put primary keyword here
2. **Include product type** — what are you selling?
3. **Add key spec if space** — material, size, or model
4. **Include buyer intent keyword** — manufacturer, wholesale
5. **Don't stuff** — 3-5 keywords max in title
6. **Match search terms** — think like your buyer

## Quality Standards

1. **Specificity over generality**: "Stainless Steel Ball Valve DN50 PN16" > "High Quality Valve"
2. **Buyer-centric**: Focus on benefits to the buyer, not just features
3. **Completeness**: All key information should be findable within the listing
4. **Professionalism**: No spelling errors, proper grammar, consistent formatting
5. **Uniqueness**: Each product needs its own optimized content — no copy-paste between listings
6. **Data-driven**: Reference actual numbers (certifications, years, capacity) not vague claims

## Common Pitfalls

1. **Keyword stuffing**: Repeating keywords in title/description hurts rankings and credibility
2. **Vague descriptions**: "High quality" without specifics means nothing to buyers
3. **Missing trade terms**: Always include MOQ, lead time, payment terms
4. **Poor images**: Dark, blurry, or unprofessional photos kill inquiries
5. **Copying competitors**: Learn from them, but differentiate your content
6. **Neglecting mobile**: Many B2B platform users browse on mobile — ensure readability
7. **No video**: Products with video get 2-3x more inquiries than those without
8. **Ignoring data**: Use platform analytics to understand what's working

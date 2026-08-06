---
name: b2b-linkedin-marketing
description: LinkedIn 营销 — Profile 优化、内容策略、InMail 模板、Account IQ 深度分析
when_to_use:
  - "优化 LinkedIn 个人 Profile"
  - "生成 LinkedIn 内容日历 / 文章 / InMail"
  - "用户提到「LinkedIn 运营」「领英开发」"
  - "不要用于：Facebook / Instagram / TikTok（用 b2b-social-media）"
triggers:
  - LinkedIn营销
  - 领英营销
  - LinkedIn策略
  - 领英开发客户
  - LinkedIn内容
  - 领英帖子
  - LinkedIn开发信
  - linkedin marketing
  - linkedin strategy
  - linkedin post
  # ... (see skill_registry.py for full list)
category: 内容营销
version: 1.0.0
author: Foreign Trade Assistant
injection_prompt: |
  你是 b2b-linkedin-marketing 技能。用于**LinkedIn 全栈营销**，从个人主页打造到客户开发到内容运营。

  **7 天 LinkedIn 主页打造计划**：
  Day1：头像（400x400，不能是 LOGO/合照）+ Banner（1584x396）+ 个性化 URL
  Day2：Headline（产品词+角色+价值，≤150 字符，三种结构（A）产品词+公司角色+核心优势（B）I help... 表达（C）职位+公司+业务范围）+ About（Who we are→What we make→Who we serve→Strengths，≤800 字符，3W+1H 或 Dream+Help 或 Story+Specialties 或 数据+案例 或 Pain Point 五种架构）
  Day3：Experience（至少 2 份，公司 20 条优势→价值展示而非罗列职责→嵌入关键词）+ Skills（10-15 个英文关键词）
  Day4：Featured 富媒体（产品册 PDF、工厂视频、案例链接）+ Media（Title≤60 字符，Description≤500 字符）
  Day5：推荐信（至少 3 封，先给别人写）
  Day6：Contact Info + 证书/专利背书
  Day7：隐私设置检查——联系人名单仅自己可见、动态关闭公开、公开档案给买家看/隐身看同行、重要 Groups 必须隐私、两步验证开启、用无痕浏览器模拟买家视角检查

  **LinkedIn 五维度内容营销**：
  1. Post-视频（产品展示/工厂参观/客户案例）
  2. Post-照片（工程现场/装箱发货/团队活动）
  3. Post-文章（行业深度长文，SEO 权重高，长尾词可排谷歌首页）
  4. 投票（高参与度，轻互动，引导评论）
  5. Document（上传高价值资料如产品目录/选型指南，引导客户下载获取线索，标题带产品关键词）

  **Document 引流打法**：文档名称=产品关键词（如"Guy Grip / Dead End Clamp / Insulator Clamp"），Description 引导目标客户画像素级客户来下载，用客户画像的关键词吸引南美/澳洲/中东等特定市场。

  **客户开发三步闭环**：
  1. 画像素级客户画像（仅需主营产品→输出目标市场/行业分类/搜索关键词/客户类型/公司规模/决策人职位 6 大维度）
  2. Sales Navigator 精准搜索（使用布尔运算符：职位 OR 产品关键词 OR 行业 AND 国家 AND 公司规模 11-200 人）
  3. Add Note 300 字符开发（人维度/公司维度两套模板，必须引用买家背景关键词+提产品匹配点，专业真诚不推销）

  **Add Note 铁则**：关注→有 post 就评论→忍不住想开发才用 Add Note。哪怕没 post 也一定关注（关注后 LinkedIn 算法更懂你）。先发 Connection Request 而非 InMail，按后台数据（是否看过视频/案例/分享）决定跟进话术。

  **Smart Link 三步法**：Step1 画客户画像→Step2 Sales Navigator 搜索→Step3 针对单一客户定制 Smart Link（命名带对方公司名、打包 3 个文件：本地气候应对 PDF+安装视频+成功案例）

  **LinkedIn 安全规则**：一天加好友不超过 100 个、新号先内部互加 50 人再开发、不加国内同行（防举报封号）、界面语言切英文（功能更全）

  **高级会员专属用法**：Spy 竞品公司员工列表、TeamLink 突破二度人脉、Lead Builder 保存搜索模板、竞争对手动态监控、InMail 直触

  **全年内容规划**：三支柱（技术 40%/项目 30%/动态 30%）+ 季度市场重点 + 月主题线 + 周二/四/六发布。Post 结构：吸睛开头(emoji+节奏感)→实操内容→行业关键词→CTA→精选标签。

  **领英公司主页**：About us 含产品关键词和工厂优势、公司规模/成立年份/认证/主要市场全部填写。用 Google Site Search 搜索：`site:linkedin.com "职位" "行业" "国家"` 扩展搜索。
---


Industry: [Target industry — e.g., manufacturing, retail, construction]
Company Size: [1-10 / 11-50 / 51-200 / 200+ employees]
Roles: [Purchasing Manager, CEO, Operations Director, etc.]
Region: [Specific countries or regions]
Pain Points: [Top 3 challenges they face]
Goals: [What they're trying to achieve]
Buying Behavior: [Price-sensitive / quality-focused / relationship-driven]
```

### Example (Generic B2B Manufacturing)

```
Industry: Industrial equipment manufacturing
Company Size: 50-200 employees
Roles: Purchasing Manager, Plant Manager, CEO
Region: North America, Europe, Southeast Asia
Pain Points: Quality consistency, lead time, communication barriers
Goals: Find reliable suppliers, reduce costs, scale production
Buying Behavior: Quality-focused, requires certifications, longer sales cycle
```

## Phase 2: Personal Profile Optimization (5 Sections)

### Section 1: Profile Photo & Banner

- **Photo**: Professional headshot with clear face visible, smiling, neutral background
- **Banner**: Company product/factory image OR brand statement image (1584 x 396 px)

### Section 2: Headline (220 characters max)

**Formula**: `[Job Title] | [Core Value Proposition] | [Industry/Product]`

**Examples**:
- `Export Sales Manager | Helping Global Partners Source Quality [Product] at Competitive Prices | 10+ Years Experience`
- `B2B Sourcing Expert | Connecting Worldwide Buyers with Top-Tier Manufacturers | Certified Supply Chain Partner`
- `[Product] Supplier | Your Reliable China Sourcing Partner | ISO Certified Factory`

### Section 3: About Section (3,000 characters max)

**Structure**:

```
[HOOK — 1-2 sentences addressing their pain point]
I've helped [X]+ companies in [industry] solve [specific problem].

[YOUR BACKGROUND — Credibility]
With [X] years in [industry], I understand the challenges you face.

[WHAT YOU OFFER — Clear value proposition]
I specialize in:
• [Service/Product 1] — [Benefit]
• [Service/Product 2] — [Benefit]
• [Service/Product 3] — [Benefit]

[CTA — Next step]
📩 Connect with me to discuss your sourcing needs.
🌐 [Website]
🔗 [Product catalog link]
```

### Section 4: Experience

**Format**: `[Job Title] at [Company Name]`
- Use keywords in job titles (Export Manager, B2B Sales, Sourcing Specialist)
- Write 40-50 words per position describing achievements

### Section 5: Skills & Endorsements

- Add 50 skills relevant to your industry
- Prioritize: Product Sourcing, B2B Sales, Negotiation, Supply Chain Management, Quality Control, International Trade
- Ask colleagues to endorse your top skills

## Phase 3: Company Page Setup

### Company Page Sections

1. **Name**: `[Your Brand] — Professional [Product] Manufacturer`
2. **Tagline**: `[X] Years of Excellence in [Industry] | Your Trusted [Product] Partner`
3. **About**: Similar structure to personal profile, company-focused
4. **Products**: Add all product categories with descriptions and images
5. **Media**: Factory photos, certifications, team, trade show presence

### Content Strategy for Company Page

- Post company updates 3-5x per week
- Share behind-the-scenes content
- Post certifications and quality compliance
- Share client testimonials (with permission)

## Phase 4: Annual LinkedIn Marketing Plan

### Monthly Content Calendar Template

| Week | Content Type | Topic Focus | Goal |
|------|-------------|------------|------|
| Week 1 | Video/Photos + Article | Product showcase + Industry insight | Awareness |
| Week 2 | Poll + Text Post | Engagement boost + Industry question | Engagement |
| Week 3 | Document + Article | Lead magnet + How-to guide | Lead generation |
| Week 4 | Video + Text Post | Factory/culture + Quick tip | Trust building |

### Sample Annual Content Plan

```
Q1 (Jan-Mar): Brand awareness & foundation
- Month 1: Profile optimization, 5 foundational posts
- Month 2: First article series (industry trends)
- Month 3: Document post (product guide v1)

Q2 (Apr-Jun): Lead generation focus
- Month 4: First poll series, engagement campaign
- Month 5: Case study article, client testimonial
- Month 6: Product catalog document, company milestone

Q3 (Jul-Sep): Authority building
- Month 7: Thought leadership articles
- Month 8: Trade show coverage, industry event
- Month 9: Expert interview series

Q4 (Oct-Dec): Year-end review & planning
- Month 10: Annual industry report
- Month 11: Client success stories
- Month 12: Year in review, next year preview
```

## Phase 5: Outreach Message Templates

### Connection Request (≤300 characters)

**Formula**: `[提及对方的痛点或共同点] + [你能帮TA解决什么问题] + [CTA]`

核心原则：不推销产品，而是让对方意识到「这个人可能帮我省时间/省钱/降低风险」。

**Examples**:
- `Hi [Name], saw your post about supplier quality issues. I help [industry] buyers eliminate inconsistent product quality with a 3-step process. Open to connecting?`
- `Hi [Name], many purchasing managers in [industry] tell me their lead times are killing their margins. We built a system that cuts it by 30%. Worth a coffee chat?`
- `Hi [Name], I noticed your company is expanding in [market]. Getting CE/FDA certification right from the start saves months of rework — happy to share what we've learned.`

### Follow-Up After Connection (Day 3-5)

```
Hi [Name],

Enjoyed connecting with you!

I know that for [product] buyers in [industry], keeping quality consistent across multiple containers is a constant headache. One of our clients in [similar company/region] was seeing 8% defect rates from their previous supplier, which ate up their margins on every order.

We built [specific process/capability] that brought it down to under 2% and saved them about $[X] on their last three shipments.

Would you be open to a 15-minute call? I'd love to understand what frustrates you most about your current sourcing setup.

Best,
[Your Name]
```

### InMail for Prospects

```
Subject: [Their company] + supply chain idea

Hi [Name],

I know that for [industry] companies expanding in [region], finding a supplier who actually understands [local certification/regulation requirements] can make or break a product launch.

We recently worked with [a company similar to prospect] who were stuck because their existing suppliers couldn't meet [specific requirement]. We stepped in with [specific solution] and got their product to market [X weeks/months faster].

Is supply chain reliability something you're focused on right now? Happy to share what we've learned — no pitch, just insight.

Best,
[Your Name]
```

## Phase 6: Content Templates by Type

### Video/Photo Post Template

```
[Visual: 客户使用场景 / 定制化服务过程 / 检测实验室 / 客户反馈截图]

[用客户痛点开头 — 1-2句]
Most [industry] buyers don't realize that [a hidden problem] costs them [X]% on every order...

[你的独到解决方案 — 3-4句]
At [company], we [specific thing you do differently], which means:
→ [Benefit for customer — money/time/risk]
→ [Benefit for customer — money/time/risk]
→ [Benefit for customer — money/time/risk]

[CTA — 让读者参与]
Is [problem] something your team faces? Comment below or DM me.

#industry #sourcing #supplychain #qualitycontrol
```

### Article Template

```
Title: [Number] Things You Must Know About Sourcing [Product] from [Country]

Introduction: [Hook — address their pain point]

Section 1: [Topic]
[2-3 paragraphs]

Section 2: [Topic]
[2-3 paragraphs]

Section 3: [Topic]
[2-3 paragraphs]

Conclusion: [Summary + CTA]
[Author bio with photo]

#industry #sourcing #[product] #[country]
```

### Document Post Template

```
🎁 FREE GUIDE: [Title]

This [X]-page guide covers:
📌 [Key point 1]
📌 [Key point 2]
📌 [Key point 3]
📌 [Key point 4]

Comment "GUIDE" below and I'll send you the link!

#industry #[product] #sourcing #[country]
```

### Text Post Template

```
[用客户的视角切入 — 痛点、误区、踩坑经历]

[你遇到过的真实案例或行业现象]

[你或你的团队是如何解决这个问题的 — 重点讲流程、工具、服务,不讲产品参数]

[以一个问题结尾，邀请讨论]

#industry #supplychain #foreigntrade #[topic-not-product]
```

## Quality Standards

1. **No placeholders**: All content must be complete and ready to publish. No "XXX", "[insert]", or "[TBD]"
2. **Industry-specific**: Use actual product terminology from user's资料. Adapt examples to their industry
3. **Platform-native**: Content should feel natural for LinkedIn, not repurposed blog content
4. **Visual requirement**: Every post should have an image/video or clear visual description
5. **Character limits**: Respect LinkedIn limits — headline 220 chars, connection note 300 chars, article title 100 chars
6. **Hashtag strategy**: Use 3-5 relevant hashtags per post, mix broad (#B2B #Sourcing) with specific (#Machinery #Electronics)
7. **客户价值优先**: 每篇内容先想「读这篇文章的人最关心什么」——不是你的产品有多好，而是你能让TA的工作更容易、更挣钱、更少风险。产品参数是支撑证据，不是主角。

## Common Pitfalls

1. **Generic content**: Don't create one-size-fits-all posts. Always adapt to user's specific industry and products
2. **Product-first mentality** 🔴 **最严重的错误**: 帖子开头就讲产品参数、规格、价格优势。正确做法：先谈客户痛点 → 解决方案 → 工厂硬实力展示 → 产品作为支撑证据出现
3. **过度推销**: 没人关注只会贴产品目录的账号。产品/工厂内容占 25% 左右，且须裹在客户价值叙事里
4. **空洞话术**: 不要说「质量好」「价格优」「服务好」——每个供应商都这么说。具体讲「我们的出货检验包含 X 项测试」「48 小时打样承诺」「拉美市场 CE 认证我们有专门文件团队」
5. **Ignoring engagement**: Respond to comments within 24 hours. Engagement drives algorithmic reach
6. **Inconsistent posting**: Better to post 3x/week consistently than 10x one week and none the next
7. **Cold outreach without personalization**: Always reference something specific about the prospect before pitching
8. **No CTA**: Every post should have a clear call-to-action (comment, share, click link, DM)

## LinkedIn SEO Optimization

To appear in search results when prospects search for suppliers:

1. **Keywords in profile**: Put industry/product keywords in headline, About section, and Experience titles
2. **Consistent posting**: LinkedIn rewards active accounts with better search visibility
3. **Engagement**: Comment on industry posts to increase visibility
4. **Connections**: Grow your network — aim for 500+ connections in your target industry
5. **Recommendations**: Ask clients for recommendations — they appear in search results

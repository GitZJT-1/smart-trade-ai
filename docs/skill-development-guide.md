# Skill 开发指南

本文档描述 Foreign Trade Assistant 的 Skill 系统的完整开发流程。阅读后你应该能够独立创建、调试和发布一个新的 B2B skill。

---

## 1. Skill 系统架构

```
skills/b2b-{name}/SKILL.md          ← 你创建的 .md 文件（前端注入内容，源代码控制）
        │
        ├─ skill_registry.py         ← L4 数据层：注册 triggers/aliases/input_fmt/output_fmt
        │     └─ _SKILLS 列表中加一条 dict
        │
        ├─ skill_router.py           ← L2 逻辑层：match_skill(query) 做关键词匹配
        │     │                       augment_query(query) 注入 SKILL.md 的 injection_prompt
        │     └─ _load_injection_prompt(name) 解析 YAML frontmatter，带 mtime 缓存
        │
        └─ helpers.py build_query()  ← L2 调用方：构建 prompt 时先 match_skill() 再拼装
```

**三层注入机制：**

| 层 | 位置 | 作用 |
|----|------|------|
| `triggers` | `skill_registry.py` | 决定用户输入是否能匹配到此 skill |
| `injection_prompt` | `skills/b2b-{name}/SKILL.md` frontmatter | 匹配后注入给 LLM 的详细指令（主要文本） |
| `augment_prompt` | `skill_registry.py` | 降级后备：SKILL.md 加载失败时使用（新 skill 不需要填此项） |

---

## 2. 创建新 Skill 的步骤

### Step 1: 创建 SKILL.md

在 `skills/` 下新建目录和文件：

```bash
mkdir skills/b2b-{your-skill-name}
touch skills/b2b-{your-skill-name}/SKILL.md
```

**目录命名规则：**
- 前缀 `b2b-` 表示 Trade 专属 skill
- 名称用连字符，全小写，如 `b2b-price-negotiation`
- `chat-memory` 是唯一不遵循 `b2b-` 前缀的特殊 skill（聊天记忆）

### Step 2: 编写 SKILL.md frontmatter

```yaml
---
name: b2b-{your-skill-name}
description: >-
  一句话描述这个 skill 做什么。这个 description 字段目前主要用于人类阅读，
  不参与自动路由。
triggers: []
category: b2b-sales
version: "1.0.0"
author: 你的名字
injection_prompt: |
  你是 b2b-{your-skill-name} 技能。当用户的查询涉及 XXX 时，按以下流程操作。

  ════════════════════════════════════════
  Phase 1: （阶段名）
  ════════════════════════════════════════
  1. 第一步做什么
  2. 第二步做什么

  ════════════════════════════════════════
  约束条件
  ════════════════════════════════════════
  - 数据真实性：所有陈述必须有可追溯的事实依据。基于公开可验证的数据来源
    （公司官网、LinkedIn、企业注册数据库、行业报告等）进行分析。
  - 引用格式：每条关键信息后附上来源 URL、文件路径或截图
  - 当无法找到某条信息的确凿来源时，明确标注"未经证实"或"待验证"，不做推断性描述
  - RESTRICTION: Google only. DO NOT use Browser. Start immediately.
```

**frontmatter 字段说明：**

| 字段 | 必填 | 用途 |
|------|------|------|
| `name` | ✅ | Skill 标识符，需与目录名一致 |
| `description` | 可选 | 人类可读的描述，不参与路由匹配 |
| `triggers` | 可选 | SKILL.md 内嵌的触发词（当前路由机制以 `skill_registry.py` 中的 `_SKILLS[].triggers` 为准） |
| `injection_prompt` | ✅ | **核心字段**。匹配到此 skill 后，这段文本会被注入到 LLM 的语境中 |

**`injection_prompt` 编写要点：**

1. 开头声明身份：`你是 b2b-xxx 技能。`
2. 使用 `═══` 分隔符划分阶段（Phase），每个阶段列出具体执行步骤
3. 使用 `STOP RULE` 明确终止条件（防止 agent 死循环）
4. 明确输出格式（JSON / 表格 / Markdown）
5. 指定工具使用策略（`web_search` / `browser_navigate` / `read_file` 等）
6. **必须包含数据真实性约束**：明确说明数据来源必须可追溯，禁止编造

### Step 3: 注册到 skill_registry.py

编辑 `trade/skill_registry.py`，在 `_SKILLS` 列表末尾添加一条：

```python
{
    "name": "b2b-{your-skill-name}",
    "triggers": [
        # 中文触发词 — 用户说这些词时自动匹配到此 skill
        "你的触发词1", "触发词2", "触发词3",
        # English triggers（可选）
        "english trigger 1", "english trigger 2",
    ],
    "aliases": ["别名1", "别名2"],  # 可选，该 skill 的其他叫法
    "input_fmt": "用户应提供什么信息（自然语言描述）",
    "output_fmt": "用户会得到什么结果（自然语言描述）",
},
```

**触发词设计原则：**

- 每个 skill 至少 5 个中文触发词
- 覆盖口语化表达（"查一下"、"帮我看看"）和术语（"WHOIS"、"尽职调查"）
- 避免与其他 skill 的触发词重叠
- 考虑中英文混合场景
- 不要太宽泛（如单个字"查"），会误匹配
- 测试 `tests/test_api.py::TestSkillRouter::test_no_duplicate_triggers` 确保无重复
- 如 skill 完全由 LLM 工具调用触发（如 `chat-memory`），`triggers` 可以为空

**约定：**
- `input_fmt` 和 `output_fmt` 用中文写，面向开发者而非最终用户

### Step 4: 运行测试验证

```bash
pip install -e ".[dev]"
install-trade-skills                           # 将新 skill 安装到 ~/.hermes/skills/
python -m pytest tests/test_api.py -v -k "skill"   # 跑 skill 相关测试
ruff check .                                   # lint 检查
```

`install-trade-skills` 会把 `skills/` 下的新文件复制到 `~/.hermes/skills/`，Hermes Agent 才能发现它。

---

## 3. Skills 目录结构约定

```
skills/
├── b2b-osint/             # OSINT 背调（6层检测流水线）
│   └── SKILL.md
├── b2b-platform/          # B2B 平台诊断
│   └── SKILL.md
├── b2b-lead-generation/   # 客户开发
│   └── SKILL.md
├── b2b-cold-outreach/     # 冷 outreach 邮件
│   └── SKILL.md
├── b2b-document/          # 文档分析
│   └── SKILL.md
├── b2b-doc-generation/    # 文档生成
│   └── SKILL.md
├── b2b-email-intel/       # 邮箱情报
│   └── SKILL.md
├── b2b-social-media/      # 社媒营销
│   └── SKILL.md
├── b2b-linkedin-marketing/# LinkedIn 营销
│   └── SKILL.md
├── b2b-customs-data/      # 海关数据分析
│   └── SKILL.md
├── b2b-data-directory/    # 数据目录管理
│   └── SKILL.md
├── b2b-onboarding/        # 新用户引导
│   └── SKILL.md
├── b2b-customer-mgmt/     # 客户管理
│   └── SKILL.md
├── b2b-daily-automation/  # 日常自动化
│   └── SKILL.md
├── b2b-trade-ops/         # 外贸履约 & 售后
│   └── SKILL.md
├── b2b-trade-compliance/  # 合规 & 规范校验
│   └── SKILL.md
├── b2b-skill-generator/   # Skill 生成器
│   └── SKILL.md
├── b2b-email-imitation/   # 开发信仿写与再创作
│   └── SKILL.md
├── b2b-buyer-persona/     # 买家画像与角色分层
│   └── SKILL.md
├── b2b-market-analysis/   # 市场分析作战地图
│   └── SKILL.md
├── b2b-sales-pipeline/    # 销售管线策略
│   └── SKILL.md
├── auto-trade-customer-development/  # 全自动客户开发编排
│   └── SKILL.md
├── auto-smtp-email/       # SMTP 邮件发送
│   └── SKILL.md
└── chat-memory/           # 聊天记忆（特殊 skill，无前缀）
    └── SKILL.md
```

---

## 4. Skill 匹配流程

```
用户输入: "帮我查一下这个公司的背景"
    │
    ▼
skill_router.match_skill(query)
    │
    ├─ 1. explicit_regex 匹配? ("@b2b-osint" 等 @skill 语法)
    │     └─ YES → 返回该 skill
    │
    ├─ 2. keyword 匹配? (遍历 _SKILLS，大小写不敏感)
    │     └─ 匹配多个 skill? → 按 _SKILLS 注册顺序，返回第一个匹配的
    │
    └─ 3. 无匹配 → pass-through，不注入任何 skill prompt
```

**调试技巧：**
- 查看 `skill_router.match_skill("你的测试 query")` 的返回值
- 检查 `~/.hermes/skills/b2b-{name}/SKILL.md` 是否被正确复制
- SKILL.md 的 mtime 缓存：修改 skill 后需重启 server 或等 mtime 变化

---

## 5. injection_prompt 最佳实践

### DO ✅

```yaml
injection_prompt: |
  你是 b2b-platform 技能。当用户需要诊断或优化任何网站时，按以下流程操作。

  1. 加载 skill: b2b-platform
  2. 获取数据：用 browser_navigate 打开目标 URL 并截图
  3. 分析维度：标题/图片/描述/关键词/询盘转化
  4. 返回格式：
     - 总体评级（优秀/良好/需改进/差）
     - 各维度具体问题
     - 优化建议（按优先级排列）
     - 行动清单

  RESTRICTION: Google only. DO NOT use Browser. Start immediately.
```

要点：
- 分阶段清晰的结构
- 具体的输出格式要求
- 明确的工具使用指令
- STOP RULE 防止死循环

### DON'T ❌

```yaml
injection_prompt: |
  你好，请帮用户做平台诊断。你需要分析网站然后给出建议。
```

问题：没有结构、没有约束、没有输出格式、agent 可能随意发挥。

---

## 6. 现有 24 个 Skills 的触发词快速参考

| Skill | 典型触发词 |
|-------|-----------|
| b2b-osint | 背景调查、背调、whois、尽职调查 |
| b2b-platform | 平台诊断、优化、店铺、独立站 |
| b2b-lead-generation | 开发信、客户开发、cold email、领英开发 |
| b2b-cold-outreach | 开发信、产品推广信、推广邮件、跟进信 |
| b2b-document | 分析文档、PDF、报价单分析 |
| b2b-doc-generation | 生成报价单、生成合同、做一份 |
| b2b-email-intel | 邮箱查一下、邮箱注册、邮箱背调 |
| b2b-social-media | 社媒、社交媒体、Facebook、Instagram |
| b2b-linkedin-marketing | LinkedIn、领英、profile优化 |
| b2b-customs-data | 海关数据、进出口、HS编码 |
| b2b-data-directory | 数据目录、数据管理、文件组织 |
| b2b-onboarding | 新手上路、引导、设置 |
| b2b-customer-mgmt | 客户管理、CRM、客户信息 |
| b2b-daily-automation | 定时任务、自动化、简报、日报 |
| b2b-trade-ops | 催款、索赔、展会、验厂、物流异常 |
| b2b-trade-compliance | 文化禁忌、Incoterms、翻译二审、投标 |
| chat-memory | 之前说过、上周聊的、历史记录、帮我查 |
| b2b-skill-generator | 生成skill、创建技能、新建能力、做个skill |
| b2b-email-imitation | 仿写开发信、模仿邮件、参考邮件写、按这个风格写 |
| b2b-buyer-persona | 买家画像、客户画像、角色分析、按角色写 |
| b2b-market-analysis | 市场分析、目标市场、作战地图、竞品分析 |
| b2b-sales-pipeline | 销售推进、跟进策略、怎么跟进、下一步怎么办 |
| b2b-inquiry-training | 询盘训练、回复练习、模拟买家、反对意见 |
| auto-trade-customer-development | 全自动客户开发、一键开发客户、端到端 |
| auto-smtp-email | 发邮件、SMTP发送、群发邮件、开发信发送 |

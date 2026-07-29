# 01-basic-tender-search.md

## 场景
矿山设备出口商查找非洲地区的招标机会。

## 用户输入
```
帮我查一下非洲地区最近的水泥厂设备招标信息，主要做破碎机和输送设备。
```

## Agent 执行过程（示意）

### Phase 1 — 需求确认
Agent 确认：
- 产品：水泥厂设备 — 破碎机、输送设备
- 区域：非洲（无具体国家，默认扫全非）
- 关键词：`cement plant equipment crusher conveyor Africa tender`

### Phase 2 — 招标搜索
web_search 执行搜索：
1. `site:ted.europa.eu "cement plant" Africa tender 2026`
2. `site:afdb.org tender cement plant equipment`
3. `site:ungm.org "crusher" OR "conveyor" Africa`
4. `cement plant tender Africa 2026`
5. `"cement plant" procurement Africa "crusher" OR "conveyor"`

### Phase 3 — 结构化提取
对找到的招标逐条提取字段、评估匹配度。

---

## 预期输出

```
# 📋 招标信息汇总报告 — 水泥厂设备 / 非洲
生成日期：2026-07-28
搜索关键词：cement plant equipment, crusher, conveyor, Africa, tender

---

## 概览
| 指标 | 值 |
|------|----|
| 搜索平台数 | 5 |
| 找到招标数 | 3 |
| 高匹配度 | 1 条 |
| 中匹配度 | 1 条 |
| 30天内截止 | 2 条 |

---

## 招标详情

### No.1 — Supply of Crusher and Conveyor System for Dangote Cement Plant Expansion
| 字段 | 内容 |
|------|------|
| **采购方** | Dangote Cement Plc（尼日利亚） |
| **预算** | 未公开[推断：大型企业扩产项目，通常在 $500K-$2M] |
| **截止** | 2026-08-15（还剩 18 天 — 🟡 紧张） |
| **资质要求** | ISO 9001 认证、尼日利亚当地代理或合作方、类似项目 3 年以上业绩证明 |
| **投标方式** | 线上（电子招标系统） |
| **来源** | dgMarket → [原文链接](https://www.dgmarket.com/tender/...) |
| **匹配度** | 🟢 高 |
| **可行性** | 需在尼日利亚有当地代理；提供此前同类项目供货记录 |

> **摘要**：Dangote Cement 计划扩建 Obajana 工厂，采购一套 500TPH 破碎机系统及配套输送设备（长度约 2.5km），含安装指导。
> **评估**：产品高度匹配，Dangote 为非洲最大水泥生产商，付款信誉好。建议本周内找尼日利亚当地代理或确认是否有代理渠道。

---

### No.2 — Supply of Material Handling Equipment for New Cement Plant (Ethiopia)
| 字段 | 内容 |
|------|------|
| **采购方** | National Cement Share Company（埃塞俄比亚） |
| **预算** | $200K-$500K |
| **截止** | 2026-08-05（还剩 8 天 — 🔴 紧急） |
| **资质要求** | 供应商需具备 5 年以上出口经验、CE 认证、东非地区项目经验优先 |
| **投标方式** | 密封报价（Sealed Bid），线下递交 |
| **来源** | Ethiopian Public Procurement Portal → [原文链接](https://www.eprocure.gov.et/...) |
| **匹配度** | 🟡 中 |
| **可行性** | 距截止仅 8 天，准备时间非常紧张；CE 认证可提供，但线下递交需要埃塞当地人或快递 |

> **摘要**：埃塞俄比亚 National Cement 新建工厂，采购物料输送设备（堆取料机、皮带机、斗提机等），含 2 年备件包。
> **评估**：产品部分匹配，但准备时间太短。如用户在当地有代理人可以考虑加急跟进。

---

### No.3 — Consultancy Services for Cement Plant Feasibility Study (Tanzania)
| 字段 | 内容 |
|------|------|
| **采购方** | Tanzania Ministry of Industry（坦桑尼亚） |
| **预算** | $80K-$120K |
| **截止** | 2026-09-01（还剩 35 天 — 🟢 充裕） |
| **资质要求** | 工程咨询资质，非设备供应 |
| **投标方式** | 线上递交 |
| **来源** | African Development Bank → [原文链接](https://www.afdb.org/.../tender/...) |
| **匹配度** | 🔴 低 |
| **可行性** | 此为工程咨询服务招标，非设备采购，不匹配 |

> **摘要**：坦桑尼亚工业部委托做新建水泥厂可行性研究，非设备采购。
> **评估**：不适用，但说明坦桑尼亚正在规划新建水泥厂，未来 6-12 个月可能出现设备采购招标。建议关注该国的后续招标动态。

---

## 搜索总结与建议

### 未能获取的信息
- 部分非洲国家（如喀麦隆、科特迪瓦）的政府采购平台需要注册才能查看招标详情
- Dangote 项目预算未公开—此类大型企业通常不公开预算

### 建议行动
1. 🥇 **优先跟进**：No.1 Dangote Cement（尼日利亚）— 匹配度高、客户信誉好、时间充裕
2. 🥈 **关注备选**：No.2 National Cement（埃塞俄比亚）— 虽然时间紧但如已有代理可跟进
3. 🗓️ **定期提醒**：建议设置 cron 任务每周搜索非洲水泥厂设备招标 → 如需设置请说"帮我设置招标监控"

### 注意事项
- 非洲项目通常要求本地代理，请确认贵司在尼日利亚和埃塞俄比亚是否有合作方
- Dangote 对供应商资质审核较严，建议提前准备公司资质文件 PDF 包
- 部分招标需要投标保函（通常为报价金额的 2-5%），银行办理需 3-5 个工作日
```

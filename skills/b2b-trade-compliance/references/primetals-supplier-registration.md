# Primetals Technologies 供应商注册 — 实战核查案例（2026-08）

> 本案例演示 Phase 7 完整流程：用户说「提交 Oracle 注册」，实际核查后是官网网页表单。

## 任务背景

- 用户：「Primetals Technologies 供应商注册表草稿已完成，帮我提交 Oracle 注册 + 发跟进邮件」
- 草稿：`Desktop\沈阳山泰通用机械有限公司\客户资料\Primetals供应商注册草稿.md`（2026-07-13）
- 草稿状态：含 Code of Conduct 确认、9 部分内容，但 7 项待办中有 5 项为必填空缺

## 核查过程与结论

| 检查项 | 方法 | 结果 |
|--------|------|------|
| 注册入口 | web_extract 官网 `/en/contact-us/new-supplier` + `/en/about-us/supply-chain-management` | ✅ **官网网页表单**，非 Oracle 门户；字段含 Company*/Street/Post Code/City/Country/Website/DUNS/Type of Company*/Employees/Turnover*/Currency*/Contact Person/E-Mail*/Department*/Position*/附件(≤3MB PDF/JPEG/PNG)/Privacy Disclaimer |
| Oracle 门户证据 | web_search「primetals + oracle + supplier portal」 | ❌ 无任何公开证据；官网明确写 "submit our Supplier Registration Form" |
| 邮箱邀请 | IMAP 搜企业邮箱（关键词 primetals / supplier registration / oracle / new supplier） | ❌ 0 命中 |
| 客户台账 | xlrd 读 `山泰市场部客户跟进台账260115.xls` 搜索 prim/metals/注册 | ❌ 无记录 |

**结论**：用户说「Oracle 注册」不准确 → 真实入口是官网表单；注册只能由用户手动提交（无浏览器自动化/验证码），Agent 交付「填表清单 + 跟进邮件」。

## 交付物（可复用结构）

1. **提交填表清单**：23 字段逐项映射表（字段名→填写值→状态✅/🔴），含 Request 英文正文建议
2. **跟进邮件模板**：提交后第 7 工作日跟进 / 收到门户邀请后的回复

## 必填空缺示例（禁止编造）

- 上年营业额 + 币种（Total Turnover From Last Year* / Currency*）
- 公司邮箱（建议企业域名邮箱）
- 手机号（含 +86）
- DUNS 编码（表单专用；无 DUNS 可免费申请 dnb.com 或留空尝试）
- 邮编 + ISO 9001 认证编号

## 技术要点

- **xls 台账读取**：`pip install xlrd`（2.0.2 已装于 hermes venv）；旧 .xls 用 xlrd，新 .xlsx 用 openpyxl
- **企业邮箱 IMAP 搜索**（163 企业邮）：`imap.qiye.163.com:993` SSL；登录后 `search(None, 'OR SUBJECT "kw" FROM "kw"')`，`fetch` 取 `BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]`；中文关键词需先编码或跳过
- **执行环境**：execute_code 沙箱无 xlrd → 用 `terminal` 跑 `python -c "..."`（系统 venv 有 xlrd）
- 163 企业邮箱监控脚本位置：`%LOCALAPPDATA%\hermes\scripts\monitor_qiye163_email.py`（含账号，仅 IMAP 读取，无 SMTP 发送）

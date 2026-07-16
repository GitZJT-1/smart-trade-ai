---
name: auto-smtp-email
description: SMTP 邮件发送技能 — 从 ~/.hermes/.env 读凭证，预览后发送，支持 HTML 模板 + 抄送 + 附件 + 限速群发
triggers:
  - 发邮件
  - 发送邮件
  - SMTP 发送
  - 发开发信
  - 群发邮件
  - 批量发送
  - 预览后发送
  - send email
  - smtp send
  - send cold email
  - bulk send
  - mail out
  - 帮我发
  - 发出去
category: email
version: 1.0.0
author: Trade
injection_prompt: |
  你是 auto-smtp-email 技能。当用户需要通过 SMTP 实际发送邮件（而非生成草稿）时启用此技能。

  ════════════════════════════════════════
  铁律 — 预览后发送，绝不在用户确认前调用 SMTP
  ════════════════════════════════════════
  1. 先生成完整邮件预览（收件人/主题/正文/附件）给用户看
  2. 用户明确回复「确认发送」「发吧」「OK」后才能调用 SMTP
  3. 用户回复「改一下」「等等」「先别发」必须停下重新预览
  4. 任何模糊回复（如「嗯」「好」）必须二次确认 — "确认现在发出？回复 Y 继续"

  ════════════════════════════════════════
  凭证读取 — 交互式配置向导
  ════════════════════════════════════════
  第一次使用时，如果读取失败，**必须用交互式向导引导用户一步步配置**，而不是让用户自己去编辑 .env 文件。

  读取流程：
  1. 调用 execute_code 工具：
     ```python
     from pathlib import Path
     env_file = Path.home() / ".hermes" / ".env"
     if not env_file.is_file():
         raise SystemExit("SMTP 未配置")
     content = env_file.read_text(encoding="utf-8")
     creds = {}
     for line in content.splitlines():
         line = line.strip()
         if line.startswith("#") or "=" not in line:
             continue
         k, v = line.split("=", 1)
         if k.startswith("SMTP_"):
             creds[k] = v
     required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"]
     missing = [k for k in required if k not in creds]
     if missing:
         raise SystemExit(f"SMTP 缺少必需字段：{missing}")
     print(creds)
     ```

  2. 如果缺少配置，启动交互式向导，不能只是报错。按以下步骤逐一询问：

  ### 向导流程

  **Step 1 — 选择邮箱服务商**
  输出选项让用户选择：
  ```
  ━━━ SMTP 配置向导 ━━━
  请选择你的邮箱服务商：
    1. Gmail
    2. 163 邮箱
    3. 腾讯企业邮箱
    4. Outlook / Hotmail
    5. QQ 邮箱
    6. 其他（自定义 SMTP）
  输入序号（1-6）：
  ```

  **Step 2 — 获取邮箱地址**
  根据用户选择，要求提供邮箱地址。如果是自定义（选项 6），额外要求提供 SMTP_HOST 和 SMTP_PORT。

  **Step 3 — 提供授权码指引**
  根据服务商给出授权码获取链接，然后让用户把授权码粘贴过来：
  ```
  ━━━ 获取授权码 ━━━
  请按以下步骤生成授权码（不是登录密码）：
    1. 打开：https://myaccount.google.com/apppasswords
    2. 登录你的 Google 账号
    3. 在「应用名称」输入「Trade AI」
    4. 点击「生成」
    5. 把生成的 16 位授权码复制后发给我
  ```

  **Step 4 — 写入配置**
  收集齐所有字段后，调用 execute_code 写入 .env：
  ```python
  env_file = Path.home() / ".hermes" / ".env"
  existing = env_file.read_text(encoding="utf-8") if env_file.is_file() else ""
  # 追加或更新 SMTP_ 设置
  import os
  lines = existing.splitlines() if existing else []
  kept = [l for l in lines if not l.strip().startswith("SMTP_")]
  kept.append(f'SMTP_HOST={smtp_host}')
  kept.append(f'SMTP_PORT={smtp_port}')
  kept.append(f'SMTP_USER={smtp_user}')
  kept.append(f'SMTP_PASS={smtp_pass}')
  if from_name: kept.append(f'SMTP_FROM_NAME={from_name}')
  env_file.write_text("\n".join(kept) + "\n", encoding="utf-8")
  print(f"✅ SMTP 配置已保存到 {env_file}")
  ```

  **Step 5 — 验证**
  写入成功后再读取一次凭证，确认配置正确，然后询问用户是否需要发送测试邮件。

  如果用户提供的邮箱地址或授权码有误（发送时报错），返回 Step 1 重新配置，并告知具体错误（如「535 认证失败，请检查授权码是否正确」）。

  ### 服务商参数对照表
  | 服务商 | SMTP_HOST | SMTP_PORT | 授权码获取地址 |
  |--------|-----------|-----------|--------------|
  | Gmail | smtp.gmail.com | 465 | https://myaccount.google.com/apppasswords |
  | 163 邮箱 | smtp.163.com | 465 | 邮箱设置 → POP3/SMTP/IMAP → 开启 → 生成授权码 |
  | 腾讯企业邮箱 | smtp.exmail.qq.com | 465 | 邮箱设置 → 客户端专用密码 |
  | Outlook/Hotmail | smtp.office365.com | 587 | 账户安全 → 应用密码 |
  | QQ 邮箱 | smtp.qq.com | 465 | 邮箱设置 → 账户 → POP3/SMTP → 生成授权码 |

  ════════════════════════════════════════
  发送流程
  ════════════════════════════════════════

  【单封发送】
  1. 生成预览（Markdown 格式）：
     ```
     ━━━ 邮件预览 ━━━
     收件人：[Name] <email@example.com>
     抄送：[可选]
     主题：[Subject]
     附件：[文件名列表，如有]

     --- 正文（纯文本）---
     [Plain text body]

     --- 正文（HTML 预览）---
     [HTML rendered preview]

     ━━━ 确认发送请回复 Y，取消请回复 N ━━━
     ```
  2. 用户确认后，调用 execute_code 执行：
     ```python
     import smtplib
     from email.mime.multipart import MIMEMultipart
     from email.mime.text import MIMEText
     from email.mime.application import MIMEApplication
     from pathlib import Path
     import os, time

     # 读取凭证（同上）
     ...

     msg = MIMEMultipart("alternative")
     msg["From"] = f"{from_name} <{smtp_user}>"
     msg["To"] = to_addr
     msg["Cc"] = ",".join(cc_list)
     msg["Subject"] = subject
     msg.attach(MIMEText(plain_body, "plain", "utf-8"))
     msg.attach(MIMEText(html_body, "html", "utf-8"))

     for attachment_path in attachments:
         with open(attachment_path, "rb") as f:
             part = MIMEApplication(f.read())
         part.add_header("Content-Disposition",
                         f'attachment; filename="{Path(attachment_path).name}"')
         msg.attach(part)

     # SSL 连接（端口 465）
     with smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=30) as s:
         s.login(smtp_user, smtp_pass)
         s.sendmail(smtp_user, [to_addr] + cc_list, msg.as_string())

     print(f"✅ 发送成功 → {to_addr} at {time.strftime('%Y-%m-%d %H:%M:%S')}")
     ```
  3. STARTTLS（端口 587）用 smtplib.SMTP + s.starttls() 替代 SMTP_SSL
  4. 发送结果记录到 ~/.trade/audit/smtp-send-log.md（时间/收件人/主题/状态/错误）

  【批量发送】
  1. 生成预览清单（表格形式）：
     ```
     ━━━ 批量发送预览（共 N 封）━━━
     # | 收件人 | 公司 | 主题 | 附件
     1 | alice@x.com | X Corp | Subject A | -
     2 | bob@y.com | Y Inc | Subject B | quote.pdf
     ...

     ⏱ 预计耗时：N × 60-120s = X 分钟（每封间隔随机 60-120 秒）
     ━━━ 确认发送全部请回复 Y，仅发某几封请回复序号（如 1,3,5）━━━
     ```
  2. 用户确认后循环调用上面的发送代码，每封之间 sleep(random.randint(60, 120))
  3. 单封失败不阻断后续，记录到 send_log 的 status="failed" + error_msg
  4. 全部完成后输出汇总：
     ```
     ✅ 成功 N 封 / ❌ 失败 M 封 / ⏭ 跳过 K 封
     失败详情：[1] alice@x.com — SMTPAuthenticationError: 535
     完整日志：~/.trade/audit/smtp-send-log-{date}.md
     ```

  ════════════════════════════════════════
  HTML 模板规则
  ════════════════════════════════════════
  1. 必须同时提供纯文本版本（multipart/alternative），避免被识别为垃圾邮件
  2. HTML 内联 CSS，避免 <style> 标签（部分客户端会剥离）
  3. 禁止使用 JavaScript / 外部图片追踪像素 / iframe
  4. 图片必须用 cid: 内嵌或公网可访问的 https URL
  5. 字体使用 web-safe（Arial / Helvetica / Georgia），不用 web font
  6. 移动端友好：单列布局 / 字号 ≥14px / 按钮 padding ≥14px

  基础 HTML 模板：
  ```html
  <!DOCTYPE html>
  <html>
  <body style="font-family: Arial, Helvetica, sans-serif; font-size: 15px;
               line-height: 1.6; color: #1a1a1a; max-width: 600px;
               margin: 0 auto; padding: 20px;">
    <p>Hi [Name],</p>
    <p>[Opening — specific observation about their company]</p>
    <p>[Value proposition — 2-3 bullets]</p>
    <ul>
      <li>[Benefit 1]</li>
      <li>[Benefit 2]</li>
    </ul>
    <p>[CTA — clear next step]</p>
    <p>Best regards,<br>[Your Name]<br>[Title] | [Company]<br>
       [Phone] | [WhatsApp]</p>
  </body>
  </html>
  ```

  ════════════════════════════════════════
  反垃圾邮件自检（发送前强制）
  ════════════════════════════════════════
  对照检查清单，任何一项 fail 都必须修改后重新预览：
  - [ ] 主题行不含 SPAM 触发词（FREE/URGENT/GUARANTEED/100%/WINNER 等）
  - [ ] 主题行不全大写、不含过多感叹号
  - [ ] 主题行 30-50 字符
  - [ ] 正文不含过多大写单词（≤1 个）
  - [ ] 正文不滥用红色字体（≤2 处强调）
  - [ ] 图片面积 < 总面积的 50%（避免被识别为 image-heavy spam）
  - [ ] 包含明确的退订方式（"Reply STOP to unsubscribe"）
  - [ ] 附件大小 < 10MB（超过则给下载链接）
  - [ ] 收件人邮箱已验证（非 role email 如 info@/sales@，且非个人邮箱如 gmail.com 用于 B2B）

  ════════════════════════════════════════
  错误处理对照表
  ════════════════════════════════════════
  | SMTP 错误码 | 含义 | 处理建议 |
  |-------------|------|---------|
  | 535 | 认证失败 | 检查 SMTP_PASS 是否为授权码（非登录密码）|
  | 550 | 邮箱不存在 | 从列表剔除，不要重试 |
  | 551 | 用户非本地 | 检查收件人邮箱拼写 |
  | 552 | 邮件过大 | 附件压缩或改用下载链接 |
  | 553 | 邮箱名不支持 | 检查 From 地址格式 |
  | 554 | 拒绝服务 | 可能被列入黑名单，暂停 24h |
  | 421 | 服务不可用 | 5 分钟后重试 |
  | 450 / 451 | 临时失败 | 30 分钟后重试 |
  | 超时 | 网络问题 | 检查 SMTP_HOST/PORT 是否被防火墙拦截 |

  如果用户没有明确说明收件人/主题/正文，先询问这三项。如果用户说「把这封发出去」，则从对话上文提取最近一封邮件草稿。
---

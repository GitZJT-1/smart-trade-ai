# 网易企业邮 IMAP 操作笔记

## 连接参数

| 参数 | 值 |
|------|-----|
| IMAP 服务器 | imap.qiye.163.com |
| 端口 | 993 (SSL) |
| 邮箱 | user@example.com |
| 授权码 | APP_PASSWORD |

## 文件夹编码 (IMAP UTF-7)

| 文件夹 | IMAP 编码 | 用途 |
|--------|-----------|------|
| 收件箱 | INBOX | 接收邮件 |
| 已发送 | &XfJT0ZAB- | 复制已发送格式 |
| 草稿箱 | &g0l6P3ux- | 保存草稿 |

## Python IMAP 操作模板

### 读取已发送邮件格式

```python
import imaplib, email
from email.header import decode_header

conn = imaplib.IMAP4_SSL("imap.qiye.163.com", 993)
conn.login("user@example.com", "APP_PASSWORD")

# 选择已发送文件夹
conn.select('&XfJT0ZAB-')
_, msgs = conn.search(None, 'ALL')
ids = msgs[0].split()
_, data = conn.fetch(ids[-1], '(RFC822)')  # 最新的一封
msg = email.message_from_bytes(data[0][1])

# 提取正文
if msg.is_multipart():
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            body = part.get_payload(decode=True).decode('utf-8', errors='replace')
else:
    body = msg.get_payload(decode=True).decode('utf-8', errors='replace')

# 解码主题
subj = decode_header(msg['Subject'])
subject = subj[0][0].decode() if isinstance(subj[0][0], bytes) else subj[0][0]

conn.logout()
```

### 保存草稿

```python
from email.mime.text import MIMEText
from email.header import Header
import imaplib, time

body_text = """邮件正文"""
subject = "邮件主题"

msg = MIMEText(body_text, 'plain', 'utf-8')
msg['From'] = 'user@example.com'
msg['To'] = 'recipient@example.com'
msg['Subject'] = Header(subject, 'utf-8')

conn = imaplib.IMAP4_SSL("imap.qiye.163.com", 993)
conn.login("user@example.com", "APP_PASSWORD")

internal_date = imaplib.Time2Internaldate(time.localtime())
conn.append('&g0l6P3ux-', '\\Draft', internal_date, msg.as_bytes())
conn.logout()
```

## 已发送询价邮件格式 (2026-07-22)

从禾望询价邮件提取的标准格式：

```
尊敬的[公司全称]销售团队，您好！

我是沈阳罗菲机械设备贸易有限公司的 业务员（user@example.com），
我司正在为俄罗斯客户 NLMK（新利佩茨克钢铁）的[项目名]进行备件采购。

现需向贵司询价以下[产品类别]（详见附件），请提供报价：

[明细清单]

报价要求：
1. 报价有效期：请注明（建议≥30天）
2. 付款方式：请注明可接受的付款条件
3. 交货期：自收到订单及预付款之日起多少天
4. 质保期：请注明（建议≥12个月）
5. 原产地：请确认为原厂正品

如有疑问请随时与我联系，期待您的回复！


业务员 外贸业务经理
沈阳罗菲机械设备贸易有限公司
邮箱：user@example.com
```

## 注意事项

- `Time2Internaldate()` 接受 `time.localtime()` 的返回值（struct_time），不接受 `None`
- IMAP UTF-7 编码的文件夹名在 Python 字符串中直接使用编码名即可
- 草稿保存后用户需手动补充附件再发送

## 登录故障排查 (2026-08-05)

网易企业邮客户端登录常见错误及含义：

| 错误 | 含义 | 处理 |
|------|------|------|
| `LOGIN.PERMDENY` | 服务端识别该账号但**永久拒绝客户端登录** | ① 授权密码错误（网页端 设置→客户端授权密码 重新生成，区分大小写）；② 账号未开通 IMAP/SMTP 服务（网页端安全设置或管理员后台开启）；③ 多次失败被锁定（等 30 分钟） |
| `LOGIN Login error` | 账号或密码不匹配（ym.163.com 线路） | 核对账号/授权码 |
| `ERR.ILLEGAL.EMAIL` | 登录名格式非法 | 必须用完整邮箱地址，不能用前缀 |
| `LOGIN.PERMDENY`(POP3) | 同 IMAP，协议层被禁 | 同上 |

**对照排查法（关键）**：若同一网络/代码下老账号可登录、新账号 PERMDENY，则问题 100% 在账号侧（授权码/服务开关），与服务器、端口、代码无关。

**网易企业邮服务器线路**：
- 老版 `qiye.163.com`：IMAP `imap.qiye.163.com:993` / SMTP `smtp.qiye.163.com:465|994` / POP `pop.qiye.163.com:995`
- 新版 `ym.163.com`：IMAP `imap.ym.163.com:993` / SMTP `smtp.ym.163.com:465` / POP `pop.ym.163.com:995`
- 企业域名 webmail 通常 CNAME 到 `mailhz.qiye.163.com`，证书 `*.qiye.163.com`
- 登录前必须发 ID 命令：`server.xatom("ID", '("name" "X" "version" "1.0" "vendor" "Y")')`

**批量拉取工具**（收件箱备份）：`C:/Users/<user>\Desktop\沈阳罗菲机械设备贸易有限公司\邮箱工具\` — fetch_inbox.py（增量/全量/断点续传/附件提取/Excel 索引）+ config.json + 拉取收件箱.bat

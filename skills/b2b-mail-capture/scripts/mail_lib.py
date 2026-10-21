# -*- coding: utf-8 -*-
"""邮件监控共享库 — 从 mail_accounts.json 读取凭据，IMAP 只读抓取新业务邮件。

设计要点：
  * 凭据单一数据源在 mail_accounts.json（不硬编码），脚本被删不影响凭据，重建只需恢复脚本。
  * 无 SMTP 发送，仅 IMAP 读取。
  * 增量：按账号持久化 last_check 日期 + last_uid，只打印真正的新业务邮件。
  * 无新邮件 → 不打印（cron 静默，符合 hermes-upkeep 看门狗契约）。
执行环境：stdlib imaplib，无需第三方包。
"""
import imaplib
import ssl
import os
import sys
import json
import re
import email
import email.header
import email.utils
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "mail_accounts.json")

# 抓取结果 / 日志落盘目录。优先级：环境变量 MAIL_CAPTURE_DIR > mail_accounts.json 的 output_dir > 此处默认值
DEFAULT_OUTPUT_DIR = os.environ.get(
    "MAIL_CAPTURE_DIR",
    os.path.join(os.path.expanduser("~"), "Desktop", "邮件抓取结果"),
)


def ensure_output_dir(outdir):
    try:
        os.makedirs(outdir, exist_ok=True)
    except Exception as e:
        print(f"[警告] 输出目录不可用 {outdir}: {e}")
    return outdir


def save_result_file(outdir, name, text):
    """按账号写本次抓取结果（覆盖写）。仅保留兼容，已不再被 run_for 调用。"""
    path = os.path.join(outdir, f"{name}_邮件.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path
    except Exception:
        return None


def save_email_results(outdir, account_email, matches):
    """按用户的输出约定：结果文件按天归档 + 按「日期_主题」逐封命名，不再覆盖。

    规则：
      * 归档到 outdir/<邮件日期 YYYY-MM-DD>/，每天一个子目录，历史批次不被后盖。
      * 每个邮件一封 <YYYY-MM-DD>_<主题>.txt，同一天同主题冲突时追加 _<uid> 去重。
      * 只写被模型判断为业务内容的新邮件（matches 已过滤噪音/增量），不生成任何 xlsx 清单。
    返回落盘路径列表。
    """
    saved = []
    taken = set()
    for m in matches:
        day = m["date"][:10]  # YYYY-MM-DD（用邮件自身日期归档）
        day_dir = os.path.join(outdir, day)
        try:
            os.makedirs(day_dir, exist_ok=True)
        except Exception:
            continue
        # 路径在 fetch_recent 抓取时已定（附件也已按同名目录落盘），这里沿用
        txt_path = m.get("txt_path")
        att_dir = m.get("att_dir")
        if not txt_path or not att_dir:
            day_dir, txt_path, att_dir, nm = mail_paths(outdir, m["date"], m["subject"], m["uid"], taken)
        else:
            nm = os.path.splitext(os.path.basename(txt_path))[0]
        taken.add(nm)
        path = txt_path
        if not m.get("txt_path") and os.path.exists(path):
            path = os.path.join(day_dir, f"{nm}_{m['uid']}.txt")
        att_files = m.get("att_files") or []
        content = (
            f"抓取账号: {account_email}\n"
            f"邮件时间: {m['date']}\n"
            f"发件人: {m['from']}\n"
            f"主题: {m['subject']}\n"
            f"附件: {m['attachments'] if m['attachments'] else '(无附件)'}\n"
        )
        if att_files:
            content += f"附件目录: {att_dir}（已下载 {len(att_files)} 个文件）\n"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            saved.append(path)
        except Exception:
            continue
    return saved


def save_log_line(outdir, name, line):
    """按账号追加一条运行日志（时间戳 + 状态）。"""
    path = os.path.join(outdir, f"{name}_日志.txt")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return path
    except Exception:
        return None

# 黑名单噪音：系统通知 / 安全提醒 / 验证码 / 退信等非业务邮件（命中即忽略，不打印）
EXCLUDE_FROM_RE = re.compile(
    r"notice@qiye\.163\.com|qiye\.163\.com|163\.com"
    r"|no-?reply|noreply|donotreply|do-not-reply|system@|service@"
    r"|postmaster@|mailer-daemon@|bounce@|undeliver"
    r"|amazon|alibaba\.com|made-in-china|aliyun|tencent|google|microsoft",
    re.IGNORECASE,
)
EXCLUDE_SUBJECT_RE = re.compile(
    r"账户安全|异地登录|登录提醒|安全提醒|验证码|账号(?:冻结|锁定|风险|异常)"
    r"|Remote login|login reminder|security|verification code|two-factor|2fa"
    r"|блокировк|смен(?:а|ы|е)\s+парол|парол(?:ь|я)\s*(?:измен|смен)"
    r"|undeliver|delivery (?:status )?notification|spam|автоответ"
    r"|weekly digest|newsletter|subscription|退订|订阅",
    re.IGNORECASE,
)


def load_accounts():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def account_state_path():
    cfg = load_accounts()
    return os.path.join(SCRIPT_DIR, cfg.get("state_file", "mail_monitor_state.json"))


def load_state():
    p = account_state_path()
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    p = account_state_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def safe(s, n=80):
    """文件名安全化：去掉非法字符，折叠空白。"""
    s = re.sub(r"[\\/:*?\"<>|]", "_", (s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:n] or "msg")[:n]


# 附件落盘：每封邮件的附件放到与其 .txt 同名的「_附件」子目录里
ATT_DIR_SUFFIX = "_附件"
# 邮箱正文内联装饰图（签名 logo 等），不是业务附件
IMAGE_NOISE_RE = re.compile(r"^image00\d\.(png|jpe?g|gif)$", re.IGNORECASE)


def is_noise_attachment(fn, part, payload):
    """判断某 part 是否属于「不是业务附件」的噪音（签名图/空体）。"""
    if not fn or payload is None:
        return True
    if IMAGE_NOISE_RE.match(fn):
        return True
    ctype = (part.get_content_type() or "").lower()
    if (part.get_content_disposition() or "") == "inline" and ctype.startswith("image/") \
            and len(payload) < 60 * 1024:
        return True
    return False


def mail_paths(outdir, date_iso, subject, uid, taken=None):
    """决定一封邮件的落盘路径 -> (day_dir, txt_path, att_dir, basename)。

    基名 = <YYYY-MM-DD>_<主题前70字符>；同一天同主题冲突时追加 _<uid>。
    taken: 同一批次已占用的基名集合（避免同批次多封同主题邮件互相覆盖）。
    """
    day = date_iso[:10]
    day_dir = os.path.join(outdir, day)
    base = f"{day}_{safe(subject, 70)}"
    for nm in (base, f"{base}_{uid}"):
        txt = os.path.join(day_dir, nm + ".txt")
        att_dir = os.path.join(day_dir, nm + ATT_DIR_SUFFIX)
        if (taken is not None and nm in taken) or os.path.exists(txt) or os.path.exists(att_dir):
            continue
        return day_dir, txt, att_dir, nm
    nm = f"{base}_{uid}"
    return day_dir, os.path.join(day_dir, nm + ".txt"), os.path.join(day_dir, nm + ATT_DIR_SUFFIX), nm


def download_attachments(msg, att_dir):
    """把 msg 里的业务附件写到 att_dir，返回落盘文件名列表（同名自动加序号）。"""
    saved = []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn:
            continue
        fn = decode_mime(fn)
        try:
            payload = part.get_payload(decode=True)
        except Exception:
            continue
        if is_noise_attachment(fn, part, payload):
            continue
        try:
            os.makedirs(att_dir, exist_ok=True)
        except Exception:
            return saved
        stem = safe(os.path.splitext(fn)[0], 60)
        ext = os.path.splitext(fn)[1]
        fname = stem + ext
        path = os.path.join(att_dir, fname)
        i = 2
        while os.path.exists(path):
            path = os.path.join(att_dir, f"{stem}({i}){ext}")
            i += 1
        try:
            with open(path, "wb") as f:
                f.write(payload)
        except Exception:
            continue
        saved.append(os.path.basename(path))
    return saved


def decode_mime(s):
    if not s:
        return s
    try:
        parts = email.header.decode_header(s)
        out = []
        for part, charset in parts:
            if isinstance(part, bytes):
                try:
                    out.append(part.decode(charset or "utf-8", errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    out.append(part.decode("utf-8", errors="replace"))
            else:
                out.append(str(part))
        return "".join(out)
    except Exception:
        return s


def is_noise(frm, subject):
    return bool(EXCLUDE_FROM_RE.search(frm or "") or EXCLUDE_SUBJECT_RE.search(subject or ""))


def connect(account):
    ctx = ssl.create_default_context()
    conn = imaplib.IMAP4_SSL(account["imap_host"], int(account["imap_port"]), ssl_context=ctx, timeout=40)
    try:
        conn.xatom("ID", '("name" "HermesMailMonitor" "version" "1.0" "vendor" "LocalScript")')
    except Exception:
        pass
    conn.login(account["email"], account["auth_code"])
    conn.select("INBOX")
    return conn


def fetch_recent(conn, since_date, min_uid, outdir=None, taken=None):
    """返回 >= since_date 且 UID 大于 min_uid 的邮件元数据列表（按 UID 升序）。

    outdir 非空时：为每封保留邮件下载业务附件到 `<outdir>/<日期>/<日期_主题>_附件/`，
    并把路径记进返回值（txt_path / att_dir / att_files），供 save_email_results 直接沿用。
    """
    matches = []
    if taken is None:
        taken = set()
    try:
        typ, data = conn.uid("SEARCH", None, "SINCE", since_date)
    except Exception:
        try:
            typ, data = conn.search(None, "SINCE", since_date)
        except Exception:
            return []
    if typ != "OK" or not data or not data[0]:
        return []
    # data[0] 可能是 b'1 2 3 4' 或 [b'1', b'2', ...]
    if isinstance(data[0], (list, tuple)):
        nums = data[0]
    else:
        nums = data[0].split()
    # SEARCH via uid() 返回的是 UID 列表（而不是序号），直接当作 uid
    uids = [int(x) for x in nums if x]
    for uid in uids:
        # 拉全量消息（fetch_inbox 验证过的路径），响应为 [(prefix_bytes, message_bytes), b')']
        typ, msg_data = conn.uid("FETCH", str(uid), "(RFC822)")
        if typ != "OK" or not msg_data:
            continue
        raw = None
        for item in msg_data:
            if isinstance(item, tuple):
                if len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                    raw = bytes(item[1])
                elif len(item) >= 2 and isinstance(item[0], (bytes, bytearray)):
                    raw = bytes(item[0])
                break
        if not raw:
            continue
        try:
            msg = email.message_from_bytes(raw)
        except Exception:
            continue
        date_raw = msg.get("Date", "")
        try:
            dt = email.utils.parsedate_to_datetime(date_raw)
            date_iso = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_iso = date_raw[:32]
        subj = decode_mime(msg.get("Subject", "")) or "(无主题)"
        frm = decode_mime(msg.get("From", "")) or ""
        atts = []
        try:
            for part in msg.walk():
                fn = part.get_filename()
                if fn:
                    fn = decode_mime(fn)
                    if not IMAGE_NOISE_RE.match(fn):
                        atts.append(fn)
        except Exception:
            pass
        if uid is None:
            continue
        if uid <= min_uid:
            continue
        if is_noise(frm, subj):
            continue
        # 落盘路径 + 附件下载（附件目录与 .txt 同名，便于对照）
        day_dir, txt_path, att_dir, nm = mail_paths(outdir or ".", date_iso, subj, uid, taken)
        taken.add(nm)
        att_files = []
        if atts and outdir:
            try:
                att_files = download_attachments(msg, att_dir)
            except Exception:
                att_files = []
        matches.append({
            "uid": uid,
            "date": date_iso,
            "from": frm,
            "subject": subj,
            "attachments": "; ".join(atts),
            "att_files": att_files,
            "att_dir": att_dir,
            "txt_path": txt_path,
        })
    matches.sort(key=lambda m: m["uid"])
    return matches


def build_report(account, matches):
    lines = []
    lines.append(f"邮箱监控 - {account['email']}（{account.get('name', '')}）")
    lines.append(f"运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    if not matches:
        lines.append("无新邮件")
        return "\n".join(lines)
    lines.append(f"📥 新增业务邮件 {len(matches)} 封:")
    lines.append("")
    for m in matches:
        lines.append(f"• [{m['date']}] {m['from']}")
        lines.append(f"  主题: {m['subject']}")
        if m["attachments"]:
            lines.append(f"  附件: {m['attachments']}")
        lines.append("")
    return "\n".join(lines)


def run_for(account_email=None):
    cfg = load_accounts()
    accounts = cfg.get("accounts", [])
    if account_email:
        accounts = [a for a in accounts if a["email"] == account_email or a.get("name") == account_email]
    outdir = ensure_output_dir(cfg.get("output_dir") or DEFAULT_OUTPUT_DIR)
    state = load_state()
    reports = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for account in accounts:
        email_addr = account["email"]
        acct_name = account.get("name") or email_addr.split("@")[0]
        if not account.get("auth_code"):
            line = f"[跳过] {email_addr}: 未配置授权码（auth_code 为空），需在 mail_accounts.json 补齐"
            reports.append(line)
            save_log_line(outdir, acct_name, f"{now_str} {line}")
            continue
        acct_state = state.get(email_addr, {})
        last_check = acct_state.get("last_check")
        last_uid = int(acct_state.get("last_uid", 0))
        # 首次运行：回看最近 24 小时（覆盖停机期间积压的邮件）
        if not last_check:
            since_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
        else:
            try:
                since_dt = datetime.datetime.strptime(last_check[:19], "%Y-%m-%d %H:%M:%S")
                since_date = since_dt.strftime("%d-%b-%Y")
            except Exception:
                since_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
        conn = None
        try:
            conn = connect(account)
            matches = fetch_recent(conn, since_date, last_uid, outdir=outdir)
            n_att = sum(len(m.get("att_files") or []) for m in matches)
            max_uid = max([m["uid"] for m in matches] + [last_uid])
            state[email_addr] = {
                "last_check": now_str,
                "last_uid": max_uid,
            }
            report_text = build_report(account, matches)
            # 落盘：结果文件按天归档 + 按「日期_主题」逐封命名（不再覆盖），仅写日志追加
            save_email_results(outdir, email_addr, matches)
            if matches:
                # 兼容静默契约：有内容时也打印到 stdout（cron md 照常）
                print(f"归档 {len(matches)} 封到 {os.path.join(outdir, [m['date'][:10] for m in matches][0]) or outdir}"
                      f"，下载附件 {n_att} 个")
                status = f"新增业务邮件 {len(matches)} 封（{email_addr}），附件 {n_att} 个"
            else:
                status = f"无新邮件（{email_addr}）"
            save_log_line(outdir, acct_name, f"{now_str} [成功] {status}")
            reports.append(report_text)
        except imaplib.IMAP4.error as e:
            line = f"[失败] {email_addr}: IMAP 认证/连接失败 - {e}"
            reports.append(line)
            save_log_line(outdir, acct_name, f"{now_str} {line}")
        except Exception as e:
            line = f"[失败] {email_addr}: {type(e).__name__} - {e}"
            reports.append(line)
            save_log_line(outdir, acct_name, f"{now_str} {line}")
        finally:
            if conn:
                try:
                    conn.logout()
                except Exception:
                    pass
    save_state(state)
    # 只输出有实际内容的报告（跳过"无新邮件"的静默项 + 未配置项）
    meaningful = [r for r in reports if not r.endswith("无新邮件")
                  and not r.startswith("[跳过]") and not r.startswith("[失败]")]
    out = "\n\n".join(meaningful)
    if out.strip():
        print(out)
    return 0


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_for(arg)
    return 0


if __name__ == "__main__":
    sys.exit(main())

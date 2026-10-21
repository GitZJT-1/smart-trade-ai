# -*- coding: utf-8 -*-
"""补抓历史邮件的附件 — 把桌面「邮件抓取结果」里已有的邮件 .txt 对应附件从 IMAP 重新拉下来。

背景：cron 用的 mail_lib.py 早期只记录附件「文件名」，不下载文件本体；
本脚本按已有 .txt 的「日期_主题」命名把附件补落到同名的 `<...>_附件/` 子目录，并在 .txt 末尾补一行「附件目录」。

用法：
    python backfill_attachments.py [SINCE 日期，默认 01-Sep-2026]
"""
import os
import re
import sys
import email
import email.utils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mail_lib as M  # noqa: E402


def list_business_attachments(msg):
    """返回 (文件名列表, part 列表) —— 过滤掉正文内联签名图/空体。"""
    names, parts = [], []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn:
            continue
        fn = M.decode_mime(fn)
        try:
            payload = part.get_payload(decode=True)
        except Exception:
            continue
        if M.is_noise_attachment(fn, part, payload):
            continue
        names.append(fn)
        parts.append(part)
    return names, parts


def find_existing_txt(outdir, day, subject, uid, account_email):
    """按 cron 命名规则找到已有的 .txt（并核对抓取账号）。"""
    day_dir = os.path.join(outdir, day)
    if not os.path.isdir(day_dir):
        return None, None, None
    base = f"{day}_{M.safe(subject, 70)}"
    for nm in (base, f"{base}_{uid}"):
        txt = os.path.join(day_dir, nm + ".txt")
        if not os.path.exists(txt):
            continue
        try:
            with open(txt, "r", encoding="utf-8") as f:
                first = f.readline()
        except Exception:
            continue
        if account_email in first:
            return nm, txt, os.path.join(day_dir, nm + M.ATT_DIR_SUFFIX)
    return None, None, None


def append_att_line(txt, att_dir, n_files):
    """在 .txt 末尾补一行附件目录（只补一次）。"""
    try:
        with open(txt, "r", encoding="utf-8") as f:
            body = f.read()
    except Exception:
        return False
    if "附件目录:" in body:
        return False
    line = f"附件目录: {att_dir}（已下载 {n_files} 个文件）\n"
    try:
        with open(txt, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        return False
    return True


def main():
    since = sys.argv[1] if len(sys.argv) > 1 else "01-Sep-2026"
    cfg = M.load_accounts()
    outdir = cfg.get("output_dir") or M.DEFAULT_OUTPUT_DIR
    print(f"补抓窗口: SINCE {since}")
    print(f"输出目录: {outdir}")
    print("=" * 60)

    grand_files = 0
    grand_mails = 0
    unmatched = []
    for account in cfg.get("accounts", []):
        if not account.get("auth_code"):
            print(f"[跳过] {account['email']}: 未配置授权码")
            continue
        conn = M.connect(account)
        try:
            typ, data = conn.uid("SEARCH", None, "SINCE", since)
            raw_uids = data[0].split() if (data and data[0]) else []
            uids = sorted(int(x) for x in raw_uids)
            n_files = n_mails = 0
            print(f"[{account['email']}] 窗口内邮件 {len(uids)} 封，开始扫描附件…")
            for uid in uids:
                typ, md = conn.uid("FETCH", str(uid), "(RFC822)")
                raw = None
                if md:
                    for it in md:
                        if isinstance(it, tuple) and len(it) >= 2 and isinstance(it[1], (bytes, bytearray)):
                            raw = bytes(it[1])
                            break
                if not raw:
                    continue
                msg = email.message_from_bytes(raw)
                subj = M.decode_mime(msg.get("Subject", "")) or "(无主题)"
                frm = M.decode_mime(msg.get("From", "")) or ""
                if M.is_noise(frm, subj):
                    continue
                names, _parts = list_business_attachments(msg)
                if not names:
                    continue
                try:
                    day = email.utils.parsedate_to_datetime(msg.get("Date", "")).strftime("%Y-%m-%d")
                except Exception:
                    continue
                nm, txt, att_dir = find_existing_txt(outdir, day, subj, uid, account["email"])
                if not txt:
                    unmatched.append((account["email"], uid, day, subj, "; ".join(names)))
                    continue
                saved = M.download_attachments(msg, att_dir)
                if not saved:
                    continue
                append_att_line(txt, att_dir, len(saved))
                n_mails += 1
                n_files += len(saved)
                print(f"  + [{day}] {subj[:48]} -> {len(saved)} 个: {'; '.join(saved)[:70]}")
            print(f"[{account['email']}] 完成：{n_mails} 封邮件，{n_files} 个附件文件")
            grand_files += n_files
            grand_mails += n_mails
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    print("=" * 60)
    print(f"合计：{grand_mails} 封邮件 / {grand_files} 个附件文件")
    if unmatched:
        print(f"未匹配到已有 .txt 的邮件 {len(unmatched)} 封（跳过）：")
        for a, uid, day, subj, names in unmatched[:20]:
            print(f"  - [{day}] uid={uid} {subj[:50]} | {names[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

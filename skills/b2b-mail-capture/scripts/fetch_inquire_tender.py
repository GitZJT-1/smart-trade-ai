# -*- coding: utf-8 -*-
"""近两天 询价/招标 邮件抓取：拉取、分类、下载附件、生成 xlsx 清单。"""
import imaplib, ssl, email, email.header, email.utils, email.policy
import datetime, os, re, json, sys
import mail_lib as M

# ---------------- 配置 ----------------
ACCOUNT = os.environ.get("MAIL_ACCOUNT", "")   # 目标邮箱；留空则取 mail_accounts.json 第一个有授权码的账号
DAYS_BACK = 2
BASE = os.environ.get("MAIL_CAPTURE_DIR", "")  # 留空则取 mail_accounts.json 的 output_dir / mail_lib 默认
OUTDIR = os.path.join(BASE, datetime.date.today().strftime("%Y%m%d") + "-近两天询价招标")

# 分类关键词
INQUIRY_RE = re.compile(r"запрос|кп|цен[аыу]|кой\s*ц|quote|inquiry|опрос|thermo", re.IGNORECASE)
TENDER_RE = re.compile(r"конкурс|тендер|закупк|запрос\s*предлож|зп[-]|сп[.]|п[аа]о\s*[\"«]*нлмк|закуп", re.IGNORECASE)

def safe(s, n=60):
    s = re.sub(r"[\\/:*?\"<>|]", "_", (s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:n] or "msg")[:n]

def classify(subject):
    if INQUIRY_RE.search(subject):
        if TENDER_RE.search(subject):
            return "招标" if TENDER_RE.search(subject) else "询价"
        return "询价"
    if TENDER_RE.search(subject):
        return "招标"
    return "其他"

def fmt_date(dt):
    try:
        return email.utils.parsedate_to_datetime(dt).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt[:32]

def download_attachments(msg, folder, att_names):
    saved = []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn:
            continue
        fn = M.decode_mime(fn)
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        # 去掉邮箱自带的签名图（image001.png 等）避免噪音
        if re.match(r"image00\d\.(png|jpg|jpeg)$", fn, re.IGNORECASE):
            continue
        fname = safe(os.path.splitext(fn)[0], 60) + os.path.splitext(fn)[1]
        path = os.path.join(folder, fname)
        with open(path, "wb") as f:
            f.write(payload)
        saved.append(fname)
        att_names.add(fname)
    return saved

def main():
    global BASE, OUTDIR, ACCOUNT
    cfg = M.load_accounts()
    if not BASE:
        BASE = cfg.get("output_dir") or M.DEFAULT_OUTPUT_DIR
    OUTDIR = os.path.join(BASE, datetime.date.today().strftime("%Y%m%d") + "-近两天询价招标")
    cands = [a for a in cfg["accounts"] if a.get("auth_code")]
    acct = ([a for a in cands if a["email"] == ACCOUNT] or cands)[0]
    ACCOUNT = acct["email"]
    os.makedirs(OUTDIR, exist_ok=True)
    conn = M.connect(acct)
    since = (datetime.date.today() - datetime.timedelta(days=DAYS_BACK)).strftime("%d-%b-%Y")
    typ, data = conn.uid("SEARCH", None, "SINCE", since)
    uids = sorted(int(x) for x in (data[0].split() if data and data[0] else [])) if (data and data[0]) else []

    rows = []
    atts = set()
    cat0 = {"询价": 0, "招标": 0}
    for uid in uids:
        t, md = conn.uid("FETCH", str(uid), "(RFC822)")
        raw = None
        for it in md:
            if isinstance(it, tuple) and len(it) >= 2 and isinstance(it[1], (bytes, bytearray)):
                raw = bytes(it[1]); break
        if not raw:
            continue
        msg = email.message_from_bytes(raw)
        subj = M.decode_mime(msg.get("Subject", "")) or "(无主题)"
        frm = M.decode_mime(msg.get("From", "")) or ""
        date = fmt_date(msg.get("Date", ""))
        cat = classify(subj)
        if cat == "其他":
            continue
        cat0[cat] += 1
        key = f"{date[:10]}_{safe(subj, 40)}_{uid}"
        folder = os.path.join(OUTDIR, cat, key)
        os.makedirs(folder, exist_ok=True)
        saved = download_attachments(msg, folder, atts)
        attstr = "; ".join(saved) if saved else "(无附件)"
        rows.append({"分类": cat, "日期": date, "发件人": frm, "主题": subj,
                     "附件": attstr, "时间戳": "", "邮箱": ACCOUNT, "存储路径": folder})

    conn.logout()

    # ---- 输出：仅按「日期_主题」逐封落盘（邮件子目录），不再生成 xlsx 清单 ----
    print(f"抓取窗口: SINCE {since}（{DAYS_BACK}天）")
    print(f"账号: {ACCOUNT}")
    print(f"分类: 询价 {cat0['询价']} 封, 招标 {cat0['招标']} 封, 其他被过滤")
    print(f"附件下载: 共 {len(atts)} 个")
    print(f"输出目录: {OUTDIR}")
    print("=" * 60)
    for r in rows:
        print(f"[{r['分类']}] {r['日期']}  {r['发件人'][:32]}")
        print(f"      主题: {r['主题'][:70]}")
        if r["附件"] != "(无附件)":
            print(f"      附件: {r['附件'][:70]}")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

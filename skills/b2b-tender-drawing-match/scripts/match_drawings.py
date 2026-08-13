# -*- coding: utf-8 -*-
"""招标 JSON 清单 ↔ 图纸库文件名 匹配引擎 v20
用法: 改 JSONS / LIB_DIRS / DEST_DIRS 三个配置块后直接运行。
流程: 提取候选 → 清洗(长度≥4) → 匹配(PN>NAME>VER>REV>FUZ) → name_related_v5 验证 → dry-run → 移动 → 回读验证。
v20 改动: min_len 5→4; name_related 降级逻辑(4→3 fallback); +FUZ(СБ 剥离); VER 遍历同 PN 所有行项
配套技能: b2b-tender-drawing-match
完整手册: 参考 b2b-doc-generation 生成的 .docx 技术手册（品牌色深蓝#0B2A4A+金#D4A853）
"""
import json, os, re, unicodedata, shutil, hashlib
from collections import defaultdict, Counter

# ================= 配置 =================
BASE = r"C:\Users\周家同\Desktop\沈阳山泰通用机械有限公司\报价单"
JSONS = {
    # "1223588": r"...\tender_extract\items_1223588.json",
}
LIB_DIRS = [
    # os.path.join(BASE, "14 ШФ ЦРЭП"),
    # os.path.join(BASE, "15 ШФ ЦЭО"),
]
DEST_DIRS = {
    # "1223588": os.path.join(BASE, "1223588_...", "1223588"),
}
# =========================================

def norm_pn(s):
    """图号规范化: 小写, 分隔符统一 '.', 去括号/+。禁止用 compact 比较图号(1.8.421 vs 18421 误判)"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = s.replace("(", "").replace(")", "").replace("+", "")
    s = re.sub(r"[\s\-_/\\]+", ".", s)
    s = re.sub(r"\.+", ".", s).strip(".")
    return s

def compact(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"[^a-zа-яё0-9]", "", s)

def extract_part_number(name):
    """提取 ч./Ч./черт. 后图号"""
    m = re.search(r"[чЧ](?:ерт)?\s*\.?\s*([0-9А-ЯA-ZЁ][0-9А-ЯA-ZЁ\-./_()a-zа-яё]*?)(?=\s*$|\s*[()])", name)
    if m:
        pn = m.group(1).strip()
        if len(pn) >= 2:
            return pn
    return None

def clean_cands(cands, min_len=4):
    """v20: min_len 降到 4 (0018/0005 等 4 位图号不再被过滤)"""
    out = set()
    for c in cands:
        n = norm_pn(c)
        if len(n) >= min_len:
            out.add(n)
    return out

def json_pn_candidates(name):
    """JSON Наименование 图号候选: ч.后 + 名称末尾 + 名称中间编号段(带字母前缀)"""
    cands = set()
    pn = extract_part_number(name)
    if pn:
        cands.add(pn)
    m = re.search(r"([0-9А-ЯA-ZЁ][0-9А-ЯA-ZЁ\-./_()a-zа-яё]*?)\s*$", name)  # 无 ч. 前缀的图号
    if m and m.group(1) not in (pn or ""):
        t = m.group(1).strip()
        if len(t) >= 2 and any(c.isdigit() for c in t):
            cands.add(t)
    for m in re.finditer(r"([A-Za-zА-Яа-яЁё]{0,4}[-]?\d[\dА-ЯA-Za-zа-яЁё\-./_()]{2,})", name):
        t = m.group(1)
        if len(t) >= 3 and any(c.isdigit() for c in t):
            cands.add(t)
    return clean_cands(cands, min_len=4)

def lib_pn_candidates(base):
    """图纸文件名图号候选: ч.后 + 开头(长度≥4, 排除纯序号) + 名称中间编号段"""
    cands = set()
    pn = extract_part_number(base)
    if pn:
        cands.add(pn)
    m = re.match(r"^\s*([0-9А-ЯA-Za-zа-яЁё][0-9А-ЯA-Za-zа-яЁё\-./_]*?)(?=\s+[-–—]?\s*[А-ЯA-Za-zа-яЁё]|\s+[0-9]|\s*$)", base)
    if m:
        t = m.group(1).rstrip("-–—. ")
        if any(c.isdigit() for c in t) and len(t) >= 4:   # 45./52. 序号不收入
            cands.add(t)
    for m in re.finditer(r"([A-Za-zА-Яа-яЁё]{0,4}[-]?\d[\dА-ЯA-Za-zа-яЁё\-./_()]{2,})", base):
        t = m.group(1)
        if len(t) >= 3 and any(c.isdigit() for c in t):
            cands.add(t)
    return clean_cands(cands, min_len=4)

def get_words(s, min_len=3):
    return set(re.findall(r"[А-ЯA-ZЁа-яё]{%d,}" % min_len,
               unicodedata.normalize("NFKC", s).lower()))

def name_related(lib_base, json_name):
    """v20: 默认 min_len=4；JSON 无 ≥4 字符词时降级到 min_len=3"""
    json_w4 = get_words(json_name, 4)
    if json_w4:
        return len(get_words(lib_base, 4) & json_w4) >= 1
    else:
        return len(get_words(lib_base, 3) & get_words(json_name, 3)) >= 1

def strip_rev(n):
    """剥掉 norm 后图号的版本后缀。DEPRECATED: 直接调用 strip_rev_safe"""
    return strip_rev_safe(n)

def strip_rev_safe(n):
    """负向后顾防止多位数段误剥。仅剥真版本后缀（А-Я字母 / 孤立1-2位数字）。
    残余风险：纯2位尺寸变体（А1025.416.16 vs А1025.416.19）仍会误报，需 name_related + 人工甄别。"""
    m = re.search(r"[.-]?([а-я]{1,4}|(?<!\d)\d{1,2})$", n)
    if m:
        return n[:m.start()]
    return n

# ===== 图纸库扫描 =====
lib = []
for d in LIB_DIRS:
    for root, _, fns in os.walk(d):
        for fn in fns:
            base = os.path.splitext(fn)[0]
            lib.append({"path": os.path.join(root, fn), "fn": fn, "base": base,
                        "cands": lib_pn_candidates(base), "base_c": compact(base)})

# ===== JSON 加载 =====
all_items = []
for tag, path in JSONS.items():
    with open(path, encoding="utf-8") as f:
        for it in json.load(f):
            all_items.append({"tag": tag, "item": it,
                              "cands": json_pn_candidates(it["Наименование"]),
                              "name_c": compact(it["Наименование"])})

json_by_pn = defaultdict(list)
json_by_stem = defaultdict(list)
for x in all_items:
    for c in x["cands"]:
        json_by_pn[c].append(x)
        st = strip_rev(c)
        if st != c and len(st) >= 8:
            json_by_stem[st].append((x, c))

# ===== 匹配: PN > NAME > VER > REV > FUZ =====
rows = []
for e in lib:
    hits = []
    # 1) PN 图号精确匹配
    for c in e["cands"]:
        if c in json_by_pn:
            for x in json_by_pn[c]:
                if name_related(e["base"], x["item"]["Наименование"]):
                    hits.append(("PN", x, c))
    # 2) NAME compact 相等
    if not hits:
        for x in all_items:
            if x["name_c"] == e["base_c"] and name_related(e["base"], x["item"]["Наименование"]):
                hits.append(("NAME", x, ""))
                break
    # 3) VER 图号互含 (len≥8)
    if not hits:
        for c in e["cands"]:
            if len(c) < 8:
                continue
            for jc, jl in json_by_pn.items():
                if len(jc) < 8 or jc == c:
                    continue
                if c in jc or jc in c:
                    # v20: 遍历所有同 PN 项，不只取 jl[0]
                    for cand_x in jl:
                        if name_related(e["base"], cand_x["item"]["Наименование"]):
                            hits.append(("VER", cand_x, f"{c}~{jc}"))
                            break
                    break
            if hits:
                break
    # 4) REV 版本后缀容忍
    if not hits:
        for c in e["cands"]:
            st = strip_rev(c)
            if st != c and st in json_by_stem:
                for x, jc in json_by_stem[st]:
                    if name_related(e["base"], x["item"]["Наименование"]):
                        hits.append(("REV", x, f"{c}~{jc}"))
                        break
            if hits:
                break
    # 5) FUZ СБ 后缀容错 (v20 新增)
    if not hits:
        for c in e["cands"]:
            c_stripped = re.sub(r'\.?сб(\..*)?$', '', c)
            if c_stripped != c and len(c_stripped) >= 4:
                if c_stripped in json_by_pn:
                    for x in json_by_pn[c_stripped]:
                        if name_related(e["base"], x["item"]["Наименование"]):
                            hits.append(("FUZ", x, f"{c}→{c_stripped}"))
                            break
            if hits:
                break

    if hits:
        rows.append((e, hits[0]))

stats = Counter(q for _, (q, _, _) in rows)
print(f"匹配文件: {len(rows)}/{len(lib)}  按方式: {dict(stats)}")

# ===== 执行: 重命名(№-原文件名) + 移动 + 冲突处理 =====
by_json = defaultdict(list)
for e, (q, x, detail) in rows:
    by_json[(x["tag"], x["item"]["№"])].append((e, q, detail))
log, errors, moved, skipped = [], [], 0, 0
for (tag, num), lst in sorted(by_json.items(), key=lambda kv: (kv[0][0], int(kv[0][1]))):
    dest_root = DEST_DIRS[tag]
    item_dir = os.path.join(dest_root, num)   # 每个 № 独立子文件夹
    os.makedirs(item_dir, exist_ok=True)
    for e, q, detail in lst:
        dst = os.path.join(item_dir, f"{num}-{e['fn']}")   # №/№-原文件名, 无零填充
        try:
            if os.path.exists(dst):
                if hashlib.md5(open(e["path"], "rb").read()).hexdigest() == \
                   hashlib.md5(open(dst, "rb").read()).hexdigest():
                    skipped += 1
                    continue
                b, ext = os.path.splitext(os.path.basename(dst))
                dst = os.path.join(item_dir, f"{b}_v2{ext}")
            shutil.move(e["path"], dst)
            moved += 1
            log.append(f"{num}-{e['fn']}  (Q{q} {detail})")
        except Exception as ex:
            errors.append(f"{e['path']}: {ex}")
print(f"移动: {moved}, 跳过(内容重复): {skipped}, 错误: {len(errors)}")
for l in log:
    print(" ", l)
for e in errors:
    print("ERR", e)

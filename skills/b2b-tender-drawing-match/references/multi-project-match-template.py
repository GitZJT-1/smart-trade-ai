# -*- coding: utf-8 -*-
"""多项目图纸匹配+归档引擎 (v20 批量版)
用法: 修改顶部 JSONS/LIB_DIRS/DEST_DIRS 三个配置块后直接运行。
流程: 一次扫描所有共享图纸库 → 逐文件匹配所有项目 → 按项目分别归档 → 验证。
输出: 每个项目的归档子目录 (№/№-原文件名) + 匹配日志 JSON。

与单项目版 `scripts/match_drawings.py` 的区别:
- JSONS/DEST_DIRS 是 dict[tag] 而非单个值
- 主循环逐文件×逐项目匹配（非逐项目扫描）
- 自动处理跨项目文件冲突（同文件命中多项目 → 归入 lexicographic 先者）

⚠️ 跨项目冲突说明: 同一文件匹配多个项目时，只有第一个项目能真正移走文件；
后续项目会报 [Errno 2] No such file，这是预期行为，非数据丢失。
冲突数量在最终报告中标注。
"""
import json, os, re, unicodedata, shutil, hashlib
from collections import defaultdict, Counter

# ================= 配置 =================
BASE = r"C:\Users\周家同\Desktop\沈阳山泰通用机械有限公司\报价单"

JSONS = {
    "1225472": os.path.join(BASE, "items_1225472.json"),
    "1223570": os.path.join(BASE, "items_1223570.json"),
}

LIB_DIRS = [
    os.path.join(BASE, "3 БФ"),
    os.path.join(BASE, "7 СФ"),
    os.path.join(BASE, "9 ШФ ДРМО, ПМ"),
    os.path.join(BASE, "14 ШФ ЦРЭП"),
    os.path.join(BASE, "15 ШФ ЦЭО"),
    os.path.join(BASE, "Taishet"),
    os.path.join(BASE, "kf_ckr"),
    os.path.join(BASE, "kf_crap"),
    os.path.join(BASE, "kf_crep"),
    os.path.join(BASE, "kf_crgpm"),
    os.path.join(BASE, "kf_crlp"),
    os.path.join(BASE, "kf_other"),
    os.path.join(BASE, "nf_ckr"),
    os.path.join(BASE, "nf_crap"),
    os.path.join(BASE, "nf_crep"),
    os.path.join(BASE, "nf_crgpm"),
    os.path.join(BASE, "nf_crlp"),
    os.path.join(BASE, "nf_other"),
    os.path.join(BASE, "shf_ckr"),
    os.path.join(BASE, "shf_crap"),
    os.path.join(BASE, "shf_crgpm"),
    os.path.join(BASE, "shf_crlp"),
]

DEST_DIRS = {
    "1225472": os.path.join(BASE, "1225472_归档", "1225472"),
    "1223570": os.path.join(BASE, "1223570_归档", "1223570"),
}

# =========================================

# --- Core engine (same as match_drawings.py v20) ---

def norm_pn(s):
    if not s: return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = s.replace("(", "").replace(")", "").replace("+", "")
    s = re.sub(r"[\s\-_/\\]+", ".", s)
    s = re.sub(r"\.+", ".", s).strip(".")
    return s

def compact(s):
    if s is None: return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r"[^a-zа-яё0-9]", "", s)

def extract_part_number(name):
    m = re.search(r"[чЧ](?:ерт)?\s*\.?\s*([0-9А-ЯA-ZЁ][0-9А-ЯA-ZЁ\-./_()a-zа-яё]*?)(?=\s*$|\s*[()])", name)
    if m:
        pn = m.group(1).strip()
        if len(pn) >= 2: return pn
    return None

def clean_cands(cands, min_len=4):
    out = set()
    for c in cands:
        n = norm_pn(c)
        if len(n) >= min_len: out.add(n)
    return out

def json_pn_candidates(name):
    cands = set()
    pn = extract_part_number(name)
    if pn: cands.add(pn)
    m = re.search(r"([0-9А-ЯA-ZЁ][0-9А-ЯA-ZЁ\-./_()a-zа-яё]*?)\s*$", name)
    if m and m.group(1) not in (pn or ""):
        t = m.group(1).strip()
        if len(t) >= 2 and any(c.isdigit() for c in t): cands.add(t)
    for m in re.finditer(r"([A-Za-zА-Яа-яЁё]{0,4}[-]?\d[\dА-ЯA-Za-zа-яЁё\-./_()]{2,})", name):
        t = m.group(1)
        if len(t) >= 3 and any(c.isdigit() for c in t): cands.add(t)
    return clean_cands(cands, min_len=4)

def lib_pn_candidates(base):
    cands = set()
    pn = extract_part_number(base)
    if pn: cands.add(pn)
    m = re.match(r"^\s*([0-9А-ЯA-Za-zа-яЁё][0-9А-ЯA-Za-zа-яЁё\-./_]*?)(?=\s+[-–—]?\s*[А-ЯA-Za-zа-яЁё]|\s+[0-9]|\s*$)", base)
    if m:
        t = m.group(1).rstrip("-–—. ")
        if any(c.isdigit() for c in t) and len(t) >= 4: cands.add(t)
    for m in re.finditer(r"([A-Za-zА-Яа-яЁё]{0,4}[-]?\d[\dА-ЯA-Za-zа-яЁё\-./_()]{2,})", base):
        t = m.group(1)
        if len(t) >= 3 and any(c.isdigit() for c in t): cands.add(t)
    return clean_cands(cands, min_len=4)

def get_words(s, min_len=3):
    return set(re.findall(r"[А-ЯA-ZЁа-яё]{%d,}" % min_len,
               unicodedata.normalize("NFKC", s).lower()))

def name_related(lib_base, json_name):
    json_w4 = get_words(json_name, 4)
    if json_w4:
        return len(get_words(lib_base, 4) & json_w4) >= 1
    else:
        return len(get_words(lib_base, 3) & get_words(json_name, 3)) >= 1

def strip_rev_safe(n):
    m = re.search(r"[.-]?([а-я]{1,4}|(?<!\d)\d{1,2})$", n)
    if m: return n[:m.start()]
    return n

# --- Scan ---
print("=== 扫描图纸库 ===")
lib = []
seen = set()
for d in LIB_DIRS:
    if not os.path.isdir(d): continue
    cnt = 0
    for root, _, fns in os.walk(d):
        for fn in fns:
            fp = os.path.join(root, fn)
            if fp in seen: continue
            seen.add(fp)
            base = os.path.splitext(fn)[0]
            lib.append({"path": fp, "fn": fn, "base": base,
                        "cands": lib_pn_candidates(base), "base_c": compact(base)})
            cnt += 1
    print(f"  {os.path.basename(d)}: {cnt}")
print(f"  总计: {len(lib)}")

# --- Load items ---
print("\n=== 加载清单 ===")
all_items = {}
json_by_pn = {}
json_by_stem = {}
for tag, path in JSONS.items():
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    items = []
    for it in raw:
        items.append({"tag": tag, "item": it, "cands": json_pn_candidates(it["Наименование"]),
                       "name_c": compact(it["Наименование"])})
    all_items[tag] = items
    by_pn = defaultdict(list)
    by_stem = defaultdict(list)
    for x in items:
        for c in x["cands"]:
            by_pn[c].append(x)
            st = strip_rev_safe(c)
            if st != c and len(st) >= 8:
                by_stem[st].append((x, c))
    json_by_pn[tag] = by_pn
    json_by_stem[tag] = by_stem
    print(f"  {tag}: {len(items)}")

# --- Match: PN > NAME > VER > REV > FUZ ---
print("\n=== 匹配 (逐文件 × 逐项目) ===")
rows = []
for e in lib:
    for tag in JSONS:
        by_pn, by_stem = json_by_pn[tag], json_by_stem[tag]
        items_list = all_items[tag]
        hits = []
        # PN
        for c in e["cands"]:
            if c in by_pn:
                for x in by_pn[c]:
                    if name_related(e["base"], x["item"]["Наименование"]):
                        hits.append(("PN", x, c)); break
                if hits: break
        # NAME
        if not hits:
            for x in items_list:
                if x["name_c"] == e["base_c"] and name_related(e["base"], x["item"]["Наименование"]):
                    hits.append(("NAME", x, "")); break
        # VER
        if not hits:
            for c in e["cands"]:
                if len(c) < 8: continue
                for jc, jl in by_pn.items():
                    if len(jc) < 8 or jc == c: continue
                    if c in jc or jc in c:
                        for cand_x in jl:
                            if name_related(e["base"], cand_x["item"]["Наименование"]):
                                hits.append(("VER", cand_x, f"{c}~{jc}")); break
                        break
                if hits: break
        # REV
        if not hits:
            for c in e["cands"]:
                st = strip_rev_safe(c)
                if st != c and st in by_stem:
                    for x, jc in by_stem[st]:
                        if name_related(e["base"], x["item"]["Наименование"]):
                            hits.append(("REV", x, f"{c}~{jc}")); break
                if hits: break
        # FUZ
        if not hits:
            for c in e["cands"]:
                cs = re.sub(r'\.?сб(\..*)?$', '', c)
                if cs != c and len(cs) >= 4:
                    if cs in by_pn:
                        for x in by_pn[cs]:
                            if name_related(e["base"], x["item"]["Наименование"]):
                                hits.append(("FUZ", x, f"{c}→{cs}")); break
                if hits: break
        if hits:
            rows.append((e, hits[0][0], hits[0][1], hits[0][2], tag))

# --- Stats ---
print(f"\n匹配文件: {len(rows)}/{len(lib)}")
for tag in JSONS:
    tag_rows = [r for r in rows if r[4] == tag]
    stats = Counter(q for _, q, _, _, _ in tag_rows)
    unique = len(set(r[2]["item"]["№"] for r in tag_rows))
    print(f"  {tag}: {len(tag_rows)} hits / {unique} unique items / strategies: {dict(stats)}")

# --- Archive ---
print("\n=== 归档 ===")
by_json = defaultdict(list)
for e, q, x, detail, tag in rows:
    by_json[(tag, x["item"]["№"])].append((e, q, detail))

tag_moved, tag_skipped, tag_conflict = Counter(), Counter(), Counter()
all_errors = []

for (tag, num), lst in sorted(by_json.items(), key=lambda kv: (kv[0][0], int(kv[0][1]))):
    dest_root = DEST_DIRS[tag]
    item_dir = os.path.join(dest_root, num)
    os.makedirs(item_dir, exist_ok=True)
    for e, q, detail in lst:
        dst = os.path.join(item_dir, f"{num}-{e['fn']}")
        try:
            if os.path.exists(dst):
                h1 = hashlib.md5(open(e["path"], "rb").read()).hexdigest()
                h2 = hashlib.md5(open(dst, "rb").read()).hexdigest()
                if h1 == h2: tag_skipped[tag] += 1; continue
                b, ext = os.path.splitext(dst)
                dst = os.path.join(item_dir, f"{b}_v2{ext}")
            shutil.move(e["path"], dst)
            tag_moved[tag] += 1
        except FileNotFoundError:
            tag_conflict[tag] += 1  # cross-project: already moved by another project
        except Exception as ex:
            all_errors.append(f"[{tag}] {e['fn']}: {ex}")

for tag in JSONS:
    print(f"  {tag}: moved={tag_moved[tag]} skipped(dup)={tag_skipped[tag]} conflict(cross-project)={tag_conflict[tag]}")
print(f"  总计 moved: {sum(tag_moved.values())}")

# --- Verify ---
print("\n=== 验证 ===")
for tag in JSONS:
    dest = DEST_DIRS[tag]
    subdirs, total_f = 0, 0
    if os.path.isdir(dest):
        for s in os.listdir(dest):
            sp = os.path.join(dest, s)
            if os.path.isdir(sp):
                subdirs += 1
                total_f += len(os.listdir(sp))
    items_total = len(all_items[tag])
    print(f"  {tag}: {subdirs}/{items_total} items ({subdirs/items_total*100:.1f}%) / {total_f} files")

# Cross-project overlap summary
by_file = defaultdict(list)
for _, _, x, _, tag in rows:
    by_file[x["item"]["Наименование"]].append(tag)
overlap = sum(1 for projs in by_file.values() if len(set(projs)) > 1)
print(f"\n跨项目冲突: {overlap} 个文件同时匹配多个项目")
print("=== DONE ===")

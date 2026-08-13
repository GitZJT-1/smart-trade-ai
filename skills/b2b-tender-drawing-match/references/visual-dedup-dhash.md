# 同图号·异内容视觉去重（Layer 2 dHash）完整配方

> 触发：用户问「同一图号在不同年份目录里有内容不同的扫描件，能否只保留一个，但别误删其他相关图纸」。
> 归属：`b2b-tender-drawing-match` 的「跨年份目录去重」一节。本文件是可直接改路径复跑的完整实现。

## 核心思路

同一图号组（`_diff_content_groups.json` 按 norm_pn 分组后，组内多 MD5 = 内容不同）里混着两类：

| 判定 | 动作 |
|---|---|
| 视觉近同（dHash 海明距离 ≤6）+ 同名 + 同类型 + 同改版 | 保留最佳，其余回收站 |
| 视觉不同 / 名称不同 / 类型冲突 / 改版冲突 | 全部保留 |

**绝不能按图号硬删**：`norm_pn` 会把不同零件归并（`втулка ч.1564.03.001` 与 `щека 1564.03.01сб` 都归 `1564.3.1`）。实测 1032 组里 522 组是「干净文件名≥2」的不同图纸。

## 五道防误删护栏（缺一不可）

1. **同名约束（关键·2026-08-13 实测）**：`name_key(base)` = 去列表前缀 `^\d{1,3}\.`、去 `-signed`、去 ` (N)`、去尾随 `+`、空白折叠。两文件归一化名不同 → 绝不合并。这是拦 `л.3/л.4/л.5/л.6`（不同页）、`BM31HF` vs `BRE250`（不同设备）误判同一张的硬门槛。⚠️ v1 脚本漏了这条，产生 127 个误合并簇（289 文件）；补上后待删从 1023 骤降到 431。
2. **跨顶级库不合并**：`lib_of(path)` = relpath 首段，不同首段 = 不同客户，绝不合并。
3. **改版号冲突不合并**：`rev_of(name)` 提取 `\bизм[.\s]*(\d+)`。两文件 изм 号不同 → 跳过；一个带 изm 一个不带 → 也跳过。
4. **文档类型冲突不合并**：`type_of(name)` 提取 `сб`/`сп`/`деталировк`/`спецификац` 关键词集，两文件类型集不同 → 跳过。
5. **渲染失败一律保留**：打不开的图（损坏 PDF/TIF、DecompressionBomb 超限、截断 EXIF）绝不下删除结论。

## 完整脚本骨架（改 `root` 与输入 JSON 即可跑）

```python
import os, re, json, hashlib, unicodedata, ctypes
from collections import defaultdict
from ctypes import wintypes
import fitz
from PIL import Image

root = r"C:\...\报价单"
THRESH = 6   # dHash(64bit) 汉明距离 ≤6 = 同一张图（保守）

# ---- 回收站（send2trash 常缺失，用 SHFileOperationW）----
FOF_ALLOWUNDO = 0x0040; FOF_NOCONFIRMATION = 0x0010; FOF_SILENT = 0x0004; FOF_NOERRORUI = 0x0400
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", wintypes.BOOL), ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR)]
def send2trash(path):
    op = SHFILEOPSTRUCTW(); op.wFunc = 3  # FO_DELETE
    op.pFrom = os.path.abspath(path) + '\0\0'
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))  # 0=成功, 2=已删

# ---- 渲染首页 ----
def render_first(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        doc = fitz.open(path)
        if doc.page_count == 0: doc.close(); return None
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(1, 1))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        res = pix.width * pix.height; doc.close(); return img, res
    else:
        img = Image.open(path); img.load()
        w, h = img.size; img = img.convert("RGB"); return img, w * h

def dhash(img, hash_size=9):
    img = img.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
    val = 0
    for r in range(hash_size):
        for c in range(hash_size - 1):
            val = (val << 1) | (1 if img.getpixel((c, r)) > img.getpixel((c + 1, r)) else 0)
    return val

def hamming(a, b): return bin(a ^ b).count('1')

def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).lower()
    return re.sub(r'\s+', ' ', s).strip()

def rev_of(name):
    m = re.search(r'\bизм[.\s]*(\d+)', norm(name)); return int(m.group(1)) if m else None

def type_of(name):
    n = norm(name); toks = []
    if re.search(r'\bсб\b', n): toks.append('сб')
    if re.search(r'\bсп\b', n): toks.append('сп')
    if re.search(r'деталировк', n): toks.append('деталировка')
    if re.search(r'спецификац', n): toks.append('спецификация')
    return tuple(sorted(toks))

def name_key(base):
    """同名归一化（护栏1）：去列表前缀 ^\d{1,3}\. / 去 -signed / 去 (N) / 去尾随 + / 空白折叠"""
    s = unicodedata.normalize("NFKC", base).lower()
    s = re.sub(r'^\s*\d{1,3}\.\s*', '', s)
    s = s.replace('-signed', '')
    s = re.sub(r'\s*\(\d+\)', '', s)
    s = s.rstrip('+')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def is_signed(path):
    return '-signed' in os.path.basename(path).lower()

def year_of(path):
    ys = [int(m) for m in re.findall(r'\b(20(?:2[0-9]|3[0-1]))\b', path)]
    return max(ys) if ys else 0

def lib_of(path):
    return os.path.relpath(path, root).split(os.sep)[0]

# 输入：{pn: {md5: [[path, size, basename], ...]}}（同 md5 的文件字节相同，只渲染一次）
with open(os.path.join(root, '_diff_content_groups.json'), encoding='utf-8') as f:
    diff = json.load(f)

cache = {}  # md5 -> (dhash, res) or None
def get_render(md5, fp):
    if md5 not in cache:
        r = render_first(fp)
        cache[md5] = (dhash(r[0]), r[1]) if r else None
    return cache[md5]

same_drawing = []; render_fail = []
for pn, md5map in diff.items():
    reps = []
    for m5, lst in md5map.items():
        fp, sz, base = lst[0]
        dh = get_render(m5, fp)
        if dh is None: render_fail.append(fp)
        reps.append({'md5': m5, 'path': fp, 'size': sz, 'year': year_of(fp),
                     'dh': dh[0] if dh else None, 'res': dh[1] if dh else 0,
                     'base': base, 'nk': name_key(base), 'rev': rev_of(base),
                     'type': type_of(base), 'lib': lib_of(fp), 'signed': is_signed(fp)})
    # 贪心代表法（2026-08-13 修正）：按「签名>年>大小」排序，每个文件只挂到【直接 dHash<=THRESH 且全护栏】的代表上。
    # 不用 union-find——其传递闭包会把间接相近（A~B~C 但 A~C>6，视觉不同）误合并。
    reps.sort(key=lambda r: (r['signed'], r['year'], r['size']), reverse=True)
    kept_reps = []
    for r in reps:
        if r['dh'] is None:
            continue  # 渲染失败绝不参与
        if not any(k['lib'] == r['lib'] and k['rev'] == r['rev']
                   and k['type'] == r['type'] and k['nk'] == r['nk']
                   and hamming(k['dh'], r['dh']) <= THRESH for k in kept_reps):
            kept_reps.append(r)
    for k in kept_reps:
        recyc = [r for r in reps if r is not k and r['dh'] is not None
                 and k['lib'] == r['lib'] and k['rev'] == r['rev']
                 and k['type'] == r['type'] and k['nk'] == r['nk']
                 and hamming(k['dh'], r['dh']) <= THRESH]
        if recyc:
            same_drawing.append((k, recyc, pn))
```

## 验证要点

- **删除/保留列表必须与 `render_fail` 零交集**（渲染失败的文件绝不能进删除名单）。
- **去重簇跨年份占比**：`(kept, recyc)` 两路径的年份集合 >1 即跨年份重复，正是用户描述的「不同年份目录」场景。
- **格式分布**：保留 `.pdf` 远多于 `.tif` 说明默认「最新年份+最大文件」偏向 pdf；若用户要保留原图号扫描件需另议 keep-best 权重。
- 先 dry-run 出报告、人工抽样核验（尤其看「保留 vs 删除」是否真的是同一张图），确认后再执行 `send2trash`。

## 实测数据锚点（2026-08-13 沈阳山泰报价单）

⚠️ **两版对比（同名约束+贪心法前后的差异，直接证明护栏价值）**：

| 版本 | 分组键 | 护栏 | 簇数 | 待删 | 渲染失败 |
|---|---|---|---|---|---|
| v1（旧·有 bug） | canon 零填充 | 仅库/改版/类型（漏同名） | 484 | **1023** | 779 |
| v3（修正） | 精确 norm_pn | 同名+库+改版+类型+贪心代表 | **409** | **431** | 3 |

- v3：2165 个同图号异内容组、5415 文件、5415 唯一 MD5（norm_pn 比 canon 分组更细）
- 431 待删中：107 份视觉完全相同（dHash=0）、324 份近同重扫（dHash 1-6）；跨年份簇 315
- 高危实证：v1 因漏「同名约束」产生 127 个误合并簇（289 文件，如 `л.3/л.4/л.5/л.6` 不同页、`BM31HF` vs `BRE250` 不同设备）；补上后全部保住

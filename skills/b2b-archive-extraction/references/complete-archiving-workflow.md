# 完整归档流程：解压后文件归组

> 配套 SKILL.md 中「完整归档流程」章节的详细实现参考。
> 目标：零残留压缩包 + 零平放文件（或仅剩无法归组的散件）。

## 背景

解压乱码修复后，常有文件因乱码期间无法正确识别 `№-` 前缀而被遗漏在顶层。完整归档流程对全部平放文件执行多轮渐进式归组。

## 实战案例（2026-08-12）

五个项目归档文件夹（1223570/1225472/1223588/1224501/1224579），284 个乱码文件修复后重新归档。初始状态：

| 项目 | 顶层文件 | 归档后 | 残留档案 | 最终状态 |
|:-----|------:|-----:|:------:|:---:|
| 1223570 | 469 | 1,711 文件 | 32 个 .7z | ✅ 0 loose |
| 1225472 | 354 | 2,018 文件 | 0 | ✅ 0 loose |
| 1223588 | 47 | 207 文件 | 0 | ✅ 0 loose |
| 1224501 | 540 | 765 文件 | 0 | ⚠ 11 loose |
| 1224579 | 307 | 698 文件 | 0 | ✅ 0 loose |

## 完整 Python 实现

### 第 1 轮：`№-` 前缀归组

```python
import os, re, shutil, hashlib

def md5_file(filepath):
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def group_by_number_prefix(proj_path):
    """Group top-level files by №- prefix into numbered folders."""
    moved = skipped = dupes = conflicts = 0
    
    for fname in os.listdir(proj_path):
        fpath = os.path.join(proj_path, fname)
        if not os.path.isfile(fpath):
            continue
        
        m = re.match(r'^(\d+)-(.+)', fname)
        if not m:
            skipped += 1
            continue
        
        num = m.group(1)
        dst_dir = os.path.join(proj_path, num)
        dst_path = os.path.join(dst_dir, fname)
        os.makedirs(dst_dir, exist_ok=True)
        
        if os.path.exists(dst_path):
            if md5_file(fpath) == md5_file(dst_path):
                os.remove(fpath)  # identical → delete source
                dupes += 1
            else:
                # Different content → _v2 suffix
                name, ext = os.path.splitext(fname)
                v2_name = f"{name}_v2{ext}"
                shutil.move(fpath, os.path.join(dst_dir, v2_name))
                conflicts += 1
        else:
            shutil.move(fpath, dst_path)
            moved += 1
    
    return moved, skipped, dupes, conflicts
```

### 第 2-4 轮：非标准命名智能匹配

```python
def smart_group_remaining(proj_path):
    """Multi-pass handling for files without clear №- prefix."""
    existing_nums = {d for d in os.listdir(proj_path) 
                     if os.path.isdir(os.path.join(proj_path, d)) and d.isdigit()}
    
    remaining = [f for f in os.listdir(proj_path) 
                 if os.path.isfile(os.path.join(proj_path, f))]
    
    for fname in remaining:
        src = os.path.join(proj_path, fname)
        folder = None
        
        # Rule A: Thumbs.db → delete
        if fname.lower() == 'thumbs.db':
            os.remove(src)
            continue
        
        # Rule B: Leading digit ≥4 chars + folder exists
        m = re.match(r'^(\d{4,})', fname)
        if m and m.group(1) in existing_nums:
            folder = m.group(1)
        
        # Rule C: ч. drawing number → folder must exist
        if not folder:
            m = re.search(r'[чЧ]\s*\.\s*(\d+)', fname)
            if m and m.group(1) in existing_nums:
                folder = m.group(1)
        
        # Rule D: img- pattern → always create folder
        if not folder:
            m = re.match(r'img-(\d+)-', fname)
            if m:
                folder = m.group(1)
        
        # Rule E: MYSCAN pattern → always create folder
        if not folder:
            m = re.match(r'MYSCAN_(\d+)_', fname)
            if m:
                folder = m.group(1)
        
        # Rule F: scan pattern → always create folder
        if not folder:
            m = re.match(r'scan(\d+)\.', fname)
            if m:
                folder = m.group(1)
        
        # Rule G: СК/М drawing numbers → always create folder
        if not folder:
            for prefix in ['СК', 'М']:
                m = re.search(rf'{prefix}(\d+)', fname)
                if m:
                    folder = m.group(1)
                    break
        
        if folder:
            dst_dir = os.path.join(proj_path, folder)
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, os.path.join(dst_dir, fname))
```

### 第 5 轮：零件名归组

```python
def group_by_part_name(proj_path):
    """Group remaining files by shared part name."""
    remaining = [f for f in os.listdir(proj_path) 
                 if os.path.isfile(os.path.join(proj_path, f))]
    
    # Normalize names: strip trailing numbers, collapse whitespace
    groups = {}
    for fname in remaining:
        base = re.sub(r'\s*\d+', '', os.path.splitext(fname)[0])
        base = re.sub(r'\s+', ' ', base).strip()
        if base:
            groups.setdefault(base, []).append(fname)
    
    # Only group if ≥2 files share same base name
    for base_name, files in groups.items():
        if len(files) >= 2:
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
            dst_dir = os.path.join(proj_path, safe_name)
            os.makedirs(dst_dir, exist_ok=True)
            for f in files:
                src = os.path.join(proj_path, f)
                if os.path.exists(src):
                    shutil.move(src, os.path.join(dst_dir, f))
```

### 验证函数

```python
def verify_archiving(proj_path):
    """Return (loose_count, archive_count, total_files)."""
    loose = [x for x in os.listdir(proj_path) 
             if os.path.isfile(os.path.join(proj_path, x))]
    archives = 0
    total = 0
    for root, dirs, files in os.walk(proj_path):
        total += len(files)
        for f in files:
            if f.lower().endswith(('.7z', '.rar', '.zip', '.gz')):
                archives += 1
    return len(loose), archives, total
```

## 陷阱

- **img- 文件匹配时文件夹可能不存在**：img-/MYSCAN/scan 模式创建新文件夹（不要求已存在），而 ч./СК/М 模式仅当目标文件夹已存在时才移动——避免为 1 个文件创建孤岛文件夹
- **单文件散件不要创建文件夹**：`Untitled.pdf`、`Корпус.tif` 这类无编号单文件保持平放，在报告中标注「无法归组」而非当作错误
- **Thumbs.db 先删后处理**：Windows 缩略图缓存文件是噪音，在所有轮次之前清理
- **多轮归组后文件夹数可能暴涨**：img- 模式的一次扫描可能创建 60+ 个新文件夹（每个扫描编号一个），这是正常现象
- **CC/СС 图纸号（如 `СС 40.173.00.000`）用 compact digits 方案**：提取全部数字拼接成文件夹名（`4017300000`），避免截断首段造成不同零件混入同一文件夹

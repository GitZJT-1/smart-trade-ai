# 解压后文件夹改名：非纯数字 → 纯数字编号

## 背景
招标压缩包解压后，产物文件夹名通常带俄文描述（如 `1007-Ролик ч.1.07.49.12.03.00.000сб`、`Барабан натяжной СС 40.363.00.000 СБ`），需要统一改为纯数字编号以匹配用户归档规范。

## 改名策略（优先级从高到低）

### 1. 从文件夹名提取前导数字
```python
import re
m = re.match(r'^(\d+)', folder_name)
if m:
    new_name = m.group(1)  # "1007-Ролик..." → "1007"
```

### 2. 从原始压缩包名推断
压缩包 `691-Барабан натяжной СС 40.363.00.000 СБ.7z` 解压后产物文件夹可能是 `Барабан натяжной СС 40.363.00.000 СБ`（去掉了编号前缀）。此时通过匹配原始包名中俄文部分定位编号：
```
archive: "691-Барабан натяжной СС 40.363.00.000 СБ.7z"
output folder: "Барабан натяжной  СС 40.363.00.000 СБ"
→ target number: 691
```

### 3. 从俄文关键词反查
`печной`（炉子的）来自 `164-187_Свод печи новый` — 通过关键词 `печи` ↔ `печной` 匹配。

`RA 20104 00 000` 来自 `142-153_Платформа ч.RA20104.00.000СБ` — 通过图号 `RA20104` 匹配。

## 冲突处理：目标编号文件夹已存在
当 `1007-Ролик...` 要改名为 `1007` 但 `1007/` 已存在时：
1. **逐文件比对**源和目标中同名文件的大小（`os.path.getsize`）
2. 大小完全一致 → 重复解压产物，安全删除源文件夹（`shutil.rmtree`）
3. 大小不一致或仅源有 → `shutil.move` 移入目标
4. 源清空后 `os.rmdir` 删除空目录

**案例**：1225472 归档中 `25-Скоба зажима М428.02.07/` 与 `25/` 同时存在——子目录 `Скоба зажима М428.02.07` 在两边各有 5 个相同文件，确认后删除源。

## 乱码文件夹名（Mojibake）
俄文名在 Windows 下可能解压成 GBK 乱码（如 `娻氆_憡1643.00.000憗` = `Крыло СК1643.00.000СБ`）。处理方式同正常文件夹——匹配到原始包名后改名。

## 完整流程示例（Python 伪代码）
```python
import os, re, shutil

# Phase 1: rename clean cases (leading number, target doesn't exist)
for folder in non_numeric_folders:
    m = re.match(r'^(\d+)', folder)
    if m and not os.path.exists(target_path):
        os.rename(src, target_path)

# Phase 2: handle conflicts (merge or verify-and-delete)
for folder in non_numeric_folders:
    if os.path.exists(target_path):
        for item in os.listdir(src):
            if os.path.exists(os.path.join(target, item)):
                if os.path.getsize(src_item) == os.path.getsize(dst_item):
                    continue  # duplicate, skip
            else:
                shutil.move(src_item, dst_item)
        if not os.listdir(src):
            os.rmdir(src)
        # else: report remaining items
```

# 跨项目归档修复 — 交叉匹配文件补档

## 场景

多项目匹配执行后发现交叉匹配文件（同一源文件命中多个项目清单）只归档到了一个项目，
另一个项目缺少该文件。源文件可能已被 `shutil.move` 移除，无法从源目录重新获取。

## 修复策略：从已有归档复制

源文件虽然不在原始共享库，但已在其中一个项目的归档目录中。
从已有项目归档复制到缺失项目归档。

### 步骤

1. **加载匹配日志**：读取 `tmp_match_log_{projA}_{projB}.json`，
   筛选 `len(projects) == 2` 的交叉匹配项

2. **构建目标文件集合**：用 `os.path.basename(source_path).lower()` 作为唯一键

3. **双向扫描归档目录**：遍历两个项目的 `归档/` 目录树，
   对每个归档文件（格式 `{item_no}-{original_filename}`），
   检查 `-{target_lower}` 子串匹配（处理 `1090-47 Боек 1564.01.004.tif` 这类命名）

4. **找出缺失端**：`found_A - found_B` = 只在 A，需补到 B

5. **执行复制**：
   - 目标目录：`{archive_B}/{item_no_B}/`
   - 目标文件名：`{item_no_B}-{original_filename}`
   - 用 `shutil.copy2` 保留时间戳

6. **验证**：双向再扫一次，确认 `found_in_both == target_set`

### 关键代码片段

```python
def find_in_archive(arch_dir, targets_lower):
    """返回 archives 中匹配 targets 的 lowercase 文件名集合"""
    found = set()
    for root, dirs, files in os.walk(arch_dir):
        for f in files:
            fl = f.lower()
            for t in targets_lower:
                if fl.endswith(t) or f'-{t}' in fl:
                    found.add(t)
    return found
```

### 陷阱

- **文件名大小写**：俄语文件名中 `Б` vs `б`、`.TIF` vs `.tif` — 统一 lowercase
- **归档前缀**：归档文件是 `{item_no}-{original_name}`，匹配时用 `-{target}` 子串
- **源文件不在原始路径**：`shutil.move` 后源路径失效，必须从已有归档复制
- **`shutil.copy2` 非 `move`**：交叉匹配场景下永远不要 move，每个项目独立拥有一份副本

## 2026-08-11 实例

1225472 × 1223570 双项目匹配，41 个唯一交叉文件，35 个只在 1223570 归档。
从 `1223570_归档` 复制 35 次到 `1225472_归档`，全部验证通过。

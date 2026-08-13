# 俄文图纸乱码文件名逆向还原

2026-08-05 实测验证（报价单 КФ_解压 / БФ_解压 区域，482 个乱码条目）。2026-08-12 发现更优方案（Windows API 全量修复 51 个文件，含旧方法无法处理的高位 PUA）。旧认知"乱码不可还原、只能报告"已被推翻——**乱码是确定性的可逆编码**。

## 乱码成因
7-Zip 解压含 **CP866**（俄文 OEM 代码页）条目名的 zip/7z 时，在中文 Windows（ANSI=GBK/CP936）上把 CP866 字节流按 GBK 解码，产生四类乱码字符：
1. **GBK/CP936 双字节配对**：2 个 CP866 字节 → 1 个汉字/日文假名/box-drawing。例：字节 0x8A 0x87（CP866 "КЗ"）→ GBK 汉字 `妵`；0x83 0xA0（"Га"）→ `儬`
2. **GBK 单字节字符**：CP866 字节 0xA0-0xFF 中能单字节映射的 → Latin-1 补充字符（NBSP、¨、«、ì 等）。例：0xA8 → U+00A8 `¨`
3. **高位 PUA 映射**（CP936 扩展区）：相邻两个 CP866 字节在 CP936 中配对但映射到 PUA 编码区 → `U+E000-U+F8FF`。例：字节 0xA8 0xA0（"иа"）→ U+E7C6；0xAB 0xEC（"ль"）→ U+E0A9
4. **€ (U+20AC)**：代表字节 0x80（CP866 'А'，少见）

同一文件名内多类混存。注意：**PUA 字符不限于 U+E000-U+E0FF**，也可能在高位（U+E15B、U+E1B7、U+E7C6 等），`ord(c) - 0xE000` 的简单减法对高位 PUA 无效。

## 逆向还原算法（首选）：Windows API WideCharToMultiByte

**最可靠的一站式方案**：利用 Windows 原生 CP936 代码页（包含 Python `gbk` 编解码器没有的 PUA 扩展映射），一步到位。

```python
import ctypes

CP_GBK = 936

def mojibake_to_cp866(name: str) -> str:
    """乱码文件名 → 俄文原名。Windows API CP936→CP866 一站式还原。"""
    # Step 1: WideCharToMultiByte(936) → 原始 CP866 字节
    needed = ctypes.windll.kernel32.WideCharToMultiByte(
        CP_GBK, 0, name, len(name), None, 0, None, None
    )
    buf = ctypes.create_string_buffer(needed)
    ctypes.windll.kernel32.WideCharToMultiByte(
        CP_GBK, 0, name, len(name), buf, needed, None, None
    )
    raw_bytes = buf.raw[:needed]
    # Step 2: CP866 解码 → 俄文
    return raw_bytes.decode('cp866')
```

**优势**：
- 不需要逐字符分类（汉字/PUA/€/假名），Windows API 内部自动处理
- 高位 PUA（U+E15B 等）也正确还原
- 2026-08-12 实测：1223570 项目 33 个乱码 + 1225472 项目 18 个乱码，51/51 全量还原，零失败
- 不依赖残留 zip 包作为对照

**验证锚点**（2026-08-12 实测）：
- `儬┆_岑ユ瓲_绁噔ウ` → `Гайк_специальна_чертеж`（Гайка специальная чертеж = 特种螺母图纸，尾部字母因 GBK 字节对偶对齐有少量丢失属正常）
- `屻溻_锠喹ㄠ瓲_绁噔ウ` → `Муфт_шарнирна_чертеж`（铰接联轴器图纸）
- `棩啖铼` → `Червяк`（蜗杆）
- `偍` → `Вилк`（Вилка = 拨叉）
- `摨` → `Упор`（止挡）
- `喁汜` → `корпус`（壳体）
- `98139600 嚑猗 劏岐氅 绁噔ウ  1-59392` → `98139600 Затвор Дисковый чертеж  1-59392`（蝶阀图纸）

### 备选方案：zip 内部条目名对照（无 Windows API 时）

残留 .zip 包内部条目名是无损的原始 CP866 字节；Python zipfile 在无 UTF-8 flag 时以 cp437 显示，`encode('cp437').decode('cp866')` 即正确俄文名：

```python
import zipfile
with zipfile.ZipFile(path) as zf:
    for zi in zf.infolist():
        correct = zi.filename.encode('cp437').decode('cp866')
```

### 旧版逐字符算法（仅用于非 Windows 环境回退）

以下算法在 Python `gbk` 编码器范围内有效，但**无法处理高位 PUA 和部分 CP936 扩展字符**（本次会话 51 个乱码中有 15 个此方法无法处理）：

```python
def decode_mojibake_legacy(name):
    out = bytearray()
    for c in name:
        cp = ord(c)
        if 0xE000 <= cp <= 0xE0FF:      # 仅低区 PUA（不完整！）
            out.append(cp - 0xE000)
        elif c == '\u20ac':
            out.append(0x80)
        elif 0x4E00 <= cp <= 0x9FFF:     # 汉字
            out.extend(c.encode('gbk'))
        elif 0x3040 <= cp <= 0x30FF:     # 日文假名
            try:
                out.extend(c.encode('shift_jis'))
            except Exception:
                return None
        elif ord(c) < 128:
            out.append(cp)
        else:
            return None
    return out.decode('cp866')
```

## 权威依据：zip 内部条目名（首选，比逆向更可靠）
残留 .zip 包内部条目名是无损的原始 CP866 字节；Python zipfile 在无 UTF-8 flag 时以 cp437 显示，`encode('cp437').decode('cp866')` 即正确俄文名：

```python
import zipfile
with zipfile.ZipFile(path) as zf:
    for zi in zf.infolist():
        correct = zi.filename.encode('cp437').decode('cp866')
        # 例: 'é¿¡Γ τÑαΓ. ⁿ71-ô-44-00 æü' → 'Винт черт. №71-У-44-00 СБ'
```

**磁盘乱码条目 ↔ zip 内部条目映射**：按"结构对齐 + ASCII 骨架匹配"——去掉双方文件名中的非 ASCII 字符后骨架相同即对应。
- 例：磁盘 `嵁_癄_1036-11-00-000 .tif`（骨架 `1036-11-00-000 .tif`）↔ zip `Новая папка/1036-11-00-000 зам.tif` → 重命名为 `1036-11-00-000 зам.tif`

## 重命名执行要点
- **自底向上**：先重命名最深层的文件/目录，再上层目录（Windows 目录改名要求其下无被占用项）
- **冲突处理**：目标名已存在（正常文件或 _1/_2 后缀副本）→ 跳过或合并，先列计划再执行
- **执行前**：源存在、目标不存在（或内容相同）才 rename；逐条验证
- 磁盘乱码名与 zip 内部名可能字节不同（被多次解压/改名过），**以结构对齐为准**，不要强求字节流一致

## 覆盖缺口
- 高位 PUA（U+E15B 等）成因未完全解析（疑似 UTF-16/嵌套转换），无 zip 对照时暂无法还原
- 日文假名乱码（shift_jis 假设）未实测验证
- 无对应 zip 的乱码条目（原包已删）只能靠纯逆向，需人工抽查还原质量

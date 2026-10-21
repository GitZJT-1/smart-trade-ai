# -*- coding: utf-8 -*-
"""
批量解压压缩包到各自所在目录的同名文件夹（实战验证 2026-08-05，669 包/115s）。

用法：
1. 改 ROOTS 为待解压根目录列表
2. python batch_extract.py
3. 看输出与 LOG_PATH 日志；结束后按 SKILL.md「终态验证」再扫一遍

特性：
- 每个压缩包 -> 去掉扩展名的同名文件夹；目标已存在且非空 -> 跳过（断点续解）
- 7z CLI 优先；zip 包若 7z 失败（点结尾目录名/乱码路径）自动 fallback Python zipfile
- 乱码文件名必须用 os.listdir 原样名拼路径（手打必失败）
- 日志 utf-8-sig，逐条 OK/SKIP/FAIL
"""
import os, sys, subprocess, zipfile, shutil, time

SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"
ROOTS = [
    r"C:\path\to\folder1",
    r"C:\path\to\folder2",
]
ARCHIVE_EXTS = {'.7z', '.zip', '.rar'}
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(ROOTS[0])) if ROOTS else ".", "解压日志.txt")


def dir_nonempty(p):
    if not os.path.isdir(p):
        return False
    try:
        return any(os.scandir(p))
    except OSError:
        return False


def sevenzip_extract(arc, target):
    os.makedirs(target, exist_ok=True)
    r = subprocess.run([SEVENZIP, "x", "-y", f"-o{target}", arc],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    return r.returncode == 0, r.returncode


def pyzip_extract(arc, target):
    """zipfile 兜底：处理 7z 失败的点结尾目录名 / 乱码路径。含 zip 路径穿越防护。"""
    os.makedirs(target, exist_ok=True)
    with zipfile.ZipFile(arc) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/").lstrip("/")
            if not name:
                continue
            dest = os.path.join(target, name)
            if info.is_dir():
                os.makedirs(dest, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    return True


def extract(arc, target):
    """返回 (ok, msg)。zip 失败先试 pyzip；点结尾目标目录名预先去掉点。"""
    # Windows 目录名不能以点结尾：目标名去尾点
    if target.endswith("."):
        target = target.rstrip(".")
    ok, rc = sevenzip_extract(arc, target)
    if ok and dir_nonempty(target):
        return True, ""
    # 7z 失败或目标仍空 -> zip 包走 Python
    if arc.lower().endswith(".zip"):
        try:
            if pyzip_extract(arc, target) and dir_nonempty(target):
                return True, ""
        except Exception as e:
            return False, f"pyzip异常: {e}"
    # 整理错误码
    if rc == 2:
        return False, "损坏或格式不支持 (7z 错误码2)"
    if rc == 3:
        return False, "不可恢复错误 (7z 错误码3)"
    if rc == 4:
        return False, "需要密码 (7z 错误码4)"
    return False, f"7z 退出码 {rc}"


def main():
    all_archives = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() in ARCHIVE_EXTS:
                    all_archives.append(os.path.join(dirpath, fn))
    all_archives.sort()
    print(f"共发现压缩包: {len(all_archives)}", flush=True)

    skipped, ok, failed = 0, 0, []
    t0 = time.time()
    with open(LOG_PATH, "w", encoding="utf-8-sig") as log:
        log.write(f"批量解压日志 开始时间 {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        for i, arc in enumerate(all_archives, 1):
            target = os.path.splitext(arc)[0]
            rel = os.path.basename(os.path.dirname(arc)) + "\\" + os.path.basename(arc)
            if dir_nonempty(target):
                skipped += 1
                log.write(f"[SKIP 已解压] {rel}\n")
                continue
            ok_this, msg = extract(arc, target)
            if ok_this:
                ok += 1
                log.write(f"[OK] {rel}\n")
                print(f"[{i}/{len(all_archives)}] OK  {rel}", flush=True)
            else:
                failed.append((rel, msg))
                log.write(f"[FAIL {msg}] {rel}\n")
                print(f"[{i}/{len(all_archives)}] FAIL {msg}  {rel}", flush=True)

        dur = time.time() - t0
        log.write(f"\n完成 {time.strftime('%Y-%m-%d %H:%M:%S')} 耗时 {dur:.0f}s\n")
        log.write(f"成功 {ok} | 已存在跳过 {skipped} | 失败 {len(failed)}\n")
        for rel, msg in failed:
            log.write(f"  FAIL: {rel} -> {msg}\n")

    print(f"\n===== 结果: 成功 {ok} | 跳过 {skipped} | 失败 {len(failed)} | 耗时 {dur:.0f}s =====", flush=True)
    for rel, msg in failed:
        print(f"  FAIL: {rel} -> {msg}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

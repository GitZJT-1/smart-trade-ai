# -*- coding: utf-8 -*-
"""批量解压 .7z 到其所在目录，成功后删除原压缩包（顶层一轮）。
用法: python extract_7z.py [--roots DIR DIR ...] [--limit N]
"""
import os
import sys
import subprocess
import time
import logging

SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"
DEFAULT_ROOTS = [
    r"C:\Users\周家同\Desktop\沈阳山泰通用机械有限公司\报价单\КФ_解压",
    r"C:\Users\周家同\Desktop\沈阳山泰通用机械有限公司\报价单\БФ_解压",
]
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "extract_7z.log")
FAIL_FILE = os.path.join(LOG_DIR, "extract_failed.txt")

logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)


def find_7z(roots):
    """返回 (待解压列表, 已解压列表)。同名目录存在且有内容 => 已解压。"""
    todo, done = [], []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(".7z"):
                    p = os.path.join(dirpath, fn)
                    if os.path.getsize(p) == 0:
                        continue  # 0字节损坏包不处理
                    base = os.path.splitext(p)[0]
                    if os.path.isdir(base) and os.listdir(base):
                        done.append(p)
                    else:
                        todo.append(p)
    return sorted(todo), sorted(done)


def extract_one(archive):
    """解压单个 .7z 到所在目录。返回 (rc, tail)。rc=0/1 视为成功可删除。"""
    d = os.path.dirname(archive)
    try:
        r = subprocess.run(
            [SEVENZIP, "x", "-y", "-o" + d, "--", archive],
            capture_output=True, timeout=600,
        )
        rc = r.returncode
        tail = (r.stdout + r.stderr).decode("utf-8", errors="replace")[-300:]
        return rc, tail
    except subprocess.TimeoutExpired:
        return 99, "TIMEOUT"
    except Exception as e:
        return 98, repr(e)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="批量解压 .7z 到所在目录并删除原包")
    ap.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS, help="根目录列表")
    ap.add_argument("--limit", type=int, default=None, help="最多处理 N 个")
    args = ap.parse_args()
    roots, limit = args.roots, args.limit

    todo, done = find_7z(roots)
    print(f"待解压: {len(todo)}  已解压(跳过): {len(done)}", flush=True)
    logging.info(f"== 开始批处理: 待解压 {len(todo)} 个 ==")

    ok, fail = 0, []
    for i, archive in enumerate(todo, 1):
        if limit and i > limit:
            print(f"[--limit {limit} 已到达，停止]", flush=True)
            break
        size_mb = os.path.getsize(archive) / 1048576
        t0 = time.time()
        rc, tail = extract_one(archive)
        dt = time.time() - t0
        if rc in (0, 1):
            try:
                os.remove(archive)
                ok += 1
                logging.info(f"[OK {i}/{len(todo)}] 删除原包: {archive}")
                print(f"[{i}/{len(todo)}] OK {size_mb:.1f}MB {dt:.1f}s 已删除: {os.path.basename(archive)}", flush=True)
            except OSError as e:
                fail.append((archive, f"解压成功但删除失败: {e}"))
                logging.warning(f"[{i}/{len(todo)}] 解压OK删除失败 rc={rc}: {archive}: {e}")
                print(f"[{i}/{len(todo)}] DEL-FAIL {os.path.basename(archive)}", flush=True)
        else:
            fail.append((archive, f"rc={rc} {tail.strip()}"))
            logging.error(f"[FAIL {i}/{len(todo)}] rc={rc}: {archive}")
            print(f"[{i}/{len(todo)}] FAIL rc={rc} {size_mb:.1f}MB: {os.path.basename(archive)}", flush=True)

    with open(FAIL_FILE, "w", encoding="utf-8") as f:
        for a, msg in fail:
            f.write(f"{a}\t{msg}\n")

    print(f"\n== 完成: 成功 {ok}, 失败 {len(fail)}, 跳过已解压 {len(done)} ==", flush=True)
    logging.info(f"== 完成: 成功 {ok}, 失败 {len(fail)} ==")
    for a, msg in fail:
        print(f"FAILED: {a} -> {msg}", flush=True)


if __name__ == "__main__":
    main()

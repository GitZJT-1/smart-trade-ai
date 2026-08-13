# -*- coding: utf-8 -*-
"""迭代解压所有嵌套 .7z：每轮扫描解压并删除原包，直到无 .7z 残留。
防无限循环：最多 15 轮；若某轮无进展则停止。
用法: python extract_nested_7z.py [--roots DIR DIR ...]
"""
import os
import subprocess
import logging

SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"
ROOTS = [
    r"C:\Users\周家同\Desktop\沈阳山泰通用机械有限公司\报价单\КФ_解压",
    r"C:\Users\周家同\Desktop\沈阳山泰通用机械有限公司\报价单\БФ_解压",
]
LOGDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
logging.basicConfig(
    filename=os.path.join(LOGDIR, "extract_nested.log"),
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)


def scan(roots=None):
    roots = roots or ROOTS
    out = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(".7z"):
                    p = os.path.join(dirpath, fn)
                    if os.path.getsize(p) > 0:
                        out.append(p)
    return sorted(out)


def extract_one(archive):
    d = os.path.dirname(archive)
    try:
        r = subprocess.run([SEVENZIP, "x", "-y", "-o" + d, "--", archive],
                           capture_output=True, timeout=600)
        return r.returncode
    except Exception as e:
        logging.error(f"extract exception {archive}: {e}")
        return 98


def main():
    import argparse
    ap = argparse.ArgumentParser(description="迭代解压嵌套 .7z 并删除原包")
    ap.add_argument("--roots", nargs="*", default=ROOTS, help="根目录列表")
    args = ap.parse_args()
    roots = args.roots

    fail = []  # (path, stage)
    for rnd in range(1, 16):
        todo = scan(roots)
        if not todo:
            print(f"第{rnd}轮: 无 .7z 残留，完成。", flush=True)
            return
        ok = 0
        for p in todo:
            rc = extract_one(p)
            if rc in (0, 1):
                try:
                    os.remove(p)
                    ok += 1
                    logging.info(f"[R{rnd}] OK {p}")
                except OSError as e:
                    fail.append((p, f"del:{e}"))
                    logging.warning(f"[R{rnd}] del-fail {p}: {e}")
            else:
                fail.append((p, f"rc={rc}"))
                logging.error(f"[R{rnd}] FAIL rc={rc} {p}")
        print(f"第{rnd}轮: 处理 {len(todo)} 个，成功删除 {ok} 个，失败 {len(todo)-ok} 个", flush=True)
        if ok == 0:
            print("无进展，停止迭代。", flush=True)
            break
    # 最终扫描
    todo = scan(roots)
    print(f"\n最终剩余 .7z: {len(todo)}", flush=True)
    for p in todo:
        print("  REMAIN:", p, flush=True)
    print(f"\n处理失败列表: {len(fail)}", flush=True)
    for p, msg in fail:
        print(f"  FAILED {p} -> {msg}", flush=True)


if __name__ == "__main__":
    main()

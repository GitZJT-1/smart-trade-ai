# -*- coding: utf-8 -*-
"""重试删除被占用的 .7z 原包（解压已完成，仅删除失败）。
用法: python retry_delete_7z.py [--fail-file PATH] [--delay SECONDS] [--rounds N]
"""
import os
import sys
import time

LOGDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
FAIL_FILE = os.path.join(LOGDIR, "extract_failed.txt")
DELAY = 20  # 每轮等待秒数
ROUNDS = 5


def load_paths(fail_file):
    with open(fail_file, encoding="utf-8") as f:
        return [l.split("\t")[0] for l in f.read().splitlines() if l.strip()]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="重试删除解压后仍被占用的 .7z 原包")
    ap.add_argument("--fail-file", default=FAIL_FILE)
    ap.add_argument("--delay", type=float, default=DELAY)
    ap.add_argument("--rounds", type=int, default=ROUNDS)
    args = ap.parse_args()

    paths = load_paths(args.fail_file)
    print(f"待重试删除: {len(paths)}", flush=True)

    for attempt in range(1, args.rounds + 1):
        remaining = []
        for p in paths:
            if not os.path.exists(p):
                continue  # 已删除
            try:
                os.remove(p)
                print(f"[轮{attempt}] OK 已删除: {os.path.basename(p)}", flush=True)
            except OSError as e:
                remaining.append(p)
        paths = remaining
        if not paths:
            print("== 全部删除成功 ==", flush=True)
            break
        print(f"[轮{attempt}] 剩余 {len(paths)} 个, 等待 {args.delay}s 后重试...", flush=True)
        time.sleep(args.delay)

    if paths:
        print(f"\n== 仍有 {len(paths)} 个无法删除 ==", flush=True)
        for p in paths:
            print("  STILL LOCKED:", p, flush=True)
    else:
        print("== 完成 ==", flush=True)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
download_resumable.py — MinIO S3 并行分块下载器 (boto3, 8线程 x 8MB, 断点续传)
本会话实测可用（2026-08-04，tender.pro MinIO）。

用法:
  python download_resumable.py --targets targets.json --dir "目标目录"

targets.json 格式:
  {"keys": ["文件1.7z", "文件2.7z"], "milestone_index": 0}
  milestone_index: 该文件完成时打印 ASCII 里程碑标记 (=== MILESTONE_XXX_DONE ===)，供外部 watch_patterns 捕获

特性:
  - 分块下载到 <目标>/<文件名>.blocks/000000 等，断点续传（已有完整块跳过）
  - 每轮重试未完成块 (MAX_ROUNDS)，掉速/断线自动续
  - 全部块完成后合并为最终文件并清理分块
  - 进度写 <目标>/_下载日志.txt + stdout
"""
import argparse
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.config import Config

ENDPOINT = os.environ.get("TENDER_S3_ENDPOINT", "http://minio.pc1.tender.pro:9000")
ACCESS = os.environ.get("TENDER_S3_ACCESS", "MINIO_ACCESS_KEY")
SECRET = os.environ.get("TENDER_S3_SECRET", "MINIO_SECRET_KEY")
BUCKET = os.environ.get("TENDER_S3_BUCKET", "MINIO_BUCKET")
BLOCK = 8 * 1024 * 1024  # 8MB
WORKERS = 8
MAX_ROUNDS = 40

_lock = threading.Lock()


def get_client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS,
        aws_secret_access_key=SECRET,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 4},
            connect_timeout=30,
            read_timeout=300,
        ),
    )


def log(msg, log_path=None):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if log_path:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def head_size(client, key):
    r = client.head_object(Bucket=BUCKET, Key=key)
    return int(r["ContentLength"])


def fetch_block(client, key, i, start, want, block_dir, log_path):
    """下载一个分块到 block_dir/{i:06d}。成功返回 True。"""
    bf = os.path.join(block_dir, f"{i:06d}")
    if os.path.exists(bf) and os.path.getsize(bf) == want:
        return True
    tmp = bf + ".tmp"
    try:
        resp = client.get_object(Bucket=BUCKET, Key=key, Range=f"bytes={start}-{start + want - 1}")
        with open(tmp, "wb") as f:
            while True:
                chunk = resp["Body"].read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.getsize(tmp) == want:
            os.replace(tmp, bf)
            return True
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    except Exception as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        with _lock:
            log(f"    [block {i} err] {type(e).__name__}: {str(e)[:120]}", log_path)
        return False


def download_file(client, key, dest_dir, log_path, milestone=False):
    fname = os.path.basename(key) or key.replace("/", "_")
    final_path = os.path.join(dest_dir, fname)
    size = head_size(client, key)
    if os.path.exists(final_path) and os.path.getsize(final_path) == size:
        log(f"[SKIP] {fname} 已完整存在", log_path)
        return "done"

    nblocks = (size + BLOCK - 1) // BLOCK
    block_dir = final_path + ".blocks"
    os.makedirs(block_dir, exist_ok=True)

    have = 0
    pending = []
    for i in range(nblocks):
        start = i * BLOCK
        want = min(BLOCK, size - start)
        bf = os.path.join(block_dir, f"{i:06d}")
        if os.path.exists(bf) and os.path.getsize(bf) == want:
            have += 1
        else:
            pending.append((i, start, want))
    log(f"[START] {fname} ({size/1024/1024/1024:.2f} GB, {nblocks} 块, 已有 {have}, 待下 {len(pending)})", log_path)

    total_done_all = [have * BLOCK]
    start_t = time.time()

    for round_no in range(1, MAX_ROUNDS + 1):
        if not pending:
            break
        log(f"  [ROUND {round_no}] 待下 {len(pending)} 块", log_path)
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(fetch_block, client, key, i, st, w, block_dir, log_path): (i, st, w) for i, st, w in pending}
            for fut in as_completed(futs):
                i, st, w = futs[fut]
                if fut.result():
                    with _lock:
                        total_done_all[0] += w
                        el = time.time() - start_t
                        speed = total_done_all[0] / 1024 / 1024 / el if el > 0 else 0
                        if total_done_all[0] % (16 * 1024 * 1024) < w:
                            log(
                                f"  ... {total_done_all[0]/1024/1024:.1f}/{size/1024/1024:.1f} MB "
                                f"({total_done_all[0]*100/size:.1f}%) {speed:.2f} MB/s",
                                log_path,
                            )
        pending = [
            (i, st, w) for i, st, w in pending
            if not (os.path.exists(os.path.join(block_dir, f"{i:06d}"))
                    and os.path.getsize(os.path.join(block_dir, f"{i:06d}")) == w)
        ]
        if pending:
            log(f"  [ROUND {round_no} 结束] 完成 {nblocks - len(pending)}/{nblocks} 块, 剩余 {len(pending)}", log_path)
            time.sleep(5)

    if pending:
        log(f"[ERROR] {fname} 还有 {len(pending)} 块未完成, 保留分块待续传", log_path)
        return "error"

    log(f"[MERGE] {fname} 合并 {nblocks} 块...", log_path)
    tmp_final = final_path + ".merging"
    with open(tmp_final, "wb") as out:
        for i in range(nblocks):
            bf = os.path.join(block_dir, f"{i:06d}")
            with open(bf, "rb") as f:
                while True:
                    chunk = f.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
    if os.path.getsize(tmp_final) != size:
        os.remove(tmp_final)
        log(f"[ERROR] {fname} 合并大小不符, 保留分块", log_path)
        return "error"
    os.replace(tmp_final, final_path)
    for i in range(nblocks):
        try:
            os.remove(os.path.join(block_dir, f"{i:06d}"))
        except OSError:
            pass
    try:
        os.rmdir(block_dir)
    except OSError:
        pass
    log(f"[COMPLETE] {fname} ({size} bytes)", log_path)
    if milestone:
        print("=== MILESTONE_MPAR_DONE ===", flush=True)
    return "done"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()

    cfg = json.load(open(args.targets, encoding="utf-8"))
    keys = cfg["keys"]
    milestone_idx = int(cfg.get("milestone_index", -1))
    os.makedirs(args.dir, exist_ok=True)
    log_path = os.path.join(args.dir, "_下载日志.txt")

    client = get_client()
    log(f"===== 下载任务启动: {len(keys)} 个文件 =====", log_path)
    results = {}
    for idx, key in enumerate(keys):
        log(f">>> [{idx+1}/{len(keys)}] {key}", log_path)
        try:
            res = download_file(client, key, args.dir, log_path, milestone=(idx == milestone_idx))
        except Exception as e:
            res = f"error:{type(e).__name__}:{str(e)[:120]}"
            log(f"[EXC] {key}: {res}", log_path)
        results[key] = res
        log(f"    -> {res}", log_path)

    ok = sum(1 for v in results.values() if v == "done")
    log(f"===== 全部处理完毕: {ok}/{len(results)} 成功 =====", log_path)
    print(f"=== SUMMARY: {ok}/{len(results)} ===", flush=True)
    sys.exit(0 if ok == len(results) else 2)


if __name__ == "__main__":
    main()

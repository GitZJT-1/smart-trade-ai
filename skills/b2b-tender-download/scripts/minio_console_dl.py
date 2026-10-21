# -*- coding: utf-8 -*-
"""
MinIO Console 控制台 API 批量下载器（招标 7z/rar 附件场景）
本次会话实战打磨版 — 单实例锁 + 分块并发 + 断点续传 + 异常安全

用法（Windows git-bash）:
  python minio_console_dl.py --base https://minio.pc1.tender.pro \
      --bucket MINIO_BUCKET \
      --ak MINIO_ACCESS_KEY --sk '密码' \
      --target "C:\\目标目录" \
      [--workers 10] [--block 8] [--only 文件名子串] [--max-rounds 4]

特性:
  - 直连（ProxyHandler({}) 禁代理，Clash 对 RU 站点极慢/不稳）
  - 登录取 token（POST /api/v1/login → 204 + Set-Cookie token，body 为空）
  - 对象清单分页拉取（next 游标）
  - 每文件内多线程 Range 分块下载到 <file>.blocks/，全部完成合并
  - 断点续传：已存在且 size 匹配的块/文件自动跳过
  - 单实例锁：lockfile + PID 存活检查，杜绝多进程踩踏
  - merge 前校验总字节数，全程 try/except 不裸崩
验证: 文件 size == 对象清单 size
"""
import argparse, json, os, shutil, sys, time, urllib.request, urllib.parse, http.cookiejar
from concurrent.futures import ThreadPoolExecutor, as_completed

LOCK_SUFFIX = '.minio_console_dl.lock'


def _opener(cookies=None):
    handlers = [urllib.request.ProxyHandler({})]  # 直连，不走系统代理
    if cookies is not None:
        handlers.append(urllib.request.HTTPCookieProcessor(cookies))
    return urllib.request.build_opener(*handlers)


def login(base, ak, sk):
    cj = http.cookiejar.CookieJar()
    op = _opener(cookies=cj)
    body = json.dumps({'accessKey': ak, 'secretKey': sk}).encode()
    req = urllib.request.Request(base + '/api/v1/login', data=body, method='POST',
                                 headers={'Content-Type': 'application/json'})
    with op.open(req, timeout=60) as r:
        r.read()  # 204 No Content，token 在 Set-Cookie
    token = next((c.value for c in cj if c.name == 'token'), None)
    if not token:
        raise RuntimeError('登录失败：未取得 token cookie（检查账号/密码）')
    return token


def api_get(base, path, token, timeout=90):
    req = urllib.request.Request(base + path, headers={'Cookie': 'token=' + token})
    with _opener().open(req, timeout=timeout) as r:
        return r.read()


def list_objects(base, token, bucket):
    objs, marker = [], None
    while True:
        path = '/api/v1/buckets/%s/objects?prefix=' % urllib.parse.quote(bucket)
        if marker:
            path += '&next=' + urllib.parse.quote(marker)
        data = json.loads(api_get(base, path, token).decode('utf-8'))
        objs.extend(data.get('objects', []))
        marker = data.get('next')
        if not marker:
            break
    return objs


def block_want(i, block, size):
    return min(block, size - i * block)


def fetch_block(base, token, bucket, name, i, block, size, block_dir, timeout=90):
    bf = os.path.join(block_dir, '%06d' % i)
    want = block_want(i, block, size)
    if os.path.exists(bf) and os.path.getsize(bf) == want:
        return True
    start, end = i * block, i * block + want - 1
    path = ('/api/v1/buckets/%s/objects/download?prefix=' % urllib.parse.quote(bucket)
            + urllib.parse.quote(name))  # 西里尔名必须 urllib.parse.quote，curl --data-urlencode 会 500
    tmp = bf + '.tmp'
    try:
        req = urllib.request.Request(base + path,
                                     headers={'Cookie': 'token=' + token,
                                              'Range': 'bytes=%d-%d' % (start, end)})
        with _opener().open(req, timeout=timeout) as r, open(tmp, 'wb') as f:
            while True:
                chunk = r.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        if os.path.getsize(tmp) == want:
            os.replace(tmp, bf)
            return True
        os.remove(tmp)
        return False
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def download_file(base, token, bucket, name, size, target, workers, block_mb, max_rounds=4):
    fpath = os.path.join(target, name)
    if os.path.exists(fpath) and os.path.getsize(fpath) == size:
        return 'skip'
    block = block_mb * 1024 * 1024
    nblocks = (size + block - 1) // block
    bdir = fpath + '.blocks'
    os.makedirs(bdir, exist_ok=True)
    pending = list(range(nblocks))
    for rnd in range(1, max_rounds + 1):
        if not pending:
            break
        ok = set()
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_block, base, token, bucket, name, i, block, size, bdir): i
                    for i in pending}
            for fut in as_completed(futs):
                if fut.result():
                    ok.add(futs[fut])
        pending = [i for i in pending if i not in ok]
        done = sum(1 for i in range(nblocks)
                   if os.path.exists(os.path.join(bdir, '%06d' % i))
                   and os.path.getsize(os.path.join(bdir, '%06d' % i)) == block_want(i, block, size))
        print('  [R%d] %d/%d blocks' % (rnd, done, nblocks), flush=True)
        if pending:
            time.sleep(3)
    if pending:
        return 'error'
    tmp_f = fpath + '.merging'
    try:
        with open(tmp_f, 'wb') as out:
            for i in range(nblocks):
                with open(os.path.join(bdir, '%06d' % i), 'rb') as f:
                    while True:
                        chunk = f.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
        if os.path.getsize(tmp_f) != size:
            os.remove(tmp_f)
            return 'error'
        os.replace(tmp_f, fpath)
    except Exception as e:
        print('  [MERGE ERROR] %s' % e, flush=True)
        try:
            os.remove(tmp_f)
        except OSError:
            pass
        return 'error'
    shutil.rmtree(bdir, ignore_errors=True)
    print('  [OK] %s (%d bytes)' % (name, size), flush=True)
    return 'done'


def acquire_lock(target):
    lock = os.path.join(target, LOCK_SUFFIX)
    if os.path.exists(lock):
        with open(lock) as f:
            pid = f.read().strip()
        rc = os.system('tasklist /FI "PID eq %s" /NH 2>nul | findstr /I "%s" >nul' % (pid, pid))
        if rc == 0:
            print('另一个下载实例在运行 (pid %s)，退出。' % pid)
            return None
        print('清理陈旧锁 (pid %s)' % pid)
        os.remove(lock)
    with open(lock, 'w') as f:
        f.write(str(os.getpid()))
    return lock


def main():
    ap = argparse.ArgumentParser(description='MinIO Console 招标附件批量下载器')
    ap.add_argument('--base', default='https://minio.pc1.tender.pro')
    ap.add_argument('--bucket', required=True)
    ap.add_argument('--ak', required=True)
    ap.add_argument('--sk', required=True)
    ap.add_argument('--target', required=True)
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--block', type=int, default=8, help='分块大小 MB')
    ap.add_argument('--only', default=None, help='只下载文件名含该子串的对象')
    args = ap.parse_args()

    os.makedirs(args.target, exist_ok=True)
    lock = acquire_lock(args.target)
    if not lock:
        return 3
    try:
        token = login(args.base, args.ak, args.sk)
        objs = list_objects(args.base, token, args.bucket)
        total = sum(o['size'] for o in objs)
        print('存储桶 %s: %d 个对象, %.2f GB' % (args.bucket, len(objs), total / 1024 ** 3))
        log = os.path.join(args.target, '下载日志.txt')
        results = {}
        with open(log, 'a', encoding='utf-8') as lf:
            lf.write("\n===== 下载会话 %s =====\n" % time.strftime('%Y-%m-%d %H:%M:%S'))
            lf.flush()
            for o in objs:
                name = o['name']
                if args.only and args.only not in name:
                    continue
                fpath = os.path.join(args.target, name)
                if os.path.exists(fpath) and os.path.getsize(fpath) == o['size']:
                    lf.write('[SKIP] %s (exists)\n' % name)
                    lf.flush()
                    results[name] = 'skip'
                    continue
                print('\n>>> %s (%.2f GB)' % (name, o['size'] / 1024 ** 3), flush=True)
                res = download_file(args.base, token, args.bucket, name, o['size'],
                                    args.target, args.workers, args.block)
                lf.write('[%s] %s\n' % (res.upper(), name))
                lf.flush()
                results[name] = res
        ok = sum(1 for v in results.values() if v in ('done', 'skip'))
        print('\n=== %d/%d 完成 ===' % (ok, len(results)))
        for n, v in results.items():
            print('  %-8s %s' % (v, n))
        return 0 if ok == len(results) else 2
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


if __name__ == '__main__':
    sys.exit(main())

# tender.pro MinIO 下载参考（2026-08 实测；2026-10 合并两版笔记）

## 存储桶与账号

- 桶：一个 bucket 下 15 个 `.7z` 招标档案，合计约 20.7 GB，全为 7zAES 加密（LZMA2:25 7zAES）
- 浏览器地址：`https://minio.pc1.tender.pro/browser/<BUCKET>`
- 只读账号：`<ACCESS_KEY>` / `<SECRET_KEY>`（登录名/密码 == S3 access key / secret key）
- 凭据来源：招标文件《Инструкция - чертежи на облаке.docx》里 "MinIO Console Логин/Пароль"
- ⚠️ 该文档**只有 MinIO 凭据，没有 7z 解压密码**；Приглашение PDF 也无密码

## 对象清单（2026-08-04 抓取，size 为权威基准）

| # | 对象 | size (bytes) | 约 | 当时的完成状态 |
|:-:|:--|--:|--:|:--|
| 1 | АРХИВ МПАР_Р_01_04.08.2026.7z | 866,840,325 | 0.87 GB | ✅ 已完整 |
| 2 | АРХИВ МППА_Р_01_04.08.2026.7z | 321,762,551 | 0.32 GB | 曾下载中 |
| 3 | БФ.7z | 3,781,926,966 | 3.78 GB | |
| 4 | КФ.7z | 3,706,108,877 | 3.71 GB | |
| 5 | МРСБУ_10 -01.7z | 105,624,205 | 0.11 GB | ✅ 已完整 + 结构验证 |
| 6 | НФ.7z | 1,559,438,146 | 1.56 GB | |
| 7 | СФ.7z | 2,894,212,779 | 2.89 GB | |
| 8 | ТФ.7z | 532,579,252 | 0.53 GB | |
| 9 | ШФ ДРМО, ПМ.7z | 1,304,290,863 | 1.30 GB | |
| 10 | ШФ ЦКР.7z | 550,536,923 | 0.55 GB | |
| 11 | ШФ ЦРАП.7z | 358,081,191 | 0.36 GB | |
| 12 | ШФ ЦРГПМ.7z | 412,817,652 | 0.41 GB | |
| 13 | ШФ ЦРЛП.7z | 3,576,453,963 | 3.58 GB | |
| 14 | ШФ ЦРЭП.7z | 712,906,207 | 0.71 GB | |
| 15 | ШФ ЦЭО.7z | 38,269,285 | 0.04 GB | |

> 清单随时会变（招标批次不同）——**每次开工重新 list**，把 size 落 JSON 当验证基准，别拿本表当现状。

## 端点与认证

### S3 API（首选）

```python
boto3.client("s3", endpoint_url="http://minio.pc1.tender.pro:9000",
    aws_access_key_id=ACCESS, aws_secret_access_key=SECRET,
    region_name="us-east-1",
    config=Config(signature_version="s3v4", max_pool_connections=32))
```

- 列对象 `list_objects_v2` 分页（`ContinuationToken`）；下载 `get_object(Range="bytes=start-end")`
- ⚠️ 2026-08-04 另一会话实测 **9000/9001 从外部不通（000）**，仅 443 可达——S3 端口可能只在服务器内网开放或随网络环境变化。不通时直接用下面的控制台 API（443）同样能完成全部下载

### 控制台 API（token 方案，443 实测可用）

- 登录：`POST https://minio.pc1.tender.pro/api/v1/login`，body `{"accessKey": "...", "secretKey": "..."}`
  → **204 + `Set-Cookie: token=...; Max-Age=43200`（12h）**，body 为空，别按 JSON 解析
- 对象清单：`GET /api/v1/buckets/<bucket>/objects?prefix=` → `{"objects":[{name,size,etag,last_modified}], "next": <游标>}`，`next` 非空则 `&next=<urlencode>` 翻页
- 下载：`GET /api/v1/buckets/<bucket>/objects/download?prefix=<urllib.parse.quote(key)>` + `Cookie: token=...` + `Range` 头
- 必须禁代理（`ProxyHandler({})`）：有 Clash（127.0.0.1:7897）时会 403 / IncompleteRead；直连实测 ~412KB/s 稳定
- **curl 落盘 cookie 解析坑**：`curl -c cookies.txt` 的 Netscape 格式中 `#HttpOnly_<host>` 开头行**不是注释**，是带 HttpOnly 属性的记录。按「# 开头跳过」会解析不出 token → 下载报 500 `Access Denied`。正确：先 `line[len('#HttpOnly_'):]` 去掉前缀再按 tab 切，token 在字段 5/6

## 速度与限速（关键）

- 单连接 1MB 请求约 1s；16MB 请求 >90s 未完成；6×8MB 并发 300s 未完成 48MB
- 2026-08-04 控制台 API 并发压测（直连 443）：4 连 452KB/s → 8 连 712KB/s → 16 连 773KB/s → 24 连 956KB/s
- 结论：**并发有收益但边际递减**，服务端按 IP 限速 ~1MB/s 封顶；workers 设 10–16，ETA 按 0.5–1MB/s 估算
- 0.87GB ≈ 20–30min（12 workers 实测），19.3GB 总量 6–8h → 需挂机/分批

## 目录约定与分片格式

- 目标根（业务）：`<交付根目录>/报价单`；招标子目录：`报价单/待报价/<tender号>_<名称>/`
- 日志：`下载日志.txt`（控制台下载器）、`_下载日志.txt`（S3 分块下载器）
- 分片格式对照（看分片名就能判断是哪个下载器留下的）：

| 分片格式 | 来源下载器 | 块大小 |
|:--|:--|:--|
| `.p0000` | `download_s3_v2` | 32MB |
| `.part0000` | `resume_s3_dl` | 32MB |
| `.blocks/000000` | `minio_dl3` / `download_s3.py` | 8–16MB |

## 历史脚本清单（`%LOCALAPPDATA%\Temp`，仅作排障线索）

- `download_s3_v4.py` — 主力 S3 分块下载器（已收敛进本 skill 的 `scripts/download_s3.py`）
- `minio_dl3.py` — urllib 直连 + Cookie token（已收敛进 `scripts/minio_console_dl.py`）；`minio_dl2.py` 为前版
- `download_s3.py / v2 / v3` — 早期迭代（v2 用 `.pNNNN` 分片，v3 用目录）
- `resume_s3_dl.py` — 早期续传入口（手写 SigV4，已废弃）
- `watch_download.py` / `monitor_*.py` — 进度监控（monitor 会等文件完成后自动跑 `7z t` 并写验证结果；有 40 分钟 deadline，别误当下载进程杀掉）
- `list_minio.py` / `minio_all_objs_full.json` — 对象清单
- `minio_cookies.txt` — token 存储（minio_dl3 从这里读）

## 既往失败模式（别再踩）

1. Minio SDK `fget_object(..., num_threads=N)` → `TypeError: unexpected keyword argument`（装的 SDK 版本不支持）→ 用 boto3
2. 手写 SigV4 直连卡死 0 字节 → 用 boto3 或控制台 token 通道
3. 控制台 token 过期 → 旧下载器反复空转重启；重新登录拿新 token 即可
4. 后端监督脚本会清理分片目录 → 自己的下载器用独立目录/独立命名
5. git-bash 里 `python -c "多行代码"` 转义爆炸 → 写 `.py` 文件执行
6. 多实例并发写同一 `.blocks/` → merge 竞争 + 已完成的文件被另一实例 rmtree 删掉（详见 SKILL.md 陷阱 10/11）

## 运行环境

- 带 boto3 的 venv：`<项目>/.venv/Scripts/python.exe`
- 安装：`uv pip install --python <该venv> boto3`（系统 python 是 uv 托管，`--system` 会被拒）

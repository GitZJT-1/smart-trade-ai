# tender.pro MinIO 下载参考（2026-08-04 实测）

## 存储桶与账号
- 桶: `MINIO_BUCKET`（15 个 .7z 招标档案，合计 ~20.7 GB）
- 只读账号: `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`（登录名/密码 == S3 access key/secret key）
- 浏览器地址: `https://minio.pc1.tender.pro/browser/MINIO_BUCKET`

## 对象清单（2026-08-04 实测，按名称升序）
| # | 对象 | 大小 |
|:-:|:--|:--|
| 1 | АРХИВ МПАР_Р_01_04.08.2026.7z | 0.87 GB |
| 2 | АРХИВ МППА_Р_01_04.08.2026.7z | 0.32 GB |
| 3 | БФ.7z | 3.78 GB |
| 4 | КФ.7z | 3.71 GB |
| 5 | МРСБУ_10 -01.7z | 0.11 GB |
| 6 | НФ.7z | 1.56 GB |
| 7 | СФ.7z | 2.89 GB |
| 8 | ТФ.7z | 0.53 GB |
| 9 | ШФ ДРМО, ПМ.7z | 1.30 GB |
| 10 | ШФ ЦКР.7z | 0.55 GB |
| 11 | ШФ ЦРАП.7z | 0.36 GB |
| 12 | ШФ ЦРГПМ.7z | 0.41 GB |
| 13 | ШФ ЦРЛП.7z | 3.58 GB |
| 14 | ШФ ЦРЭП.7z | 0.71 GB |
| 15 | ШФ ЦЭО.7z | 0.04 GB |

## 端点与认证
- **S3 API（首选，boto3 实测可用）**：
  ```python
  boto3.client("s3", endpoint_url="http://minio.pc1.tender.pro:9000",
      aws_access_key_id="MINIO_ACCESS_KEY", aws_secret_access_key="MINIO_SECRET_KEY",
      region_name="us-east-1", config=Config(signature_version="s3v4", ...))
  ```
  列出对象用 `list_objects_v2` 分页；分段下载用 `get_object(Range="bytes=start-end")`。
  ⚠️ 2026-08-04 另一会话实测 **9000/9001 端口从外部不通（000）**，仅 443 可达——S3 端口可能只在服务器内网开放或随网络环境变化；不通时直接用下方控制台 API（443）同样能完成全部下载。
- **控制台 API（token 方案，443 实测可用）**：
  - 登录：`POST https://minio.pc1.tender.pro/api/v1/login`，body `{"accessKey": "...", "secretKey": "..."}`
  - **响应是 204 + `Set-Cookie: token=...; Max-Age=43200`（12h），body 为空** → 从 Set-Cookie 提取 token
  - 对象清单：`GET /api/v1/buckets/<bucket>/objects?prefix=`（返回 `{"objects":[{name,size,etag,last_modified}], "next":游标}`，next 非空则 `&next=<urlencode>` 翻页）
  - 下载：`GET /api/v1/buckets/MINIO_BUCKET/objects/download?prefix=<urllib.parse.quote(key)>` + `Cookie: token=...` + `Range` 头
- 必须禁代理（`ProxyHandler({})`），否则请求会走本地 Clash 代理（7897）返回 403/失败；实测直连 ~412KB/s 稳定，Clash 代理 `IncompleteRead` 失败
- **curl 落盘 cookie 解析坑**：`curl -c cookies.txt` 写出的 Netscape 格式中 `#HttpOnly_<host>` 开头的行**不是注释**，是带 HttpOnly 属性的记录——按"# 开头跳过"会解析不出 token → 下载报 500 `Access Denied`。正确：先 `line[len('#HttpOnly_'):]` 去掉前缀再按 tab 切分，token 在字段 5/6

## 速度观测（关键！IP 级限速）
- 单连接 1MB 请求 ~1s；16MB 请求 >90s 未完成；6×8MB 并发 300s 未完成 48MB
- 2026-08-04 控制台 API 并发压测（直连 443）：4 连 452KB/s → 8 连 712KB/s → 16 连 773KB/s → 24 连 956KB/s
- 结论：**并发有收益但边际递减**（翻 6 倍并发只翻 2 倍速度），服务端按 IP 限速 ~1MB/s 封顶；ETA 按 0.5~1MB/s 估算，workers 设 10-16 即可，别堆 24+
- 0.87GB ≈ 20~30min（12 workers 实测），19.3GB 总量 6~8h，需挂机/分批

## 目录约定（山泰业务）
- 目标根：`C:/Users/<user>\Desktop\沈阳山泰通用机械有限公司\报价单`
- 招标子文件夹：`报价单\待报价\<tender号>_<名称>\`（如 `1223588_ISO三分部-自动化车间集采109项-7.31-9.15`）
- 日志：`下载日志.txt`（minio_dl3 控制台下载器）、`_下载日志.txt`（resume_s3_dl / download_resumable）
- 分片格式对照：`.p0000` = download_s3_v2（32MB 块）；`.part0000` = resume_s3_dl（32MB 块）；`.blocks/000000` = minio_dl3 / download_resumable（8-16MB 块）

## 既往失败模式（别再踩）
1. Minio SDK `fget_object(..., num_threads=N)` → `TypeError: unexpected keyword argument 'num_threads'`（装的 SDK 版本不支持）
2. 手写 SigV4 直连（resume_s3_dl.py）→ 卡死 0 字节；用 boto3 代替
3. minio_dl3.py 控制台 token 过期 → 反复空转重启；重新登录拿新 token
4. 后端监督脚本会清理分片目录 → 自己的下载器放独立目录/独立命名，避免被清
5. git-bash 中 `python -c "多行代码"` 转义爆炸 → 写 .py 文件执行

## 运行环境
- Python venv 带 boto3：`C:/Users/<user>\smart-trade-ai\.venv\Scripts\python.exe`
- 安装：`uv pip install --python <该venv> boto3`（系统 python 是 uv 托管，`--system` 会被拒绝）

---
name: b2b-tender-download
description: 招标大文件批量下载（MinIO S3 / 控制台 token / Nextcloud 分享）— 对象清单、并行分块、断点续传、卡死诊断、teardown 清理、7z 完整性验证。用户给出 MinIO/Nextcloud 链接与凭据要求下载招标压缩包或图纸档案、说「继续/中止/汇报进度」、或报 WinError 32 时使用。
when_to_use:
  - 用户给出 MinIO Console 链接 + 凭据，要求把招标 7z/rar 附件批量下载到本地文件夹
  - 用户给出 Nextcloud 分享链接 + 密码（招标邮件里常只给一条链接），要求取技术资料包
  - 续传或继续之前中断的大文件下载任务；用户说「汇报下载进度」「验证当前模式可行性」
  - 下载器卡住、进度不动、分块不增长，需要诊断是哪个进程在干什么
  - 用户要求终止下载任务、清理下载进程与 %TEMP% 过程文件（teardown）
  - 需要 7z 完整性验证并判断是否需要解压密码
  - 不要用于：纯单文件小下载（直接 curl/浏览器即可）；压缩包解压与归档整理（用 b2b-archive-extraction）
triggers:
  - 招标压缩包
  - 招标档案下载
  - MinIO 下载
  - MinIO Console
  - 大文件下载
  - 并行分块下载
  - 断点续传
  - 继续下载
  - 下载卡住
  - 下载进度
  - 清理下载进程
  - WinError 32
  - 7z 校验
  - Nextcloud 下载
category: 自动化
version: 2.0.0
author: Foreign Trade Assistant
---

# 招标大文件批量下载（MinIO / Nextcloud）

> 两条来源通道：① MinIO（S3 API 或控制台 token API）；② Nextcloud 分享链接（招标邮件里常只给一条链接 + 密码）。
> 下载完的解压与归档走 `b2b-archive-extraction`，本文只负责「拿到完整文件并核验」。

## 铁律：先查进程与现状，再动手

**先诊断再动手**（续传场景尤其如此，否则会把已有进度搞乱）：

1. `ls` 目标目录找分片：`.pXXXX` / `.partXXXX` / `.blocks/` 三种格式对应不同下载器（对照见参考文档）
2. 读日志：`下载日志.txt`（控制台 API 下载器）与 `_下载日志.txt`（S3 分块下载器）能还原每个会话干了什么
3. 查进程：`wmic process where "name like '%python%'" get ProcessId,CommandLine`（中文列名乱码但 CommandLine 可读），或 PowerShell `Get-CimInstance Win32_Process`。**提权进程 CommandLine 为空**，用父进程链 + 创建时间推断
4. 查 `%TEMP%` 下近期修改的 `.py` —— 上一次会话留下的下载器
5. 确认目标文件是否已完整存在（`ls -la` 目标目录）

**多进程同写一个 `.blocks/` = 数据损坏 + WinError 32**（已踩过两次，且会导致「已标记完成」的文件凭空消失）：

- 把 `minio_dl3 / download_s3* / watch_download / monitor_*` 全杀，**只留一个**下载器
- 杀完**等 60 秒复查**——PID 循环复用会让遗留进程看起来像「新进程」，误判成守护自动拉起
- 排除守护来源：Hermes cron（`%LOCALAPPDATA%\hermes\cron\jobs.json`）+ `schtasks`
- 发现别的下载器/后端服务正在下同一文件（哪怕到别的目录）→ 协调，别开第二个；分片命名格式别混用
- 下载器自身要带单实例锁（lockfile + PID 存活判定，见 `scripts/minio_console_dl.py`）；merge 阶段 try/except + 校验合并总字节 == 清单 size，失败删 `.merging` 重来，绝不裸崩

## 工作流

1. **获取对象清单**：S3 `list_objects_v2` 或控制台 `GET /api/v1/buckets/<bucket>/objects?prefix=`，存 `{name, size, etag}` JSON。**size 是之后唯一权威基准**；清单在手就别反复 list
2. **下载**：`scripts/download_s3.py`（boto3 S3 分块，8 线程 × 8MB，`.blocks/` 断点续传，多轮重试，完成合并后删块）
   - `--targets targets.json --dir "目标目录"`；targets.json = `{"keys": ["文件1.7z", ...], "milestone_index": 0}`
   - 控制台 token 通道用 `scripts/minio_console_dl.py`（443 端口，S3 端口不通时用它）
3. **验证**（三项，缺一不可）：
   - 文件大小 == 清单/`head_object` ContentLength（**首要判据**，精确匹配即基本可信）
   - `7z l <file>` 能列出内部结构（加密包也能读：`Type=7z, 7zAES`）
   - `7z t` 完整校验需密码；**加密包密码通常不在招标说明文档里**（文档往往只有 MinIO 凭据）→ 汇报时明说「加密压缩包，无法本地校验」
4. **汇报**：表格化（大小 / 进度 / 速度 / 落盘位置 / 下一步建议），主动提示加密包需密码
5. **解压**：交给 `b2b-archive-extraction`（本文不复述解压细节）

**里程碑通知模式**（用户说「下载完 X 通知我，然后继续下其余的」）：

- 阶段 1 = 里程碑文件单独跑，后台 `notify_on_complete`；`milestone_index` 会在该文件完成时打印 `=== MILESTONE_XXX_DONE ===` 供 watch 捕获
- 收到完成通知 → 回复「X 已完成 ✅」→ **同一回合**立即启动阶段 2（其余文件）
- 全部结束再汇报最终总结（成功数、大小核对）

## 两条通道怎么选

| 通道 | 端点 | 何时用 | 脚本 |
|:--|:--|:--|:--|
| S3 API（boto3 SigV4） | `http://minio.pc1.tender.pro:9000` | 首选；速度稳、支持 Range 分块 | `download_s3.py` |
| 控制台 token API | `https://minio.pc1.tender.pro`（443） | 9000/9001 不通，或只读账号对 S3 list/stat/get 全 AccessDenied 时 | `minio_console_dl.py` |

- **S3 全拒 ≠ 凭证失效**：只读账号对 9000 端口 S3 API 全 AccessDenied，但同一账号的控制台下载端点 + token 返回 206 正常。判定顺序：S3 直连全拒 → 别重试，直接切 token 通道；先用 1MB Range GET 验证 token 有效再启动
- **控制台登录**：`POST /api/v1/login` body `{"accessKey","secretKey"}` → **204 + `Set-Cookie: token=...; Max-Age=43200`（12h），body 为空** —— 别按 JSON 解析，从 Set-Cookie 提取
- **必须禁代理**：`urllib` 用 `ProxyHandler({})`、boto3 不配代理。环境有 Clash（127.0.0.1:7897）时代理会返回 403 或 IncompleteRead

## 卡死诊断

- 启动后**先等 30–60 秒确认分块在增长**，再向用户汇报「已开始下载」
- 看 `.blocks/` 内分块文件的时间戳/大小判断进展，别只盯日志（日志按 16MB 才打一行）
- 服务端 IP 级限速，实测 4 连 452KB/s → 8 连 712 → 16 连 773 → 24 连 956KB/s：**翻 6 倍并发只翻 2 倍速度**，~1MB/s 封顶。workers 设 10–16，ETA 按 0.5–1MB/s 估算，别承诺快
- `netstat -ano | grep <pid>` 逐 PID 查连接；**别过滤 127.0.0.1**——走代理时连接全是 localhost 地址，过滤会漏判
- token 过期后旧下载器会反复空转重启 → 重新登录拿新 token 即可

## 终止与清理（teardown）

用户说「终止所有下载进程 / 清理过程文件」时：

1. **盘点进程**：每个下载脚本常跑成**父子双进程**（hermes venv python 壳 + uv python 子进程），两个都要终止
2. **保护名单，绝不误杀**：`server.py`（Trade AI 后端）、`hermes gateway run` 必须保留；只杀 CommandLine 匹配 `download|minio|monitor|watch|targets|s3` 的
3. **普通权限先杀**：`taskkill //F //PID <pid>`（git-bash 双斜杠）。报「没有找到进程」= 已自行退出，正常
4. **提权进程杀不掉**（CommandLine 为空 + 拒绝访问）：走 UAC 提权
   `powershell -NoProfile -Command "Start-Process taskkill -ArgumentList '/F','/T','/PID','<pid>' -Verb RunAs -Wait"`（弹一次 UAC，用户点确认）
5. **杀完必验证**：逐 PID 确认 dead，再全量扫一遍 python 进程确认无残留（防漏网子进程）
6. **清理 `%TEMP%` 过程文件**：下载脚本（`download_s3*.py` / `minio_dl*.py` / `monitor_*.py` / `watch_*.py`）、`targets_*.json`、cookie/token 文件（`minio_cookies.txt` / `cookies.txt` / `minio_token_fresh.txt`）、下载日志
7. **清理目标目录**：删分片 `.pXXXX` / `.blocks/` 与 `_下载日志.txt`；**保留**已完整文件（size == ContentLength）与无关业务子目录（如 `待报价/`）——删前先读验证日志确认哪些是交付物

## Nextcloud 分享链接（招标邮件只给链接的场景）

部分招标邮件不挂附件，只附一个 docx，内容仅一行：`Техническая документация по ссылке: https://drive.nlmk.com/index.php/s/<TOKEN>` + `Пароль: <PW>`。走 public WebDAV，无需浏览器：

- 列目录 / 看大小：`curl -u "<TOKEN>:<PW>" -X PROPFIND -H "Depth: 1" https://<host>/public.php/webdav/`（207 + ContentLength）
- 直下：`curl -u "<TOKEN>:<PW>" -C - -o <绝对路径> https://<host>/public.php/webdav/`（单文件分享 = 包路径），约 1MB/s，69MB 约 90s
- **输出路径写 `C:/...`**：MSYS 的 `/c/...` 传给原生 curl 不翻译，文件会「凭空消失」
- 下完 `stat` 比对 ContentLength 再解包
- **包内常见两层套娃**：外层 `.7z`（每行项一个子目录，目录名 = `{ОЗМ号} {名称} {图号}`）→ 内层 **RAR5 分包**（`xxx.part1.rar` + `part2.rar`）
  - 7z：`py7zr.SevenZipFile(p).extractall(out)`（能正确还原西里尔名；bsdtar/tar 会解成乱码）
  - RAR5 分包：`7z x <dir>\xxx.part1.rar -o<dir> -y`（同目录所有卷自动接续）；**别用 Windows 自带 `tar.exe`**，只能列首卷、末尾必报 `Too small block encountered`
  - 本机默认没装 7-Zip 时装一次：`curl -sL -o 7zsetup.exe https://www.7-zip.org/a/7z2603-x64.exe && ./7zsetup.exe /S`（SYSTEM 会话无需 UAC）

## 陷阱

1. **wmic 输出是 UTF-16LE**（中文 Windows）：grep 报 `Binary file matches`、cat 乱码 → `raw.decode('utf-16', errors='replace').replace('\u0000','')`；`tasklist` 是 GBK，用 `iconv -f GBK -t UTF-8`
2. **git-bash glob 对西里尔文件名失效**（`ls *.p*`、`ls АРХИВ*` 返回空）→ 用 Python `os.listdir`
3. **PID 复用**：杀完出现「新 PID」≠ 守护进程，按上文 60 秒复查 + cron/schtasks 排除
4. **直连不走代理**：RU 站点过代理极慢/不稳；urllib 里 `ProxyHandler({})`，boto3 不配代理
5. **该存储桶慢**（0.03→0.10 MB/s 爬升）：100MB 约 15 分钟，按 `.blocks/` 时间戳判断进展
6. **清理损坏状态**：`rm -rf "<file>.blocks"` 后重下即干净；完整文件 + 无 `.blocks` = 干净终态
7. **残留 `.p0000` 分片/日志**属旧版下载器痕迹，确认无进程占用后清理
8. **curl cookie 里 `#HttpOnly_` 前缀行不是注释**：`curl -c` 写出的 Netscape 格式中这是带 HttpOnly 的正常记录。按「# 开头跳过」会丢 token → 下载报 500 `Access Denied`。解析：先去掉 `#HttpOnly_` 前缀再按 tab 切，token 在字段 5/6
9. **curl `--data-urlencode` 对西里尔名报 500**（`Object name with non UTF-8 strings are not supported`）：curl 按本地编码传参。改用 Python `urllib.parse.quote(name)` 拼 `download?prefix=` URL
10. **「文件消失」先查外部移动，再怀疑丢失**：诊断特征 `[ROUND 1 end] done 104/104` 后又出现 `[ROUND 2] 12 blocks pending + done 0/104` = blocks 目录已被另一实例删掉、本实例空转 → 立即杀光全部实例。恢复前三查：数 python 下载实例并杀光 → 全盘搜（Desktop/Temp/Downloads + **微信 `xwechat_files`**，别全盘 find）→ Python `os.listdir` 复核目标目录（bash 对西里尔+空格路径偶发 No such file）
11. **多实例并发可致已验证完整的文件凭空消失**：A 合并后 `rmtree`，B 仍在写；**已合并完成不是安全终态**，任何「完成」汇报前必须 `os.path.exists + size` 复核
12. **加密 7z 无法本地验证**：`7z t` 会卡在 `Enter password` 等输入 → 只能核大小 == ContentLength，解压需用户提供密码
13. **boto3 安装**：系统 python 是 uv 托管，`uv pip install --system` 会被拒 → `uv pip install --python <venv>/Scripts/python.exe boto3`
14. **bash 里跑 PowerShell 单行命令，`$_` 会被 bash 吞掉** → 涉及 `$_` 的 PS 逻辑写成 `.ps1` 再 `-File` 执行；中文输出乱码用 `iconv -f GBK -t UTF-8`
15. **git-bash 里 `python -c "多行代码"` 会被转义打爆** → 一律写成 `.py` 文件执行

## 支持文件

- `references/tender-pro-minio.md` — tender.pro 端点/认证（S3 + 控制台 token）、对象清单、分片格式对照、速度观测、既往失败模式
- `scripts/download_s3.py` — S3 分块断点续传下载器（boto3，目标清单 + 里程碑标记）
- `scripts/minio_console_dl.py` — 控制台 token 通道下载器（单实例锁，443 端口）

## 验证（交付前）

- 每个文件 `stat -c %s` == ContentLength（或清单 size）
- 需要时 `7z l` / `7z t` 校验（用户未要求时不必；加密包只核大小）
- 目标目录无残留 `.blocks/` / `.pXXXX` 分片

---
name: b2b-tender-archive-download
description: 招标档案/大文件批量下载 — MinIO S3/控制台 API 断点续传、token 刷新、卡死下载诊断、里程碑通知。用户给出 MinIO 浏览器链接+账号密码要求下载压缩包/图纸档案时使用。
when_to_use:
  - 用户给出 MinIO 浏览器链接 + 账号密码，要求下载压缩包/图纸档案到本地
  - 续传或继续之前中断的大文件下载任务
  - 下载器卡住、进度不动，需要诊断是哪个进程在干什么
  - 要求终止下载任务、清理下载进程与过程文件
  - 不要用于：只需下载一两个小文件（直接 curl/浏览器即可）；要整理已下好的招标压缩包（用 b2b-archive-extraction）
triggers:
  - 招标档案下载
  - MinIO 下载
  - 断点续传
  - 大文件下载
  - 下载卡住
  - 继续下载
  - 清理下载进程
category: 自动化
version: 1.0.0
author: Foreign Trade Assistant
---

# B2B 招标档案批量下载 (MinIO)

## 触发条件
- 用户给出 MinIO 浏览器链接（如 `https://minio.pc1.tender.pro/browser/iso-xxx-bucket`）+ 登录账号密码，要求下载压缩包/图纸档案到本地文件夹
- 续传/继续之前中断的下载任务
- 下载器卡住、进度不动、需要诊断是哪个进程在干什么
- 用户要求终止下载任务、清理下载进程/过程文件（teardown）

## 铁律
1. **先诊断再动手** — 续传场景下，先搞清楚现状再启动新下载：
   - `ls` 目标目录，找分片文件：`.pXXXX` / `.partXXXX` / `.blocks/` 三种格式对应不同下载器
   - 读日志：`下载日志.txt`（控制台 API 下载器）与 `_下载日志.txt`（S3 下载器）能还原每个会话干了什么
   - 查进程：`wmic process where "name like '%python%'" get ProcessId,CommandLine`（git-bash 下中文列名乱码但 CommandLine 可读，可用）；PowerShell `Get-CimInstance Win32_Process` 更清晰。注意**提权进程 CommandLine 显示为空**（普通权限读不到），用父进程链（ParentProcessId）和创建时间推断身份
   - 查 `%TEMP%` 下近期修改的 `.py` 脚本 — 之前的会话留下的下载器
   - 确认目标文件是否已完整存在（`ls -la` 目标文件夹）
2. **不要重复下载** — 若检测到其他下载器/后端服务正在下载同一文件（哪怕到别的目录），协调而非开第二个；分片命名格式别混用
3. **大文件必须分块+断点续传** — 服务端限速严重（见参考），单流直下必失败
4. **下载器必须自带单实例锁**（工程化防线，别只靠人工查进程）：
   - 启动时检查 lockfile：存在且 PID 存活 → 拒绝启动（`tasklist /FI "PID eq <pid>" /NH | findstr` 判断）；PID 已死 → 视为陈旧锁清除
   - 退出时 finally 删除锁文件
   - 实测教训（2026-08-04）：同一批文件同时跑多个下载器实例 → 写同一 `.blocks/` 目录互相覆盖 + merge 时 os.replace 互相竞争 → **已标记 DONE 的文件凭空消失**（МРСБУ、МППА 两个文件丢失），进程也因 merge 冲突裸崩 exit 1。日志出现多个"会话开始"记录即多实例信号
   - merge 阶段同样要 try/except + 校验合并后总字节数 == 清单 size，失败就删 .merging 重来，绝不裸崩

## 标准流程
1. 用 `scripts/download_resumable.py` 下载（boto3 SigV4 S3 API，8 线程×8MB 分块，断点续传，自动重试）：
   - `python download_resumable.py --targets targets.json --dir "目标目录"`
   - targets.json 格式：`{"keys": ["文件1.7z", ...], "milestone_index": 0}`
   - `milestone_index` 指文件完成时打印 `=== MILESTONE_XXX_DONE ===` 的 ASCII 标记（供 watch）
2. **里程碑通知模式**（用户说「下载完 X 通知我，继续下载」时）：
   - 阶段 1 = 里程碑文件单独跑，后台 `notify_on_complete=true`
   - 收到完成通知 → 回复用户「X 已完成 ✅」→ 同一回合立即启动阶段 2（其余文件）
   - 全程结束再汇报最终总结（成功数、文件大小核对）
3. 完成后核对：最终文件大小 == S3 head_object ContentLength；分片目录合并后删除

## 终止与清理流程（teardown — 用户说「终止所有下载进程/清理过程文件」时）
1. **盘点进程**：`wmic process where "name like '%python%'" get ProcessId,CommandLine` 列出所有 python 进程及其命令行（git-bash 下 wmic 中文列名是乱码但 CommandLine 可读）。注意**每个下载脚本通常跑成父子双进程**：hermes venv python 壳进程 + uv python 子进程，两个都要终止
2. **锁定保护名单，绝不误杀**：`server.py`（Trade AI 后端）、`hermes gateway run` 的进程必须保留；只杀 CommandLine 匹配 `download|minio|monitor|watch|targets|mrsbu|s3` 的
3. **普通权限先杀**：`taskkill //F //PID <pid>`（git-bash 双斜杠）。报「没有找到进程」= 已自行退出，属正常
4. **提权进程杀不掉**：CommandLine 为空 + taskkill 报「拒绝访问」= 管理员权限进程 → 用 UAC 提权杀：
   `powershell -NoProfile -Command "Start-Process taskkill -ArgumentList '/F','/T','/PID','<pid>' -Verb RunAs -Wait"`（会弹一次 UAC 确认框，用户点确认即可）
5. **杀完必验证**：逐 PID `Get-Process -Id <pid> -ErrorAction SilentlyContinue` 确认 dead；再全量扫一遍 python 进程确认无下载相关残留（防漏网的后台/子进程）
6. **清理 %TEMP% 过程文件**：下载脚本（download_s3*.py / minio_dl*.py / monitor_*.py / watch_*.py）、targets_*.json、cookies/token 文件（minio_cookies.txt / cookies.txt / minio_token_fresh.txt）、下载日志
7. **清理目标目录**：删分片文件 `.pXXXX` / `.blocks/` 目录和 `_下载日志.txt` 等过程文件；**保留**：已完整下载的交付物（大小==ContentLength，如 МРСБУ_10 -01.7z）和无关业务子目录（如 待报价/）——清理前先读验证日志确认哪些是完整交付物

## NLMK 技术资料链接（Nextcloud 分享，2026-09-15 实测）

部分招标邮件不挂图纸附件，只附一个 docx，内容仅一行：
`Техническая документация по ссылке: https://drive.nlmk.com/index.php/s/<TOKEN>` + `Пароль: <PW>`。

下载（无需浏览器，Nextcloud public WebDAV）：

```bash
# 列目录/看大小（207 + ContentLength）
curl -s -u "<TOKEN>:<PW>" -X PROPFIND -H "Depth: 1" "https://drive.nlmk.com/public.php/webdav/" -o prop.xml
# 直下（单文件分享）= 包路径；约 1 MB/s，69MB 用 90s
curl -s -u "<TOKEN>:<PW>" -C - -o "C:/Users/<user>/AppData/Local/Temp/pkg.7z" -w "%{http_code} %{size_download}\n" "https://drive.nlmk.com/public.php/webdav/"
```

- **curl 的输出文件路径写 `C:/...`**：MSYS 的 `-o /c/...` 传给原生 curl 不会翻译，文件会凭空“消失”。
- 下完用 `stat` 比对 ContentLength 再解包。
- **包内常见两层套娃**：外层 `.7z`（含每行项一个子目录，目录名 = `{ОЗМ号} {名称} {图号}`）→ 内层再套 **RAR5 分包**（`xxx.part1.rar` + `part2.rar`）。
  - 7z：`py7zr.SevenZipFile(p).extractall(out)`（hermes venv 已装，且能正确还原西里尔文件名；bsdtar/tar 会把名字解成乱码）。
  - RAR5 分包：`"C:\Program Files\7-Zip\7z.exe" x <dir>\xxx.part1.rar -o<dir> -y`（同目录所有卷自动接续）。
  - **本机默认没有 7-Zip**：`curl -sL -o 7zsetup.exe https://www.7-zip.org/a/7z2603-x64.exe && ./7zsetup.exe /S`（SYSTEM 会话无需 UAC，装完即用）。
  - **别用 Windows 自带 `tar.exe` 解 RAR 分包**：只能列首卷，末尾必报 `Too small block encountered (0 bytes)`，解出来的东西不可信。
- 图纸交付时把内层 RAR 卷删掉（已解出 PDF），只留图纸文件。

## 陷阱
- **MinIO 控制台登录**：`POST /api/v1/login` 返回 **204 + Set-Cookie: token=...**（有效期 12h），body 为空 —— 别按 JSON 解析！从 Set-Cookie 头提取 token
- boto3 安装：系统 python 是 uv 托管，直接 `uv pip install --system` 会拒绝；用 `uv pip install --python <venv>/Scripts/python.exe boto3`
- git-bash 里 `python -c "多行代码"` 会被转义打爆 → 一律写成 `.py` 文件再执行
- token 过期后旧下载器（minio_dl3.py）会反复空转重启 → 重新登录拿新 token
- 服务端 IP 级限速：并发有收益但边际递减（2026-08-04 实测 4 连 452KB/s → 24 连 956KB/s，翻 6 倍并发只翻 2 倍速度，~1MB/s 封顶）；ETA 按 0.5~1 MB/s 估算，workers 10-16 即可，别承诺快
- 其他 agent/监督脚本可能清理分片目录 → 自己的下载器用独立命名，别与既有下载共用目录
- 下载任务启动后先等 30~60s 验证分块在增长（确认没卡死），再向用户汇报
- **bash 里跑 PowerShell 单行命令，`$_` 会被 bash 吞掉**（展开成上一个命令的参数）→ 涉及 `$_` 的 PS 逻辑一律写成 `.ps1` 文件再 `powershell -NoProfile -ExecutionPolicy Bypass -File xxx.ps1` 执行；PS 中文输出乱码用 `iconv -f GBK -t UTF-8` 转码（或 `[Console]::OutputEncoding=[Text.Encoding]::UTF8`）
- **netstat 查下载连接时别过滤 127.0.0.1**：走 Clash 代理（127.0.0.1:7897）的连接全是 localhost 地址，过滤会漏判下载器是否在干活；下载器对远端只显示 CLOSE_WAIT 等状态，用 `netstat -ano | grep <pid>` 逐个 PID 查
- **加密 7z 无法本地验证完整性**：`7z t` 会卡在「Enter password」等待输入 → 只能核对大小==ContentLength，解压校验需用户提供密码；汇报时明确提示「加密压缩包，无法本地校验」

## 支持文件
- `references/tender-pro-minio.md` — tender.pro 具体端点/认证/对象清单/速度观测/既往失败模式
- `scripts/download_resumable.py` — 通用可续传分块下载器（boto3）

## 验证
- 每个文件下载后 `stat -c %s` 与 ContentLength 比对
- 需要时 `7z t` 验证压缩包完整性（用户未要求时不必）

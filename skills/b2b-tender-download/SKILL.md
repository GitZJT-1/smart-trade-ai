---
name: b2b-tender-download
description: 招标压缩包批量下载（MinIO/S3 大文件）— 对象清单获取、并行分块下载、断点续传、重复进程冲突管理、7z 完整性验证。当用户给出 MinIO Console 链接+凭据要求下载招标 7z/rar 附件，或说"继续/中止/汇报下载进度/验证下载模式"，或报 WinError 32 文件占用时使用。
when_to_use:
  - 用户给出 MinIO Console 链接 + 凭据，要求把招标 7z/rar 附件批量下载到本地
  - 用户说「继续/中止下载」「汇报下载进度」「验证下载模式」
  - 下载报 WinError 32 文件被占用、分块损坏，或发现多个下载进程并存
  - 需要 7z 完整性验证并决定是否需要解压密码
  - 不要用于：纯单文件下载；解压后的归档整理（用 b2b-archive-extraction）
triggers:
  - 招标压缩包
  - MinIO Console
  - 并行分块下载
  - 断点续传
  - WinError 32
  - 7z 校验
  - 下载进度
category: 自动化
version: 1.0.0
author: Foreign Trade Assistant
---

# B2B 招标文件下载（MinIO/S3 大文件）

## 触发条件
- 用户给出 MinIO Console 链接 + 登录/密码，要求把压缩文件下载到本地文件夹
- 用户说"继续下载任务" / "中止下载" / "汇报下载进度" / "验证当前模式可行性"
- 下载报 `WinError 32 文件被占用`、分块损坏、或发现多个下载进程

## 铁律：先查进程，再动手
多进程同时写同一个 `.blocks` 分块目录 = 数据损坏 + WinError 32（本用户已踩两次）。
1. 用 wmic 列出 python 命令行（编码见陷阱①），找出 `minio_dl3 / download_s3_v* / watch_download / monitor_* / proxy_test*` 等进程
2. 全部 `taskkill //F //PID <pid>`，只保留**一个**下载器
3. **等 60 秒复查**确认无守护进程自动拉起——PID 循环复用会让遗留进程看起来像"新进程"，误判为守护重启

## 工作流
1. **获取对象清单**：MinIO API 或 boto3 `list_objects_v2`，把 `{name, size, etag}` 存 JSON。**size 是之后验证的唯一权威基准**（对象清单已在手就别反复 list）
2. **下载**：boto3 S3 分块下载器（8 线程 × 8MB，`.blocks/` 目录断点续传，全部块完成后合并，失败块保留待续传）。脚本：`scripts/download_s3_v4.py`
3. **验证**：
   - 文件大小 == 对象清单 size（首要判据，精确匹配即基本可信）
   - `7z l <file>` 能列出内部结构（加密包也能读结构：`Type=7z, 7zAES`）
   - `7z t` 完整校验需密码；**加密包密码通常不在招标说明文档里**（文档往往只有 MinIO 凭据）
4. **汇报**：表格化输出（大小/进度/速度/落盘位置/下一步建议），主动告知加密包需要密码

## 陷阱
1. **wmic 输出是 UTF-16LE**（中文 Windows）：grep 报 `Binary file matches`、cat 乱码。用 python 解码：
   ```python
   txt = raw.decode('utf-16', errors='replace').replace('\u0000', '')
   ```
   tasklist 输出是 GBK：`iconv -f GBK -t UTF-8` 或 `decode('gbk')`
2. **git-bash glob 对西里尔文件名失效**（`ls *.p*`、`ls АРХИВ*` 返回空）→ 用 `python os.listdir` 列目录
3. **PID 复用**：杀完出现"新 PID"≠守护进程。查 Hermes cron（`%LOCALAPPDATA%\hermes\cron\jobs.json`）+ `schtasks` 排除，再等 60s 确认
4. **直连不走代理**：minio.pc1.tender.pro 用直连（urllib 里 `ProxyHandler({})` 禁用代理；boto3 不配代理）。环境变量有 Clash 代理（127.0.0.1:7897）时 urllib/curl 默认走代理且对 RU 站点极慢/不稳
5. **该存储桶速度慢**（0.03→0.10 MB/s 爬升）：100MB 约 15 分钟。看 `.blocks/` 目录内分块文件时间戳/大小判断进展，别只盯控制台日志（日志按 16MB 才打一行）
6. **清理损坏状态**：`rm -rf "<file>.blocks"` 后重下即干净；完整文件 + 无 `.blocks` 目录 = 干净终态
7. 下载完成后根目录若残留 `.p0000` 类分片/日志文件，属于旧版下载器痕迹，可确认无进程占用后清理
8. **curl cookie 文件里 `#HttpOnly_` 前缀行不是注释**：`curl -c` 写出的 Netscape 格式中，`#HttpOnly_minio.example.com<TAB>...` 是带 HttpOnly 属性的正常记录。若按"# 开头跳过"解析会丢 token → 下载报 500 `Access Denied`。正确解析：先 `line[len('#HttpOnly_'):]` 去掉前缀，再按 tab 切分，token 取字段 5（name）/6（value）。已有 curl 落盘的 cookie 可复用，不必重新登录
9. **curl `--data-urlencode` 对西里尔文件名报 500** `Object name with non UTF-8 strings are not supported`：git-bash 下 curl 把西里尔参数按本地编码传输，MinIO 拒绝。必须用 Python `urllib.parse.quote(name)` 构造 `download?prefix=` URL（urllib 内部正确 UTF-8 编码），Python 端下载正常
10. **下载器自带单实例锁**（防多进程踩踏的工程化实现）：启动时检查 lockfile——若存在且 PID 存活则拒绝启动（`tasklist /FI "PID eq <pid>" /NH | findstr` 判断存活），PID 已死则视为陈旧锁清除；退出时 finally 删除。见 `scripts/minio_console_dl.py`
11. **并发限速实测**（2026-08-04，直连）：4 连 452KB/s → 8 连 712KB/s → 16 连 773KB/s → 24 连 956KB/s。翻 6 倍并发只翻 2 倍速度（收益递减，服务端 IP 级限速 ~1MB/s 封顶）。ETA 按 ~0.5-1MB/s 估算；workers 设 10-16 即可，别堆到 24+
12. **MinIO 控制台登录**：`POST /api/v1/login` body={"accessKey","secretKey"} → **204 + Set-Cookie: token=...**（HttpOnly，约 1 小时/12h 级时效），body 为空——别按 JSON 解析，从 Set-Cookie 头提取。报 403 即 token 过期，重新登录拿新 token 即可（旧下载器 token 过期会反复空转重启）
13. **S3 API 全拒 ≠ 凭证失效（2026-08-04 第三次会话实测）**：只读账号对 9000 端口的 S3 API list/stat/get **全部 AccessDenied**，但同一账号的 Console API 下载端点 + cookie token 返回 206 正常。判定顺序：S3 直连全拒 → 别再重试 S3，直接切 Console API token 通道（minio_dl3/minio_dl4.py 系，`%TEMP%` 可复用），1MB Range GET 验证 token 有效再启动
14. **"文件消失"先查外部移动，再怀疑丢失（2026-08-04 实测）**：已核验完整的文件（МППА 321,762,551 字节 16:02 存在、16:11 全盘无踪）可能被：①并发实例的合并/rmtree 清掉——诊断特征：`[ROUND 1 end] done 104/104` 后又出现 `[ROUND 2] 12 blocks pending` + `done 0/104`（blocks 目录已被另一实例删掉，本实例空转重试，立即杀光全部实例别等 max_rounds）；②用户/其他会话移动——本机实测文件出现在微信目录 `xwechat_files\...\msg\file\2026-08\`，且 `报价单\待报价\` 整层被上移展平为 `报价单\<标段>\`。恢复下载前三查：wmic 数 python 下载实例杀光 → 全盘搜（Desktop/Temp/Downloads + **微信 xwechat_files 目录**，别全盘 find C 盘会超时）→ Python os.listdir 复核目标目录现状（bash cd 对西里尔+空格路径偶发 No such file or directory）
15. **多实例并发可致"已验证完整"的文件凭空消失**：两个实例同写同一 `.blocks/`，实例 A 合并后 `shutil.rmtree(block_dir)`，实例 B 仍在写 → B 的空转轮次全失败；A/B 各自的 merge + os.replace + rmtree 组合在并发下会互相覆盖甚至删掉最终文件。**已合并完成的文件不是安全终态**，只要还有其他实例在跑就随时可能被清。任何"完成"汇报前必须再 `os.path.exists + size` 复核

## 解压阶段（下载/收到压缩包后）
用户把已下载的 7z/zip/rar 放好说"把 XX 文件夹里所有未解压的压缩包解压到对应位置"时，用 `scripts/batch_extract.py`（已实战验证），模式：**每个压缩包 → 其所在目录下同名文件夹**（`X.7z` → `X/`），目标文件夹已存在且非空即跳过（断点续解）。要点：
1. 先 `os.walk` 全量收集压缩包（含嵌套目录），排序后逐个处理；**解压一轮后必须重新扫描**——一个 7z 内部常嵌套更多 7z/zip/rar（本会话首批 669 个，解压后新增一批嵌套包，需二次处理）
2. 目标目录命名 = 压缩包去掉扩展名；**目录名以点结尾时 Windows 会拒绝**（如 `...2019г..zip` → 目标 `...2019г.` 变空目录），改用 Python `zipfile` 解到去点目录
3. 7z CLI 退出码：0=成功、1=警告、2=致命（损坏/格式不支持）、3=不可恢复、4=需要密码。错误码 2 的文件先记下来，很多内容其实已在同目录平铺存在（源包本身损坏但图纸散落在外）
4. **乱码文件名（mojibake）**：俄文名下载时被错误转码（如 `搻€媻悁_€_悡憖_佮犫岐.zip`，含 PUA 字符 `\ue127`）。手打/复制路径必失败——必须 `os.listdir()` 取回磁盘上的**原样文件名**再拼路径；7z 对这种路径报"系统找不到文件"，用 Python `zipfile` 解压内容完好
5. 日志写 `utf-8-sig`（中文 Windows 记事本可读），逐条记录 OK/SKIP/FAIL 和原因

## 终态验证（外部移动文件时）
本用户环境有外部流程（微信/其他会话/归档脚本）会**边解压边移走源压缩包**——源 7z 消失 ≠ 解压失败。终态判据：**所有现存压缩包都有非空同名目录**，而非源文件是否存在。批量解压后必须：重新 os.walk → 对每个现存压缩包检查 `目标目录非空` → 剩下的逐个补解。本会话首轮 578 个 [OK] 中源文件已剩 42/200，但 576/578 目标非空，结论正确。

## 参考
- `references/tender-pro-minio.md` — 当前招标存储桶端点/凭据位置/15 项对象清单/脚本清单/实测历史坑
- `references/batch-extraction.md` — 批量解压实战记录（7z 退出码/乱码名/点结尾/嵌套包的完整对策）
- `scripts/download_s3_v4.py` — 已知可用的 boto3 分块下载器（凭据改自招标说明文档）
- `scripts/batch_extract.py` — 批量解压器：7z CLI + Python zipfile 双通道、嵌套重扫、utf-8-sig 日志

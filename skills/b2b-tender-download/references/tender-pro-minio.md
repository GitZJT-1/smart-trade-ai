# tender.pro MinIO 存储桶速查（2026-08 活跃）

## 端点与凭据
- Console: https://minio.pc1.tender.pro/browser/MINIO_BUCKET
- S3 API: http://minio.pc1.tender.pro:9000（HTTP 9000，signature s3v4）
- 凭据: `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`（只读 reader 账号）
- 来源: 招标文件《Инструкция - чертежи на облаке.docx》里 "MinIO Console Логин/Пароль"
- 注意: 该文档只有 MinIO 凭据，**没有 7z 解压密码**；Приглашение PDF 也无密码

## 目标目录
- 根目录: `C:/Users/<user>\Desktop\沈阳山泰通用机械有限公司\报价单`
- 子目录（minio_dl3.py 的 TARGET）: `报价单\待报价\1223588_ISO三分部-自动化车间集采109项-7.31-9.15`

## 对象清单（15 项，2026-08-04 抓取，size 为权威基准）
| 对象 | size (bytes) | 状态 |
|---|---|---|
| АРХИВ МПАР_Р_01_04.08.2026.7z | 866840325 | ✅ 子目录已完整 |
| АРХИВ МППА_Р_01_04.08.2026.7z | 321762551 | 曾下载中 |
| БФ.7z | 3781926966 | |
| КФ.7z | 3706108877 | |
| МРСБУ_10 -01.7z | 105624205 | ✅ 已完整 + 7z 结构验证 |
| НФ.7z | 1559438146 | |
| СФ.7z | 2894212779 | |
| ТФ.7z | 532579252 | |
| ШФ ДРМО, ПМ.7z | 1304290863 | |
| ШФ ЦКР.7z | 550536923 | |
| ШФ ЦРАП.7z | 358081191 | |
| ШФ ЦРГПМ.7z | 412817652 | |
| ШФ ЦРЛП.7z | 3576453963 | |
| ШФ ЦРЭП.7z | 712906207 | |
| ШФ ЦЭО.7z | 38269285 | |

合计约 20GB。全为 7zAES 加密（LZMA2:25 7zAES）。

## 脚本清单（%LOCALAPPDATA%\Temp）
- `download_s3_v4.py` — 主力下载器（boto3, 8线程×8MB, .blocks 断点续传, 多轮重试, 合并后删块）→ 已复制到 skill scripts/
- `minio_dl3.py` — urllib 直连 + Cookie token（写子目录 TARGET）；`minio_dl2.py` 为前版
- `download_s3.py / v2 / v3` — 早期迭代版（v2 用 .pNNNN 分片，v3 目录）
- `resume_s3_dl.py` — 续传入口；`watch_download.py` / `monitor_mrsbu.py` — 进度监控（monitor 会等文件完成后自动跑 7z t 并写 _МРСБУ验证结果.txt）
- `list_minio.py` / `minio_all_objs_full.json` — 对象清单获取
- `minio_cookies.txt` — token 存储（minio_dl3 从这读）

## 实测历史（2026-08-04）
1. **重复进程冲突（第 2 次发生）**：8+ 个进程并存——`minio_dl3.py`×4、`download_s3_v2/v4`×4、`monitor_mrsbu.py`×2、`proxy_test2.py`×2，全部写同一批分块 → WinError 32 文件占用 + 数据损坏风险。处理：全杀 → 单进程重下。
2. 无守护进程：Hermes cron jobs.json 与 schtasks 均无下载任务；等 60s 无新进程 → 结论"PID 循环复用误判"。
3. 速度慢：0.03→0.10 MB/s 爬升，100MB 约 15 分钟；日志按 16MB 打一行，看 .blocks 内分块时间戳更实时。
4. `monitor_mrsbu.py` 有 40 分钟 deadline，超时即放弃验证，需注意其存在（会被误认为重复下载进程，但它是监控非下载）。

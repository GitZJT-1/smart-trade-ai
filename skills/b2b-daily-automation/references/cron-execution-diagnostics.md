# Cron 执行诊断手册（慢 / 卡死 / 重复触发）

> 2026-08-03 早安简报（job 9639fd6352ed）执行耗时 ~3 分钟排查实战总结。当用户反馈「定时任务太慢 / 没结果 / 状态不对」时按此排查。

## 1. 数据源与定位

HERMES_HOME = `C:\Users\<user>\AppData\Local\hermes`（注意不是 `~/.hermes`，那是旧副本）

| 文件 | 作用 |
|------|------|
| `cron/executions.db` | SQLite，表 `executions` — 每次执行记录（时间、状态、PID） |
| `cron/jobs.json` | 任务定义 + `last_run_at` / `last_status` / `fire_claim` / `repeat` |
| `cron/output/{job_id}/` | 任务输出文件（.md） |
| `logs/agent.log` | 逐次 API 调用与工具耗时明细 |
| `logs/errors.log` | 工具错误 / 超时 |
| `cron/ticker_heartbeat` | 调度器心跳时间戳（unix epoch） |

## 2. executions.db 表结构

```sql
PRAGMA table_info(executions);
-- id, job_id, source, process_id, pid, process_started_at,
-- status, claimed_at, started_at, finished_at, error
```

- `source`: `direct`（手动触发）/ `builtin`（调度器自动）
- `status`: `running` / `completed` / `failed`
- `process_started_at` 是毫秒级 unix 时间戳（约 1.785e11）

**查某任务全部执行记录：**

```bash
python -c "
import sqlite3, json
conn = sqlite3.connect(r'C:\Users\<user>\AppData\Local\hermes\cron\executions.db')
cur = conn.cursor()
cols = [c[1] for c in cur.execute('PRAGMA table_info(executions)').fetchall()]
cur.execute(\"SELECT * FROM executions WHERE job_id='<JOB_ID>' ORDER BY claimed_at\")
for r in cur.fetchall():
    print(json.dumps(dict(zip(cols, r)), ensure_ascii=False, default=str))
    print('---')
"
```

## 3. agent.log 耗时分析

session 命名模式：`cron_{job_id}_{yyyyMMdd_HHmmss}`（如 `cron_9639fd6352ed_20260803_110715`）

```bash
grep -n "cron_9639fd6352ed_20260803_110715" logs/agent.log | grep "API call"
# API call #N: model=... in=X out=Y latency=Zs cache=...
grep -n "cron_9639fd6352ed_20260803_110715" logs/agent.log | grep "tool .* completed"
# tool web_search completed (2.18s, 5837 chars)  ← 工具耗时
```

**耗时分类判定：**
- `API call ... latency=50s+` → 模型服务端生成慢（DeepSeek 波动，正常现象），不是本地问题
- `tool web_search completed (Xs)` → 每个 2-5s 正常；8 次搜索 ≈ 25s
- `tool terminal completed` → 本地命令，通常 <3s
- 4 次 API call 总 latency 153.8s / 全程 179.5s = **86% 时间耗在等模型输出**（实测案例）

## 4. 僵尸执行判定与处理

特征：
1. executions.db 中 `status='running'` 且 `finished_at` 为空
2. `tasklist //FI "PID eq <pid>"` 查不到该进程（进程已死）
3. jobs.json 的 `last_status` 仍是旧值（ok），说明新执行从未完成

处理：手动把 executions.db 中该条状态修正为 `failed` 并补 `finished_at`，避免污染统计；`jobs.json` 无需改（调度器会在下次 tick 正常接管）。

## 5. 重复触发根因

- 已设 cron schedule 的任务，**手动触发（hermes cron run / cronjob 工具）会与调度器 claim 叠加**，产生第二条 `source=direct` 执行
- 证据：executions.db 同 job 两条 direct 记录 + jobs.json `fire_claim.at` 指向第二条
- 规则：**有 schedule 的任务平时不要手动触发**；确需立即执行时先确认无排队执行

## 6. 性能优化建议（早安简报实测）

| 现状 | 优化后 |
|------|--------|
| 8 次独立 web_search（汇率×3、大宗×4、新闻×N） | 合并为 3-4 次：汇率一次、大宗一次、新闻一次 |
| 每轮搜索都触发模型决策（4+ API calls） | 减少轮次，总耗时 ~180s → 预估 <90s |

## 7. 环境要点

- `hermes` CLI 路径：`C:\Users\<user>\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`（bash 里需 `export PATH=...venv/Scripts:$PATH` 或直接写全路径）
- git-bash 中 `tasklist //FI "PID eq N"`（双斜杠转义），查不到 = 进程不存在

## 8. 幽灵任务：任务消失 / 前端不显示（2026-08-03 邮箱监控实测）

### 症状

- Trade AI 前端「📡 已激活的定时任务」面板不显示某任务；`hermes cron list` 也不显示
- 但 `cron/output/{job_id}/` 目录有今天的执行输出，executions.db 有 `source=builtin` 记录

### 判定链（前端不显示 = 注册表里没有，不是前端 bug）

1. **前端数据源**：`trade/api/cron.py` 的 `/api/cron/jobs` 与 `/api/cron/today` 直接读 `%LOCALAPPDATA%\hermes\cron\jobs.json`（`_JOBS_FILE`，HERMES_HOME env 优先）。任务不在 jobs.json → 前端与 CLI 都看不到
2. **注意正常隐藏场景**：`/cron/today` 会过滤 script 以 `_gate.py` 结尾或名称含「门控」的任务（静默后台任务，故意不显示）；`/cron/jobs` 不过滤。排查先排除这两种情况
3. **幽灵判定**：executions.db 按 job_id 分组看 `MIN/MAX(claimed_at)` 与执行次数——"只执行过 1 次就消失" + jobs.json 无此 id = 注册表被覆盖丢失
4. **后果**：调度器每 tick 重读 jobs.json（`cron/scheduler_provider.py`：built-in 调度器 no-op 即每 tick 重读）→ 丢失后永不再触发，任务"死亡"而非"隐藏"

### 证据 SQL

```sql
SELECT job_id, MIN(claimed_at), MAX(claimed_at), COUNT(*)
FROM executions GROUP BY job_id ORDER BY MIN(claimed_at);
-- 幽灵任务特征：count=1 且 last_claimed 之后 jobs.json 里已无此 id
```

### 修复：无痛重建（状态文件保留，不重复告警）

no_agent 脚本任务（如邮箱监控）重建命令：

```bash
hermes cron add "every 30m" --name "163邮箱监控 - xx@163.com" \
  --no-agent --script monitor_163_email.py --deliver local
```

- 脚本在 `%LOCALAPPDATA%\hermes\scripts\` 下，`--script` 传文件名即可
- 状态文件（如 `.email_check_state.json` 的 `last_uid`）保留 → 重建后不会对历史邮件重复告警
- 重建后**必须** `hermes cron list` 验证注册已持久化

### 丢失根因（本次案例）

10:45 重建任务（新 job_id）→ 11:17/11:18 首次执行成功 → 11:23-11:25 期间（早安简报 prompt 优化 + 手动触发完成）jobs.json 被重写时新任务不在写入方快照里 → 被覆盖丢失。agent.log 无 `cron remove` 记录，非有意删除。教训：**创建/编辑任务后立即 `hermes cron list` 验证**；怀疑丢失时以 jobs.json 为准排查，不要只看执行记录。

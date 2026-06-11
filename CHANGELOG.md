# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式规范。

## [Unreleased]

### Added
- **session 级公司绑定**：首次请求自动绑定 session→company_id，跨公司操作返回 403，显式切换需通过 `POST /companies/{id}/switch`
- **CDN SRI 完整性校验**：marked.js 和 DOMPurify 添加 integrity 哈希
- **SSRF 内网防护**：tech_stack.py 拒绝 RFC1918/loopback/multicast/保留 IP
- **README 故障排除章节**：升级按钮无反应、拖拽文件报错、样式异常的三平台手动修复步骤

### Changed
- **list_companies 脱敏**：仅返回 id/name/slug/is_active，隐藏 contact_email 等 PII
- **chat 限流按公司隔离**：全局改为 per-company，防止单租户 DoS
- **PID 验证三层防御**：cmdline → psutil exe 路径比对 → chmod 0600
- **system 端点加 session token 认证**：update/backup/restart 不再无认证暴露
- **delete 公司要求 X-Confirm-Delete header**：防止误操作或 XSS 触发永久删除

### Fixed
- **C-1**: 系统端点无认证（第五轮审计）
- **C-2**: 移除 GATEWAY_ALLOW_ALL_USERS
- **C-3**: License 端点支持 company_id 多租户隔离
- **H-4**: warning filter 缩小到 hermes_cli.tools 路径，不再吞所有 ImportError
- **H-5**: chat 限流按 company_id 隔离
- **H-6**: _capture_output 加 threading.Lock 防并发 stdout 污染
- **H-7**: memory.py 锁文件前检查 is_symlink()
- **M-1**: 公司创建 rollback 仅清理 is_new 目录
- **M-2**: 审计日志写入失败改 logging.warning
- **M-5**: prompt 注入防御加强（控制字符清理、[] 转义、200 字符限制）
- **M-8**: tech_stack.py SSRF 防护
- **M-9**: email_intel json.loads 后检查 list 类型
- **M-10**: skill_router 环境变量解析加 try/except
- **M-11**: 删除 skill_registry 未使用的 _COMPILED 预编译正则
- **路径跨平台**：.hermes/.trade 在 Windows 上统一走 LOCALAPPDATA，bootstrap 启动时注入 HERMES_HOME
- **并发安全**：_ACTIVE_COMPANY dict、_FILE_CACHE、_INJECTION_CACHE 加 threading.Lock
- **边界条件**：WHOIS 不支持的 TLD 优雅降级、DNS MX TC 截断检测、LIKE 通配符转义
- **代码质量**：get_event_loop → get_running_loop、SSE 加 Cache-Control header、限流字典简化

## [0.6.0] — 2026-06-10

### Added
- **拖拽/粘贴文件上传**：拖入文件或目录到聊天框 → 选择工作子目录 → 自动导入，Agent 递归读取分析；图片文件提示用 vision 或 Tesseract OCR 识别
- **版本更新检测**：页面每 30 分钟自动对比 GitHub 最新版本，顶部横幅提醒升级
- **Windows 开机自启动**：Task Scheduler 用户登录后自动后台启动 Trade
- **Linux 开机自启动**：systemd user unit
- **macOS 桌面入口**：tradewin.py PyWebView 独立桌面应用

### Changed
- **CLAUDE.md** 补充 tradewin 桌面应用、test_license.py、Desktop App 章节
- **README** 顶端加科学上网提示 + LLM 免责声明
- **README** Windows 安装增加长路径支持说明
- **prompt.py** 新增 AI 免责块，禁止输出法律建议和编造数据

### Fixed
- **P0-1**: update_skills 下载加 1MB 大小限制
- **P0-2**: license 首次启动写入失败不再静默
- **P0-3**: 激活限流从内存改为 SQLite 持久化
- **P0-4**: 公司名路径穿越防护（.. 和 NUL 拒绝）
- **P1-1**: 重启 PID 校验优先用 psutil
- **P1-6**: 拖拽上传 100MB 单文件上限
- **重启按钮修复**：subprocess.Popen 拉起新进程 + 前端轮询自动刷新
- **拖拽上传 session token 缺失**：window.TOKEN → TOKEN
- **系统更新按钮三层防御**：event 参数 + DOM 查询兜底，永不失效
- **upload_to_work_dir** 不再重复创建目录（万花筒-2 问题）
- **customer._row_to_dict** 补回 extra1/extra2 字段
- **TOCTOU 目录竞争**：mkdir exist_ok=False → True
- **大目录拖入**：readEntries 循环读取直到空
- **slug 从错误表查询**：skill_router 改为从 companies 表查

## [0.4.4] — 2026-05-21

### Changed
- **仓库重命名**：`foreign-trade-assistant` → `smart-trade-ai`
- **README 重构**：痛点导向首页 + 截图 + 场景化功能分类
- 项目名称更新为 Smart Trade AI

### Fixed
- **今日简报 cron 输出不展示**：进入今日简报时，已完成任务的输出自动作为 AI 对话消息显示
- **系统更新按钮全链路修复**：增加 install_skills + update_skills + 模板同步 + 自动重启（跨平台）
- **`/system/update` 等端点 401**：移到不受 session token 保护的独立路由组
- **update_skills 网络超时**：增加 3 次重试 + 递增退避

## [0.4.3] — 2026-05-20

### Added
- **Skill 开发指南**：`docs/skill-development-guide.md`，覆盖 frontmatter 规范、触发词设计原则、injection_prompt 最佳实践、15 个 skill 快速参考
- **Agent 重试机制**：sync 和 SSE 双端点均支持，RuntimeError / 空响应自动重试（最多 2 次，指数退避）

### Changed
- **License 安全加固**：移除硬编码 HMAC 密钥，强制 `TRADE_LICENSE_SECRET`；新增 `generate-secret` CLI；激活码支持 company_id 隔离；暴力破解限流（60s 内 10 次）
- **helpers.py 重构**：所有函数体内 import 提升到模块级别
- **Chat 端点增加输入长度限制**（max 10000 字符）和内存限流（60s 内 20 次请求）

### Fixed
- **订单 API 多租户隔离缺失**：GET/PUT/DELETE /orders/{id} + link/unlink 全部补上 company_id 校验
- **chat-memory skill 触发词为空**：补充 35 个中文触发词，原先永不被匹配
- **License 跨公司共享**：`_get_license_data` / `_save_license_data` 改为按 company_id 隔离
- **slug 路径穿越风险**：`_validate_slug()` 禁止 `..`、`/`、`\` 字符
- **company.delete() 文件残留**：删除时清理 `~/.trade/{slug}/` 和桌面工作目录
- **OSINT 同步调用阻塞事件循环**：WHOIS/邮箱验证/制裁/技术栈 4 个调用放入 `run_in_executor`
- **update_trade 缺少依赖更新**：恢复 pip install（移除 `--no-deps`）
- **session token 日志泄露**：从打印前 16 字符缩减到 8 字符
- **_check_hermes_version import 时 sys.exit(1)**：改为返回 bool，退出逻辑移至 main()
- **前端定时任务列表一直显示加载中**：`loadActiveCronJobs` 改用 `document.getElementById`

## [0.4.2] — 2026-05-20

### Added
- **轻量订单系统**：orders 表（13 字段）+ order_libraries 关联表，支持 3 层上下文查询
- **数据库文档**：8 张表的完整字段说明 + 关系图（draw.io / PNG）
- **客户列表两行布局**：公司名 + 联系人 + 等级/职位/联系方式/跟进项目一目了然
- **客户表单新增联系人字段**，注入到 AI 上下文
- **6 个 skill 增加内容真实性约束**：防编造数字、专业术语规范化
- **到期页面显示微信名片**

### Changed
- 客户列表从 8 列缩减为 3 列，信息密度提升
- 移除微信字段（外国客户不需要）
- `trade update` 后自动重启服务时补全 PATH

### Fixed
- **OSINT 网络测试加 pytest.skip 防 flaky**
- 美元符号 bug（多个 `$$` 导致 JS 模板解析错误）
- `agent_identity.md` vs `agent-identity.md` 文件名不一致
- launchctl 在非标准 PATH 下找不到的问题

## [0.4.1] — 2026-05-19

### Changed
- backup_trade 无数据时以非零退出码退出
- README 测试数、项目结构、开发命令更新
- SECURITY.md 支持版本更新到 0.4.x
- Roger Lau → Roger Lococo

## [0.4.0] — 2026-05-19

### Added
- **Hermes v0.14 适配**：config.model 从嵌套 dict 变为扁平字符串，Trade 自动兼容两种格式
- **启动时自动从 GitHub 拉取最新 B2B skills**，确保 skills 始终与仓库同步
- **macOS 开机自启动**（launchd，后台静默无终端窗口），安装脚本自动配置；`trade update` 后自动重启服务
- **定时任务使用说明书**：页面上方嵌入零基础 cron 表达式教程，含速查表、符号说明和常见问题
- **`trade update / backup / skills-update` 子命令**正确路由，无需启动服务器即可更新
- **输出语言规则**：LinkedIn/lead-generation/social-media 三个 skill 均按目标客户语言输出，默认英语
- `TRADE_HOME` 环境变量支持：测试和开发环境下工作目录不会污染桌面

### Changed
- hermes-agent 从 `chefroger/hermes-agent` fork 迁移到上游 `NousResearch/hermes-agent` v0.14
- **LinkedIn/lead-generation/social-media 三个 skill 全面转向客户价值导向**：内容以客户痛点+解决方案为中心，产品/工厂占 20-25%
- 版本约束从 `>=0.12.0,<0.14.0` 提升到 `>=0.13.0,<0.15.0`
- OSINT 背调使用精简 system prompt，不再把文档生成指南带入调查场景
- OSINT 背调时禁止注入历史对话，防止上一轮背调话题污染当前查询

### Fixed
- SQLite 增加 `busy_timeout=30000`，防止并发写入 database is locked
- SSE QueueFull 防护：工具事件过于频繁时静默丢弃而非崩溃
- API 异常信息脱敏：异常详情只写日志，前端返回通用错误消息
- `customer.update` 越权修复：extra 字段更新时缺少 company_id 校验
- `api_key` 跨 provider 兜底可能导致拿错 key，改为精确匹配
- `DELETE /companies/{id}` 缺少鉴权：已认证用户可越权删除其他公司数据
- `post_install.py` 中 `urllib.error` 未 import 导致 HTTP 错误时 NameError 崩溃
- `email_intel.py` trio/asyncio event loop 混合崩溃：async 路径改为子进程运行 holehe
- `linkedin_verify.py` 中 `{domain_clean}` 占位符未被 f-string 替换
- `orchestrator.py` LinkedIn 搜索时把 email 当公司名
- 测试中 `/tmp` 硬编码路径在 Windows 上崩溃
- `memory.py` 中 `import fcntl` 在 Windows 上崩溃
- 6 处 `~/.hermes/` / `~/.trade/` 硬编码路径改为平台感知的默认路径
- Windows `install.ps1` 中 `trade.cmd` HERMES_HOME 赋值错误 + 未加 PATH
- cron/jobs API 适配 Hermes 实际 jobs.json 数据结构（`{"jobs": [...]}` 格式）
- F401 lint 规则从全局豁免改为 per-file-ignores
- 全项目 100+ 函数 docstring 英→中转换 + 150+ if-branch 中文注释补全

## [0.3.0] — 2026-05-15

### Added
- CI 三平台测试矩阵 (Ubuntu + macOS + Windows, Python 3.11/3.12/3.13)
- CI `python -m compileall` 语法检查（lint job）
- CI ruff check（lint job）
- 使用说明书

### Changed
- hermes-agent 版本对齐 v0.13（>=0.12.0, <0.14.0）
- stderr monkey-patch 替换为 logging Filter，在 Hermes import 前安装
- ruff auto-fix 172 处 lint 问题

### Fixed
- WHOIS 域名解析错误
- DNS MX 查询交易 ID 随机化（防 DNS 欺骗）
- Token 比较使用 `secrets.compare_digest`（防时序攻击）
- 异步上下文中阻塞 socket 调用改为 executor
- Token 估算修正（中英文混合处理）
- WHOIS socket recv 循环改为正确检测对端关闭
- ChatRequest Pydantic 模型化
- customer.update 事务化（单事务，失败统一回滚）
- Skill router LRU 缓存上限可配置
- 制裁阈值提高，减少短查询误报

## [0.2.0] — 2026-05-14

### Added
- 海关数据工作目录（自动创建 + CSV/Excel 文件支持）
- b2b-customs-data skill 自动读取海关数据目录
- toolsets 环境变量可配置（TRADE_ENABLED_TOOLSETS）
- 显式启用 web/search/file/terminal/code_execution/browser/skills/memory/cronjob/todo toolset

### Changed
- 平台诊断 skill 改为支持任何网站（B2B 平台 + 公司官网 + 独立站）
- SQL 时间比较改为参数化

### Fixed
- create_agent 修复 Agent 无法搜索网络的问题
- customer.update 死代码行（NameError）
- saveCustomer 参数缺失

## [0.1.0] — 2026-05-13

### Added
- 首个公开版本
- FastAPI 服务器 + B2B chat SPA
- 多公司管理（multi-tenancy）
- 文档库管理（libraries CRUD）
- 客户管理（customers CRUD + 文档库关联）
- 对话记忆（conversations + Hindsight 长期记忆）
- 13 个 b2b-* skills（OSINT/邮件情报/客户开发/文档/文档生成/平台/领英/社媒/海关/onboarding/自动化/客户管理/数据目录）
- OSINT 尽职调查（WHOIS + 邮箱验证 + 制裁筛查 + 技术栈 + LinkedIn）
- 定时任务（Cron）集成
- 首次运行引导（onboarding）
- Windows 兼容（Gateway 启动 + CREATE_NEW_PROCESS_GROUP）
- Skill 自动路由（关键词匹配 + 注入）

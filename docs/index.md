---
layout: default
---

<style>
  .container { max-width: 100% !important; padding: 0 2rem !important; }
  .container .content { max-width: 100% !important; }
  pre, code { white-space: pre-wrap !important; word-break: break-all !important; }
  pre { padding: 1rem !important; font-size: 0.9rem !important; }
</style>

<!-- Hero -->
<div style="text-align:center; padding:2rem 1rem 1rem;">
  <h1 style="font-size:2.4rem; margin-bottom:0.2em;">Smart Trade AI</h1>
  <p style="font-size:1.2rem; color:#58a6ff; margin:0;">外贸业务员的本地 AI 助手</p>
  <p style="color:#8b949e;">不需要懂技术，跟着步骤走，10 分钟装好</p>
  <a href="#windows-install" class="btn" style="margin:0.5rem;">点我开始安装 →</a>
</div>

---

<div style="text-align:center;">
  <img src="screenshot-2.png" alt="Customer & Cron Panel" style="max-width:75%; border-radius:8px; box-shadow:0 4px 24px rgba(0,0,0,.4);">
  <p><em>客户管理 + 定时任务面板</em></p>
</div>

---

## 这个工具能帮你做什么？

| 你平时的麻烦 | 用了这个工具之后 |
|-------------|----------------|
| 每天打开好几个网站查汇率、金价、新闻 | 每天早上自动生成一份简报，汇率、行情、客户提醒全在里面 |
| 想了解一个新客户靠不靠谱，不知道从哪查 | 输入邮箱或公司名，自动帮你查域名、制裁名单、LinkedIn 等 6 项 |
| 给客户写开发信，每封都要重新想 | 告诉它客户是做什么的，它帮你写好开发信 |
| 阿里国际站、中国制造网要每天登录看有没有新询盘 | 它定时帮你检查，有新的就提醒你 |
| 客户资料散落在微信、Excel、邮件里，找起来费劲 | 统一管理，按重要程度分 A/B/C 级，还能关联合同文件 |
| 不知道 LinkedIn 该发什么内容 | 每周帮你规划好要发什么，轮换不同话题 |

---

<div style="text-align:center;">
  <img src="screenshot-1.png" alt="AI Chat Interface" style="max-width:75%; border-radius:8px; box-shadow:0 4px 24px rgba(0,0,0,.4);">
  <p><em>AI 对话界面 — 像聊天一样使用</em></p>
</div>

---

## <a id="windows-install"></a>Windows 电脑安装教程

> 如果你是 Windows 电脑，看这一节就够了。整个过程大约 10 分钟，不需要任何电脑知识，跟着做就行。

### 第一步：安装 Python（只需做一次）

这个工具是用 Python 语言写的，所以你的电脑需要能"读懂" Python。就像要看 PDF 需要装 Adobe Reader 一样，要运行这个工具需要装 Python。

**怎么装：**

1. 打开浏览器，访问 [python.org](https://www.python.org/downloads/)
2. 页面会自动识别你是 Windows，点击黄色的大按钮下载
3. 下载完成后，双击打开安装文件
4. **重要：第一个界面底部有一个勾选框「Add Python to PATH」，一定要打勾！**（不打勾的话后面没法用）
5. 打勾后，点击「Install Now」按钮
6. 等待进度条跑完，显示「Setup was successful」就装好了

> 如果已经装过 Python，可以跳过这一步。

### 第二步：打开 PowerShell

接下来的安装操作都在一个叫 **PowerShell** 的窗口里进行。它是 Windows 自带的，不用额外安装，就是一个输入文字然后电脑帮你干活的东西。你不用理解它，**只需要把命令复制进去，按回车就行**。

**怎么打开：**

1. 按键盘上的 **Win 键**（键盘左下角，四个方块那个图标），然后直接打字：`powershell`
2. 搜索结果里会出现一个蓝色图标的「Windows PowerShell」，点它打开
3. 你会看到一个**蓝底白字**（或黑底白字）的窗口，这就是 PowerShell

> 下文所有灰底绿字的内容，都是你需要**完整复制**到 PowerShell 窗口里、然后**按回车**执行的命令。在 PowerShell 里粘贴是**点右键**（不是 Ctrl+V）。

### 第三步：开启长路径支持（只做一次，做过的跳过）

Windows 默认不允许文件路径太长，但这个工具的文件路径比较长，需要提前放开限制。

1. 按 **Win 键**，输入 `powershell`
2. 搜索结果里，**右键点击**「Windows PowerShell」，选择「**以管理员身份运行**」
3. 在弹出的确认框点「是」
4. 把下面这行命令**完整复制**，在 PowerShell 窗口里**右键粘贴**，按回车：

```
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

5. 看到执行完没有报错就 OK 了
6. **重启电脑**让设置生效

> 这一步只需要做一次，以后永远不用再管。

### 第四步：安装 Hermes Agent（底层 AI 引擎）

这个工具依赖一个叫 Hermes Agent 的基础程序。Hermes Agent 就像是汽车的发动机，我们的工具是车身——得先有发动机才行。

把下面这行命令**完整复制**到 PowerShell 窗口，按回车：

```
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex
```

> 安装过程中会下载一些文件，需要几分钟。看到「安装完成」或「Installation complete」就说明好了。

### 第五步：安装 Smart Trade AI

发动机有了，现在装车身。

把下面这 4 行命令**一行一行**地复制到 PowerShell、按回车。等每一行跑完（光标重新闪烁）再复制下一行：

```
git clone --branch main https://github.com/chefroger/smart-trade-ai.git $env:LOCALAPPDATA\trade\foreign-trade-assistant

cd $env:LOCALAPPDATA\trade\foreign-trade-assistant

pip install -e "."

install-trade-skills
```

> 如果中间出现红色的报错文字，不要慌。大多数情况是网络不好没下载完整。把报错的那行重新复制执行一次就行。

### 第六步：获取 API Key

这个工具靠 AI 大模型来回答问题，你需要去模型厂商那里注册一个账号，获取一串 **API Key**（可以理解为一串密码，用来证明你有权限使用这个 AI）。

**推荐用 DeepSeek，目前性价比最高：**

1. 打开浏览器，访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 用手机号注册账号
3. 登录后点「充值」，充个 10 块钱就够用很久了
4. 在左侧菜单找到「API Keys」，点「创建 API Key」
5. 把生成的那串字符**复制保存好**（只显示一次，关了就看不到了）

拿到了 API Key 之后，回到 PowerShell 窗口，输入：

```
hermes setup
```

会出来一个选择界面，用键盘上下箭头选 DeepSeek，回车。把刚才复制的 API Key **右键粘贴**进去，回车。

> 还建议顺便注册 [Tavily](https://tavily.com)（免费，不用充值），用于搜索客户信息。同样在 `hermes setup` 里配置。

### 第七步：启动！

一切都准备好了。在PowerShell 窗口输入：

```
python server.py
```

回车后看到「Uvicorn running on http://127.0.0.1:9119」就说明启动成功了。

打开浏览器，在地址栏输入 **http://127.0.0.1:9119/trade**，回车，你就能看到界面了。

> 每次想用的时候，都要先打开 PowerShell，输入 `cd $env:LOCALAPPDATA\trade\foreign-trade-assistant`，回车；再输入 `python server.py`，回车。然后打开浏览器访问上面那个地址。关掉 PowerShell 窗口，程序就停了。

### 让电脑每次开机自动启动（可选）

如果你不想每次手动打开，可以在安装完成后，输入下面两行命令（一行一行执行）：

```
pip install pyinstaller

powershell -File scripts/build.ps1
```

完成后会在 `dist` 文件夹里生成一个 `Smart Trade AI.exe`，双击就能运行，不需要打开 PowerShell。可以把它拖到桌面。

### 安装中可能遇到的问题

| 你看到的 | 是什么意思 | 怎么办 |
|---------|-----------|--------|
| "不是内部或外部命令" | 说明 Python 没装好，或者装的时候没勾那个勾 | 回到第一步重新装 Python，**一定要勾选 Add Python to PATH** |
| 下载到一半卡住了 | 网络访问 GitHub 不稳定 | 你需要开 VPN（翻墙工具）的全局模式。如果不会用 VPN，可以找身边懂电脑的朋友帮忙。开了 VPN 后重试出错的命令 |
| 红色报错一大堆 | 通常是网络问题导致没下载完整 | 把报错那行命令重新执行一次。如果反复失败，确保 VPN 开着 |
| 打开网页显示「无法访问」 | 程序没启动成功 | 回到 PowerShell 窗口看看有没有报错。如果关了，重新打开 PowerShell，重新执行第七步 |
| 页面显示乱掉或按钮点不动 | 浏览器缓存了旧文件 | 按键盘上的 **Ctrl + Shift + R** 三个键一起按，强制刷新页面 |

---

## 苹果电脑（Mac）安装教程

### 第一步：打开"终端"

Mac 上的命令行叫「终端」。

在桌面右上角点放大镜图标（Spotlight），输入 `终端`，回车打开。

### 第二步：一键安装

把下面这行命令复制到终端窗口，按回车：

```
curl -fsSL https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh | bash
```

脚本自动完成所有安装。看到安装完成的提示后，执行：

```
hermes setup
```

按提示选择模型厂商、填入 API Key（和上面 Windows 第六步一样）。

然后启动：

```
python server.py
```

浏览器打开 http://127.0.0.1:9119/trade 。

### 手动安装（如果一键脚本失败）

把下面每一行依次复制到终端执行：

```
git clone --branch main https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent

cd ~/.hermes/hermes-agent && pip install -e "."

hermes setup

git clone --branch main https://github.com/chefroger/smart-trade-ai.git ~/.trade/foreign-trade-assistant

cd ~/.trade/foreign-trade-assistant && pip install -e "."

install-trade-skills

python server.py
```

> Mac 用户如果遇到 `git clone` 超时，同样需要开 VPN 全局模式。

---

## 15 项专业能力

| 场景 | 能力 |
|------|------|
| 平台诊断 | 分析阿里国际站 / 中国制造网产品页面，给出优化建议 |
| 社媒营销 | 生成 Facebook / Instagram / TikTok / YouTube 内容日历 |
| LinkedIn 运营 | 个人资料优化 + 内容策略 + 私信模板 |
| 海关数据 | 分析进出口数据，帮你找到高价值采购商 |
| 客户开发 | 根据目标市场和产品，自动生成开发信和跟进邮件 |
| 客户管理 | A/B/C 重要度分级、客户详情、关联合同文件 |
| 文档分析 | 上传 PDF / Word / Excel / PPT，AI 自动读取分析 |
| 商务文档生成 | 一键生成报价单、形式发票、合同 |
| 报价谈判 | 根据产品库和客户情况，给出谈判策略建议 |
| 客户背调 | 6 层验证：邮箱检测 → WHOIS → 制裁名单 → 邮箱真实性 → 技术栈 → LinkedIn |
| 每日简报 | 实时汇率 + 大宗商品行情 + 市场新闻 + 客户跟进提醒 |
| 定时任务 | 工作日自动执行：早报、开发信、社媒发布、每日总结 |
| 对话记录 | 按公司分开存储聊天记录，随时搜索回顾 |
| 能力生成器 | 用大白话描述你的需求，自动创建新功能 |

---

## 你的数据安全吗？

- **所有业务数据都存在你自己的电脑里**，不会上传到任何服务器
- 如果你用的是云端 AI（比如 DeepSeek），对话内容会发给 AI 厂商处理，**但不会包含客户姓名等身份信息**
- 如果你装 [Ollama](https://ollama.com) 用本地模型，连对话内容都不出你的电脑
- 多公司之间数据互相隔离
- 程序只允许你自己电脑上的浏览器访问，别人看不到

---

## 联系作者

<div style="text-align:center;">
  <img src="wechat-contact.jpeg" alt="WeChat Contact" width="200" style="border-radius:8px;">
  <p>扫码添加微信，备注「Trade」</p>
  <p>商务合作或技术支持：<a href="mailto:lauroge@gmail.com">lauroge@gmail.com</a></p>
</div>

---

<p style="text-align:center; color:#8b949e;">
  Smart Trade AI — 外贸业务员的本地 AI 助手 · 不需要懂技术<br>
  <a href="https://github.com/chefroger/smart-trade-ai">GitHub</a> ·
  <a href="https://github.com/chefroger/smart-trade-ai/releases">Releases</a>
</p>

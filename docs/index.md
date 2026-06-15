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

> 整个过程大约 10 分钟。你不需要懂任何电脑技术，只要会下载安装软件、会复制粘贴文字就行。

---

### 第一步：安装 Python（只需做一次）

这个工具是用 Python 语言写的，你的电脑需要先装一个 Python 才能运行它。就像你要看 PDF 文件得先装一个 PDF 阅读器一样。

**操作步骤：**

1. 打开浏览器（就是上网用的那个程序），在地址栏输入 **python.org/downloads** 然后回车
2. 页面会自动识别你是 Windows 电脑，点击页面上那个 **黄色的大按钮** 开始下载
3. 下载完后，**双击**打开刚才下载的那个文件（一般在浏览器左下角能点开）
4. 安装窗口打开后，**先看窗口最下面**——有一个小方框写着「**Add Python to PATH**」，**一定要打勾！** 这一步最容易忘记，忘了后面整个装不了
5. 打勾之后，点击上面的「**Install Now**」按钮
6. 等进度条跑完，出现「Setup was successful」就装好了，关掉安装窗口

> 如果你以前已经装过 Python，这一步可以跳过。

---

### 第二步：打开 PowerShell

接下来的安装步骤需要在 **PowerShell** 里操作。你可能在电视剧里见过黑客在黑屏幕上敲代码——PowerShell 就是那样的一个窗口。不过别紧张，你不需要自己写代码，只要**把我给你的命令复制进去、按回车就行**。

**怎么找到 PowerShell：**

1. 看你的键盘，**左下角有一个 Windows 图标的键**（四个方块组成的那个，叫 Win 键），按一下它
2. 这时候屏幕上会弹出一个搜索框，**直接打字**输入：`powershell`
3. 搜索结果里会出现一个图标是**蓝色**的、名字叫「**Windows PowerShell**」的程序，**点击它**
4. 屏幕上会弹出一个**蓝色背景**（也可能是黑色背景）的窗口，里面有一些白色文字和一个闪烁的光标——这就是 PowerShell 了

> **两个小提示：**
> - 在 PowerShell 里**粘贴文字的方法**和平时不一样：不是按 Ctrl+V，而是**在窗口里点一下鼠标右键**，刚才复制的内容就会粘上去
> - 下面出现的所有 `灰底文字`，都是你需要复制到 PowerShell 里执行的命令

---

### 第三步（推荐）：一键安装

Python 装好之后，最省事的方法是用**一键安装脚本**——把下面这一行命令复制到 PowerShell 里执行，它会自动帮你装好所有东西：

```
irm https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.ps1 | iex
```

这个脚本会自动完成：安装 AI 引擎 → 安装 Smart Trade AI → 安装 15 个专业功能 → 初始化数据库 → 设置开机自启动。

等它跑完后，继续往下看**第六步**获取 API Key 就行。

> **如果一键脚本跑失败了**，不要紧，跟着下面的第四步和第五步手动装就行，效果一样。

---

### 第四步：开启长路径支持（只做一次，以前做过的跳过）

> 如果你已经通过一键脚本安装成功，可以跳过第四步和第五步，直接看第六步。

Windows 系统有一个默认设置，不允许文件路径太长。但这个工具安装时会产生比较长的路径，如果不改这个设置，后面安装会报错。我们只需要改一次，改完就不用管了。

**操作步骤：**

Windows 系统有一个默认设置，不允许文件路径太长。但这个工具安装时会产生比较长的路径，如果不改这个设置，后面安装会报错。我们只需要改一次，改完就不用管了。

**操作步骤：**

1. 按键盘上的 **Win 键**，输入 `powershell`
2. 这一次不要直接点开，而是**用鼠标右键点击**搜索结果里的「Windows PowerShell」
3. 在弹出的菜单里点「**以管理员身份运行**」
4. 弹出一个提示问"是否允许此应用对设备进行更改"，点「**是**」
5. 这时打开的 PowerShell 窗口标题栏会写着「**管理员**」——说明你成功以管理员身份打开了
6. 把下面这行命令**完整复制**（从 New 一直复制到 Force），在 PowerShell 窗口里**点右键粘贴**，然后**按回车**：

```
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

7. 没有出现红色报错就说明成功了，**关掉这个管理员窗口**
8. **重启电脑**让设置生效

> 这一步一辈子只需要做一次。重启电脑后继续下一步。

---

### 第五步：安装 Hermes Agent

这个工具背后需要一个叫 Hermes Agent 的程序来驱动 AI 功能。你可以把它理解为"发动机"——我们的工具是车身，得先有发动机才能跑。

1. 打开 PowerShell（这次用**普通方式**打开就行，不需要管理员）
2. 把下面这行命令**完整复制**，在 PowerShell 里**点右键粘贴**，按回车：

```
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex
```

3. 等待几分钟，它会自动下载和安装需要的文件
4. 看到提示「安装完成」或「Installation complete」就说明好了

> 如果等了很久都没反应或者报错了，多半是网络问题——参考页面底部的「常见问题」。

---

### 第六步：安装 Smart Trade AI

发动机装好了，现在装车身。

把下面 4 行命令**一行一行**地复制到 PowerShell 里执行。方法是：复制第一行 → 在 PowerShell 里右键粘贴 → 按回车 → 等它跑完 → 再复制第二行……以此类推。

```
git clone --branch main https://github.com/chefroger/smart-trade-ai.git $env:LOCALAPPDATA\trade\foreign-trade-assistant
```

```
cd $env:LOCALAPPDATA\trade\foreign-trade-assistant
```

```
pip install -e "."
```

```
install-trade-skills
```

> 每一行都要等它跑完再执行下一行。如果中间某一行出现红色报错，不要慌，大多数是网络不好——重新复制那一行再执行一次。

---

### 第七步：获取 API Key

这个工具需要连接 AI 大模型才能工作。AI 不是免费的，你需要去 AI 厂商那里注册一个账号、获取一个 **API Key**。

API Key 是一串很长的字母和数字，就像一个密码，用来证明你有权限使用这个 AI 服务。

**推荐用 DeepSeek（国产，便宜好用）：**

1. 打开浏览器，访问 **platform.deepseek.com**
2. 用手机号注册一个账号
3. 登录之后，点页面上的「**充值**」，充 10 块钱就够了（按用量扣费，10 块钱能用很久）
4. 在页面左侧找到「**API Keys**」，点进去，再点「**创建 API Key**」
5. 页面上会显示一串字符——这就是你的 API Key。**立刻把它复制保存下来**（比如粘贴到记事本里），因为它只显示这一次，关了就看不到了

拿到 API Key 之后，回到 PowerShell 窗口，输入下面这个命令然后回车：

```
hermes setup
```

这时会出现一个交互界面，操作方法：
1. 用键盘的 **上下方向键** 选择「**DeepSeek**」，选中后**按回车**
2. 它会问你要 API Key——把刚才保存的那串字符**右键粘贴**进去，按回车
3. 看到「配置成功」之类的提示就完成了

> 还建议顺手注册一个 [Tavily](https://tavily.com)（免费的，不用充值），它能让工具搜索实时信息。注册后同样在 `hermes setup` 里配置，选 Tavily 那一项，粘贴 Key。

---

### 第八步：启动！

全部装好了，现在来运行它。在 PowerShell 里输入：

```
python server.py
```

按回车。等待几秒，看到窗口里出现 **「Uvicorn running on http://127.0.0.1:9119」** 这行字，就说明启动成功了。

然后打开浏览器，在地址栏输入：**http://127.0.0.1:9119/trade** ，按回车，你就能看到界面了。

> **以后每次要用的时侯：** 打开 PowerShell → 输入 `cd $env:LOCALAPPDATA\trade\foreign-trade-assistant` 回车 → 输入 `python server.py` 回车 → 打开浏览器访问上面的地址。**关掉 PowerShell 窗口，程序就会停止**，所以使用期间不要关那个窗口。

---

### 让电脑每次开机自动启动（可选）

如果你不想每次都手动打开 PowerShell 输入命令，可以生成一个 exe 程序，以后双击就能运行：

在 PowerShell 里依次执行这两行（一行一行来）：

```
pip install pyinstaller
```

```
powershell -File scripts\build.ps1
```

等它跑完后，在安装目录下的 `dist` 文件夹里会出现一个 **Smart Trade AI.exe**。你可以把它**拖到桌面上**，以后双击这个图标就能启动，不需要再打开 PowerShell。

---

### 安装中可能遇到的问题

| 你看到的现象 | 可能的原因 | 怎么解决 |
|------------|-----------|---------|
| 输入 python 后提示「不是内部或外部命令」 | 安装 Python 时忘记勾选「Add Python to PATH」 | 回到第一步重新安装 Python，**一定要勾选那个框**。装完后关闭 PowerShell 重新打开再试 |
| 安装到一半卡住不动了 | 你的网络访问 GitHub 不稳定 | 你需要开 **VPN**（就是翻墙工具），开到**全局模式**。开好之后关掉 PowerShell 重新打开，重新执行卡住的那行命令 |
| 出现一大堆红色文字 | 大多是网络不好，没下载完整 | 把报错的那行命令重新复制执行一次。反复报错就确认 VPN 是否开好了 |
| 浏览器打开显示「无法访问此网站」 | 程序没有在运行 | 回到 PowerShell 看看是不是关掉了或者报错了。如果关了就重新打开 PowerShell，重新执行 `python server.py` |
| 页面打开了但是显示不正常、按钮点不动 | 浏览器缓存了旧版本的文件 | 同时按下键盘的 **Ctrl + Shift + R** 三个键，页面会强制刷新 |
| 提示「Filename too long」 | 第四步的长路径设置没生效 | 确认第四步已经做过，并且**重启过电脑**。如果还没重启，先重启再来 |

---

## 苹果电脑（Mac）安装教程

### 打开终端

Mac 上的操作窗口叫「**终端**」，和 Windows 的 PowerShell 类似。

**怎么打开：** 在桌面右上角点**放大镜图标**（或者同时按 Command + 空格键），输入 `终端` 两个字，按回车，就打开了。

### 一键安装

在终端里复制粘贴下面这行命令，按回车：

```
curl -fsSL https://raw.githubusercontent.com/chefroger/smart-trade-ai/main/scripts/install.sh | bash
```

等它自动安装完，然后配置 AI：

```
hermes setup
```

按提示选择 DeepSeek，粘贴 API Key（和上面 Windows 第七步的操作一样）。

最后启动：

```
python server.py
```

浏览器打开 **http://127.0.0.1:9119/trade** 。

### 手动安装（一键脚本失败时用）

在终端里依次执行以下每一行：

```
git clone --branch main https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
```

```
cd ~/.hermes/hermes-agent && pip install -e "."
```

```
hermes setup
```

```
git clone --branch main https://github.com/chefroger/smart-trade-ai.git ~/.trade/foreign-trade-assistant
```

```
cd ~/.trade/foreign-trade-assistant && pip install -e "."
```

```
install-trade-skills
```

```
python server.py
```

> Mac 如果遇到下载超时，同样需要开 VPN 全局模式。

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

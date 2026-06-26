---
layout: default
---

<style>
  .container { max-width: 100% !important; padding: 0 2rem !important; }
  .container .content { max-width: 100% !important; }
  pre, code { white-space: pre-wrap !important; word-break: break-all !important; }
  pre { padding: 1rem !important; font-size: 0.9rem !important; }
  .step-num { display:inline-block; width:32px; height:32px; line-height:32px;
    text-align:center; background:#2563EB; color:#fff; border-radius:50%;
    font-weight:bold; font-size:16px; margin-right:8px; }
  .step-title { font-size:1.3rem; font-weight:bold; margin:1.5rem 0 0.5rem; }
</style>

<!-- Hero -->
<div style="text-align:center; padding:2rem 1rem 1rem;">
  <h1 style="font-size:2.4rem; margin-bottom:0.2em;">Smart Trade AI</h1>
  <p style="font-size:1.2rem; color:#58a6ff; margin:0;">外贸业务员的本地 AI 助手</p>
  <p style="color:#8b949e;">Windows 版安装教程 · 不需要懂技术，跟着步骤走，20 分钟装好</p>
</div>

<div style="text-align:center; margin:1rem 0;">
  <p style="color:#8b949e; margin-bottom:0.5rem;">安装遇到问题？扫码加微信，备注「Trade」</p>
  <img src="wechat-contact.jpeg" alt="WeChat Contact" width="180" style="border-radius:8px;">
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

## 第一步：确保科学上网已启动

这个工具需要从 GitHub 下载代码，而 GitHub 在国内访问不稳定。在开始之前，**必须先打开你的科学上网工具**（VPN / Clash / V2Ray 等），确保网络通畅。

**验证方法：** 打开 **Google Chrome 浏览器**，在地址栏输入 `github.com`，回车。如果页面能正常打开，说明网络没问题，可以继续。

> 如果 GitHub 打不开，检查你的科学上网工具是否已启动、是否设为**全局模式**或 **TUN 模式**。

---

## 第二步：注册 DeepSeek 并获取 API Key

AI 不是免费的，需要去 DeepSeek 注册账号并充值。

1. 用 **Google Chrome 浏览器** 打开 **platform.deepseek.com**
2. 点击「注册」，用手机号注册一个账号
3. 登录后，点击页面上的「**充值**」，**充值 10 元以上**（按用量扣费，10 块钱能用很久）
4. 在左侧菜单找到「**API Keys**」，点击进入
5. 点击「**创建 API Key**」，名称填 `trade`，点确定
6. 页面上会显示一串字符（以 `sk-` 开头）——这就是你的 **DeepSeek API Key**
7. **立刻复制保存**，关掉后就再也看不到了

> 把这串 Key 先粘贴到记事本里，后面要用。

---

## 第三步：注册 Tavily 并获取 API Key

Tavily 是联网搜索引擎，让 AI 能搜索实时信息。

1. 用 **Google Chrome 浏览器** 打开 **tavily.com**
2. 点击「Sign Up」，**用 Gmail 邮箱注册**一个账号
3. 登录后进入 Dashboard，在 API Keys 区域找到你的 Key（以 `tvly-` 开头）
4. **复制保存**到记事本里

> Tavily 每月有 1000 次免费搜索额度，个人使用足够了。

---

## 第四步：在桌面创建 API Key 文件

把刚才拿到的两个 Key 整理到一个文件里，后面配置时会用到。

1. 在桌面上**右键** → 新建 → 文本文档
2. 把文件重命名为 `apikey.txt`
3. 打开文件，按以下格式粘贴：

```
DeepSeek API Key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Tavily API Key: tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

4. 保存并关闭。后面配置 Hermes 时需要从这里复制粘贴。

---

## 第五步：安装 Hermes Agent（AI 引擎）

Hermes Agent 是驱动 AI 的底层引擎，Trade 基于它运行。

### 5.1 以管理员身份打开 PowerShell

1. 按键盘 **Win 键**，输入 `powershell`
2. **右键点击**搜索结果里的「Windows PowerShell」
3. 选择「**以管理员身份运行**」
4. 弹出提示问"是否允许此应用对设备进行更改"，点「**是**」

### 5.2 开启长路径支持

在 PowerShell 里粘贴下面这行命令，按回车：

```
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### 5.3 一键安装 Hermes

接着执行下面这行命令：

```
irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1 | iex
```

等待几分钟，看到「安装完成」提示即可。

> 在 PowerShell 里粘贴的方法是**点一下鼠标右键**（不是 Ctrl+V）。

---

## 第六步：配置 Hermes（大模型 + 搜索）

安装完成后，在同一个 PowerShell 窗口输入：

```
hermes setup
```

这时会出现交互配置界面，按以下步骤操作：

1. 用键盘的 **上下方向键** 选择「**DeepSeek**」→ 按回车
2. 选择模型时，选「**deepseek-v4-flash**」（即 DeepSeek V4 Flash）→ 按回车
3. 粘贴你的 **DeepSeek API Key**（从桌面的 `apikey.txt` 复制）→ 按回车
4. 搜索服务选「**Tavily**」→ 按回车
5. 粘贴你的 **Tavily API Key** → 按回车

看到「配置成功」提示就完成了。

---

## 第七步：验证 Hermes 是否正常

在 PowerShell 里输入：

```
hermes
```

等它启动后，在对话框里输入：

```
hello
```

按回车发送。如果 AI 正常回复了，说明大模型配置成功。

> 按 `Ctrl+C` 可以退出 Hermes，回到命令行。

---

## 第八步：让 AI 帮你安装 Trade

重新启动 Hermes（输入 `hermes`），在聊天框里**复制粘贴**下面这句话：

```
请帮我安装 trade，地址是 https://github.com/chefroger/smart-trade-ai
```

AI 会自己去 GitHub 查看项目说明，然后自动执行所有安装命令。遇到报错它会自己排查重试，你只需要等它装完。

装完后，**关闭当前 PowerShell，重新打开一个新的**，输入：

```
trade
```

浏览器会自动打开 Trade 界面。如果没有自动打开，手动访问 **http://127.0.0.1:9119/trade**。

> 验证能用后，按 `Ctrl+C` 退出 trade（暂时退出，下一步设置开机自启后会自动运行）。

---

## 第九步：设置 Hermes Gateway 开机自启

Hermes Gateway 是定时任务调度器，Trade 的定时简报、定时询盘检查都依赖它。必须让它随系统启动，否则每天还要手动开。

在 PowerShell 里执行：

```
hermes gateway install
```

看到「服务已安装」或类似提示即成功。**以后开机时 Hermes Gateway 会自动在后台运行，无需手动启动。**

> 验证是否装好：按 `Win+R`，输入 `services.msc`，回车。在列表里找到「Hermes Gateway」服务，状态应为「正在运行」。

---

## 第十步：设置 Trade 开机自启（无终端窗口）

上一步装好了 Gateway，但 Trade 本身还没设为自启。这一步用**注册表 + VBS 脚本**的方式让 Trade 开机自动运行，**且不弹出任何终端窗口**——开机后直接打开浏览器访问 **http://127.0.0.1:9119/trade** 就能用。

### 10.1 创建启动器脚本（VBS + BAT，带日志）

把下面**整段命令**复制粘贴到 PowerShell 里，按回车：

```powershell
# 探测 trade.exe 完整路径（避免开机时 PATH 未完全加载导致找不到）
$tradeExe = (Get-Command trade -ErrorAction Stop).Source
if (-not $tradeExe) {
    Write-Host "❌ 找不到 trade.exe，请先确认 trade 已安装" -ForegroundColor Red
} else {
    Write-Host "找到 trade.exe：$tradeExe" -ForegroundColor Green
    $dir = "$env:LOCALAPPDATA\trade"
    $bat = "$dir\trade-autostart.bat"
    $vbs = "$dir\trade-autostart.vbs"
    $logFile = "$dir\trade-autostart.log"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    # .bat 用完整路径调用 trade.exe 并重定向日志（启动失败时可查日志）
    @"
@echo off
"$tradeExe" > "$logFile" 2>&1
"@ | Out-File -FilePath $bat -Encoding ASCII

    # VBS 隐藏窗口启动 .bat（不等待，不弹窗）
    @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c ""$bat""", 0, False
"@ | Out-File -FilePath $vbs -Encoding ASCII

    Write-Host "已创建启动器：$vbs" -ForegroundColor Green
    Write-Host "日志文件：$logFile（启动失败时打开它排查）" -ForegroundColor Yellow
}
```

看到绿色「已创建启动器」即成功。

> **这段命令做了什么：**
> 1. 用 `Get-Command trade` 探测 `trade.exe` 的完整路径，写入 .bat 文件——**不依赖 PATH**，开机早期也能找到
> 2. .bat 把 trade 的所有输出重定向到 `trade-autostart.log`——启动失败时打开这个日志就能看到错误，不用两眼一抹黑
> 3. VBS 以**隐藏窗口**模式启动 .bat——不会弹出黑框终端

### 10.2 写入注册表，开机自动运行该脚本

继续在 PowerShell 里粘贴下面这行，按回车：

```powershell
New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "TradeAutoStart" -Value "wscript.exe `"$env:LOCALAPPDATA\trade\trade-autostart.vbs`"" -PropertyType String -Force
```

没有报错就说明写入成功。

### 10.3 立即测试（可选但推荐）

不想等到明天才验证？在 PowerShell 里执行：

```powershell
wscript.exe "$env:LOCALAPPDATA\trade\trade-autostart.vbs"
```

等约 15 秒，然后打开浏览器访问 **http://127.0.0.1:9119/trade**。如果能看到 Trade 界面，且**没有弹出任何终端窗口**，说明配置完全正确。

> **如果打不开**：打开文件 `%LOCALAPPDATA%\trade\trade-autostart.log`（直接在资源管理器地址栏粘贴这个路径回车），看里面的错误信息。最常见的是 `ModuleNotFoundError`——说明 trade 安装有问题，回到第八步重装。

> **以后的使用方式：** 每天打开电脑，等约 30 秒（系统启动 + Trade 自动启动），直接浏览器访问 **http://127.0.0.1:9119/trade** 即可，**再也不用打开 PowerShell 手动输入 `trade`**。

### 10.4 如果想取消开机自启

将来不想要自启了，在 PowerShell 里执行：

```powershell
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "TradeAutoStart" -Force
```

即可移除自启，不影响 Trade 本身的使用。

---

## 常见问题

| 你看到的现象 | 怎么解决 |
|------------|---------|
| 第五步安装 Hermes 卡住不动 | 科学上网没开好。确认 VPN 是全局模式，关掉 PowerShell 重开再试 |
| `hermes` 输入后提示「不是内部或外部命令」 | 关掉 PowerShell 重新打开一个新的 |
| `trade` 输入后提示「不是内部或外部命令」 | 改成输入 `cd $env:LOCALAPPDATA\trade\foreign-trade-assistant` 然后 `python server.py` |
| Hermes 对话没反应 | API Key 没配置对。重新运行 `hermes setup` 检查 |
| 浏览器打开显示「无法访问此网站」 | 程序没在运行。打开一个新的 PowerShell，输入 `trade` 启动 |
| 开机后访问 127.0.0.1:9119/trade 打不开 | Trade 自启还没跑完，等 30 秒再试。若仍不行，打开 `%LOCALAPPDATA%\trade\trade-autostart.log` 看错误日志；或按 `Win+R` 输入 `taskmgr` 回车，看进程里有没有 `python.exe`，没有就手动运行第十步的 VBS 脚本 |
| 定时任务（每日简报等）不执行 | 第九步的 Hermes Gateway 没装好或没运行。重新执行 `hermes gateway install`，再到 `services.msc` 确认服务状态 |
| 提示「Filename too long」 | 第五步的长路径设置没做。回到 5.2 执行那行命令，然后**重启电脑** |

---

<p style="text-align:center; color:#8b949e; margin-top:3rem;">
  Smart Trade AI — 外贸业务员的本地 AI 助手<br>
  <a href="https://github.com/chefroger/smart-trade-ai">GitHub</a> ·
  <a href="https://github.com/chefroger/smart-trade-ai/releases">Releases</a>
</p>

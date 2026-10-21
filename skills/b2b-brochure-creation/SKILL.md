---
name: b2b-brochure-creation
description: 企业宣传册/产品目录制作全流程 — 从调研到PPTX交付，含多轮迭代优化
triggers:
  - "宣传册"
  - "产品目录"
  - "brochure"
  - "产品样册"
  - "企业画册"
  - "宣传册PPT"
  - "PPT宣传册"
  - "图册"
  - "产品分类"
  - "品类展示"
  - "插入幻灯片"
  - "产品展示页"
  - "修改幻灯片"
  - "补图"
  - "缺图"
  - "空白页"
  - "空缺"
  - "Wikimedia"
  - "Commons"
  - "配图"
category: 内容营销
version: 1.9.0
injection_prompt: |
  你是 b2b-brochure-creation 技能。当用户要求制作企业宣传册/产品目录/PPT时，执行以下完整12阶段工作流。
author: Foreign Trade Assistant
when_to_use:
  - 用户要做出企业宣传册 / 产品目录 / 公司介绍 PPTX（从零到交付）
  - 需要先调研对标企业、搜集产品实拍图、再按版式生成多页 PPTX
  - 已有大纲或草稿，需要迭代优化版式与图文排布
  - 不要用于：只改已有 PPTX 的文字/字号/换图（用 deck-revision-in-place）；单页海报或落地页设计
---

# b2b-brochure-creation — 企业宣传册制作工作流

## 阶段一：调研 & 信息收集

0. **⚠️ 必须先主动向用户索要参考资料再开始任务**
   - 提示用户："请提供本次宣传册的参考资料，例如目标公司网站、产品清单、已有样册PDF、行业对标企业清单等"
   - 参考文件存放位置如 `C:/Users/<user>\Desktop\沈阳山泰通用机械有限公司\产品规格\` 中的对标企业清单等
   - 用户未提供参考资料前，不得自行开始调研或生成内容
1. **目标公司信息**：确认宣传册对应的公司名称，从以下渠道收集真实数据：
   - 官网（web_extract 提取公司介绍、产品线、生产设备、检测设备、认证资质、合作客户等）
   - 对话/文档库中已有的客户资料
   - 同类型竞争对手网站（用户指定或自行搜索）
2. **整理数据清单**：确认以下信息是否齐全：
   - 公司中英文名称、地址、成立时间
   - 主营业务描述（1-2句话）
   - 产品线清单（含图片链接）
   - 生产设备清单
   - 检测设备清单
   - 认证资质
   - 合作国家/客户案例
   - 联系方式

## 阶段二：目录大纲

1. 根据调研结果制定目录大纲（中英双语），典型结构：
   - P1: 封面 Cover
   - P2: 企业概况 Company Overview（中英双栏 + 数据条）
   - P3: 产品中心 Products（图片网格 + 参数卡片）
   - P4: 制造能力 Manufacturing（设备表格 + 缩略图）
   - P5: 质量检测 Quality Control（信息卡片）
   - P6: 全球伙伴 Global Partners（区域分布 + 客户标志）
   - P7: 售后服务 After-Sales Service（服务流程 + 承诺）
   - P8: 为什么选择我们 Why Us（优势卡片）
   - P9: 封底 Back Cover（联系信息）
2. 提交给用户确认后再填充内容

## 阶段三：内容填充 & HTML初稿

1. 使用真实数据填充所有页面
2. 语言：中英双语（中文为主，英文为辅，或按用户要求）
3. 输出格式：单文件HTML（内联样式，无外部依赖）
4. 页面尺寸：默认A4竖版（210mm×297mm），用户要求横版时改为16:9（210mm×118mm）
5. 使用 `<div class="cover">` + `<div class="inner page">` + `<div class="back-cover">` 结构
6. 每个 inner page 格式：
   ```html
   <div class="inner page" id="p2">
     <div class="page-header">
       <div class="section-title">企业概况</div>
       <div class="section-title-en">Company Overview</div>
     </div>
     ...内容...
   </div>
   ```

## 阶段四：配图策略

### ⚠️ 关键前置步骤：配图方案须先经用户审批

> **教训来源**：用户曾经多次对嵌入后的图片不满意，不得不手动编辑PPTX删除不满意的图片。为避免重复返工，**在下载任何图片并将其嵌入PPT之前，必须先执行本步骤**。

#### 操作流程

1. **整理图片候选清单** — 按品类汇总找到的图片，格式如下：
   ```
   ## 配图方案 — 请审批

   | 品类 | 建议图片 | 来源 | 分辨率 | 说明 |
   |:-----|:---------|:-----|:-------|:-----|
   | 颚式破碎机 | 实景图-井下颚破 | 官网产品页 | 2816×2112 | ✅ 无logo，实景 |
   | 圆锥破碎机 | 设备图-圆锥破 | Wikimedia Commons | 2500×2000 | ✅ CC许可，无品牌标识 |
   | 球磨机 | (缺图) | 搜索中 | — | ⚠️ 官网无合适图片 |
   | ... | ... | ... | ... | ... |
   ```
2. **向用户展示清单** — 说明以下信息：
   - 每个品类的图片来源
   - 是否有品牌logo（需要裁剪的标注）
   - 缺少图片的品类和替代方案
3. **等待用户确认或调整** — 用户可能：
   - ✅ 批准方案 → 进入嵌入阶段
   - ❌ 指定换某些图片 → 重新搜索
   - ✏️ 提供新的来源（「去对标企业官网找」/「用Wikimedia搜」）
4. **不在用户确认前嵌入任何图片** — 即使是「我先放一版看看效果」也不行，必须先走审批

#### 常见用户反馈及处理

| 用户说 | 含义 | 处理 |
|:-------|:-----|:-----|
| "图片使用一定不要重复" | 整个PPT中每张图片只能出现一次 | 用哈希检查全PPT的图片去重 |
| "先去官网找，没有再去Wikipedia" | 优先级别1-2，用尽再升级 | 重新调整图片来源优先级 |
| "图片不完全符合要求" | 选择的图片类型/风格不对 | 展示清单时让用户指出不满意的具体品类 |
| "把竞品logo裁掉" | 对标企业图片可用但需去商标 | 裁剪后重新展示 |
| "我手动调整了一些图片" | 用户自己动手了 = 我的方案不达标 | 分析用户做了哪些修改，学习偏好 |

### 图片获取优先级（Cascade）

按以下严格顺序获取图片，前一来源不满足才进入下一级：

**⚠️ 前置检查：验证图片来源是否可用**
在开始爬取前，先用 `web_extract` 或 `requests` 检查目标网站是否在线：
- 官网域名是否过期/在售（如客户官网域名已过期，返回域名出售页面）
- 官网是否超时（如 sanland.com.cn 长时间无响应）
- 如官网不可用，直接从 Level 3 或 Level 4 开始
- 从之前对话中已下载的图片库（`C:/Users/<user>\Desktop\百欧PPT配图\`）优先使用

| 级别 | 来源 | 说明 |
|:----|:-----|:-----|
| **1. 目标公司官网** | 公司官网产品页/案例页 | `web_extract` + 图片URL下载，优先从其官网&母公司官网 |
| **2. 同集团官网** | 关联公司/母公司网站（如百欧的山泰官网） | 产品线重叠度高，图片风格一致 |
| **3. 对标企业官网** | 推荐清单中的同行网站 | 以黎明重工、浙矿重工、耐普矿机等，裁剪掉logo后使用 |
| **4. Wikimedia Commons** | CC许可免费商用图库 | 搜索 `Category:Jaw_crushers` 等设备分类 |
| **5. 通用搜索** | 广泛搜索内容相关的图片 | 明确标注为"行业参考示意图" |
| **6. 实体/图标** | 仅作为背景装饰 | banner式工厂实景照、emoji/Unicode图标 |

**关键检查项**：
- 每张图片在整个PPT中只能使用一次（**不重复**）
- 检查图片是否含品牌logo或水印（有则裁剪或弃用）
- 首轮使用级别1-2的图片，**用尽之后**再进入下一级

### 当官网图片不足时

1. 从以下渠道补充：
   - 同行业可比公司官网（参考推荐清单 `可直接对标参考｜国内矿山设备&备件正规官网企业清单.docx`）
   - **Wikimedia Commons**（CC许可免费商用图库，详见下方配图指南）
   - 广泛搜索内容相关图片（web_search）
   - **工厂实景图（如官网banner）** 可作为产品占位图，适合填充展示设备照片不足的品类
   - Unicode 图标/emoji 作为补充元素（非关键视觉位置）
2. **禁止使用AI生成的虚构产品图片**
3. 所有图片用 base64 内联嵌入 HTML（避免外部依赖）

### 配图指南：从 Wikimedia Commons 获取无品牌logo设备图片

> 已发现的可商用图片清单见 `references/wikimedia-commons-equipment-images.md`

当官网图片不满足以下之一时，应从 Wikimedia Commons 补充：

#### 已知的Commons品类覆盖情况

| 设备类型 | Commons覆盖 | 搜索关键词 | 建议 |
|:---------|:-----------|:-----------|:-----|
| 颚式破碎机 Jaw Crusher | ✅ 好 | `Category:Jaw_crushers` | 有~18张图，选2000px+ |
| 圆锥破碎机 Cone Crusher | ⚠️ 一般 | `Category:Crushers` | 专有分类缺失，从Crushers找 |
| 反击式破碎机 Impact Crusher | ❌ 无 | — | 从Pixabay或竞品官网找 |
| 锤式破碎机 Hammer Crusher | ❌ 无 | — | 从Pixabay或竞品官网找 |
| 球磨机 Ball Mill | ✅ 好 | `Category:Ball_mills` | ~38张图，多个选择 |
| 棒磨机 Rod Mill | ❌ 无 | — | 从竞品官网找 |
| 立式磨机 Vertical Mill | ❌ 无 | — | 从Pixabay找 |
| 振动筛 Vibrating Screen | ⚠️ 一般 | `Category:Vibrating_screens` | 图片较少但质量好 |
| 带式输送机 Belt Conveyor | ✅ 好 | `Category:Conveyor_belts` | ~200+张图，过滤mining类 |
| 板式给料机 Apron Feeder | ✅ 已找到 | `RCR_APRON_FEEDERS.JPG` | CC BY-SA, 1920×1080，无品牌logo，见 reference |
| 振动给料机 Vibrating Feeder | ❌ 无 | — | Pixabay / Flickr CC |
| 斗式提升机 Bucket Elevator | ❌ 无 | — | 仅图纸，需其他来源 |
| 耐磨配件 Wear Parts | ✅ 有 | `Category:Rock_crushers` | 如Bowl_Mantle.jpg |
| 工厂实景 Factory | ✅ 好 | `Category:Machine_shops` | 大量可选 |
- **图片含第三方品牌logo/水印** → 搜索无logo的实景图替代
- **产品类型缺图**（例如有颚破无圆锥破）→ 按品类找对应类别图
- **图片分辨率低 / 尺寸小** → 找2000px+大图

#### 操作步骤

1. **按设备分类浏览 Commons 类别页**
   常用矿业设备分类页（已收录大量 CC 许可图片）：
   ```
   https://commons.wikimedia.org/wiki/Category:Jaw_crushers
   https://commons.wikimedia.org/wiki/Category:Crushers
   https://commons.wikimedia.org/wiki/Category:Ball_mills
   https://commons.wikimedia.org/wiki/Category:Vibrating_screens
   https://commons.wikimedia.org/wiki/Category:Grinding_mills
   https://commons.wikimedia.org/wiki/Category:Conveyor_belts
   https://commons.wikimedia.org/wiki/Category:Rock_crushers
   https://commons.wikimedia.org/wiki/Category:Mining_machines
   https://commons.wikimedia.org/wiki/Category:Mineral_processing
   ```

2. **从类别页找到具体的图片文件页**（例如 `File:UG_jaw_crusher.jpg`）
   - 点开缩略图进入文件详情页
   - 确认许可协议（CC-BY / CC-BY-SA / GFDL 均可商业使用但需署名）
   - 从详情页提取原始文件直链：`https://upload.wikimedia.org/wikipedia/commons/{2ch}/{2ch}/{filename}`

3. **通过代理下载图片（Windows Clash 环境）**
   ```bash
   curl -L -o 01-颚式破碎机.jpg \
     -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
     -x http://127.0.0.1:7897 \
     --connect-timeout 15 \
     "https://upload.wikimedia.org/wikipedia/commons/7/75/UG_jaw_crusher.jpg"
   ```
   参数说明：
   - `-H "User-Agent: ..."` — 必须设置，否则 Commons 返回 403
   - `-x http://127.0.0.1:7897` — 走 Clash 代理（本用户环境）
   - `--connect-timeout 15` — 代理不稳时避免长等待

4. **验证下载成功**
   ```bash
   file 图片文件名.jpg  # 应为 "JPEG image data, ..."
   ls -lh              # 检查文件大小合理
   ```

5. **检查图片中是否包含品牌logo**
   - 如有明显logo，弃用并找替代
   - 可从竞品官网裁剪图片去掉logo区域
   - 优先选择采石场/矿井实景图（通常无品牌标识）

#### 下载失败排障

| 现象 | 原因 | 处理 |
|:-----|:-----|:-----|
| curl 返回 HTML（小文件非 JPEG） | URL 非 upload.wikimedia.org 直链 | 从 File 页取 `Original file` 直链 |
| 403 Forbidden | 缺少 User-Agent | 加 `-H "User-Agent: Mozilla/5.0 ..."` |
| 下载极慢或 timeout | 代理未通 | 检查 `curl -x http://127.0.0.1:7897 -I https://commons.wikimedia.org` |
| **HTTP 429 (Rate Limited)** | 限流，代理出口IP被限制 | 策略A: 去掉 `-x` 直连；策略B: 等30秒重试（`sleep 5 && curl ...`）；策略C: 换个代理端口或直连 |
| 图片含明显品牌logo | 来自竞品官网 | 截取无logo区域 / 换Commons图片 / 裁剪 |
| **python-pptx: `ValueError: unsupported image format, expected one of: ['BMP', 'GIF', 'JPEG', 'PNG', 'TIFF', 'WMF'], got 'MPO'`** | Commons上的某些.JPG文件实际是MPO格式（Multi-Picture Object，立体/3D照片格式）而非标准JPEG | 用PIL转换：`from PIL import Image; img = Image.open('file.jpg'); img = img.convert('RGB'); img.save('file_converted.jpg', 'JPEG', quality=90)` |

#### 竞品官网图片使用原则

从对标企业官网（如黎明重工、耐普矿机）下载的图片：
- 可以借鉴 **设备实景照片**，前提是裁剪掉品牌logo和标识
- 不得直接使用对方品牌logo作为自家宣传素材
- 图片标注为"行业参考示意图"而非"本公司产品实拍"

参考对标企业清单见 `C:/Users/<user>\Desktop\沈阳山泰通用机械有限公司\产品规格\可直接对标参考｜国内矿山设备&备件正规官网企业清单.docx`

### 动态排版原则（根据可用资源决定页数）

当为已有PPTX替换/更新产品图片时，按以下原则动态调整：

1. **盘点可用图片** — 按品类统计从官方渠道（目标公司官网、同集团官网）获取的 **新图片数量**（从未在当前PPT中使用的）
2. **每品类基准** — 每页展示5-6个产品，每个产品配1张唯一图
3. **页数决定规则**：
   - 某品类有 **≥10张** 可用新图 → **2页展示**（"主页面"+"续页"）
   - 某品类有 **5-9张** 可用新图 → **1页展示**（合并为1页，删除"续"页）
   - 某品类有 **<5张** 可用新图 → **与相邻品类合并**或使用工厂实景图填充
4. **删页操作** — 使用 python-pptx 的 `prs.slides._sldIdLst` 删除不需要的幻灯片（详见阶段十）

### 图片唯一性保证

```python
# 检查所有图片使用哈希确保唯一
all_hashes = []
for slide_idx in range(len(prs.slides)):
    for shape in prs.slides[slide_idx].shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            blob_hash = hash(shape.image.blob[:200])
            all_hashes.append((slide_idx+1, blob_hash))
total = len(all_hashes)
unique = len(set(h for _, h in all_hashes))
# unique 应接近 total，相差不超过1
```

---

## 阶段五：多轮迭代优化（V1→V7+）

实际项目很少一次到位。按以下节奏迭代：

| 版本 | 优化重点 | 检查项 |
|:----|:---------|:-------|
| **V1** | 内容骨架 + 版面结构 | 信息完整性、数据准确性 |
| **V2** | 消除空白、填充内容 | 每页无大片空白、内容充实 |
| **V3** | 方向/布局调整 | 横版/竖版、文字量配图比 |
| **V4** | 真实图片替换SVG | 全部使用真实照片 |
| **V5** | 全图版 | 不留SVG占位符 |
| **V6** | 图片位置修正 + 补图 | 图片与内容匹配、遗漏页面补全 |
| **V7+** | 大图替换 + 精细调整 | 矢量图→大图、图标大小、色彩协调 |

所有版本保存为独立文件（V1/V2/...），方便用户对比回溯。

## 阶段六：导出为PPTX

1. 使用 python-pptx 将最终HTML版本转换为可编辑PPTX
2. 关键脚本：参考 `b2b-doc-generation` skill 的 `scripts/html_to_pptx.py`
   - **脚本存储位置**：如有通用脚本需求，保存在 `C:/Users/<user>\smart-trade-ai\skills\b2b\b2b-brochure-creation\scripts\` 目录下，不要放到桌面或临时目录
3. 映射规则：
   - HTML page div → PPTX slide
   - base64图片 → native `add_picture()`
   - SVG元素 → 跳过（PPTX不支持SVG）
   - 文字块 → `add_textbox()`
   - 装饰元素 → shapes（圆角矩形、椭圆、直线等）
4. 所有输出必须可编辑（文字在文本框内可改，图片是原生图片）

## 阶段七：PPTX图片替换（在现有幻灯片中替换图片）

> 适用场景：已有PPTX展示页模板，只需替换产品图片为新图片，保持布局不变。

### 核心思路

删除旧PICTURE shape → 在同位置添加新图片：

```python
from pptx.enum.shapes import MSO_SHAPE_TYPE

slide = prs.slides[slide_idx]
pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]

for i, old_pic in enumerate(pics):
    # 保存位置和尺寸
    left, top = old_pic.left, old_pic.top
    w, h = old_pic.width, old_pic.height
    
    # 删除旧图片XML元素
    sp = old_pic._element
    sp.getparent().remove(sp)
    
    # 在同位置添加新图片
    slide.shapes.add_picture(new_img_path, left, top, w, h)
```

### 注意事项

- python-pptx 的 `shapes.add_picture()` 总是添加到顶层z-order，刚好覆盖在背景矩形之上
- 如果一页有多个图槽位，遍历 `pics` 列表的顺序与创建顺序一致（即XML中的先后顺序）
- 图片尺寸应保持与旧图片一致（`width, height`），避免扭曲

### 批量替换指定页的所有图片（完整工作流）

> 适用场景：用户说「N-M页都删图了」—— 表示这几页的所有图片都不满意，需要全部换掉。

### 信号识别

| 用户语句 | 含义 | 操作 |
|:---------|:-----|:-----|
| N-M页都删图了 / 第N-M页都删了图 | N-M页所有图片都不合格 | 全部替换，无保留。先分析各页文本确定品类，按品类搜索 -> 下载 -> 去重（每图全PPT只用一次），确保品类风格一致，展示配图清单 -> 用户审批 -> 嵌入 |
| 第N-M页删了一些图片 / 删掉了N-M页的一些图片 | 部分图片被删，**没删的保留不动** | **先精确分析**哪些图片被删（对比原文件/分析空位）→ **只补空白处**，已有图片完全不动。展示缺图清单，用户确定方向后执行 |
| 我把N-M页的图片删了（没有进一步限定） | 模糊表述，需要澄清 | **不要假设全部删了**。反问确认：「**第N-M页上的所有图片都删了，还是只删了一部分？**」务必先澄清，避免错误替换用户要保留的图片 |
| 我没有删掉的图片说明我需要保留它们 | 用户明确强调：保留未删图，只补空白 | **严格执行** — 分析哪几个位置是空白，仅在这些位置嵌入新图。已有图片不论质量如何，一律不动 |
| 这几页的图我不满意 | 指定页面的图片选择有问题 | 展示候选方案，请用户指定不满意的品类 |
| 把我删掉的一些图片重新加上 | 用户手动删图后要求补回 | 先分析被删图片的共同特征，再选风格一致的替代图 |

注意解读中文表述：
- 都删图了 / 删图了 = **全部删了**（全页替换）
- 删掉一些图片 = **部分删了**（只补空白）
- 删了N-M页的图片 = **模糊，必须追问澄清**
- 删除图片后用户手动编辑了文件 = 默认是部分删除，**先分析哪些位置空了**再行动

#### 执行步骤

1. **分析PPTX** — 读取每页的文本内容和图片数量，确认每页主题
2. **盘点本地图片库** — 检查 `C:/Users/<user>\Desktop\百欧PPT配图\` 中的可用图片（尺寸、内容类型）
3. **验证在线来源** — 官网是否还在线；如不可用，直接从本地库 + Wikipedia Commons 挑选
4. **映射图片到槽位** — 按品类匹配，每张图在整个PPT中只使用一次
5. **替换执行** — 用 python-pptx 逐页删除旧图、添加新图到相同位置

#### 代码参考

```python
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

pptx_path = r"path\to\presentation.pptx"
prs = Presentation(pptx_path)

# 每页图片路径列表（key: slide索引0-based, value: 图片路径列表）
IMAGE_MAP = {
    2: [  # Slide 3 - 产品总览
        r"C:/Users/<user>\Desktop\百欧PPT配图\百欧-破碎机.jpg",
        r"C:/Users/<user>\Desktop\百欧PPT配图\浙矿-振动筛.jpg",
    ],
    3: [  # Slide 4 - 破碎设备
        r"C:/Users/<user>\Desktop\百欧PPT配图\01-颚式破碎机.jpg",
    ],
}

# 确保图片路径都存在
for slide_idx, img_paths in IMAGE_MAP.items():
    for p in img_paths:
        if not os.path.exists(p):
            print(f"WARNING: 图片不存在 {p}")

for slide_idx, img_paths in IMAGE_MAP.items():
    slide = prs.slides[slide_idx]
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]

    if len(pics) != len(img_paths):
        print(f"WARNING: Slide {slide_idx+1} 图片数不匹配: 旧{len(pics)} 新{len(img_paths)}")

    # 1. 保存所有旧图片的位置/尺寸
    pic_slots = [{"left": p.left, "top": p.top, "width": p.width, "height": p.height, "rotation": p.rotation} for p in pics]

    # 2. 删除旧图片
    for p in pics:
        sp = p._element
        sp.getparent().remove(sp)

    # 3. 在同位置添加新图片
    for slot, img_path in zip(pic_slots, img_paths):
        if os.path.exists(img_path):
            pic = slide.shapes.add_picture(img_path, slot["left"], slot["top"], slot["width"], slot["height"])
            if slot["rotation"]:
                pic.rotation = slot["rotation"]
```

### 幻灯片删除（当需要合并页时）

```python
# 获取幻灯片ID列表
sldIdLst = prs.slides._sldIdLst

# 删除指定索引（必须从高到低，避免索引偏移）
for idx in sorted(delete_indices_0based, reverse=True):
    sldId_elem = sldIdLst[idx]
    rId = sldId_elem.get(qn('r:id'))
    sldIdLst.remove(sldId_elem)     # 从ID列表移除
    prs.part.drop_rel(rId)          # 删除对应的关系
```

## 阶段八：PPTX空白检测与补图（从Commons填充缺图页面）

> 适用场景：已有PPTX，部分页面完全没有图片（空白页），需要从Wikimedia Commons搜索合适图片并填入。

### 分析步骤

```python
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ppt_path = r"path\to\presentation.pptx"
prs = Presentation(ppt_path)

for i, slide in enumerate(prs.slides):
    img_count = len([s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE])
    first_text = ""
    for s in slide.shapes:
        if hasattr(s, 'text') and s.text.strip():
            first_text = s.text.strip()[:40]
            break
    status = "❌ 缺图" if img_count == 0 else f"✅ {img_count}图"
    print(f"  Slide {i+1}: {status} — \"{first_text}\"")
```

### 从Commons补图的核心原则

**⚠️ 黄金法则：已有图片保留不动，只补空白处**

当用户在已有PPTX中手动删除了一些图片并要求补全时：
1. **先精确分析** — 遍历每页的 shapes，找出所有 shape_type == 13 (Picture) 的图片。记录每页的总图片数、位置、对应的产品文本
2. **对比产品数量与图片数量** — 某页有5个产品品类但只有3张图，说明有2个空位
3. **只补空白** — 只有在确定某位置完全无图片（shape 列表中缺对应位置）时才插入新图
4. **保留已有图** — 已有图片不论质量如何，不动

**⚠️ 图片来源限制：当用户指定用Wikimedia Commons时，只从Commons搜图**

- 不要同时从本地图片库 `C:/Users/<user>\\Desktop\\百欧PPT配图\\` 拉图
- 每个图片在整个PPT中只能使用一次（用哈希检查去重）
- 插入后重新验证：检查每页图片数量是否正确

### 分析PPTX空白位置的代码模板

```python
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

ppt_path = r\"path\\to\\presentation.pptx\"
prs = Presentation(ppt_path)

for i, slide in enumerate(prs.slides):
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    texts = []
    for s in slide.shapes:
        if hasattr(s, 'text') and s.text.strip() and len(s.text.strip()) > 2:
            texts.append(s.text.strip()[:60])
    # 统计产品品类数（通常每个产品有名称+规格两行文本）
    product_count = len([t for t in texts if '/' in t and len(t) < 40])  # 含"/"的短文本一般是中英产品名
    print(f'Slide {i+1}: {len(pics)} images vs ~{product_count} products | 空位: {max(0, product_count - len(pics))}')
    for p in pics:
        x, y = p.left/914400, p.top/914400
        w, h = p.width/914400, p.height/914400
        print(f'  {p.name} at ({x:.1f}\", {y:.1f}\") = {w:.1f}x{h:.1f}\"')
```

### 根据页面主题选择图片

**⚠️ 优先检查本地图片库**
在搜索Commons之前，先检查 `C:/Users/<user>\Desktop\百欧PPT配图\` 中已有的27+张预下载图片（按品类命名，含颚破/圆锥破/球磨机/振动筛/输送设备等）。这些图片来自此前会话中的官网抓取和Wikipedia下载，可直接用。

| 页面主题 | 推荐Commons搜索类别 | 说明 |
|:---------|:--------------------|:-----|
| 服务流程 / 售后服务 | `Category:Machine_shops`, `Category:Interiors_of_factories` | 工厂车间内景、工人工作场景 |
| 制造能力 | `Category:Machine_shops`, `Category:CNC_machines` | 数控机床、加工中心、车间全景 |
| 质量检测 | `Category:Quality_control` | 化验室、测量仪器、检测场景 |
| 全球伙伴 / 出口 | `Category:Ports`, `Category:Global_logistics` | 港口、码头、集装箱运输 |
| 公司概览 | `Category:Factory_buildings`, `Category:Industrial_buildings` | 工厂外景、办公楼、厂区鸟瞰 |
| 联系方式 / 封底 | `Category:Industrial_buildings` | 工厂大门、办公大楼 |

### 从Commons类别页获取图片直链

1. 用 `web_extract` 打开Commons类别页（如 `https://commons.wikimedia.org/wiki/Category:Machine_shops`）
2. 从页面的缩略图区域提取文件名和尺寸信息
3. 从缩略URL构造直链：去掉 `/thumb/` 和文件名前的尺寸前缀

```
# 缩略URL（120px版本）
https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Machine_shop_at_CRMII.agr.jpg/120px-Machine_shop_at_CRMII.agr.jpg
# 直链URL（原始分辨率）
https://upload.wikimedia.org/wikipedia/commons/9/96/Machine_shop_at_CRMII.agr.jpg
```

#### 获取Commons图片直链的两种方法

**方法一：从缩略URL构造（适用于web_extract能读到的页面）**

```python
# 从Commons file页面找到的缩略URL:
# https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/UG_jaw_crusher.jpg/960px-UG_jaw_crusher.jpg
# 去掉 /thumb/ 和 /960px- 得到直链:
# https://upload.wikimedia.org/wikipedia/commons/7/75/UG_jaw_crusher.jpg
```

即 `.../commons/thumb/X/Xx/Filename.jpg/120px-Filename.jpg` → `.../commons/X/Xx/Filename.jpg`

**方法二：使用MediaWiki API（推荐，稳定可靠）**

```bash
curl -s -x http://127.0.0.1:7897 \
  "https://commons.wikimedia.org/w/api.php?action=query&titles=File:FILENAME.jpg&prop=imageinfo&iiprop=url&format=json" \
  -H "User-Agent: Mozilla/5.0" | python -c "
import sys, json
data = json.load(sys.stdin)
pages = data['query']['pages']
for pid, info in pages.items():
    if 'imageinfo' in info:
        print(info['imageinfo'][0]['url'])
"

### 下载图片

```bash
curl -L -o "输出文件名.jpg" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -x http://127.0.0.1:7897 \
  --connect-timeout 15 \
  "https://upload.wikimedia.org/wikipedia/commons/X/Xx/Filename.jpg"
```

**代理参数**：本用户Windows环境使用 `-x http://127.0.0.1:7897`（Clash），如未挂代理可去掉。

**HTTP 404排障**：直链中的 `X/Xx` 是文件名的MD5前两个字符，有大小写区分，务必从Commons页面直接复制（可从 `web_extract` 的缩略URL中提取路径部分）。

### 将图片插入PPTX的空白页

```python
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

ppt_path = r"path\to\presentation.pptx"
prs = Presentation(ppt_path)

# 插入到缺图页面
slide = prs.slides[slide_idx]  # 缺图的幻灯片索引

# 确定不遮挡文字的放置位置
# 常用策略：
# 1. 全宽底部装饰条（不遮挡已有内容）
slide_w = prs.slide_width
slide_h = prs.slide_height
img_top = int(slide_h * 0.84)   # 放在底部16%区域
img_height = int(slide_h * 0.16)

# 2. 右侧装饰小图（如果右侧有空）
img_left = int(slide_w * 0.80)
img_width = int(slide_w * 0.18)

# 3. 左下角/右下角小图

pic = slide.shapes.add_picture(image_path, left, top, width, height)

# 将图片移到最底层（z-order最底层，不遮挡文字）
sp = pic._element
sp_parent = sp.getparent()
sp_parent.remove(sp)
sp_parent.insert(0, sp)  # 插入到XML最前面 = 视觉最底层
```

### 放置策略选择

| 策略 | 位置 | 适合页面 |
|:-----|:-----|:---------|
| **全宽底部装饰条** | y=84%~100%, x=0~100% | 页面底部有空白留白的页面 |
| **右上角装饰** | x=80%~98%, y=0.4"~2.0" | 右上角只有页码/无内容的页面 |
| **右下角装饰** | x=75%~98%, y=85%~100% | 右下角空白的页面 |
| **全页背景** | x=0~100%, y=0~100%，移到底层 | 内容较少、需要背景填充的页面 |

**重要**：插入后检查图片是否与文字/形状重叠。如有重叠，缩小或移动图片位置。

## 阶段九：PPTX修复与QA

1. 转换后的PPTX必须检查以下常见问题：
   - 元素重叠（文字穿透图形、行列碰撞）
   - 文字溢出文本框边界
   - 分页线/装饰线错位（标题换行后与装饰线脱离）
   - 图标过小或比例失调
   - 间距不均匀（某些区域拥挤、某些空旷）
   - 页边距不足
2. 使用 markitdown 提取文本验证内容完整性
   ```bash
   python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|placeholder"
   ```
3. 对每个问题修复后重新验证受影响页面
4. 常见修复操作：调整文本框尺寸、移动元素位置、缩放图片、修改字号

## 阶段十：PPTX产品分类页插入（在现有PPTX中新增页面）

### 场景说明

当客户要求在现有宣传册PPT中 **从指定位置开始插入产品分类展示页**（例如 破碎→筛分→研磨→输送，每类1-2页），python-pptx 不支持 `insert_slide()`，需要使用 **底层XML操作**（unzip → 修改 → repack）。

### 关键执行顺序

```
1. 从原PPTX提取所有图片（python-pptx → extracted_images/）
2. 解压PPTX到临时目录（zipfile）
3. ⚠️ 重命名旧幻灯片文件（如 slide3→slide11）—— 必须先做！
4. 创建新幻灯片XML（用旧slide为模板，lxml修改文本+图片引用）
5. 清理 [Content_Types].xml 重复条目后重新添加
6. 更新 presentation.xml 幻灯片顺序
7. 更新 presentation.xml.rels（修正Target + 添加新Relationship）
8. 重新打包为PPTX
9. 验证总页数
10. 清理中间文件
```

### ⚠️ 关键陷阱（必读）

| 陷阱 | 后果 | 处理方式 |
|:-----|:------|:--------|
| **先创建新 slide3.xml 再重命名旧 slide3.xml** | 旧内容被覆盖丢失 | **先重命名旧幻灯片**再创建新的，顺序不可逆 |
| **[Content_Types].xml 出现重复 Override** | PPTX打开报错或python-pptx崩溃 | 一次性删除所有slide Override后按顺序重新添加 |
| **rId冲突（rId13-rId15已被presProps/viewProps/tableStyles占用）** | python-pptx加载报 KeyError | 新幻灯片使用 rId16+，避开已占用的rId |
| **新幻灯片rels只含layout不含图片引用** | 图片显示为红叉 | 每个新幻灯片必须创建独立 `.xml.rels`，包含所有图片 Relationship |
| **extracted_images/目录被误删** | 找不到图片，全显示no image file | 图片提取后确认目录存在；若被清理需重新提取 |

### 3x2产品网格布局（推荐模式）

使用模板中的 3行×2列 网格展示产品，每个格子包含：
- **设备/配件实物图**（占格子~55%高度）
- **中英文名称**（~14%高度）
- **关键规格参数**（~25%高度）

每页展示 **5个产品**（最后一格留空或删除对应pic元素），覆盖设备+配件。

### 品类展示页内容模板

```
类别标题: 破碎设备
英文标题: Crushing Equipment
标签行: ⚡ 百欧{类别} — {副标题}
产品项: 5个 (设备名 / 英文名 / 规格参数 / 图片文件)
备件栏: 配件清单 | 材质说明
```

### 图片引用替换要点

```python
# 解析模板XML
root = etree.fromstring(template_xml_bytes)

# 1. 替换文本节点
for t_elem in root.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'):
    if t_elem.text in {'产品总览', '产品名称'}: t_elem.text = new_text
    if t_elem.text == '02 / 10': t_elem.text = f'{new_page_num:02d} / 18'

# 2. 替换图片引用（新rId必须与rels文件一致）
for pic_idx, pic in enumerate(all_pic):
    blip = pic.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
    blip.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed', f'rIdI{pic_idx}')

# 3. 删除多余pic元素
if pic_idx >= len(items):
    pic.getparent().remove(pic)

# 4. 创建新rels文件
rels = ['<Relationships xmlns=".../package/2006/relationships">']
rels.append(f'<Relationship Id="rIdI{pic_idx}" Type=".../relationships/image" Target="../media/{media_name}"/>')
rels.append(f'<Relationship Id="{layout_rid}" Type="...slideLayout" Target="../slideLayouts/slideLayout7.xml"/>')
rels.append('</Relationships>')
```

## 阶段十一：分析用户修改后的PPTX（逆向学习用户偏好）

> **场景**：用户对上一版交付物不满意，手动编辑了PPTX文件（删除/替换图片、调布局等），要求你"分析我修改后的文件"。
>
> **目的**：通过对比交付版本和用户修改版本，理解用户偏好，避免下次犯同样错误。

### 分析流程

1. **确认工作对象** — 用户修改后的 `.pptx` 文件路径
2. **提取结构信息** — 用以下命令获取每页的图片数量和页面主题：
   ```bash
   python -c "
   from pptx import Presentation
   from pptx.enum.shapes import MSO_SHAPE_TYPE
   prs = Presentation('用户修改后的文件.pptx')
   for i, slide in enumerate(prs.slides, 1):
       imgs = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
       txt = ''
       for s in slide.shapes:
           if hasattr(s, 'text') and s.text.strip():
               txt = s.text.strip()[:50]
               break
       print(f'Slide {i}: {len(imgs)} images | {txt}')
   "
   ```
3. **提取所有嵌入图片** — 解包PPTX，保存所有 `ppt/media/` 文件到临时目录用于对比
4. **对比分析（与上一次交付版本）**：
   - 哪些图片被**删除**了？→ 分析用户不喜欢的图片特征（含logo? 分辨率低? 重复?）
   - 哪些图片被**替换**了？→ 分析用户偏好的图片来源（官网→实景? 竞品→无品牌?）
   - 哪些页面被**删掉了**？→ 用户认为不需要的页面
   - 哪些位置用户**留空**了？→ 用户没有现成的图片，需要你补
5. **总结偏好信号**（记忆到 `memory` 中）：
   - 保持简洁：如"用户偏好官网实景图，拒绝竞品品牌图"
   - 指向具体：如"产品页每品类保持2张图，不超3张"
6. **根据结论行动**：补图、重新排版、或者重新制作

### 常见用户修改模式与含义

| 修改行为 | 可能含义 | 应对 |
|:---------|:---------|:-----|
| 删掉某张竞品官网图片 | 用户不喜欢用竞品素材 | 下次优先用本公司/集团官网图片 |
| 删掉整页产品展示 | 页面内容重复或不够吸睛 | 减少品类页数，提高单页质量 |
| 把A图移到B位置 | 用户有明确的视觉层次偏好 | 下次按此顺序排列品类 |
| 替换为官网/自己拍的图 | 用户有实拍素材 | 询问用户是否有未提供的素材库 |
| 删掉重复使用的图片 | "图片使用一定不要重复" | 插入前用哈希检查去重 |
| 删掉N-M页的全部图片 | 图片选择完全不达标 | 盘点所有品类，重新搜索->筛选->审批->嵌入全流程，每品类建议2-3个候选让用户选方向 |
| 全部删除只剩文字框架 | 图片风格/选择完全不符合预期 | 回到Phase 4审批步骤，让用户亲自选图。优先询问用户想要的风格方向（实景/示意图/工厂图），再提供候选方案审批

## 阶段十二：过程文件清理

## 📋 最终交付规范（必读）

### 输出文件夹

- 最终 PPTX 文件必须保存到 **桌面「宣传册」文件夹**：`C:/Users/<user>\Desktop\宣传册\`
- 如果该文件夹不存在，自动创建
- **不保留** 任何HTML中间版本在桌面上

### 过程文件清理 & 脚本存储

> ⚠️ 以下两条为 **所有 B2B Skill 的通用守则**（详见 `AGENTS.md` → `Universal Skill Operating Norms`），此处仅列摘要：

1. **过程文件自动清除** — 任务完成后自动清理所有中间产物（HTML草稿、临时图片、一次性脚本等）
2. **通用脚本统一存储** — 通用脚本保存在 `skills/b2b/b2b-brochure-creation/scripts/` 目录下，一次性脚本用后即删

## 输出文件命名规范

最终文件夹 `C:/Users/<user>\Desktop\宣传册\` 中仅保留一个文件：

```
{公司名}_矿山行业宣传册_PPT.pptx
```

如有多轮修改，同一文件直接覆盖更新，不保留多版本。

## 色板参考

| 行业 | 主色渐变 | 强调色 | 适用场景 |
|:-----|:---------|:-------|:---------|
| 矿山/重工 | #0f2027→#2c5364 | #e8c44a (金) | 破碎机、球磨机、矿山设备 |
| 精密制造 | #1a1a2e→#16213e | #c0c0c0 (银) | 数控机床、精密零件 |
| 新能源 | #0a3a2a→#1a5a3a | #00c897 (青) | 光伏、储能、电池 |
| 建筑/建材 | #2d2d2d→#4a4a4a | #d4a853 (古铜) | 钢材、水泥、工程机械 |
| 食品/农业 | #3a5a2a→#5a7a3a | #f0c040 (暖黄) | 食品机械、农业设备 |
| 科技/电子 | #0a0a2e→#1a1a4a | #00d4ff (亮蓝) | 自动化、电子设备 |

## 布局模式参考

详见 `b2b-doc-generation` skill 的 `references/brochure-layout-patterns.md`，包含6种标准布局模式（中英双栏/图片网格/表格+缩略图/信息卡片/区域分布/优势卡）。

## 页面填充技巧（消除空白）

当页面内容不足以填满高度时，用以下元素填充：

| 填充工具 | 适用页面 | 示例 |
|:---------|:---------|:-----|
| 数据条 Data-bar | 概览/检测页 | 5列数据卡片（45,000㎡ / 300+员工） |
| 功能标签行 Feature-strip | 产品/详情页 | 5个标签（铸造/热处理/机加工/装配/质检） |
| 参数卡片行 Product-spec | 产品页底部 | 6列产品参数（处理量/进料/效率...） |
| 实景图片条 | 伙伴页底部 | 3张产品/设备缩略图横排 |
| 应用场景网格 App-grid | 产品详情页 | 2x2网格列出典型项目案例 |
| 服务网格 Service-grid | 服务流程页 | 2x3网格列出6项售后服务承诺 |

## 打印支持

```css
@media print {
  body { background: #fff; }
  .page { margin: 0; box-shadow: none; page-break-after: always; }
  .cover, .back-cover {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
```

## HTML→PPTX 转换参考

详见 `b2b-doc-generation` skill 的：
- `references/html-to-pptx-session-20260715.md` — 转换注意事项
- `scripts/html_to_pptx.py` — 完整转换脚本

## 相关Skills

- `b2b-doc-generation` — HTML→PPTX转换脚本、布局模式参考
- `powerpoint` — PPTX创建/编辑/模板操作
- `creative/architecture-diagram` — SVG/架构图（如需流程图配图）

## 参考文件

- `references/pptx-insert-slides-via-xml.md` — 在现有PPTX中通过XML操作插入新幻灯片的完整方案（含rId对照表、常见错误排除）
- `references/wikimedia-commons-equipment-images.md` — Wikimedia Commons 矿山设备图片清单（直链下载URL、许可协议、操作步骤与排障）

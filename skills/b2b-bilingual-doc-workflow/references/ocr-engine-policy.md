# OCR 引擎选择原则（v2.9.0）

## 铁律：禁止外部付费 OCR API

用户明确拒绝了 Google Cloud Vision / Gemini Vision 等外部付费视觉 API 用于 OCR。
PaddleOCR-VL 与 PP-OCRv5 均为本地 + Apache 2.0 开源，符合此铁律。

## 引擎链（按场景分流）

```
整页文档/合同/扫描 PDF/表格（结构化）
  → PaddleOCR-VL（本地 GPU VLM，Markdown/JSON/DOCX，保留表格/标题/阅读顺序）

工程图纸线级文字（标题栏/BOM/尺寸标注/技术要求）
  → PP-OCRv5（本地 GPU 检测+识别，ru/uk 西里尔，每行带置信度+坐标）

兜底 → OCR.space（在线免费）→ RapidOCR（离线 ONNX）
```

## 两引擎定位

### PaddleOCR-VL（整页文档解析）
- 0.9B VLM（版面分析 PP-DocLayoutV3 + VLM 识别），109 语言含西里尔
- 适用：俄语合同/规格书/扫描件/表格整页结构化解析
- 不适用：工程图纸（文字分散成几十上百小块，VLM 逐块生成 → 单图几分钟）

### PP-OCRv5（线级检测+识别）
- 经典 OCR 管线：文字检测（PP-OCRv5_det）+ 识别（PP-OCRv5_rec）
- 适用：工程图纸（稀疏/旋转/任意位置的文字线）、标题栏、BOM 表
- 西里尔支持：ru/uk/be/bg 等 109 语言（PP-OCRv6 反而砍掉了西里尔，故用 v5）
- 输出：每行 [文本, 置信度, 坐标]，低分(≤0.5)多为乱码可程序化过滤
- 实测（磨机联轴器图纸）：西里尔拼写准确，长词全对
- 速度：GPU 每页 1-2 秒；模型 ~90MB

## 关键坑（均已在脚本内自动处理）

1. **中文用户名路径**：paddle C++ 推理层打不开 `C:/Users/<user>\.paddlex`。
   解决：`PADDLE_PDX_CACHE_HOME` 重定向到无中文路径（脚本已内置）。
2. **模型下载源**：国内用 `PADDLE_PDX_MODEL_SOURCE=modelscope`（阿里 CDN 最稳），
   HF 兜底 `PADDLE_PDX_HUGGING_FACE_ENDPOINT=https://hf-mirror.com`。
3. **GPU 驱动**：CUDA ≥ 11.8 对应驱动 ≥ 520。老驱动不可用，需升级（Studio 驱动即可）。
4. **结果结构**：PaddleOCR-VL 全文在 `res.markdown['markdown_texts']`；
   PP-OCRv5 行文本在 `res.json['res']['rec_texts']`（+ rec_scores + rec_polys）。
5. **旋转文字**：图纸上旋转/镜像标注 OCR 会出乱码，两引擎都不自动转正。
   用 `use_textline_orientation` 或按 skill 的标题栏裁剪放大法处理。

## 新机器部署计划（2026-08 立项：16GB 显存整机）

背景：当前跑在笔记本 RTX 2060 6GB，6GB 显存是 VLM/全分辨率/多进程的硬瓶颈。
计划采购 16GB 显存整机（ROG NUC 2026：5080 Laptop 16GB + Ultra 9 290HX 24核 + 32GB；或联想刃 9000K：台式 5080 16GB + U9 285K）。
Paddle 官方已适配 RTX 50 系 Windows（README：支持 Windows 用户使用英伟达 50 系显卡），无兼容坑。

### 升级矩阵（对应当前引擎）

| 场景 | 当前 | 升级目标 | 官方数据（2026-08） |
|---|---|---|---|
| 整页文档/合同/扫描件 | PaddleOCR-VL 0.9B（2025 旧版） | PaddleOCR-VL-1.6（2026-05-28 随 PaddleOCR 3.6.0） | OmniDocBench v1.6 96.3% SOTA 新纪录；109 语言含西里尔 |
| 图纸线级（西里尔主力） | PP-OCRv5 mobile | 保持 v5 ru/uk + 升 server 档；尝鲜 PP-OCRv6 medium 实测 | v6 medium(34.5M)：det +4.6% / rec +5.1%（vs v5_server）；识别 93.2%（GPT-5.5 仅 78.0）；一致性 75.3%（v5_mobile 57.7）；2.83x 降采样仍 81%+（v5_server 67.3%）；工业/点阵/数码屏字符增强；A100 全管线 0.13s |
| 批量高吞吐解析 | 无 | HPD-Parsing（2026-07-22 上线） | 4,752 tokens/s 峰值，层级并行解码，vLLM OpenAI 兼容 API（服务化） |
| 文档解析备选 | - | PP-StructureV3 | 默认中英识别，纯俄语/乌克兰语需在配置中换 ru 识别模型 |

### 关键判断

- **PP-OCRv6 不含西里尔**：官方 50 语言 = 中英日 + 46 拉丁语系，俄语不在内 → 图纸 OCR 仍以 v5 ru/uk 为主力；
  v6 对俄语图纸是否可用须用真实图纸样本实测后再决定切换，不得直接换。
- **v6 低分辨率鲁棒性是图纸场景最大卖点**：2.83x 降采样 81%+ vs v5_server 67.3%，低清扫描件是质的提升，值得实测。
- **16GB 显存解锁**：server 档模型常驻、VLM 全分辨率直跑（6GB 下被迫降采样）、2-3 个 OCR 进程并行、HPD 服务化常驻。
- **迁移成本极低**：paddleocr 3.7.0 同版本（本机已装），只改模型名；输出格式（置信度+bbox / markdown）不变，下游脚本零改动。

### 部署步骤

1. 新机装 paddlepaddle-gpu + paddleocr 3.7.0（同 `.venv-paddleocr` 结构，缓存仍走 `C:\Users\Public\paddlex_cache`），
   模型按上表升级目标切换即可，输出格式不变、下游脚本零改动。

## 版本记录

- v2.3.0 → v2.4.0：移除 Google Cloud Vision API，恢复本地免费引擎链
- v2.7.x → v2.8.0：新增 PaddleOCR-VL（整页文档结构化解析）
- v2.8.x → v2.9.0：新增 PP-OCRv5（工程图纸线级 OCR）
- v2.9.0 → v2.10.0：新增「新机器部署计划」（PP-OCRv6 / PaddleOCR-VL-1.6 / HPD-Parsing 升级矩阵，待 16GB 显存整机到手执行）

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

1. **中文用户名路径**：paddle C++ 推理层打不开 `C:\Users\周家同\.paddlex`。
   解决：`PADDLE_PDX_CACHE_HOME` 重定向到无中文路径（脚本已内置）。
2. **模型下载源**：国内用 `PADDLE_PDX_MODEL_SOURCE=modelscope`（阿里 CDN 最稳），
   HF 兜底 `PADDLE_PDX_HUGGING_FACE_ENDPOINT=https://hf-mirror.com`。
3. **GPU 驱动**：CUDA ≥ 11.8 对应驱动 ≥ 520。老驱动不可用，需升级（Studio 驱动即可）。
4. **结果结构**：PaddleOCR-VL 全文在 `res.markdown['markdown_texts']`；
   PP-OCRv5 行文本在 `res.json['res']['rec_texts']`（+ rec_scores + rec_polys）。
5. **旋转文字**：图纸上旋转/镜像标注 OCR 会出乱码，两引擎都不自动转正。
   用 `use_textline_orientation` 或按 skill 的标题栏裁剪放大法处理。

## 版本记录

- v2.3.0 → v2.4.0：移除 Google Cloud Vision API，恢复本地免费引擎链
- v2.7.x → v2.8.0：新增 PaddleOCR-VL（整页文档结构化解析）
- v2.8.x → v2.9.0：新增 PP-OCRv5（工程图纸线级 OCR）

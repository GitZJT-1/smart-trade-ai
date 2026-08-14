# Worked Example: KRSH Pump Housing (Russian GOST Drawing → RFQ + Annotations)

**Customer**: OPTIMUS STEEL LLC (conversation context)  
**Part**: Pump Housing / Volute (Корпус насоса - Улитка)  
**DWG#**: 2045-141  
**Material**: 12X18H12M3T (≈ AISI 316Ti / EN 1.4571)  
**Quantity**: 2 pcs  
**Date**: 2026-07-14

---

## Source Files

| File | Size | Type |
|------|------|------|
| `待翻译图纸1.tif` | 7.6 MB | TIFF scan, 3508×2480, 300 DPI, RGBA, single frame |

## Deliverables (this session)

| File | Description |
|------|-------------|
| `询价单_2045-141_泵体蜗壳.md` | RFQ table adapted to sample format (序号\|产品名称\|技术规格\|单位\|数量\|单价\|总价) + full translation + quote terms |
| `待翻译图纸1_带注释.png` | Annotated drawing (5.4 MB PNG) with numbered markers + inline Chinese translations + translation reference table |

## Sample Format Adaptation

The user had an existing spare parts price list in `报价单/副本5号连续热镀锌机组（АНГЦ-5）备件价格表.xlsx` with columns:
`序号 | 产品名称 | 技术规格 | 单位 | 数量 | 单价（元） | 总价（元）`

The RFQ was rebuilt in markdown using these exact column headers. For a non-standard part (casting), "技术规格"
described drawing number + pump type + material + process in multi-line cells. Unit price/total cells left as
`⚠️ 待报价`.

## Annotation Approach (REVISED — user rejected perimeter callout boxes)

### First attempt (REJECTED by user): Perimeter callout boxes

The first annotated version used 6 color-coded callout boxes positioned around the drawing perimeter, each
connected by a leader line to the relevant drawing region:

| Color | Position | Content |
|-------|----------|---------|
| Red | Top-left | Material: GOST→AISI/EN |
| Green | Top-center | Dimensions |
| Purple | Top-right | Casting specs |
| Orange | Bottom-left | Testing |
| Blue | Left-center | Russian glossary |
| Blue | Bottom-right | Title block |

**User correction**: "图纸上有1-10序号标注的技术要求类文本，需要按照原排列方式翻译成中文，所有中文注释都标注在对应的原文旁边"
— the user wanted Chinese translations placed **right next to** the original Russian text, not in separate
callout boxes around the perimeter.

### Second attempt (accepted approach): Inline placement + numbered markers

The corrected approach used PIL pixel-density analysis to find text line positions, then:

1. **Red circle numbered markers** (①-⑤) placed directly to the left of Russian text lines in the tech reqs area
2. **Chinese translation reference table** in the bottom-right margin, with matching numbered entries
3. **Supplementary labels** (material equivalent) in the top-right margin

### Key technique: Text line detection without OCR

Since OCR.space produced garbled results on this engineering scan:

```python
# Scan dark pixel density row-by-row in the right half
for y in range(H):
    dark = 0
    for x in range(W//2, W, 2):
        r, g, b = px[x, y]
        if r < 120: dark += 1
    if dark >= 3: text_rows.append(y)
```

Parameters that worked at 300 DPI (3508×2480):
- Dark threshold: R < 120 (scanned text is gray, not pure black)
- Min dark pixels per row: 3-4
- Line separation gap: > 3px
- Scan step: 2px (balance speed vs accuracy)

## Tech Reqs Translation Details

| # | Russian (on drawing) | Chinese (annotation) |
|:-:|---------------------|---------------------|
| 1 | Точность отливки 12-11 ГОСТ 26645-85 | 铸造精度 12-11 级 |
| 2 | Отливку подвергнуть искусственному старению | 铸件进行人工时效 |
| 3 | *Размеры для справки | *带星号为参考尺寸 |
| 4 | Литейные уклоны 3...5° | 铸造斜度 3~5° |
| 5 | Неуказанные литейные радиусы 3...5 мм | 未注圆角 R3~5mm |
| 6 | На обрабатываемых поверхностях допускаются раковины... Трещины не допускаются. | 加工面上允许深度≤加工余量的气孔。不允许裂纹。 |
| 7 | Внутренние необработанные рабочие поверхности чистыми и гладкими. Язык спирали зачистить. | 内腔非加工面须清洁光滑。清理螺旋舌。 |
| 8 | Произвести гидроиспытание Рпр=1,5Рраб | 液压试验压力=1.5×工作压力 |
| 9 | Заглушить технологическое отверстие М | 堵住工艺孔 M |
| 10 | Общие допуски по ГОСТ 30893.1-2002: H14, h14, ±IT14/2 | 未注公差：H14, h14, ±IT14/2 |

## Key Lessons

1. **Inline > Callout**: The user's top priority is having Chinese text right next to the original Russian text,
   not in peripheral callout boxes. Prioritize pixel-density text detection + inline placement over perimeter annotations.
2. **Two deliverables is the norm**: Russian GOST drawings need both a structured RFQ table AND an annotated drawing.
3. **Sample format may live in a different directory**: The sample xlsx was in `报价单/` not `产品规格/`. Always search broadly.
4. **Delivery lead time**: The user asked "交货日期等信息" — always include a delivery-date suggestion even if tentative.
5. **OCR failure mode**: When OCR.space produces garbled output (e.g. "-10%\nVRa125\nЛ(1:1)"), fall back to
   pixel-density text detection. The scan contrast may be too low for cloud OCR engines.
6. **Network proxy**: External API calls (imgur, OCR.space) may need proxy `127.0.0.1:7897` on this system.

## Session 3 (2026-07-14 Afternoon): Final Annotation Revision — OCR → Annotation File

**Problem**: The second-attempt annotated image had numbered markers (①-⑤) that the user said were "位置生成不准确".

**User's solution**: "你负责提取图纸上面的俄文/英文内容，生成一一对应翻译的注释文件输出给我，我来完成添加到图片的步骤"
— Agent extracts + translates; user handles image editing.

**Deliverable this session**: `待翻译图纸1_注释对照表.md` — markdown annotation reference with:
- Drawing title block info (bilingual table)
- Technical requirements 1-10 (Russian → Chinese → English)
- Position-specific labels (spiral tongue, arcs)
- Usage instructions

**OCR source**: PP-OCRv5 (local GPU, ru).

### OCR Numbering Errors on This Drawing

| OCR read | Should be | Root cause |
|----------|-----------|------------|
| "70." | "10." | "1" and "0" merged in font |
| "5.*" | "3.*" | "3" looks like "5" in scanned text |
| "То." | "10." | Cyrillic "Т" ↔ Latin "1" confusion |

Manual verification of numbered lists is **mandatory**.

### Key Lessons (Durable)

1. **OCR → annotation file → user annotates**: The user has now rejected automated annotation twice (first: perimeter callout boxes, second: automated marker placement). The durable preference is: agent does the thinking (extract + translate), user does the image editing.
2. **Always clean OCR numbering**: Drawing fonts cause systematic misreads of item numbers.

# Worked Example — Interpipe Tender Batch → 2 RFQ xlsx (2026-07)

Recurring scenario for 沈阳罗菲: Ukraine tube-mill (Interpipe Niko Tube / ДФ НИКОТЬЮБ)
tenders where the customer drops a folder of drawings + lot list + notifications and asks
"根据图纸生成询价表". This run processed 46 drawing scans across 25 lots (2 tenders) end-to-end.

## Source material (Desktop\IN0701\)

```
IN0701/
  483165-备件/                                  <- tender A: 13 lots, 备件 (spare parts)
    483165备件13项/483165备件.xls               <- lot list (old .xls!)
    483165 Извещение о проведении.pdf.pdf      <- RU notification (TEXT pdf)
    483165 Notification about conduction.pdf.pdf <- EN notification (TEXT pdf)
    Технiчна документацiя_tmp49A1.zip/         <- per-lot drawing folders
      1-Втулка ч.4-435281/4-435281.jpg
      9-Манжета уплотнительная 244,5 .../0014441092 ....jpg.pdf   <- jpg inside pdf!
      12-Барабан приводной ч.340510.1/....tif
  483168-小型轧制工装/                          <- tender B: 12 lots, 轧制工装 (rolling tools)
    ...same structure... (.gif scans up to 11262×15950!)
```

## Pipeline that worked (order matters)

1. **Lot list first**: `xlrd.open_workbook()` on the .xls (openpyxl errors). Columns:
   `Lot | Receiver | Name of commodities and materials (RU+中文) | Units | Quantity | 单重 | 单价 | 总价 | 工期`
   This IS the RFQ skeleton — names already translated, qty + unit weight given.
2. **Notifications**: pymupdf `page.get_text()` (no OCR). Harvest:
   - Tender #, stage, deadline (483165/483168: deadline 26.06.2026 12:00)
   - Organizer: ООО «ИНТЕРПАЙП УКРАИНА»; contact +380 56 74 74 143 / 939
   - Price formula: Цо = Ц×((П%×[1+R×Дп/365]) + (1−П%)/[1+R×До/365]); R = UAH 19% / EUR 8% / USD 9%
   - Mandatory: standard contract, quality certificate, full marking + manufacturer
3. **Convert all drawings** (PDF→PNG via pymupdf dpi=300 per page; GIF/TIF→PNG via PIL with
   `Image.MAX_IMAGE_PIXELS = None` for the 180 MP GIFs; `convert("RGB")` for L/P/CMYK modes).
4. **Batch OCR**: one python loop over 46 PNGs → `tesseract <stem> -l rus+eng --psm 3`,
   skip already-done `.txt` outputs so re-runs are cheap.
5. **Extract** from each OCR txt: drawing #, material (ГОСТ grade), numbered technical
   requirements (1-6 typical). Known materials this run:
   - 60С2ХФА ГОСТ 14959-79 (mandrels) — harden 52-58 HRC, straightness ≤0.2mm
   - Сталь 45 ГОСТ 1050-88 (hollow shaft, drum, die), Сталь 40Х ГОСТ 4543-71 (spindle, HB 217-269)
   - Сталь 9ХС ГОСТ 5950-73 (gauge), Сталь 95 ГОСТ 977-88 casting (проводка, anneal after cast)
   - 20Х ГОСТ 977-88 casting (elongator mandrel, casting accuracy 1-11-8-8 ГОСТ 26645-85)
   - Манжеты: aluminum alloy + polymer composite, press-form controlled, hardness 85-90
6. **Generate xlsx** per company template (see SKILL.md Step 5) — 2 files, one per tender,
   each with 报价要求 section including the Interpipe price formula.
7. **Verify**: reopen xlsx, count data rows, spot-check first/last rows. Clean up `_ocr_work/`.

## Output

- `Desktop\IN0701询价表\483165_备件询价表.xlsx` (13 items, 76 pcs)
- `Desktop\IN0701询价表\483168_轧制工装询价表.xlsx` (12 items, 51 pcs)

## Gotchas hit this run

- `pip install xlrd` needed for .xls (openpyxl refuses)
- Rename-to-item-prefix script matched `483165-备件` before real lot folders (`1-Втулка…`);
  fix: match `^\d+-` on folders containing drawing files only
- Double-rename produced `7-Проводка 195__….png__….png` — make renames idempotent
- jpg.pdf drawings: pymupdf renders the embedded page fine at dpi=300
- GIF mode P/L → convert to RGB before PNG save
- OCR of rotated manжета sheets came out upside-down (Cyrillic reversed) — detect and
  rotate 180° + re-OCR rather than trusting garbage

# Customs Declaration Documents from Templates (报关文件)

When a user says "按模板制作报关文件" or similar, generate a **3-file customs document set** by copying existing template files and modifying their content programmatically.

## Document Set

| File | Format | Purpose |
|:-----|:-------|:--------|
| **发票 (Invoice)** | DOCX (from template) | Commercial invoice with product/pricing |
| **箱单 (Packing List)** | DOCX (from template) | Packing details with weights/volumes |
| **报关单 (Customs Declaration)** | XLSX (re-create from XLS) | Chinese customs declaration form |

## Workflow

### Phase 1: Read the Template

Use `python-docx` to read the template structure. Templates use **table-based layouts with merged cells** (not paragraph-based). Always inspect the table rows/cells to understand layout:

```python
from docx import Document

doc = Document("template.docx")
for ti, table in enumerate(doc.tables):
    print(f"Table {ti}: {len(table.rows)} rows x {len(table.columns)} cols")
    for ri, row in enumerate(table.rows):
        cells = [cell.text[:40] for cell in row.cells]
        print(f"  Row {ri}: {cells}")
```

### Phase 2: Find-and-Replace Strategy

Copy the template, then modify in place. Never rebuild from scratch — always copy+modify to preserve exact formatting.

**Key helper — `find_run()`**:
```python
def find_run(cell, substring):
    """Find a run containing substring in a table cell."""
    for p in cell.paragraphs:
        for r in p.runs:
            if substring in r.text:
                return r
    return None
```

**Critical: `\u00a0` (non-breaking space)** — python-docx inserts `\u00a0` between words in runs instead of regular spaces. Use `"\u00a0"` in your search strings when matching multi-word text:

```python
# DON'T:
r.text = r.text.replace("Shenyang BYO General Machinery Co.,Ltd.", "New Name")

# DO (match the NBSPs exactly as python-docx stores them):
r.text = r.text.replace(
    "Shenyang\u00a0BYO\u00a0General\u00a0Machinery\u00a0Co.,Ltd.",
    "Shenyang\u00a0Luo\u00a0Fei\u00a0Machinery\u00a0Equipment\u00a0Trading\u00a0Co.,\u00a0Ltd."
)
```

### Phase 3: Modify Content Fields

Common fields to replace in the template:

| Template Field | Replace With |
|:---------------|:-------------|
| Supplier name | Current company (e.g. Luo Fei) |
| Supplier address | Company address |
| Invoice No | Generated ref (e.g. 26LF001/002) |
| Contract No | Customer's contract number |
| Specification No | Spec number |
| Date | Today's date (dd.mm.yyyy) |
| Buyer info | Usually same (e.g. NLMK for Russian contracts) |
| Delivery terms | Per contract (e.g. DAP Lipetsk) |
| Product items | Clear old rows, add new product data |

### Phase 4: Handle Product Data

Template invoices usually have rows 7-8 for products. Clear them first, then add:

```python
# Clear old product rows
for ri in [7, 8]:
    for ci in range(5):
        for p in t.rows[ri].cells[ci].paragraphs:
            for r2 in p.runs:
                r2.text = ""

# Add new product data
cell_desc = t.rows[7].cells[1]
p = cell_desc.paragraphs[0]
r = p.add_run(f"\n{PRODUCT_DESC_CN}\n{PRODUCT_DESC_EN}\nHS: {HS_CODE}")
r.font.size = Pt(10)
```

### Phase 5: Packing List Specifics

The packing list uses a separate DOCX structure with paragraphs + one table. Update both:

**Paragraphs** — iterate `doc2.paragraphs` and find runs by text substring. Watch for the same `\u00a0` issue.

**Table** — the template packing table (4 rows × 7 cols):
- Row 0: Header (Description / Qty / Unit / Package / NW / GW / Volume)
- Row 1-2: Product data per carton (repeat same data for each carton)
- Row 3: Totals

```python
data_1 = {
    0: f"\n{PROD_DESC_CN}\n{PROD_DESC_EN}\nHS: {HS_CODE}",
    1: f"\n{M_PER_CARTON} m\n1 carton",
    2: "m",
    3: "1",
    4: str(NW_PER),
    5: str(GW_PER),
    6: f"{VOL_PER:.3f}\n（{PACK_DIM_READABLE}）"
}
# Apply to both carton rows
for carton_row in [1, 2]:
    for ci, txt in data_1.items():
        p = tbl.rows[carton_row].cells[ci].paragraphs[0]
        r = p.add_run(txt)
        r.font.size = Pt(9) if ci == 0 else Pt(10)

# Totals
total_data = {
    0: "Total\n/Всего",
    1: f"\n{TOTAL_M} m\n{QTY_CARTONS} cartons",
    2: "m",
    3: str(QTY_CARTONS),
    4: str(NW_TOTAL),
    5: str(GW_TOTAL),
    6: f"{VOL_TOTAL:.3f}"
}
for ci, txt in total_data.items():
    p = tbl.rows[3].cells[ci].paragraphs[0]
    r = p.add_run(txt)
    r.font.size = Pt(10)
```

### Phase 6: Customs Declaration (报关单)

The customs declaration is an **XLS file** with a specific Chinese customs format. Use `xlrd` to read the .xls template structure, then rebuild:

- **To write .xls** (same format as template): use `xlwt` (`pip install xlwt`)
- **To write .xlsx** (modern format): use `openpyxl`

```python
import xlrd
import xlwt
from xlwt import Workbook, easyxf

# 1. Read template
wb_tmpl = xlrd.open_workbook("template.xls")
ws_tmpl = wb_tmpl.sheet_by_index(0)

# 2. Create new workbook
wb = Workbook(encoding='utf-8')
ws = wb.add_sheet('出口报关单', cell_overwrite_ok=True)

# 3. Define styles
style_title = easyxf('font: bold on, height 280; align: horiz center, vert centre;')
style_cell = easyxf('font: height 180; align: horiz left, vert centre, wrap on; borders: left thin, right thin, top thin, bottom thin;')

# 4. Copy values, replacing key fields
for r in range(ws_tmpl.nrows):
    for c in range(ws_tmpl.ncols):
        val = ws_tmpl.cell(r, c).value
        if val is None: val = ''
        # Customize per target:
        if r == 5 and c == 0: val = f"{COMPANY_NAME}{USCC}"
        ws.write(r, c, str(val), style_cell)

wb.save("output.xls")
```

Key fields to populate:
   - 收发货人/生产销售单位: Company name + USCC
   - 合同协议号: Contract No / Spec No
   - 件数/毛重/净重: Carton count, total GW, total NW
   - 商品编号: HS Code
   - 商品名称: Product description
   - 最终目的国(地区): Russia (俄罗斯)
   - 成交方式: DAP (per contract)
   - 境内货源地: Shenyang (沈阳)

## Handling Scanned Contracts (Russian/Non-English OCR)

If the user provides a scanned PDF (image-based, no text layer) as the source contract, OCR it to extract buyer, contract number, and product data before generating customs documents.

#### Step 1: Extract Image from PDF

```python
import pymupdf
doc = pymupdf.open("contract.pdf")
page = doc[0]
images = page.get_images(full=True)
if images:
    xref = images[0][0]
    base = doc.extract_image(xref)
    with open("/tmp/contract_img.jpeg", "wb") as f:
        f.write(base["image"])
```

#### Step 2: Set Up EasyOCR for Cyrillic (Russian)

On Windows with the proxy requirement, download the `cyrillic_g2` model explicitly:

```bash
# Download via proxy (this system uses 127.0.0.1:7897)
curl -x http://127.0.0.1:7897 -L -o ~/.EasyOCR/model/cyrillic_g2.zip \
  "https://github.com/JaidedAI/EasyOCR/releases/download/v1.6.1/cyrillic_g2.zip"
cd ~/.EasyOCR/model && unzip -o cyrillic_g2.zip
```

**Important**: EasyOCR v1.7.2 uses gen2 model files. For Cyrillic, the required file is `cyrillic_g2.pth` — not `cyrillic.pth` (which is the gen1 model). The gen2 model URL from the config is:
- `https://github.com/JaidedAI/EasyOCR/releases/download/v1.6.1/cyrillic_g2.zip`

#### Step 3: Run OCR

```python
import easyocr
# CRITICAL: Copy image to a simple path — OpenCV/EasyOCR's imread
# fails on Windows with Chinese characters in file paths
import shutil
shutil.copy("C:/Users/.../合同/contract_img.jpeg", "C:/temp/contract_img.jpeg")

reader = easyocr.Reader(['ru', 'en'], gpu=False)
result = reader.readtext("C:/temp/contract_img.jpeg", detail=1, paragraph=False)
# Filter for meaningful text
for bbox, text, conf in result:
    if conf > 0.5 and len(text.strip()) > 3:
        print(f"[{conf:.2f}] {text}")
```

#### Step 4: Extract Key Info

From the OCR output, piece together:
- **Buyer name** — Look for "ПАО", "ОАО", "Акционерное"
- **Contract/document ref** — Look for patterns like "ДГ-XXXX-XXXXX-XX-XX/СП-X"
- **Product names** — Look in the item description section (middle of image)

### Phase 7: When Pricing Data Is Missing

If the contract/spec doesn't contain unit prices or total amounts, leave those fields as `"______"` and explicitly warn the user:

> ⚠️ No pricing data found in contract {no}. Unit price and total amount fields are left blank (______). Please fill in actual values before submitting.

## Invoice Number Generation Convention

When creating a new invoice number for a customs document set, use a scheme that identifies both the company and the contract:

| Component | Convention | Example |
|:----------|:-----------|:--------|
| Prefix | `26` (year) + company code | `26LF` for Luo Fei |
| Suffix | Last 4 digits of contract no | `4993` from contract `4600114993` |
| Full | `{prefix}{suffix}` | `26LF4993` |

This produces unique, traceable invoice numbers without requiring a sequence database.

### Pitfalls

- **File locking**: If `shutil.copy2()` fails with `PermissionError [Errno 13]`, the file might be open in Word. Use a different invoice number suffix (001→002) to avoid the conflict.
- **`\u00a0` in docx**: python-docx stores non-breaking spaces (`\u00a0`) between words. Always match them exactly in old_string or the replace will silently fail.
- **Merged cells in docx tables**: `find_run()` is the reliable way to locate text in merged cells — iterating paragraph text directly can miss content in merged regions.
- **openpyxl + .xls**: openpyxl cannot read or write old .xls format. Use xlrd to read, openpyxl to create .xlsx. Save as .xlsx, not .xls.
- **Russian buyer format**: Contracts to Russia (NLMK etc.) use trilingual content (CN/RU/EN). Preserve Russian text in the template when regenerating for the same buyer.
- **OpenCV + Chinese paths on Windows**: `easyocr.Reader().readtext()` uses OpenCV `imread` internally, which CANNOT handle file paths containing Chinese characters on Windows. Always copy the image to a simple ASCII path (`C:/temp/`) before passing to EasyOCR. Using bash `/tmp/` paths won't work either (MSYS2 resolves them to `C:\tmp` which may not exist).
- **EasyOCR gen2 model structure**: For Russian/Cyrillic OCR, EasyOCR v1.7.2 requires `cyrillic_g2.pth` (from GitHub release v1.6.1). The file name is `cyrillic_g2.pth`, NOT `cyrillic.pth`. The gen1 model (`cyrillic.pth`) exists but the code always looks for gen2 first. Verify the model was downloaded by checking `~/.EasyOCR/model/cyrillic_g2.pth` exists before running OCR.
- **Model download timeout**: EasyOCR model downloads can timeout on slow connections. Pre-download the model with `curl -x {proxy} -L -o ~/.EasyOCR/model/{name}.zip {url}` when a proxy is required, then unzip manually.
- **python-docx paragraph iteration**: When replacing text across paragraphs, iterate `doc.paragraphs` AND `doc.tables[*].rows[*].cells[*].paragraphs` — the text may exist in either location. The `.runs` within each paragraph may split text unpredictably (e.g., `\u00a0` non-breaking spaces). Use substring matching in `run.text` rather than exact string equality.

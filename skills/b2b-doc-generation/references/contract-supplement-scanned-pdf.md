# Supplementing Scanned Contract PDFs with python-docx

When a contract is a **scanned image PDF** (no extractable text), you cannot directly edit it. Instead, create a **supplementary specification** document as a companion DOCX.

## Workflow

1. **OCR the scanned contract** to understand existing terms
   - Use tesseract (lightweight, see below) or marker-pdf (higher quality, ~5GB)
   - Extract images via pymupdf → OCR each page
   - Alternatively, use `read_file` on the PDF which auto-extracts images to `.jpeg`

2. **Analyze the extracted content** — identify the contract number, parties, existing products, terms

3. **Create a supplementary DOCX** using python-docx that references the original contract

## Tesseract OCR (Lightweight, Windows-friendly)

```python
import fitz
import subprocess

# Extract pages as images
doc = fitz.open("contract.pdf")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=300)
    pix.save(f"/tmp/page_{i}.png")

# OCR each page
for i in range(len(doc)):
    result = subprocess.run([
        "/c/Program Files/Tesseract-OCR/tesseract.exe",
        f"/tmp/page_{i}.png", "stdout",
        "-l", "chi_sim+eng"
    ], capture_output=True, text=True, timeout=120)
    print(result.stdout)
doc.close()
```

### Installing Chinese Language Data for Tesseract

```bash
# Download fast variant (2.4MB vs 16MB for full)
curl -L -x 127.0.0.1:7897 \
  -o /tmp/chi_sim.traineddata \
  "https://github.com/tesseract-ocr/tessdata_fast/raw/main/chi_sim.traineddata"

# Copy to user-writable location (avoid admin permissions)
mkdir -p ~/.tesseract/tessdata
cp /tmp/chi_sim.traineddata ~/.tesseract/tessdata/

# Set env var for each session
export TESSDATA_PREFIX="$HOME/.tesseract/tessdata"
```

## Creating the Supplementary Document

Use python-docx to create a professional companion document:

```python
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

doc = Document()

# Set default font
style = doc.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(10)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

# Title
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('SUPPLEMENTARY SPECIFICATION / 补充规格书')
run.bold = True
run.font.size = Pt(16)
run.font.color.rgb = RGBColor(0, 0, 128)

# Reference to original contract
ref = doc.add_paragraph()
ref.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = ref.add_run(f'To Contract No. {contract_no} / 合同号 {contract_no}')
run.font.size = Pt(11)

# Sections:
# 1. Parties table
# 2. Product specification table with HS code, packaging, weights
# 3. Terms (incoterms, delivery, payment)
# 4. Notes / remarks
# 5. Signature blocks

doc.save('output.docx')
```

## DOCX Structure for Contract Supplements

| Section | Content |
|---------|---------|
| 1. Parties | Supplier + Buyer names + Contract No. reference |
| 2. Product Spec | HS Code, product name, qty, packaging, dimensions, net/gross weight |
| 3. Terms | Delivery terms, payment, delivery date |
| 4. Notes | Clarifications, applicability references |
| 5. Signatures | Supplier + Buyer signature blocks |

## Cleanup

```python
import os
# Remove temp OCR images
for f in os.listdir('/tmp/'):
    if f.startswith('page_') and f.endswith('.png'):
        os.remove(f'/tmp/{f}')
```

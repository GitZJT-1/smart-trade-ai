# HTML → PPTX Conversion — Session Notes (2026-07-15)

## Source file
- `沈阳百欧通用机械有限公司_矿山行业宣传册_V4_实景配图版.html` (5.4 MB, 989 lines)
- 11 pages: Cover → P1(01/10) → P2(02/10) → ... → P9(09/10) → Back Cover

## Key challenge: page div extraction
**Problem**: `soup.find_all("div", class_=lambda c: c and ("page" in c or "cover" in c or ...))` 
returned 33 elements instead of 11 because nested divs inside each page also matched.

**Fix**: Use `body.find_all("div", recursive=False)` to restrict to top-level children only.
```python
body = soup.find("body")
pages = []
if body:
    for div in body.find_all("div", recursive=False):
        classes = div.get("class", [])
        if any(c in ["page", "cover", "inner", "back-cover"] for c in classes):
            pages.append(div)
```

## Base64 image handling
- All images in HTML are `data:image/jpeg;base64,...` format
- Must decode then pass as `io.BytesIO` to python-pptx
- Wrap each decode in try/except — some src attributes may be malformed
- SVG elements (`<svg>...</svg>`) cannot be converted — skip them entirely

## Visual elements mapping
| HTML structure | PPTX implementation |
|---------------|-------------------|
| Gradient backgrounds | Solid fill rectangle shapes |
| .gold-bar decorations | Small rectangles with gold fill |
| .data-item rows | ROUNDED_RECTANGLE shapes + two text boxes (number + label) |
| .img-grid | add_picture() in 3-column layout |
| .equip-table | Text boxes in grid + small thumbnail pictures |
| .process-step circles | OVAL shapes with centered text |
| .cert-badge images | add_picture() small icons |
| Page numbers | Small text box bottom-right |

## Result
- **Output**: 2.1 MB PPTX, 11 slides, 16:9 widescreen
- **File**: `C:\Users\周家同\Desktop\沈阳百欧通用机械有限公司_矿山行业宣传册_V4.pptx`
- **All slides editable**: text in text boxes, images as native pictures, shapes as native shapes

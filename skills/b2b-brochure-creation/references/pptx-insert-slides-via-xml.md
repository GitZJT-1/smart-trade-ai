# PPTX插入幻灯片 — XML操作完整方案

> 适用场景：在现有PPTX中从指定位置插入N页新幻灯片（如产品分类展示页）
> 
> 限制：python-pptx 不支持 `insert_slide()`，必须通过底层XML操作实现

## 架构概览

```
原PPTX.zip
  ├── [Content_Types].xml       ← 必须清理重复后重写
  ├── ppt/
  │   ├── presentation.xml      ← 控制幻灯片顺序 (sldIdLst)
  │   ├── _rels/
  │   │   └── presentation.xml.rels  ← 幻灯片→文件路径映射
  │   ├── slides/
  │   │   ├── slide1~2.xml      ← 原封面+概览（不变）
  │   │   ├── slide3~10.xml     ← 新创建的品类展示页
  │   │   ├── slide11~18.xml    ← 原slide3~10（已重命名）
  │   │   └── _rels/
  │   │       └── slideN.xml.rels  ← 每张幻灯片的Relationship
  │   └── media/                ← 图片文件
  └── docProps/
```

## 执行步骤

### 1. 提取原PPTX图片

```python
from pptx import Presentation
import os

prs = Presentation(src_path)
img_dir = r"C:\...\extracted_images"
os.makedirs(img_dir, exist_ok=True)

for i, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        if hasattr(shape, 'image'):
            img = shape.image
            ext = img.content_type.split('/')[-1].replace('jpeg', 'jpg')
            fname = f"slide{i}_{shape.name}_{idx}.{ext}"
            with open(os.path.join(img_dir, fname), 'wb') as f:
                f.write(img.blob)
```

### 2. 解压PPTX

```python
import zipfile, tempfile
tmp = tempfile.mkdtemp()
with zipfile.ZipFile(src, 'r') as z:
    z.extractall(tmp)
```

### 3. 重命名旧幻灯片（必须优先！）

```python
for old_num in range(3, 11):  # 假设要插入8张新幻灯片
    new_num = old_num + 8
    os.rename(f'slide{old_num}.xml', f'slide{new_num}.xml')
    # 同步更新页面编号文字
    content = content.replace(f'{old_num:02d} / 10', f'{new_num:02d} / 18')
```

### 4. 创建新幻灯片XML

使用旧幻灯片为模板，用 lxml 修改：

```python
from lxml import etree

# 用已重命名的旧slide11（即原slide3）为模板
with open('slide11.xml', 'r') as f:
    template = f.read()

root = etree.fromstring(template.encode())

# 替换文本
for t in root.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'):
    if t.text == '产品总览': t.text = '破碎设备'
    elif t.text == '02 / 10': t.text = '03 / 18'

# 替换图片引用
for pic_idx, pic in enumerate(root.findall('.//p:pic', ns)):
    if pic_idx < len(items):
        blip = pic.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
        if blip is not None:
            blip.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed',
                     f'rIdI{pic_idx}')
    else:
        pic.getparent().remove(pic)  # 删除多余的pic元素

# 保存
with open('slide3.xml', 'wb') as f:
    f.write(etree.tostring(root, encoding='UTF-8', xml_declaration=True))
```

### 5. 创建新幻灯片rels文件

```python
rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
rels.append('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">')

# 添加布局关系
rels.append(f'<Relationship Id="rId6" Type="...slideLayout" Target="../slideLayouts/slideLayout7.xml"/>')

# 添加图片关系（rId必须与slide XML中的一致）
for pic_idx, img_file in enumerate(image_files):
    rels.append(f'<Relationship Id="rIdI{pic_idx}" Type="...relationships/image" Target="../media/{img_file}"/>')

rels.append('</Relationships>')
```

### 6. 清理 [Content_Types].xml

```python
ct_root = etree.parse(ct_path).getroot()
for ov in list(ct_root):
    if '/ppt/slides/slide' in ov.get('PartName', ''):
        ct_root.remove(ov)
for i in range(1, total_slides + 1):
    ov = etree.SubElement(ct_root, '{ns}Override')
    ov.set('PartName', f'/ppt/slides/slide{i}.xml')
    ov.set('ContentType', 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
```

### 7. 更新 presentation.xml 顺序

```python
sldIdLst = pres_root.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst')
for s in list(sldIdLst): sldIdLst.remove(s)

# 新顺序: slide1(rId3), slide2(rId4), new3-10(rId16-rId23), old11-18(rId5-rId12)
for sid, rid in order:
    s = etree.SubElement(sldIdLst, '{...}sldId')
    s.set('id', str(sid))
    s.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', rid)
```

### 8. 更新 presentation.xml.rels

```python
# 修正重命名后的旧幻灯片Target
for rel in pres_rels_root:
    if rel.get('Target') == 'slides/slide3.xml':
        rel.set('Target', 'slides/slide11.xml')

# 为新幻灯片添加Relationship（使用rId16+避开已占用的rId13-rId15）
for i in range(8):
    nr = etree.SubElement(pres_rels_root, '{...}Relationship')
    nr.set('Id', f'rId{16 + i}')
    nr.set('Target', f'slides/slide{3 + i}.xml')
    nr.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide')
```

### 9. 重新打包

```python
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
    for root_dir, dirs, files in os.walk(tmp):
        for f in files:
            zout.write(os.path.join(root_dir, f),
                       os.path.relpath(os.path.join(root_dir, f), tmp))
```

## rId占用表

| rId范围 | 用途 | 说明 |
|:--------|:-----|:-----|
| rId1 | slideMaster | 幻灯片母版 |
| rId2 | theme | 主题 |
| rId3-rId12 | slides 1-10 | 原始幻灯片（仅rId3-rId4保留） |
| rId13 | presProps | 预设属性 |
| rId14 | viewProps | 视图属性 |
| rId15 | tableStyles | 表格样式 |
| **rId16-rId23** | **新slides 3-10** | **安全可用** |

## 常见错误与排除

| 错误 | 原因 | 修复 |
|:-----|:-----|:-----|
| `KeyError: 'rIdN'` | 图片/布局rId在rels中缺失 | 检查slideXML与rels一致性 |
| `Part object has no attribute slide` | 幻灯片XML结构不完整 或 Content_Types重复 | 清理Content_Types重新生成 |
| 图片红叉 | rels中缺少图片Relationship 或 图片路径错误 | 确认media/内有对应文件且rels路径正确 |
| PowerPoint打开显示空白幻灯片 | slideXML的spTree结构异常 | 检查模板解析是否丢失了元素 |

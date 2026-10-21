import sys, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

src = r"C:/Users/<user>\Desktop\260818-20155669炉盖组件-待报价\1 Трубчатая часть агрегата свода печь-ковш C.3540.SL.325-M1000 2027 ОЗМ 1193344\C_3540_SL_325-M1000_FPA001_S1_R00_AP_00.tif"
outdir = r"C:/Users/<user>\Desktop\260818-20155669炉盖组件-待报价\_png"
os.makedirs(outdir, exist_ok=True)
out = os.path.join(outdir, "FPA001.png")

img = Image.open(src)
print("mode:", img.mode, "size:", img.size, "frames:", getattr(img, "n_frames", 1))
if img.mode in ("CMYK", "RGBA", "P", "LA", "L"):
    img = img.convert("RGB")
img.save(out, "PNG")
print("saved:", out, os.path.getsize(out), "bytes")

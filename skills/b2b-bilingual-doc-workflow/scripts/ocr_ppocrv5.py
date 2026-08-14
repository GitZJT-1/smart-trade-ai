#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PP-OCRv5 线级 OCR（检测+识别）— 工程图纸专用，供 b2b-bilingual-doc-workflow 使用

与 PaddleOCR-VL 的区别：
  - PaddleOCR-VL = 整页 VLM 文档解析（适合文档，图纸上慢到不可用）
  - PP-OCRv5 = 线级检测+识别（找到图上每一条文字线再逐条识别，适合稀疏/旋转的图纸标注）
  - PP-OCRv5 支持西里尔 ru/uk/be；PP-OCRv6 反而砍掉了西里尔，故用 v5

用法:
  .venv-paddleocr/Scripts/python.exe scripts/ocr_ppocrv5.py <图片或目录> [--out 输出目录] [--lang ru]
"""
import os
import sys
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 中文路径 + 下载源（与 ocr_paddle_vl.py 同一套处理）
def _resolve_cache_home():
    if os.environ.get("PADDLE_PDX_CACHE_HOME"):
        return os.environ["PADDLE_PDX_CACHE_HOME"]
    default = os.path.join(os.path.expanduser("~"), ".paddlex")
    if all(ord(c) < 128 for c in default):
        return default
    for c in (r"C:\Users\Public\paddlex_cache", r"C:\paddlex_cache"):
        try:
            os.makedirs(c, exist_ok=True)
            if os.access(c, os.W_OK):
                return c
        except Exception:
            continue
    return default

os.environ.setdefault("PADDLE_PDX_CACHE_HOME", _resolve_cache_home())
os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "modelscope")
os.environ.setdefault("PADDLE_PDX_HUGGING_FACE_ENDPOINT", "https://hf-mirror.com")


def _extract_lines(res) -> list:
    """从 PP-OCR 结果对象抽取 [text, score, box] 行列表。"""
    d = None
    if isinstance(res, dict):
        d = res
    else:
        for attr in ("json", "str", "_json"):
            v = getattr(res, attr, None)
            if isinstance(v, dict):
                d = v
                break
    if d is None:
        return []
    inner = d.get("res") if isinstance(d.get("res"), dict) else d
    texts = inner.get("rec_texts") or []
    scores = inner.get("rec_scores") or []
    boxes = inner.get("rec_polys") or inner.get("dt_polys") or []
    lines = []
    for i, t in enumerate(texts):
        if not t or not str(t).strip():
            continue
        sc = scores[i] if i < len(scores) else None
        bx = boxes[i] if i < len(boxes) else None
        lines.append((str(t).strip(), sc, bx))
    return lines


def run(input_path, out_dir, lang, device):
    from paddleocr import PaddleOCR

    inp = Path(input_path)
    if not inp.exists():
        sys.exit(f"[错误] 输入不存在: {input_path}")
    if inp.is_dir():
        imgs = sorted([p for p in inp.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")])
    else:
        imgs = [inp]

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[PP-OCRv5] 初始化 (ocr_version=PP-OCRv5, lang={lang}, device={device}) ...")
    ocr = PaddleOCR(ocr_version="PP-OCRv5", lang=lang, device=device, use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)

    all_text = []
    for img in imgs:
        print(f"[PP-OCRv5] 处理: {img.name}")
        result = ocr.predict(input=str(img))
        for res in result:
            lines = _extract_lines(res)
            all_text.append(f"\n===== {img.name}（{len(lines)} 行）=====")
            for text, sc, bx in lines:
                score = f"  [{sc:.2f}]" if isinstance(sc, (int, float)) else ""
                all_text.append(f"{text}{score}")
                print(f"  {text}{score}")

    full = "\n".join(all_text)
    out_file = out / "ocr_full.txt"
    out_file.write_text(full, encoding="utf-8")
    print(f"\n[PP-OCRv5] 完成，全文已写: {out_file}")


def main():
    ap = argparse.ArgumentParser(description="PP-OCRv5 线级 OCR（工程图纸）")
    ap.add_argument("input", help="图片路径或含图片的目录")
    ap.add_argument("--out", default="./ppocr_out", help="输出目录")
    ap.add_argument("--lang", default="ru", help="语言：ru/uk/be 等（PP-OCRv5 支持 109 语含西里尔）")
    ap.add_argument("--device", default="gpu:0", help="推理设备")
    args = ap.parse_args()
    run(args.input, args.out, args.lang, args.device)


if __name__ == "__main__":
    main()

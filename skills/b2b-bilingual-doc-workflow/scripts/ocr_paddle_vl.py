#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PaddleOCR-VL 本地文档解析 — 供 b2b-bilingual-doc-workflow 使用

本地 VLM 文档解析引擎：
  - 0.9B 文档解析 VLM，支持 109 种语言（含西里尔字母：俄语/乌克兰语）
  - 版面分析(PP-DocLayoutV2) + VLM 识别(PaddleOCR-VL-0.9B) 两段式
  - 输出结构化 Markdown/JSON/DOCX，自动保留表格、标题层级、阅读顺序
  - Apache 2.0 + 纯本地推理，符合"禁止外部付费视觉 API"铁律

用法:
  .venv-paddleocr/Scripts/python.exe scripts/ocr_paddle_vl.py <图片或PDF> [--out 输出目录] [--device cpu] [--pipeline-version v1.6]

首次运行自动下载模型（~2-3GB，缓存在 ~/.paddlex/official_models/）。

输出（落在 --out 目录）:
  <stem>/<page>_paddleocr.md    每页 Markdown（结构化，含表格/标题/阅读顺序）
  <stem>/<page>_paddleocr.json  每页结构化 JSON
  ocr_full.txt                  全文拼接（兼容 ocr_pdf.py 的 ocr_full.txt，供字段提取/人工核对）
"""
import os
import sys
import argparse
from pathlib import Path

# 俄语/中文打印安全：Windows 终端默认 GBK，强制 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _resolve_cache_home() -> str:
    """模型缓存目录解析（必须在 import paddleocr/paddlex 之前调用）。

    paddle 的 C++ 推理层用窄字符 API，打不开含中文的路径（如 C:\\Users\\周家同\\.paddlex），
    表现为 RuntimeError: Cannot open file .../inference.json（文件明明存在）。
    中文用户名下必须把 PADDLE_PDX_CACHE_HOME 重定向到无中文的可写目录。
    """
    if os.environ.get("PADDLE_PDX_CACHE_HOME"):
        return os.environ["PADDLE_PDX_CACHE_HOME"]
    default = os.path.join(os.path.expanduser("~"), ".paddlex")
    if all(ord(c) < 128 for c in default):  # 全 ASCII 路径，直接用默认
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
# 模型下载源：国内优先 ModelScope（阿里 CDN，大文件稳）；可选 huggingface / modelscope / bos
os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "modelscope")
# HF 兜底时走国内镜像，避免 huggingface.co 直连慢/断
os.environ.setdefault("PADDLE_PDX_HUGGING_FACE_ENDPOINT", "https://hf-mirror.com")


def _extract_text(res) -> str:
    """从结果对象抽取全文（优先结构化 markdown，兜底 parsing_res_list）。

    PaddleOCRVLResult 的结构（实测）：
      res.markdown = {'markdown_texts': '# 标题\\n\\n正文...'}   ← 结构化全文（含表格/标题/阅读顺序）
      res.json    = {'res': {'parsing_res_list': [block...]}}   ← 结构化原始结果
    直接取 markdown_texts 即得完整文本。
    """
    # 首选：res.markdown['markdown_texts']（结构化 markdown 全文）
    md = getattr(res, "markdown", None)
    if isinstance(md, dict):
        texts = md.get("markdown_texts")
        if isinstance(texts, str):
            return texts
        if isinstance(texts, (list, tuple)):
            return "\n".join(str(t) for t in texts)

    # 兜底：json['res']['parsing_res_list'] 按 block_order 拼接
    d = None
    if isinstance(res, dict):
        d = res
    else:
        for attr in ("json", "str", "_json"):
            v = getattr(res, attr, None)
            if isinstance(v, dict):
                d = v
                break
    if isinstance(d, dict):
        # res.json 是 {'res': {...}} 包装结构
        inner = d.get("res") if isinstance(d.get("res"), dict) else d
        blocks = inner.get("parsing_res_list") or []

        def _bfield(b, key, default=None):
            return b.get(key, default) if isinstance(b, dict) else getattr(b, key, default)

        ordered = sorted(blocks, key=lambda b: (_bfield(b, "group_id", 0) or 0, _bfield(b, "block_order", 0) or 0))
        lines = [str(_bfield(b, "block_content", "") or "").strip() for b in ordered]
        lines = [ln for ln in lines if ln]
        if lines:
            return "\n".join(lines)
    return ""


def run(input_path: str, out_dir: str, device: str, pipeline_version: str) -> None:
    from paddleocr import PaddleOCRVL

    inp = Path(input_path)
    if not inp.exists():
        sys.exit(f"[错误] 输入不存在: {input_path}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = inp.stem

    print(f"[PaddleOCR-VL] 初始化 pipeline (device={device}, pipeline_version={pipeline_version}) ...")
    pipeline = PaddleOCRVL(device=device, pipeline_version=pipeline_version)
    print(f"[PaddleOCR-VL] 开始解析: {inp}")

    output = pipeline.predict(input=str(inp))
    pages = list(output)
    print(f"[PaddleOCR-VL] 解析完成，共 {len(pages)} 页/文件")

    # 逐页落盘 markdown + json（保留结构化，含表格/标题/阅读顺序）
    page_dir = out / f"{stem}_pages"
    page_dir.mkdir(parents=True, exist_ok=True)
    full_text_parts = []
    for i, res in enumerate(pages, 1):
        try:
            res.save_to_markdown(save_path=str(page_dir))
            res.save_to_json(save_path=str(page_dir))
        except Exception as e:
            print(f"  [警告] 第 {i} 页落盘失败: {e}")
        txt = _extract_text(res)
        full_text_parts.append(f"\n===== 第 {i} 页 =====\n{txt.strip()}")

    # 全文拼接（兼容 ocr_pdf.py 的 ocr_full.txt，供字段提取）
    full_text = "\n".join(p for p in full_text_parts if p.strip())
    full_out = out / "ocr_full.txt"
    full_out.write_text(full_text, encoding="utf-8")
    print(f"[PaddleOCR-VL] 全文已写: {full_out}")

    # PDF 多页：尝试跨页表格合并 + 标题层级重建 + 多页合并（可选增强）
    if len(pages) > 1:
        try:
            merged = list(pipeline.restructure_pages(
                pages, merge_tables=True, relevel_titles=True, concatenate_pages=True
            ))
            if merged:
                merged_dir = out / f"{stem}_merged"
                merged_dir.mkdir(parents=True, exist_ok=True)
                for j, res in enumerate(merged, 1):
                    res.save_to_markdown(save_path=str(merged_dir))
                merged_txt = "\n".join(_extract_text(r) for r in merged)
                (out / "ocr_merged.txt").write_text(merged_txt, encoding="utf-8")
                print(f"[PaddleOCR-VL] 跨页合并结果已写: {merged_dir} + ocr_merged.txt")
        except Exception as e:
            print(f"  [提示] restructure_pages 不可用（无碍主流程）: {e}")

    print(f"[PaddleOCR-VL] 完成。逐页结果目录: {page_dir}")


def main():
    ap = argparse.ArgumentParser(description="PaddleOCR-VL 本地文档解析（俄/英双语外贸文档）")
    ap.add_argument("input", help="图片或 PDF 路径（或含图片的目录）")
    ap.add_argument("--out", default="./paddleocr_out", help="输出目录")
    ap.add_argument("--device", default="gpu:0", help="推理设备，默认 gpu:0（GPU 不可用会直接报错，不会静默回退到慢 CPU）")
    ap.add_argument("--pipeline-version", default="v1.6", help="PaddleOCR-VL 版本：v1 / v1.5 / v1.6")
    args = ap.parse_args()
    run(args.input, args.out, args.device, args.pipeline_version)


if __name__ == "__main__":
    main()

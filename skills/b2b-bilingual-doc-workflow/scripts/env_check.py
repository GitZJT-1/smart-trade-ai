#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
env_check.py — 环境自检（幂等检查）：venv 依赖 / PaddleOCR GPU 引擎 / OCR.space 兜底

用法: .venv-skill/Scripts/python.exe scripts/env_check.py
退出码: 0=全就绪, 1=有缺失（输出缺失项清单）
"""
import importlib
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPOCR_PY = os.path.join(SKILL_DIR, ".venv-paddleocr", "Scripts", "python.exe")

REQUIRED_LIBS = ["xlrd", "docx", "fitz", "xlwt", "xlutils", "pandas"]

# 可选但强烈推荐的增强依赖
OPTIONAL_LIBS = {
    "rapidocr_onnxruntime": "rapidocr_onnxruntime（离线 OCR 兜底引擎）",
    "PIL": "pillow（TIF→PNG 转换）",
}


def check_paddleocr():
    """探测 .venv-paddleocr：paddle / paddleocr / GPU 是否就绪。返回 (ok, notes)"""
    if not os.path.exists(PPOCR_PY):
        return False, ["[X] .venv-paddleocr 不存在（PaddleOCR-VL / PP-OCRv5 引擎未部署）"]
    code = (
        "import paddle, paddleocr;"
        "print('paddle', paddle.__version__, '| paddleocr', paddleocr.__version__);"
        "print('cuda', paddle.is_compiled_with_cuda(), '| gpu', paddle.device.cuda.device_count())"
    )
    try:
        r = subprocess.run([PPOCR_PY, "-c", code], capture_output=True, timeout=120)
        out = r.stdout.decode("utf-8", errors="replace").strip()
        if r.returncode == 0:
            return True, ["  [OK] " + out]
        return False, ["[X] .venv-paddleocr 导入失败: " + r.stderr.decode("utf-8", errors="replace")[-300:]]
    except Exception as e:
        return False, [f"[X] 探测 .venv-paddleocr 异常: {e}"]


def main():
    problems = []
    print("== 1/3 venv 依赖 ==")
    for lib in REQUIRED_LIBS:
        try:
            importlib.import_module(lib)
            print(f"  [OK] {lib}")
        except ImportError:
            problems.append(f"缺少库 {lib}（uv pip install 装）")
            print(f"  [X] {lib} 缺失")

    for mod, desc in OPTIONAL_LIBS.items():
        try:
            importlib.import_module(mod)
            print(f"  [+] {desc}")
        except ImportError:
            print(f"  [-] {desc}（可选增强，缺失不影响基本功能）")

    print("== 2/3 PaddleOCR GPU 引擎（PaddleOCR-VL / PP-OCRv5）==")
    ok, notes = check_paddleocr()
    for n in notes:
        print(n)
    if not ok:
        problems.append("PaddleOCR GPU 引擎不可用（需 .venv-paddleocr + paddlepaddle-gpu + NVIDIA GPU 驱动≥520）")

    print("== 3/3 OCR.space（在线免费兜底引擎）==")
    try:
        import urllib.request
        urllib.request.Request("https://api.ocr.space/parse/image")
        print("  [OK] OCR.space — API 端点可达")
    except Exception:
        print("  [-] OCR.space — API 端点不可达（可选兜底引擎）")

    print()
    if problems:
        print("== 缺失项 ==")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("环境就绪 ✅")


if __name__ == "__main__":
    main()

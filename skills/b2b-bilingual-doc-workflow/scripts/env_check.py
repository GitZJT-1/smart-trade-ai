#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
env_check.py — 环境自检（幂等检查）：venv 依赖 / Tesseract / 语言包 / GOOGLE_API_KEY

用法: .venv-skill/Scripts/python.exe scripts/env_check.py
退出码: 0=全就绪, 1=有缺失（输出缺失项清单）
"""
import importlib
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Program Files\Tesseract-OCR\tessdata"
ENV_FILE = os.path.expanduser(r"~\AppData\Local\hermes\.env")

REQUIRED_LIBS = ["xlrd", "docx", "fitz", "xlwt", "xlutils", "pandas"]
REQUIRED_LANGS = ["rus", "eng"]
OPTIONAL_LANGS = ["ukr"]

def main():
    problems = []
    print("== 1/4 venv 依赖 ==")
    for lib in REQUIRED_LIBS:
        try:
            importlib.import_module(lib)
            print(f"  [OK] {lib}")
        except ImportError:
            problems.append(f"缺少库 {lib}（uv pip install 装）")
            print(f"  [X] {lib} 缺失")
    if "pandas" not in [l for l in [] ] and False:
        pass

    print("== 2/4 Tesseract ==")
    if os.path.exists(TESSERACT):
        print(f"  [OK] tesseract: {TESSERACT}")
    else:
        problems.append(f"tesseract 不存在: {TESSERACT}")
        print(f"  [X] tesseract 不存在")

    print("== 3/4 语言包 ==")
    have = set()
    if os.path.isdir(TESSDATA):
        have = {f[:-len(".traineddata")] for f in os.listdir(TESSDATA)
                if f.endswith(".traineddata")}
    for lang in REQUIRED_LANGS:
        if lang in have:
            print(f"  [OK] {lang}.traineddata")
        else:
            problems.append(f"语言包缺失: {lang}.traineddata（OCR 将降级，俄语变拉丁转写）")
            print(f"  [X] {lang}.traineddata 缺失")
    for lang in OPTIONAL_LANGS:
        print(f"  [{'OK' if lang in have else '-'}] {lang}.traineddata{'（可选，缺失降级 rus+eng）' if lang not in have else ''}")

    print("== 4/4 GOOGLE_API_KEY（vision 交叉校验可选）==")
    key = None
    if os.path.exists(ENV_FILE):
        for line in open(ENV_FILE, encoding="utf-8", errors="replace"):
            if line.strip().startswith("GOOGLE_API_KEY="):
                key = line.strip().split("=", 1)[1].strip('"').strip("'")
    if key:
        print(f"  [OK] GOOGLE_API_KEY 已配置（前缀 {key[:6]}...，配额状态需实测）")
    else:
        problems.append("GOOGLE_API_KEY 未配置（vision 交叉校验不可用，走人工核对）")
        print("  [X] GOOGLE_API_KEY 未配置")

    print()
    if problems:
        print("== 缺失项 ==")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("环境就绪 ✅")


if __name__ == "__main__":
    main()

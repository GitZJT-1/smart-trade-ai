#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
env_check.py — 环境自检（幂等检查）：venv 依赖 / Tesseract / 语言包 / OCR 引擎认证

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

# 可选但强烈推荐的 OCR 增强依赖
OPTIONAL_LIBS = {
    "google.cloud.vision": "google-cloud-vision（Google Cloud Vision OCR，俄语准确度远超 Tesseract）",
    "rapidocr_onnxruntime": "rapidocr_onnxruntime（离线 OCR 兜底引擎）",
    "PIL": "pillow（TIF→PNG 转换）",
}

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

    # 可选增强库
    for mod, desc in OPTIONAL_LIBS.items():
        try:
            importlib.import_module(mod)
            print(f"  [+] {desc}")
        except ImportError:
            print(f"  [-] {desc}（可选增强，缺失不影响基本功能）")

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

    print("== 4/4 OCR 引擎认证（Google Cloud Vision + OCR.space）==")

    # ── Google Cloud Vision ──
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds and os.path.isfile(creds):
        print(f"  [OK] Google Cloud Vision — 服务账号: {creds}")
        gcv_status = "service_account"
    else:
        key = None
        if os.path.exists(ENV_FILE):
            try:
                for line in open(ENV_FILE, encoding="utf-8", errors="replace"):
                    if line.strip().startswith("GOOGLE_API_KEY="):
                        key = line.strip().split("=", 1)[1].strip('"').strip("'")
                        break
            except OSError:
                pass
        if key:
            print(f"  [OK] Google Cloud Vision — API Key: {key[:6]}...（功能受限，建议用服务账号）")
            gcv_status = "api_key"
        else:
            print("  [-] Google Cloud Vision — 未配置认证（可选增强，缺失不影响基本功能）")
            print(f"     配置方式: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
            print(f"     或 在 {ENV_FILE} 设置 GOOGLE_API_KEY=...")
            gcv_status = None

    # Google Cloud Vision 包检测
    try:
        import google.cloud.vision
        print(f"  [OK] google-cloud-vision 包已安装")
    except ImportError:
        if gcv_status:
            problems.append("google-cloud-vision 包未安装但认证已配置（uv pip install google-cloud-vision）")
            print(f"  [X] google-cloud-vision 包未安装")
        else:
            print(f"  [-] google-cloud-vision 包未安装（可选）")

    # ── OCR.space ──
    try:
        import urllib.request
        req = urllib.request.Request("https://api.ocr.space/parse/image")
        print(f"  [OK] OCR.space — API 端点可达")
    except Exception:
        print(f"  [-] OCR.space — API 端点不可达（可选兜底引擎）")

    print()
    if problems:
        print("== 缺失项 ==")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("环境就绪 ✅")


if __name__ == "__main__":
    main()

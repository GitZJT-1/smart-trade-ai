# -*- coding: utf-8 -*-
"""冒烟测试：真实创建/解压/删除小 7z 包，验证 scripts/ 三个批处理脚本核心逻辑。
运行: python -m pytest tests/test_extract_7z_scripts.py -v
"""
import os
import subprocess
import sys

import pytest

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)

import extract_7z
import extract_nested_7z
import retry_delete_7z

SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"


def make_7z(archive, files):
    """用 7z CLI 将 files 打包为 archive（solid 压缩，模拟真实数据）。"""
    r = subprocess.run([SEVENZIP, "a", "-y", archive] + files, capture_output=True, timeout=120)
    assert r.returncode == 0, r.stdout.decode(errors="replace")


def test_find_7z_and_extract_flat(tmp_path):
    """扁平包：find_7z 识别待解压 -> extract_one 解压 -> 原包删除"""
    sub = tmp_path / "sub"
    sub.mkdir()
    data = tmp_path / "data.txt"
    data.write_text("hello world", encoding="utf-8")
    arc = sub / "sample.7z"
    make_7z(str(arc), [str(data)])

    todo, done = extract_7z.find_7z([str(tmp_path)])
    assert len(todo) == 1 and not done
    assert todo[0] == str(arc)

    rc, _ = extract_7z.extract_one(todo[0])
    assert rc in (0, 1)
    assert (sub / "data.txt").exists()

    os.remove(arc)  # 模拟批处理成功后的删除
    todo, done = extract_7z.find_7z([str(tmp_path)])
    assert not todo  # 无残留


def test_find_7z_skips_extracted(tmp_path):
    """同名目录已存在且有内容 -> 判定已解压（跳过），不进入待解压列表"""
    sub = tmp_path / "already"
    sub.mkdir()
    (sub / "file.pdf").write_bytes(b"%PDF-dummy")
    arc = tmp_path / "already.7z"
    data = tmp_path / "x.txt"
    data.write_text("x")
    make_7z(str(arc), [str(data)])
    # 同名目录已存在（内容为 file.pdf，非解压产物，但逻辑上视为已解压）
    todo, done = extract_7z.find_7z([str(tmp_path)])
    assert todo == [] and done == [str(arc)]


def test_nested_extract_iterates(tmp_path):
    """嵌套包：outer.7z 内含 inner.7z，迭代解压直到无残留"""
    a = tmp_path / "a"
    b = a / "b"
    b.mkdir(parents=True)
    data = tmp_path / "inner.txt"
    data.write_text("nested payload", encoding="utf-8")
    inner = b / "inner.7z"
    make_7z(str(inner), [str(data)])
    outer = a / "outer.7z"
    make_7z(str(outer), [str(inner)])

    # 模拟 main 迭代逻辑：每轮解压全部并删除，直到无残留
    rounds = 0
    while True:
        todo = extract_nested_7z.scan([str(tmp_path)])
        if not todo:
            break
        for p in todo:
            rc = extract_nested_7z.extract_one(p)
            assert rc in (0, 1)
            os.remove(p)
        rounds += 1
        assert rounds < 10, "疑似无限嵌套"

    # 无残留，内容全部就位（inner.txt 随 inner.7z 解压落地）
    assert extract_nested_7z.scan([str(tmp_path)]) == []
    assert (b / "inner.txt").exists()


def test_retry_delete_locked_file(tmp_path):
    """文件被占用时删除失败，释放后可删除（重试逻辑核心）"""
    arc = tmp_path / "locked.7z"
    arc.write_bytes(b"dummy-7z-content")
    fail_file = tmp_path / "failed.txt"
    fail_file.write_text(str(arc) + "\t解压成功但删除失败: test\n", encoding="utf-8")

    paths = retry_delete_7z.load_paths(str(fail_file))
    assert paths == [str(arc)]

    # 占用句柄 -> 删除失败
    fh = open(arc, "rb")
    try:
        with pytest.raises(OSError):
            os.remove(arc)
    finally:
        fh.close()

    # 释放后删除成功
    os.remove(arc)
    assert not arc.exists()

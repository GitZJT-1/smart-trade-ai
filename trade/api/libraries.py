"""
Trade AI Assistant — 文档库管理 API 路由。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from trade import library as library_module
from trade.api.deps import require_company
from trade.api.models import LibraryCreate, LibraryUpdate

router = APIRouter(tags=["libraries"])


@router.post("/upload-files")
async def upload_to_work_dir(
    subdir: str = Form(),
    files: list[UploadFile] = File(),  # noqa: B008
    x_company_id: int = Depends(require_company),
):
    """上传文件到公司桌面工作目录的指定子目录。

    拖入文件/目录后，用户选择一个子目录（如「合同」），
    文件写入该子目录下，保留浏览器传来的相对路径结构。
    """
    # 1. 校验子目录名（与 company.py _WORK_DIR_CATEGORIES 同步）
    from trade.company import _WORK_DIR_CATEGORIES
    _valid_subdirs = frozenset(name for name, _ in _WORK_DIR_CATEGORIES)
    if subdir not in _valid_subdirs:
        raise HTTPException(status_code=400, detail=f"无效的子目录: {subdir}")

    # 2. 获取公司桌面工作目录
    from trade import company as _co
    co = _co.get(x_company_id)
    if not co:
        raise HTTPException(status_code=404, detail="公司不存在")

    from trade.company import _setup_work_directory
    work_dir, _ = _setup_work_directory(co["name"], co["slug"])
    target_dir = work_dir / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    # 3. 路径穿越检测
    _path_traversal_pattern = re.compile(r"\.\.|^[/\\]|[<>:\"|?*]")

    uploaded = []
    for f in files:
        rel = getattr(f, "filename", "") or ""
        if not rel:
            rel = os.path.basename(f.filename or "untitled")

        parts = Path(rel).parts
        safe_parts = []
        for p in parts:
            if _path_traversal_pattern.search(p):
                cleaned = p.replace("..", "_")
                cleaned = re.sub(r"[<>:\"|?*]", "_", cleaned)
                safe_parts.append("_sanitized_" + cleaned)
            else:
                safe_parts.append(p)
        safe_parts = [p for p in safe_parts if p and p != "."]
        if not safe_parts:
            safe_parts = ["untitled"]

        dest = target_dir.joinpath(*safe_parts)
        try:
            dest.resolve().relative_to(work_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"路径穿越拒绝: {rel}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        content = await f.read()
        dest.write_bytes(content)
        uploaded.append(str(dest.relative_to(work_dir)))

    return {
        "uploaded": len(uploaded),
        "files": uploaded,
        "target_path": str(target_dir),
    }


@router.get("/libraries")
def list_libraries(
    x_company_id: int = Depends(require_company),
):
    """列出当前公司的所有文档库。"""
    return library_module.list_by_company(x_company_id)


@router.post("/libraries")
def create_library(
    payload: LibraryCreate,
    x_company_id: int = Depends(require_company),
):
    """创建文档库（关联到当前公司下的本地目录）。"""
    return library_module.create(
        payload.name, payload.root_path, payload.description,
        company_id=x_company_id,
    )


@router.get("/libraries/{library_id}")
def get_library(
    library_id: int,
    x_company_id: int = Depends(require_company),
):
    """获取单个文档库详情。"""
    lib = library_module.get(library_id, company_id=x_company_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    return lib


@router.put("/libraries/{library_id}")
def update_library(
    library_id: int,
    payload: LibraryUpdate,
    x_company_id: int = Depends(require_company),
):
    """更新文档库字段。"""
    kwargs = payload.model_dump(exclude_none=True)
    result = library_module.update(library_id, company_id=x_company_id, **kwargs)
    if not result:
        raise HTTPException(status_code=404, detail="Library not found")
    return result


@router.delete("/libraries/{library_id}")
def delete_library(
    library_id: int,
    x_company_id: int = Depends(require_company),
):
    """删除文档库。"""
    if not library_module.delete(library_id, company_id=x_company_id):
        raise HTTPException(status_code=404, detail="Library not found")
    return {"ok": True}


@router.get("/libraries/{library_id}/files")
def count_library_files(
    library_id: int,
    x_company_id: int = Depends(require_company),
):
    """统计文档库目录中的文件数量。"""
    lib = library_module.get(library_id, company_id=x_company_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")
    return {"count": library_module.count_files(library_id, company_id=x_company_id)}

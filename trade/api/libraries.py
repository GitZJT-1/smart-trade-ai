"""
Trade AI Assistant — 文档库管理 API 路由。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from trade import library as library_module
from trade.api.deps import require_company
from trade.api.models import LibraryCreate, LibraryUpdate

router = APIRouter(tags=["libraries"])


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


@router.post("/libraries/{library_id}/upload")
async def upload_files(
    library_id: int,
    files: list[UploadFile],
    x_company_id: int = Depends(require_company),
):
    """上传文件到文档库目录。支持多文件 + 保留 webkitRelativePath 目录结构。

    拖拽目录时浏览器会通过 webkitRelativePath 携带相对路径，
    服务端按该路径在 library root_path 下重建目录结构。
    """
    # 1. 校验 library 存在且属于当前公司
    lib = library_module.get(library_id, company_id=x_company_id)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    root = Path(lib["root_path"])
    root.mkdir(parents=True, exist_ok=True)

    # 2. 路径穿越检测正则：拒绝含 .. 或绝对路径或非法字符的片段
    _path_traversal_pattern = re.compile(r"\.\.|^[/\\]|[<>:\"|?*]")

    uploaded = []
    for f in files:
        # 获取相对路径（浏览器拖拽目录时通过 webkitRelativePath 携带）
        rel = getattr(f, "filename", "") or ""
        # 某些客户端用 filename 字段传递完整路径，取最后一个组件作为安全回退
        if not rel:
            rel = os.path.basename(f.filename or "untitled")

        # 路径穿越防护：分解路径片段，逐一检查
        parts = Path(rel).parts
        safe_parts = []
        for p in parts:
            if _path_traversal_pattern.search(p):
                # 含非法字符 → 用安全后缀替代，不拒绝整个请求
                safe_parts.append("_sanitized_" + re.sub(r"[<>:\"|?*]", "_", p))
            else:
                safe_parts.append(p)
        # 去空片段，防止空路径
        safe_parts = [p for p in safe_parts if p and p != "."]
        if not safe_parts:
            safe_parts = ["untitled"]

        dest = root.joinpath(*safe_parts)
        # 二次确认：目标路径必须在 root 子树内（防御符号链接攻击）
        try:
            dest.resolve().relative_to(root.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"路径穿越拒绝: {rel}")

        # 确保父目录存在
        dest.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        content = await f.read()
        dest.write_bytes(content)
        uploaded.append(str(dest.relative_to(root)))

    return {
        "uploaded": len(uploaded),
        "files": uploaded,
        "target_path": str(root),
    }


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

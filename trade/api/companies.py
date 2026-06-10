"""
Trade AI Assistant — 公司管理 API 路由。

端点：
  GET    /companies                          — 列出所有公司
  POST   /companies                          — 注册新公司
  GET    /companies/{company_id}              — 公司详情
  PUT    /companies/{company_id}              — 更新公司信息
  DELETE /companies/{company_id}              — 删除公司（级联删除所有数据）
  GET    /companies/{company_id}/agent-identity   — 获取 Agent 身份
  PUT    /companies/{company_id}/agent-identity   — 更新 Agent 身份
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from trade import company as company_module
from trade.api.deps import require_company
from trade.api.models import (
    AgentIdentityUpdate,
    CompanyCreate,
    CompanyUpdate,
)

router = APIRouter(tags=["companies"])


# ── 公司 CRUD ──────────────────────────────────────────────────────────────

@router.get("/companies")
def list_companies():
    """列出 Trade 系统中所有已注册的公司。"""
    return company_module.list_all()


@router.post("/companies")
def create_company(payload: CompanyCreate):
    """注册新公司。slug 省略时自动从 name 生成。自动写入默认 Agent 身份。"""
    try:
        company = company_module.create(
            name=payload.name, slug=payload.slug,
            logo_url=payload.logo_url, website=payload.website,
            contact_name=payload.contact_name, contact_email=payload.contact_email,
            address=payload.address,
            work_dir_name=payload.work_dir_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # 自动写入默认 Agent 身份（如果尚未设置）
    from trade.onboarding import _build_agent_identity
    existing = company_module.get_agent_identity(company["id"])
    if not existing:
        default_identity = _build_agent_identity(
            company["name"],
            {"products": "各类工业产品", "differentiation": "源头工厂，性价比高", "target_region": "全球市场"},
        )
        company_module.update_trade_company(
            company_id=company["id"],
            agent_identity_md=default_identity,
        )
    return company


@router.get("/companies/{company_id}")
def get_company(
    company_id: int,
    x_company_id: int = Depends(require_company),
):
    """根据 ID 获取公司详情。仅允许查询自己的公司。"""
    if x_company_id != company_id:
        # 不允许查询其他公司——即使本地运行也做数据隔离
        raise HTTPException(status_code=404, detail="Company not found")
    c = company_module.get(company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return c


@router.put("/companies/{company_id}")
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    x_company_id: int = Depends(require_company),
):
    """更新公司字段。X-Company-ID 必须与目标公司匹配。"""
    if x_company_id != company_id:
        raise HTTPException(status_code=403, detail="Cannot update another company's record.")
    result = company_module.update(
        company_id,
        name=payload.name, logo_url=payload.logo_url, website=payload.website,
        contact_name=payload.contact_name, contact_email=payload.contact_email,
        address=payload.address, is_active=payload.is_active,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    return result


@router.delete("/companies/{company_id}")
def delete_company(
    company_id: int,
    x_company_id: int = Depends(require_company),
    x_confirm_delete: str | None = Header(None, alias="X-Confirm-Delete"),
):
    """删除公司及级联删除其所有库、客户、对话记录。需要 X-Confirm-Delete header。"""
    if x_company_id != company_id:
        raise HTTPException(status_code=403, detail="Cannot delete another company.")
    if x_confirm_delete != "yes":
        raise HTTPException(
            status_code=400,
            detail="Destructive operation requires X-Confirm-Delete: yes header.",
        )
    if not company_module.delete(company_id):
        raise HTTPException(status_code=404, detail="Company not found")
    return {"ok": True}


# ── Agent 身份 ─────────────────────────────────────────────────────────────

@router.get("/companies/{company_id}/agent-identity")
def get_company_agent_identity(
    company_id: int,
    x_company_id: int = Depends(require_company),
):
    """获取公司的 Agent 身份文本（优先文件，其次 DB 缓存）。仅允许查自己的。"""
    if x_company_id != company_id:
        raise HTTPException(status_code=404, detail="Company not found")
    identity = company_module.get_agent_identity(company_id)
    return {"company_id": company_id, "agent_identity_md": identity}


@router.put("/companies/{company_id}/agent-identity")
def update_company_agent_identity(
    company_id: int,
    payload: AgentIdentityUpdate,
    x_company_id: int = Depends(require_company),
):
    """更新公司的 Agent 身份（写入 DB 缓存）。"""
    if x_company_id != company_id:
        raise HTTPException(status_code=403, detail="Cannot update another company's identity.")
    result = company_module.update_trade_company(
        company_id, agent_identity_md=payload.agent_identity_md,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    return result

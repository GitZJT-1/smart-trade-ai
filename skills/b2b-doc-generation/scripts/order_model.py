#!/usr/bin/env python3
"""
order_model.py — 订单档案（单一数据源）核心模型

为什么需要它：
  报价单 / PI / CI / 装箱单 / 报关单本质是「同一组订单数据的不同排版」。
  传统做法是每次从零手工抄，改一处要改四处，极易出错。
  本模块定义一份 order.json 作为唯一数据源：所有单据都从这份档案生成，
  改一处，其余单据联动（由后续 writer 读同一份档案实现）。

用法：
  python order_model.py init <order_no>              # 生成空白订单档案骨架
  python order_model.py recalc <order.json>          # 重算派生字段(金额/重量)并落盘
  python order_model.py dump <order.json>            # 打印订单档案摘要

依赖：仅标准库（json / uuid / datetime / dataclasses），零第三方库。
"""
import json
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

# Windows 控制台 UTF-8，防中文/俄文打印乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SCHEMA_VERSION = "1.0"


# ── 数据模型 ──────────────────────────────────────────────────────


@dataclass
class OrderItem:
    """订单行。unit_price / amount / 重量 在报价阶段允许为 null。"""
    item_uuid: str
    description_cn: str = ""
    description_en: str = ""
    description_ru: str = ""
    standard: str = ""          # DIN / ISO / GOST / ДСТУ 标准号
    material: str = ""          # 材质牌号
    hs_code: str = ""           # 海关编码
    quantity: float = 0.0
    unit: str = "pcs"
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    weight_kg_per_unit: Optional[float] = None
    total_weight_kg: Optional[float] = None
    packing: dict = field(default_factory=dict)

    def recalc(self, currency_round: int = 2) -> None:
        """重算派生字段：amount = quantity × unit_price；total_weight = quantity × 单重。"""
        if self.unit_price is not None:
            self.amount = round(self.quantity * self.unit_price, currency_round)
        else:
            self.amount = None
        if self.weight_kg_per_unit is not None:
            self.total_weight_kg = round(self.quantity * self.weight_kg_per_unit, 3)
        else:
            self.total_weight_kg = None


@dataclass
class OrderTerms:
    incoterm: str = "FOB"
    destination: str = ""
    currency: str = "USD"
    payment: str = ""
    lead_time: str = ""
    validity: str = ""
    port_of_loading: str = ""
    port_of_destination: str = ""


@dataclass
class OrderModel:
    """订单档案 —— 所有单据的唯一数据源。"""
    order_no: str
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    revision: int = 1
    seller_id: Optional[str] = None       # 引用 config/companies.yaml 的 sellers key
    buyer_id: Optional[str] = None        # 引用 config/companies.yaml 的 buyers key
    buyer_raw_name: str = ""              # 询价单上提取到的原始客户名（用于匹配）
    contract_no: str = ""                 # 客户合同号（箱单/报关单引用）
    spec_no: str = ""                     # 规格书号（箱单/报关单引用）
    terms: OrderTerms = field(default_factory=OrderTerms)
    items: list[OrderItem] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def recalc(self) -> None:
        for it in self.items:
            it.recalc()

    def total_amount(self) -> Optional[float]:
        """订单总金额（仅当所有行都有 amount 时才可算，否则返回 None）。"""
        if not self.items or any(it.amount is None for it in self.items):
            return None
        return round(sum(it.amount for it in self.items), 2)

    def total_gross_weight(self) -> Optional[float]:
        """订单总重（仅当所有行都有 total_weight_kg 时才可算，否则返回 None）。"""
        if not self.items or any(it.total_weight_kg is None for it in self.items):
            return None
        return round(sum(it.total_weight_kg for it in self.items), 3)


# ── JSON 序列化 ───────────────────────────────────────────────────


def to_dict(model: OrderModel) -> dict:
    d = asdict(model)
    return d


def from_dict(d: dict) -> OrderModel:
    terms = OrderTerms(**d.get("terms", {}))
    items = [OrderItem(**it) for it in d.get("items", [])]
    m = OrderModel(
        order_no=d["order_no"],
        date=d.get("date", ""),
        revision=d.get("revision", 1),
        seller_id=d.get("seller_id"),
        buyer_id=d.get("buyer_id"),
        buyer_raw_name=d.get("buyer_raw_name", ""),
        contract_no=d.get("contract_no", ""),
        spec_no=d.get("spec_no", ""),
        terms=terms,
        items=items,
        meta=d.get("meta", {}),
        schema_version=d.get("schema_version", SCHEMA_VERSION),
    )
    return m


def load(path: str) -> OrderModel:
    with open(path, "r", encoding="utf-8") as f:
        return from_dict(json.load(f))


def save(model: OrderModel, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_dict(model), f, ensure_ascii=False, indent=2)


def init(order_no: str) -> OrderModel:
    """生成空白订单档案骨架（含一个示例行，UUID 由本模块生成）。"""
    return OrderModel(
        order_no=order_no,
        items=[OrderItem(item_uuid=str(uuid.uuid4())[:8], description_cn="（示例：六角螺栓）")],
    )


# ── 结构级校验（schema 完整性，不含业务规则——业务规则在 precheck.py）──


def validate_schema(model: OrderModel) -> list[str]:
    """返回结构错误列表（空列表 = 结构合法）。只查"字段类型/必填"，不查业务正确性。"""
    errs = []
    if not model.order_no:
        errs.append("order_no 缺失")
    if not model.items:
        errs.append("items 为空，订单至少需要一行商品")
    for i, it in enumerate(model.items, 1):
        if not it.item_uuid:
            errs.append(f"第 {i} 行缺少 item_uuid")
        if not (it.description_cn or it.description_en or it.description_ru):
            errs.append(f"第 {i} 行缺少品名（cn/en/ru 至少其一）")
        if it.quantity is not None and it.quantity <= 0:
            errs.append(f"第 {i} 行数量非法: {it.quantity}")
    # 检查 item_uuid 唯一
    uuids = [it.item_uuid for it in model.items if it.item_uuid]
    if len(uuids) != len(set(uuids)):
        errs.append("item_uuid 存在重复")
    return errs


# ── CLI ───────────────────────────────────────────────────────────


def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "init":
        order_no = argv[2] if len(argv) > 2 else f"order_{datetime.now():%Y%m%d%H%M}"
        m = init(order_no)
        out = f"{order_no}.json"
        save(m, out)
        print(f"✅ 已生成空白订单档案: {out}")
        print(f"   订单号: {order_no} | 商品行: {len(m.items)} (示例行)")
        return 0
    if cmd == "recalc":
        path = argv[2]
        m = load(path)
        m.recalc()
        save(m, path)
        print(f"✅ 已重算派生字段并落盘: {path}")
        for it in m.items:
            print(f"   {it.item_uuid}: qty={it.quantity} price={it.unit_price} "
                  f"amount={it.amount} weight={it.total_weight_kg}")
        return 0
    if cmd == "dump":
        m = load(argv[2])
        print(f"订单 {m.order_no} | 修订 {m.revision} | 日期 {m.date}")
        print(f"seller_id={m.seller_id} | buyer_id={m.buyer_id} | raw={m.buyer_raw_name!r}")
        print(f"terms: {m.terms.incoterm} {m.terms.destination} | {m.terms.currency} | "
              f"起运港 {m.terms.port_of_loading}")
        print(f"商品 {len(m.items)} 行:")
        for it in m.items:
            print(f"  - {it.item_uuid} | {it.description_en or it.description_cn} | "
                  f"{it.quantity} {it.unit} | 单价 {it.unit_price} | 金额 {it.amount}")
        print(f"总金额: {m.total_amount()} | 总重: {m.total_gross_weight()}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))

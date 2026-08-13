#!/usr/bin/env python3
"""
precheck.py — 生成前结构化校验引擎（阻断式）

为什么需要它：
  AI 或人工生成的订单数据，在变成正式对外单证（PI/CI/报关单）之前，
  必须有确定性的机器校验兜底——不能靠肉眼或"AI 自查"。
  校验只查"结构性/一致性"问题，查不了"发错客户/金额填错但看起来合法"，
  后者仍须人工核对（SKILL.md 已强制提醒）。

规则分级：
  error   必须处理，阻断正式单据生成（退出码 1）
  warning 建议确认，默认阻断，可 --skip-warnings 放行（退出码 2）
  info    提示，不阻断

两阶段语义（--stage）：
  quote   报价阶段（单价留空是正常状态，缺价降为 info）
  formal  正式单证阶段（缺价升为 error，阻断）

用法：
  python precheck.py <order.json> [--config companies.yaml] [--stage quote|formal]
                  [--skip-warnings] [--check-only] [--report 报告.md]

退出码：
  0 = 无 error（且无 warning 或已 skip）
  1 = 有 error
  2 = 有 warning（未 skip）

依赖：pyyaml（可选，读 config 做币种/术语/实体校验）、标准库。
"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Incoterms 白名单
INCOTERMS = {"EXW", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP", "FCA", "FAS"}
# 常见币种白名单
CURRENCIES = {"USD", "CNY", "EUR", "RUB", "GBP", "JPY", "AED"}


@dataclass
class Issue:
    rule_id: str
    severity: str        # error / warning / info
    message: str
    field: str = ""


@dataclass
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    infos: list[Issue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def add(self, issue: Issue) -> None:
        if issue.severity == "error":
            self.errors.append(issue)
        elif issue.severity == "warning":
            self.warnings.append(issue)
        else:
            self.infos.append(issue)


# ── 规则集 ────────────────────────────────────────────────────────
# 每条规则：签名 fn(model, config, stage) -> list[Issue]


def r_buyer_matched(model, config, stage):
    """E001: 买家必须已匹配。未匹配 = 发错抬头风险，硬阻断。"""
    if not model.get("buyer_id"):
        return [Issue("E001", "error", "买家未匹配：buyer_id 为空。必须先跑 buyer_match 确认客户，"
                      f"原始客户名: {model.get('buyer_raw_name')!r}", "buyer_id")]
    if config and model["buyer_id"] not in (config.get("buyers") or {}):
        return [Issue("E001", "error", f"buyer_id '{model['buyer_id']}' 不在客户台账中", "buyer_id")]
    return []


def r_seller_configured(model, config, stage):
    """E002: 卖方必须已配置。"""
    if not model.get("seller_id"):
        return [Issue("E002", "error", "卖方未配置：seller_id 为空（单据表头无从填写）", "seller_id")]
    if config and model["seller_id"] not in (config.get("sellers") or {}):
        return [Issue("E002", "error", f"seller_id '{model['seller_id']}' 不在公司配置中", "seller_id")]
    return []


def r_items_present(model, config, stage):
    """E003: 商品行不能为空。"""
    items = model.get("items", [])
    if not items:
        return [Issue("E003", "error", "商品行为空，订单至少需要一行商品", "items")]
    return []


def r_quantity_valid(model, config, stage):
    """E004: 数量必须为正数。"""
    out = []
    for i, it in enumerate(model.get("items", []), 1):
        q = it.get("quantity")
        if q is None or q <= 0:
            out.append(Issue("E004", "error", f"第 {i} 行数量非法: {q!r}", f"items[{i-1}].quantity"))
    return out


def r_price_valid(model, config, stage):
    """E005/W001: 单价/金额校验（两阶段语义）。"""
    out = []
    items = model.get("items", [])
    missing_price = [i for i, it in enumerate(items, 1) if it.get("unit_price") is None]
    if missing_price:
        sev = "info" if stage == "quote" else "error"
        msg = (f"单价缺失：第 {'、'.join(map(str, missing_price))} 行未填单价"
               + ("（报价阶段正常，正式单证前须回写）" if stage == "quote" else ""))
        out.append(Issue("W001", sev, msg, "items[].unit_price"))
    for i, it in enumerate(items, 1):
        p = it.get("unit_price")
        if p is not None and p < 0:
            out.append(Issue("E005", "error", f"第 {i} 行单价为负: {p}", f"items[{i-1}].unit_price"))
        a = it.get("amount")
        if a is not None and a < 0:
            out.append(Issue("E005", "error", f"第 {i} 行金额为负: {a}", f"items[{i-1}].amount"))
    return out


def r_amount_consistent(model, config, stage):
    """E006: 金额必须 = 数量 × 单价（容差 0.01）。防手工抄错。"""
    out = []
    for i, it in enumerate(model.get("items", []), 1):
        q, p, a = it.get("quantity"), it.get("unit_price"), it.get("amount")
        if q is not None and p is not None and a is not None:
            expect = round(q * p, 2)
            if abs(expect - a) > 0.011:
                out.append(Issue("E006", "error",
                                 f"第 {i} 行金额不一致: 数量×单价={expect}，但 amount={a}",
                                 f"items[{i-1}].amount"))
    return out


def r_currency_valid(model, config, stage):
    """E007: 币种必须合法。"""
    cur = (model.get("terms") or {}).get("currency", "")
    if not cur:
        return [Issue("E007", "error", "币种缺失", "terms.currency")]
    if cur.upper() not in CURRENCIES:
        return [Issue("E007", "warning", f"币种 '{cur}' 不在常见清单，请确认", "terms.currency")]
    return []


def r_incoterm_valid(model, config, stage):
    """E008: 贸易术语必须合法。"""
    inc = (model.get("terms") or {}).get("incoterm", "")
    if not inc:
        return [Issue("E008", "warning", "贸易术语缺失", "terms.incoterm")]
    if inc.upper() not in INCOTERMS:
        return [Issue("E008", "error", f"贸易术语 '{inc}' 非法（Incoterms 2020）", "terms.incoterm")]
    return []


def r_port_destination(model, config, stage):
    """W002: 目的港缺失（CI/PL 会留白，清关常被要求补改）。"""
    t = model.get("terms") or {}
    if not t.get("port_of_destination") and not t.get("destination"):
        return [Issue("W002", "warning", "目的港/目的地缺失：CI/PL 上将留白，客户清关大概率要求补改",
                      "terms.port_of_destination")]
    return []


def r_weight_missing(model, config, stage):
    """W003: 重量缺失（PL 装箱单需要）。"""
    items = model.get("items", [])
    miss = [i for i, it in enumerate(items, 1)
            if it.get("weight_kg_per_unit") is None and not (it.get("packing") or {}).get("gw_per_carton_kg")]
    if miss:
        return [Issue("W003", "warning",
                      f"重量缺失：第 {'、'.join(map(str, miss))} 行缺单重/箱重，生成装箱单 PL 时需要补录",
                      "items[].weight_kg_per_unit")]
    return []


def r_payment_missing(model, config, stage):
    """W004: 付款条款缺失。"""
    t = model.get("terms") or {}
    if not t.get("payment"):
        return [Issue("W004", "warning", "付款条款缺失（PI 付款信息留空）", "terms.payment")]
    return []


def r_cert_reminder(model, config, stage):
    """I001: 产地证/证书需求提示。"""
    return [Issue("I001", "info", "产地证/质保书（CO/Form A/Mill Certificate）需求未记录；"
                  "俄罗斯、中亚客户清关通常需要，请与客户确认", "meta.certificates")]


RULES = [
    r_buyer_matched,
    r_seller_configured,
    r_items_present,
    r_quantity_valid,
    r_price_valid,
    r_amount_consistent,
    r_currency_valid,
    r_incoterm_valid,
    r_port_destination,
    r_weight_missing,
    r_payment_missing,
    r_cert_reminder,
]


def run_precheck(model: dict, config: dict | None = None, stage: str = "quote") -> Report:
    report = Report()
    for rule in RULES:
        for issue in rule(model, config, stage):
            report.add(issue)
    return report


# ── 渲染 ──────────────────────────────────────────────────────────


def _fmt(issue: Issue) -> str:
    tag = {"error": "错误", "warning": "警告", "info": "提示"}[issue.severity]
    return f"【{tag}】[{issue.rule_id}] {issue.message}"


def to_text(report: Report) -> str:
    lines = []
    total = len(report.errors) + len(report.warnings) + len(report.infos)
    lines.append(f"共发现 {len(report.errors)} 条错误、{len(report.warnings)} 条警告、{len(report.infos)} 条提示。")
    if report.errors:
        lines.append("")
        lines.append("-- 错误（必须处理） --")
        lines.extend(_fmt(x) for x in report.errors)
    if report.warnings:
        lines.append("")
        lines.append("-- 警告（建议确认） --")
        lines.extend(_fmt(x) for x in report.warnings)
    if report.infos:
        lines.append("")
        lines.append("-- 提示（人工注意） --")
        lines.extend(_fmt(x) for x in report.infos)
    return "\n".join(lines)


def to_markdown(report: Report, order_no: str) -> str:
    lines = [f"# 生成前校验报告 — 订单 {order_no}", "",
             f"- 错误 {len(report.errors)} / 警告 {len(report.warnings)} / 提示 {len(report.infos)}", ""]
    if report.errors:
        lines += ["## 错误（必须处理）", ""]
        lines += [f"- {_fmt(x)}" for x in report.errors] + [""]
    if report.warnings:
        lines += ["## 警告（建议确认）", ""]
        lines += [f"- {_fmt(x)}" for x in report.warnings] + [""]
    if report.infos:
        lines += ["## 提示（人工注意）", ""]
        lines += [f"- {_fmt(x)}" for x in report.infos] + [""]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────


def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    order_path = argv[1]
    stage = "quote"
    config = None
    skip_warnings = "--skip-warnings" in argv
    check_only = "--check-only" in argv
    report_path = None
    if "--stage" in argv:
        stage = argv[argv.index("--stage") + 1]
    if "--config" in argv:
        cfg_path = argv[argv.index("--config") + 1]
        if HAS_YAML:
            with open(cfg_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            print("⚠ 未安装 pyyaml，跳过 config 实体校验（E001/E002 只查非空）", file=sys.stderr)
    if "--report" in argv:
        report_path = argv[argv.index("--report") + 1]

    with open(order_path, "r", encoding="utf-8") as f:
        model = json.load(f)
    order_no = model.get("order_no", Path(order_path).stem)

    report = run_precheck(model, config, stage=stage)

    print()
    print(f"生成前检查报告 — 订单 {order_no}（阶段: {stage}）")
    print("=" * 60)
    print(to_text(report))
    print("=" * 60)

    if report_path:
        Path(report_path).write_text(to_markdown(report, order_no), encoding="utf-8")
        print(f"报告已落盘: {report_path}")

    if check_only:
        print()
        if report.has_errors:
            print("⚠ --check-only：发现错误，未生成任何单据。")
            return 1
        print("✓ --check-only：检查完成。")
        return 0

    if report.has_errors:
        print()
        print("✗ 存在错误，阻断单据生成。处理后重试。")
        return 1
    if report.warnings and not skip_warnings:
        print()
        print("⚠ 存在警告。确认无误请加 --skip-warnings 继续。")
        return 2
    print()
    print("✓ 检查通过，可生成单据。")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))

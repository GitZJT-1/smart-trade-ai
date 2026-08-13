#!/usr/bin/env python3
"""
buyer_match.py — 客户（买方）多级匹配器 + 硬阻断

为什么需要它：
  客户名拼写极不稳定（俄罗斯客户尤其：同一家公司会有 ООО/ЗАО 前后缀、
  拉丁转写、俄英混排、缩写等多种写法）。若匹配错，PI/CI 就会发给错误抬头——
  这是单证流程里最不能出错的一环。

匹配优先级（借鉴 trade-pipeline 的成熟做法）：
  1. --hint 显式指定的 buyer_id
  2. legal_names 精确匹配（规范化后）
  3. aliases 精确匹配（规范化后）
  4. 模糊匹配：剥离法律后缀后"核心名"相等（仅唯一命中才接受）
  5. 全部未命中 / 歧义 → 硬阻断：输出候选清单，退出码非 0，绝不猜测

用法：
  python buyer_match.py <config.yaml> <raw_name> [--hint buyer_id]

退出码：
  0 = 匹配成功（stdout 输出 buyer_id）
  1 = 匹配失败/歧义（stdout 输出候选清单，供人工选择）

依赖：pyyaml（读 config）、标准库。
"""
import re
import sys

try:
    import yaml
except ImportError:
    print("缺少 pyyaml，请先: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 模糊匹配核心名最短长度：短于此不参与模糊匹配（避免 "GF" 误匹配 "GF Industrial Supply"）
MIN_FUZZY_LEN = 5

# 公司名法律形式后缀（大小写无关，token 级剥离标点后比对）
LEGAL_SUFFIX_TOKENS = {
    # 英语系
    "llc", "ltd", "co", "corp", "inc", "limited", "liability", "company",
    "llp", "plc", "pte", "pty", "holdings", "group",
    # 欧陆
    "gmbh", "bv", "nv", "srl", "sa", "sarl", "ag", "oy", "ab", "aps", "kft", "spa",
    # 俄语系（拉丁转写 + 西里尔）
    "ooo", "zao", "oao", "pao", "jsc", "pjsc", "cjsc",
    "ооо", "зао", "оао", "пао", "ао", "ип", "тд", "нпо",
}


class BuyerMatchError(Exception):
    """匹配失败 / 歧义，必须停下来交人工确认，禁止静默跳过。"""

    def __init__(self, raw_name: str, candidates: list[dict], reason: str):
        self.raw_name = raw_name
        self.candidates = candidates
        self.reason = reason
        super().__init__(reason)


def normalize(name: str) -> str:
    """规范化：去引号/括号/多余空白，转小写。西里尔小写同样有效。"""
    if not name:
        return ""
    name = re.sub(r'[«»""\'“”‘’`]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.lower().strip()


def _core_name(norm: str) -> str:
    """剥离法律后缀，得到公司"核心名"。

    "ооо метиз трейдинг"  → "метиз трейдинг"
    "global fasteners llc" → "global fasteners"
    """
    tokens = [t.strip(".,;:&()[]-") for t in norm.split()]
    core = [t for t in tokens if t and t not in LEGAL_SUFFIX_TOKENS]
    return " ".join(core)


def _build_candidates(buyers: dict) -> list[dict]:
    return [
        {"id": k, "name_en": v.get("name_en", ""), "name_ru": v.get("name_ru", ""),
         "aliases": v.get("aliases", [])}
        for k, v in buyers.items()
    ]


def match_buyer(config: dict, raw_name: str, hint_buyer_id: str | None = None) -> str:
    """多级 buyer 匹配，失败抛 BuyerMatchError（硬阻断）。"""
    buyers = config.get("buyers", {}) or {}

    if not buyers:
        raise BuyerMatchError(raw_name, [], "config 中无 buyers 台账")

    # ── 优先级 1：显式指定 ──
    if hint_buyer_id:
        if hint_buyer_id in buyers:
            return hint_buyer_id
        raise BuyerMatchError(raw_name, _build_candidates(buyers),
                              f"显式指定的 buyer_id '{hint_buyer_id}' 不在台账中")

    if not raw_name or not raw_name.strip():
        raise BuyerMatchError(raw_name, _build_candidates(buyers), "未提取到客户名")

    norm = normalize(raw_name)

    # ── 优先级 2：legal_names 精确匹配 ──
    for bid, b in buyers.items():
        for legal in b.get("legal_names", []):
            if normalize(legal) == norm:
                return bid

    # ── 优先级 3：aliases 精确匹配 ──
    for bid, b in buyers.items():
        for alias in b.get("aliases", []):
            if normalize(alias) == norm:
                return bid

    # ── 优先级 4：模糊匹配（剥法律后缀后核心名相等，唯一命中才接受）──
    core = _core_name(norm)
    fuzzy = []
    if core and len(core) >= MIN_FUZZY_LEN:
        for bid, b in buyers.items():
            cand_names = b.get("legal_names", []) + [b.get("name_en", ""), b.get("name_ru", "")]
            for name in cand_names:
                if name and _core_name(normalize(name)) == core:
                    fuzzy.append(bid)
                    break
    uniq = list(set(fuzzy))
    if len(uniq) == 1:
        return uniq[0]
    if len(uniq) > 1:
        raise BuyerMatchError(raw_name, _build_candidates(buyers),
                              f"核心名 '{core}' 命中多个客户，有歧义，需人工确认")

    # ── 优先级 5：全部未命中 → 硬阻断 ──
    raise BuyerMatchError(raw_name, _build_candidates(buyers),
                          f"'{raw_name}' 未匹配到任何已知客户")


def _main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    config_path, raw_name = argv[1], argv[2]
    hint = None
    if "--hint" in argv:
        hint = argv[argv.index("--hint") + 1]

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    try:
        bid = match_buyer(config, raw_name, hint_buyer_id=hint)
    except BuyerMatchError as e:
        print(f"✗ 客户匹配失败: {e.reason}", file=sys.stderr)
        print(f"  原始名称: {e.raw_name!r}")
        if e.candidates:
            print("  已知客户候选清单（请人工选择其一，或确认为新客户）:")
            for c in e.candidates:
                names = " / ".join(x for x in [c["name_en"], c["name_ru"]] if x)
                aliases = f"  别名: {', '.join(c['aliases'])}" if c["aliases"] else ""
                print(f"    [{c['id']}] {names}{aliases}")
        return 1

    print(bid)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))

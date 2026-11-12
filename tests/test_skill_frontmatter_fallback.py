"""回归测试：PyYAML 不可用时，skill frontmatter 解析不能抛异常。

背景：/api/trade/chat 命中 skill 时会走
build_query() → augment_query() → load_injection_prompt() → _parse_frontmatter()。
后者原先把 `import yaml` 放在 try 之外，服务进程里 PyYAML 一旦不可见，
ModuleNotFoundError 就冒出 build_query() 的 try，FastAPI 返回纯文本 500
（前端只显示「请求失败（500）」）。
"""

import sys

from trade import skill_router

SAMPLE = (
    "---\n"
    "name: demo\n"
    "description: 演示用\n"
    "triggers:\n"
    "  - 发票\n"
    "injection_prompt: |\n"
    "  第一行\n"
    "  第二行\n"
    "---\n"
    "\n"
    "正文\n"
)


class TestFrontmatterFallback:
    def test_lf_frontmatter_parsed(self):
        fm, body = skill_router._parse_frontmatter(SAMPLE)
        assert fm["name"] == "demo"
        assert fm["injection_prompt"].strip() == "第一行\n第二行"
        assert body.strip() == "正文"

    def test_crlf_input_normalized(self):
        """直接传入 CRLF 字符串（上传/同步链路）也要能解析。"""
        fm, body = skill_router._parse_frontmatter(SAMPLE.replace("\n", "\r\n"))
        assert fm.get("name") == "demo"
        assert "第一行" in (fm.get("injection_prompt") or "")
        assert body.strip() == "正文"

    def test_parses_when_pyyaml_missing(self):
        class Blocker:
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in ("yaml", "ruamel"):
                    raise ImportError("blocked by test")
                return None

        saved = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name.split(".")[0] in ("yaml", "ruamel")
        }
        sys.meta_path.insert(0, Blocker())
        try:
            fm, body = skill_router._parse_frontmatter(SAMPLE)
        finally:
            sys.meta_path.pop(0)
            sys.modules.update(saved)

        assert fm["name"] == "demo"
        assert "第一行" in fm["injection_prompt"]
        assert body.strip() == "正文"

    def test_augment_query_survives_skill_hit(self):
        """命中 skill 的输入不应把主流程打挂。"""
        out = skill_router.augment_query("帮我做一张发票")
        assert isinstance(out, str) and out

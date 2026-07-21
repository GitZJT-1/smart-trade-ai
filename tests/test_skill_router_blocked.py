"""测试 _BLOCKED_SKILLS 过滤逻辑。

验证 auto-smtp-email 在任何匹配路径下都不会被触发。
"""


class TestBlockedSkills:
    """测试被禁用的 skill 不会被系统匹配。"""

    def test_auto_smtp_email_not_scored(self):
        """auto-smtp-email 不应出现在评分结果中。"""
        from trade.skill_router import _score_skills

        # 直接使用其触发词
        results = _score_skills("发邮件")
        names = [r["skill_name"] for r in results]
        assert "auto-smtp-email" not in names, (
            f"auto-smtp-email 不应出现在结果中，但得到: {names}"
        )

    def test_auto_smtp_email_not_matched_by_match_skill(self):
        """match_skill 不应返回 auto-smtp-email。"""
        from trade.skill_router import match_skill

        result = match_skill("帮我发邮件")
        assert result is None or result["name"] != "auto-smtp-email"

    def test_auto_smtp_email_not_matched_by_match_skills(self):
        """match_skills 不应包含 auto-smtp-email。"""
        from trade.skill_router import match_skills

        results = match_skills("群发邮件")
        names = [r["skill_name"] for r in results]
        assert "auto-smtp-email" not in names

    def test_blocked_skill_name_in_registry(self):
        """auto-smtp-email 应在注册表中被标记为禁用。"""
        from trade.skill_registry import _BLOCKED_SKILLS

        assert "auto-smtp-email" in _BLOCKED_SKILLS

    def test_other_email_skills_not_blocked(self):
        """b2b-email-intel 和 b2b-email-imitation 不应被禁用。"""
        from trade.skill_registry import _BLOCKED_SKILLS

        assert "b2b-email-intel" not in _BLOCKED_SKILLS
        assert "b2b-email-imitation" not in _BLOCKED_SKILLS


class TestSkillCount:
    """测试技能注册表的数量。"""

    def test_all_skills_registered(self):
        """skill_registry 应有 32 个条目。"""
        from trade.skill_registry import _SKILLS

        assert len(_SKILLS) == 33

    def test_all_skill_names_unique(self):
        """所有 skill 名称不能重复。"""
        from trade.skill_registry import _SKILLS

        names = [s["name"] for s in _SKILLS]
        assert len(names) == len(set(names)), (
            f"重复的 skill 名称: {[n for n in names if names.count(n) > 1]}"
        )

    def test_new_skills_present(self):
        """新增的 7 个技能应存在于注册表中。"""
        from trade.skill_registry import skill_names

        names = set(skill_names())
        for expected in (
            "b2b-kol-imitation", "b2b-reddit-engagement", "b2b-seo-aeo",
            "b2b-short-video", "b2b-exhibition", "b2b-product-description",
            "b2b-six-thinking-hats", "b2b-inquiry-training",
        ):
            assert expected in names, f"缺少技能: {expected}"

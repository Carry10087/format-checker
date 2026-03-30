from app.main import localize_error


def test_localize_error_for_missing_sources() -> None:
    exc = ValueError("No usable sources were collected. Enable more retrieval sources or add local knowledge.")
    assert "没有找到可用资料" in localize_error(exc)


def test_localize_error_for_missing_skill() -> None:
    exc = FileNotFoundError(r"Skill not found: D:\demo\SKILL.md")
    message = localize_error(exc)
    assert "未找到规则文件" in message
    assert r"D:\demo\SKILL.md" in message

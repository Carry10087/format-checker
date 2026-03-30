from pathlib import Path

from app.agent.skill_loader import load_skill_bundle


def test_skill_loader_reads_skill(tmp_path: Path) -> None:
    skill_dir = tmp_path / "sample-skill"
    references_dir = skill_dir / "references"
    references_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text("# Skill", encoding="utf-8")
    (references_dir / "guide.md").write_text("Guide", encoding="utf-8")

    bundle = load_skill_bundle(skill_path)
    assert "## Skill File" in bundle
    assert "Guide" in bundle

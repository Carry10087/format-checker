from __future__ import annotations

from pathlib import Path


def load_skill_bundle(skill_path: Path) -> str:
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")

    skill_text = skill_path.read_text(encoding="utf-8")
    bundle = [f"## Skill File\n\n{skill_text}"]

    references_dir = skill_path.parent / "references"
    if references_dir.exists():
        for candidate in sorted(references_dir.glob("*.md"))[:2]:
            text = candidate.read_text(encoding="utf-8")
            bundle.append(f"## Reference File: {candidate.name}\n\n{text[:12000]}")

    return "\n\n".join(bundle)

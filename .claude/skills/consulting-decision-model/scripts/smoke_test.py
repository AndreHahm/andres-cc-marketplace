#!/usr/bin/env python3
"""Structural self-test for consulting-decision-model. Makes no network call."""

import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def main() -> int:
    body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    errors = []
    for relative in re.findall(r"\]\((references/[^)#]+)", body):
        if not (SKILL / relative).is_file():
            errors.append(f"missing {relative}")
    for name in (
        "assets/decision-kit.settings.json",
        "assets/question-templates.json",
        "scripts/dck-token-shapes.json",
    ):
        try:
            json.loads((SKILL / name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    if not errors:
        templates = json.loads(
            (SKILL / "assets/question-templates.json").read_text(encoding="utf-8")
        )
        if set(templates.get("triggers", ())) != {"critical", "security", "confidence"}:
            errors.append("question-templates.json: wrong trigger keys")
    print("\n".join(errors) or "ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

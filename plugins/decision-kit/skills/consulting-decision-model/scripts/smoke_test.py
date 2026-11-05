#!/usr/bin/env python3
"""Structural self-test for consulting-decision-model. Makes no network call."""

import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SETTINGS = {
    "enabled",
    "pinned_model",
    "fallback_model",
    "proceed_max_p_block",
    "stop_min_p_block",
}


def main() -> int:
    errors = []
    try:
        body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\((references/[^)#]+)", body)
        if not links:
            errors.append("SKILL.md: no references linked")
        for relative in links:
            if not (SKILL / relative).is_file():
                errors.append(f"missing {relative}")
        data = {}
        for name in (
            "assets/decision-kit.settings.json",
            "assets/question-templates.json",
            "scripts/dck-token-shapes.json",
        ):
            data[name] = json.loads((SKILL / name).read_text(encoding="utf-8"))
        shapes = data["scripts/dck-token-shapes.json"]["shapes"]
        if not shapes or not all({"name", "pattern"} <= set(shape) for shape in shapes):
            errors.append("dck-token-shapes.json: incomplete shapes")
        settings = data["assets/decision-kit.settings.json"]
        if set(settings) != SETTINGS:
            errors.append("decision-kit.settings.json: wrong keys")
        elif not settings["proceed_max_p_block"] < settings["stop_min_p_block"]:
            errors.append("decision-kit.settings.json: thresholds out of order")
        templates = data["assets/question-templates.json"]
        if not {"risk_rubric", "data_note", "triggers"} <= set(templates):
            errors.append("question-templates.json: missing keys")
        elif not isinstance(templates["risk_rubric"], list):
            errors.append("question-templates.json: risk_rubric is not a list")
        elif set(templates["triggers"]) != {"critical", "security", "confidence"}:
            errors.append("question-templates.json: wrong trigger keys")
        else:
            for name, trigger in templates["triggers"].items():
                if not {"policy", "instructions", "true", "false"} <= set(trigger):
                    errors.append(f"question-templates.json: {name} is incomplete")
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        errors.append(str(exc))
    print("\n".join(errors) or "ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check decision-kit's setup and print one JSON report; never prints the key.

Every run with a usable key sends three fixed decisions to each model, with no project content.
Exits 0 when no check failed and 1 otherwise. Standard library only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "dck_decide", Path(__file__).resolve().with_name("dck-decide.py")
)
assert SPEC is not None and SPEC.loader is not None
dck = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dck)

PROBE = {
    "trigger": "confidence",
    "action": "Rename the local scratch file draft.txt to notes.txt.",
    "state": "The file is untracked and nothing else reads it.",
    "claude_position": "proceed",
    "claude_risk": "none",
    "options": {"rename": "Rename the file", "keep": "Keep the current name"},
    "claude_choice": "rename",
}
QUESTIONS = (
    ("yes/no", "safe_to_proceed", "noul"),
    ("choice", "best_option", "choice"),
    ("risk", "risk", "score"),
)
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[0-9T:.Z+-]{0,20}")
HTTP_HINTS = {
    401: "the key was rejected",
    402: "the account has no credit",
    403: "the key may not use this model",
    404: "no zero-data-retention endpoint, or an unknown model",
    429: "rate limited",
}


def _valid_answer(question: str, kind: str, value: object) -> bool:
    if kind == "choice":
        return isinstance(value, str) and value in PROBE["options"]
    top = 1 if question == "safe_to_proceed" else len(dck._templates()["risk_rubric"]) - 1
    return isinstance(value, (int, float)) and dck._number(value) and 0 <= value <= top


def probe(base: str, key: str, model: str, question: str, kind: str) -> tuple[str, str]:
    """One fixed decision. Returns (status, detail); the API's own text is never repeated."""
    payload = dck.build_payload(PROBE, model)
    payload["questions"] = {question: payload["questions"][question]}
    status, body = dck.post(base, key, payload, dck.REQUEST_TIMEOUT)
    if status != 200:
        hint = HTTP_HINTS.get(status or 0, "")
        return "fail", f"HTTP {status}: {hint}" if status and hint else f"HTTP {status}"
    try:
        parsed = json.loads(body)
        value = parsed["answers"][question][kind]
        if parsed.get("model") == model and _valid_answer(question, kind, value):
            return "pass", "answered"
    except (ValueError, KeyError, TypeError, RecursionError):
        pass
    return "fail", "the answer did not validate"


def _env_is_ignored(path: Path) -> bool:
    """A plain read of the .gitignore next to the file, not a git check."""
    try:
        lines = dck.read_local_file(path.with_name(".gitignore")).splitlines()
    except (OSError, ValueError):
        return False
    return any(line.strip() in (".env", ".env*", "/.env") for line in lines)


def _settings_check(start: Path) -> tuple[dict, dict]:
    warnings: list[str] = []
    settings = dck.load_settings(dck.project_root(start), warnings)
    low, high = settings["proceed_max_p_block"], settings["stop_min_p_block"]
    detail = f"enabled: {str(settings['enabled']).lower()}, thresholds {low} and {high}"
    if warnings:
        detail += "; " + "; ".join(warnings)
    status = "pass" if settings["enabled"] and not warnings else "warn"
    return settings, {"name": "settings", "status": status, "detail": detail}


def _key_check(key: str, source: str) -> dict:
    name = f"{dck.KEY_NAME} found in {source}"
    if not key:
        return _check("key", "fail", f"{dck.KEY_NAME} is not in the environment or a .env file")
    if key == dck.PLACEHOLDER_KEY:
        return _check("key", "fail", f"{name} is still the example value")
    if not re.fullmatch(r"[\x21-\x7e]+", key):
        return _check("key", "fail", f"{name} contains whitespace or control characters")
    return _check("key", "pass", name)


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def _listing_checks(models: dict, entries: list[dict] | None) -> list[dict]:
    if entries is None:
        return [_check("connection", "fail", "the model list could not be fetched")]
    found = {e["canonical_slug"]: e for e in entries}
    checks = [_check("connection", "pass", f"the API lists {len(entries)} decision models")]
    for role, model in models.items():
        name = f"{role} model listed"
        if model not in found:
            checks.append(_check(name, "fail", f"{model} is not in the list"))
        elif found[model].get("expiration_date"):
            date = found[model]["expiration_date"]
            shown = date if isinstance(date, str) and DATE.fullmatch(date) else "an unstated date"
            checks.append(_check(name, "warn", f"{model} expires on {shown}"))
        else:
            checks.append(_check(name, "pass", model))
    return checks


def _probe_checks(base: str, key: str, models: dict) -> list[dict]:
    checks = []
    for role, model in models.items():
        failed = False
        for label, question, kind in QUESTIONS:
            name = f"{role} model, {label} decision"
            if failed:
                checks.append(_check(name, "skip", "an earlier decision failed"))
                continue
            status, detail = probe(base, key, model, question, kind)
            failed = status == "fail"
            checks.append(_check(name, status, detail))
    return checks


def run(base: str, start: Path) -> dict:
    checks = [
        _check(
            "python",
            "pass" if sys.version_info >= (3, 9) else "fail",
            ".".join(str(part) for part in sys.version_info[:3]),
        )
    ]
    problem = dck.screen(["plain text"], "")
    checks.append(_check("secret screen", "fail" if problem else "pass", problem or "loaded"))
    settings, settings_check = _settings_check(start)
    checks.append(settings_check)
    key_warnings: list[str] = []
    key, source = dck.find_key(start, key_warnings)
    key_check = _key_check(key, source)
    checks.append(key_check)
    checks += [_check("key", "warn", warning) for warning in key_warnings]
    if source.endswith(dck.ENV_FILE) and not _env_is_ignored(Path(source)):
        checks.append(_check("key", "warn", f"{source} is not listed in the .gitignore beside it"))
    models = {"pinned": settings["pinned_model"], "fallback": settings["fallback_model"]}
    checks += _listing_checks(models, dck.model_entries(base, dck.LISTING_TIMEOUT))
    if key_check["status"] != "pass" or not settings["enabled"]:
        reason = "the check is off" if not settings["enabled"] else "no usable key"
        checks.append(_check("decisions", "skip", f"no decisions sent: {reason}"))
    else:
        checks += _probe_checks(base, key, models)
    return {"ok": all(check["status"] != "fail" for check in checks), "checks": checks}


def main() -> int:
    """Always prints a report. Error text can hold the key, so only the type is shown."""
    try:
        report = run(dck.API_BASE, Path.cwd())
    except Exception as exc:  # noqa: BLE001
        failure = _check("doctor", "fail", f"stopped by {type(exc).__name__}")
        report = {"ok": False, "checks": [failure]}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

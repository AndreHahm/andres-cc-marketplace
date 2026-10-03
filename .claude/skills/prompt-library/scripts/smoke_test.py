#!/usr/bin/env python3
"""Persisted smoke test for prompt-library.

Guards the properties this mutating skill depends on: frontmatter validity and
disable-model-invocation, referenced-file existence, tool grants that name only real validator
subcommands and no pre-approved Read/Write/Edit/WebFetch (a security review removed them so injected
text cannot write or fetch without a permission prompt), a body that runs only granted subcommands,
and live behavior: web-origin text carrying a fake key is refused by the validator and nothing is
filed, while clean user text goes init -> draft -> verify -> activate. Exit code 0 means all passed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
PLUGIN_SCRIPTS = SKILL_DIR.parent.parent / "scripts"
FORBIDDEN_GRANT_NAMES = {"Read", "Write", "Edit", "WebFetch", "Bash"}
ALLOWED_OTHER_GRANTS = {"Agent(prompt-reviewer)", "Skill(session-detail)"}


def _load_common():
    spec = importlib.util.spec_from_file_location(
        "plib_smoke_common", PLUGIN_SCRIPTS / "plib_smoke_common.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load plib_smoke_common.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["plib_smoke_common"] = module
    spec.loader.exec_module(module)
    return module


C = _load_common()


def check_frontmatter():
    frontmatter, _ = C.read_skill(SKILL_DIR)
    name = C.frontmatter_field(frontmatter, "name")
    if name != "prompt-library":
        return False, f"name is {name!r}, expected 'prompt-library'"
    if C.frontmatter_field(frontmatter, "disable-model-invocation") != "true":
        return False, "disable-model-invocation is not true: a prompt's text could start edits"
    if not C.has_block_description(frontmatter):
        return False, "description is not a >- block scalar"
    return True, "name, disable-model-invocation: true and block description present"


def check_referenced_files():
    _, body = C.read_skill(SKILL_DIR)
    missing = C.referenced_files_missing(SKILL_DIR, body)
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, "every referenced file exists"


def check_grants():
    frontmatter, _ = C.read_skill(SKILL_DIR)
    tools = C.frontmatter_field(frontmatter, "allowed-tools") or ""
    grants = C.split_grants(tools)
    problems = []
    for grant in grants:
        name = C.grant_name(grant)
        if name == "Bash":
            if "plib_catalog_validate.py" not in grant:
                problems.append(f"Bash grant not scoped to the validator: {grant}")
        elif name in FORBIDDEN_GRANT_NAMES:
            problems.append(f"pre-approved {name}")
        elif grant not in ALLOWED_OTHER_GRANTS:
            problems.append(f"unexpected grant {grant}")
    real = set(C.V.COMMANDS)
    unknown = sorted(set(C.validator_subcommands_granted(tools)) - real)
    if unknown:
        problems.append(f"grants name subcommands the validator does not have: {unknown}")
    if problems:
        return False, "; ".join(problems)
    return True, "no pre-approved Read/Write/Edit/WebFetch; validator grants name real subcommands"


def check_body_uses_only_granted_subcommands():
    frontmatter, body = C.read_skill(SKILL_DIR)
    granted = set(
        C.validator_subcommands_granted(C.frontmatter_field(frontmatter, "allowed-tools") or "")
    )
    used = C.body_subcommands(body)
    extra = sorted(used - granted)
    if extra:
        return False, f"body runs ungranted subcommand(s): {extra}"
    return True, f"body uses {len(used)} subcommands, all granted"


def check_live_web_secret_is_refused_and_nothing_filed():
    fx = C.Fixture()
    try:
        code, out = fx.run("init")
        if code != 0:
            return False, f"init failed: {out.get('error')}"
        source = {"url": "https://example.com/p", "retrieved_on": "2026-10-03"}
        draft = fx.scratch(origin="web", source_ref=source, _body=f"Use key {C.FAKE_KEY}")
        code, out = fx.run("draft", draft)
        message = out.get("error", "")
        if code == 0:
            return False, "draft accepted web-origin text containing a key"
        if "aws_access_key" not in message:
            return False, f"refused for the wrong reason: {message}"
        if C.FAKE_KEY in message:
            return False, "the refusal message echoed the secret"
        filed = list((fx.repo / ".claude" / "prompts").glob("*/*.md"))
        if filed:
            return False, f"a record file was left behind: {[p.name for p in filed]}"
    finally:
        fx.close()
    return True, "web text with a key is refused, the key is not echoed, nothing is filed"


def check_live_clean_prompt_lifecycle():
    fx = C.Fixture()
    try:
        fx.active_prompt()
        code, out = fx.run("show", C.SLUG)
        if code != 0 or out["records"][0]["status"] != "active":
            return False, f"activated prompt not shown as active: {out.get('error')}"
        code, out = fx.run("deactivate", "p000000000001")
        if code != 0:
            return False, f"deactivate failed: {out.get('error')}"
    finally:
        fx.close()
    return True, "init -> draft -> verify -> activate -> deactivate works for clean user text"


def main() -> int:
    checks = [
        ("frontmatter", check_frontmatter),
        ("referenced files", check_referenced_files),
        ("grants", check_grants),
        ("body uses only granted subcommands", check_body_uses_only_granted_subcommands),
        ("live: secret refused, nothing filed", check_live_web_secret_is_refused_and_nothing_filed),
        ("live: clean prompt lifecycle", check_live_clean_prompt_lifecycle),
    ]
    return C.report([C.guarded(name, fn) for name, fn in checks])


if __name__ == "__main__":
    sys.exit(main())

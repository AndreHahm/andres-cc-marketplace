#!/usr/bin/env python3
"""Persisted smoke test for status-and-learning: frontmatter validity, referenced-file
existence (same-skill, cross-skill, and plugin-root relative references),
Bash-scope grant usage, and step-header sequencing (## Quick Start) --
structural checks only, since this is a conversational skill with no
executable logic of its own to simulate. Adapted from git-kit's create-pr
smoke_test.py (same check set), extended to resolve this plugin's own
cross-skill (`../<skill>/references/...`) and plugin-root
(`../../FOUNDATION_CONTRACTS.md`, `../../host-profile.json`) relative
references, and to treat a plugin-root shared contract file named in the
body as valid evidence of a script-path Bash grant's usage without
folding that file into the general command-usage search text (which would
make the plain-command-grant check vacuous -- see check_bash_grants)."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SECTION_HEADERS = ["## Quick Start"]


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if not re.search(r"(?m)^name:\s", fm) or not re.search(r"(?m)^description:\s", fm):
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def _find_repo_root(start: pathlib.Path):
    current = start
    for _ in range(10):
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def _skill_dir_candidates(repo_root):
    # This repo mirrors every skill into a flattened .claude/skills/<name>/ copy alongside its
    # canonical plugins/<plugin>/skills/<name>/ location (see .claude/rules/
    # plugin-rulebook-enforcement.md's R20 multi-mirror sweep). Same-skill and cross-skill
    # ("../<skill>/...") relative references resolve fine from either location, since both
    # plugins/<plugin>/ and .claude/ have a skills/ subdirectory holding every skill flat. A
    # plugin-ROOT file two-plus levels up (e.g. `../../FOUNDATION_CONTRACTS.md`) does not: it
    # only exists relative to the real plugins/<plugin>/skills/<name>/ directory, never relative
    # to .claude/skills/<name>/ (a different depth from repo root). When SKILL_DIR itself doesn't
    # resolve a reference, fall back to the canonical skill directory found by matching this
    # skill's own name under plugins/*/skills/.
    candidates = [SKILL_DIR]
    if repo_root is not None:
        for c in sorted(repo_root.glob(f"plugins/*/skills/{SKILL_DIR.name}")):
            if c.resolve() != SKILL_DIR.resolve() and c not in candidates:
                candidates.append(c)
    return candidates


def check_referenced_files():
    text = SKILL_MD.read_text(encoding="utf-8")
    missing = []
    repo_root = _find_repo_root(SKILL_DIR)
    skill_dirs = _skill_dir_candidates(repo_root)

    # (?:\.\./[\w-]+/)? admits one cross-skill hop (`../<skill-name>/references/...`) in
    # addition to a same-skill reference with no `../` prefix at all -- a bare (?:\.\./)*
    # only matches an unbroken run of "../" segments, so it can never match a real cross-skill
    # path like `../linear-work-management/references/linear-entity-fields.md`, where a skill
    # directory name sits between the ".." hop and "references/".
    skill_relative = (
        r"`((?:\.\./[\w-]+/)?(?:references|scripts|assets|examples)/[\w./-]+\.(?:md|py|sh|json))`"
    )
    for match in re.finditer(skill_relative, text):
        if (SKILL_DIR / match.group(1)).resolve().exists():
            continue
        # A "scripts/..."/"references/..." path with no leading "../" can still be this
        # plugin's own shared, plugin-root scripts/references dir rather than this specific
        # skill's own -- e.g. `scripts/bridge_caller.py` lives at the plugin root and is
        # shared across several skills, not duplicated per-skill.
        if any((cand.parent.parent / match.group(1)).resolve().exists() for cand in skill_dirs):
            continue
        missing.append(match.group(1))

    plugin_relative = r"`((?:\.\./){2,}[\w./-]+\.(?:md|json))`"
    for match in re.finditer(plugin_relative, text):
        if not any((cand / match.group(1)).resolve().exists() for cand in skill_dirs):
            missing.append(match.group(1))

    # A skill body sometimes names a plugin-root file bare, with no "../" prefix at all (e.g.
    # `versioned-configuration.json`) -- deliberately checked against a small, explicit,
    # hardcoded name list rather than a generic bare-filename regex: a generic pattern would also
    # match `evals.json` (a generic-concept mention, not a specific path), a same-skill file
    # already covered by skill_relative mentioned a second time without its path prefix (e.g.
    # `intake-payload-schema.md`), or `SKILL.md` (sometimes another plugin's SKILL.md entirely,
    # e.g. "codex-review-bridge's SKILL.md") -- none of which this check could safely resolve.
    for bare_name in (
        "FOUNDATION_CONTRACTS.md",
        "host-profile.json",
        "versioned-configuration.json",
    ):
        if f"`{bare_name}`" in text and not any(
            (cand.parent.parent / bare_name).resolve().exists() for cand in skill_dirs
        ):
            missing.append(bare_name)

    repo_relative = r"`((?:docs|evals|plugins|\.claude)/[\w./-]+\.(?:md|py|json))`"
    for match in re.finditer(repo_relative, text):
        path_str = match.group(1)
        if path_str.endswith(".local.json"):
            # A `.claude/<plugin>.local.json`-style reference is this repo's own established
            # local-override convention (.claude/rules/ask-before-config-decisions.md) --
            # gitignored and install-time-optional, so it legitimately may not exist here.
            continue
        if repo_root is None:
            missing.append(path_str + " (repo root not found)")
            continue
        if not (repo_root / path_str).exists():
            missing.append(path_str)

    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def _grant_pattern(cmd: str) -> str:
    # (?![\w/-]) requires a real token boundary after the match -- without it, a grant like
    # "gh pr view" would be reported "used" by an unrelated "gh pr viewer" or "gh pr view-only"
    # elsewhere in the body, and a grant like "foo" would match inside "foobar".
    return r"[^\s]*".join(re.escape(part) for part in cmd.split("*")) + r"(?![\w/-])"


def _collect_search_text(body: str) -> str:
    search_text = body
    self_path = pathlib.Path(__file__).resolve()

    for sub in ("references", "scripts", "assets", "examples"):
        d = SKILL_DIR / sub
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if not f.is_file():
                    continue
                # Exclude this smoke test's own source (and any compiled bytecode next to it,
                # e.g. __pycache__/*.pyc from a local run) from the scripts/ scan below -- the
                # smoke test lives in scripts/ itself, and its own comments/docstrings mention
                # example grant strings like "gh pr view"/"bridge_caller.py" that would
                # otherwise leak into search_text and make check_bash_grants match against its
                # own commentary instead of the skill's real body/references.
                if f.resolve() == self_path:
                    continue
                if f.suffix == ".pyc" or "__pycache__" in f.parts:
                    continue
                try:
                    search_text += "\n" + f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    pass

    # A cross-skill reference file this skill's own body explicitly names (e.g.
    # "skills/linear-work-management/references/linear-entity-fields.md") is fair game too --
    # a skill that documents "see <other skill>'s reference file" genuinely uses whatever
    # commands/fields that file demonstrates, even though it never repeats them in its own body.
    plugin_root = SKILL_DIR.parent.parent
    for m in re.finditer(r"skills/([\w-]+)/references/([\w.-]+\.md)", body):
        other = plugin_root / "skills" / m.group(1) / "references" / m.group(2)
        if other.is_file():
            try:
                search_text += "\n" + other.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass

    return search_text


def _collect_plugin_contract_text(body: str) -> str:
    # A plugin-root shared contract file (e.g. `../../FOUNDATION_CONTRACTS.md`) can document a
    # *script-path* Bash grant's real usage (a named shared procedure, e.g. bridge_caller.py's
    # Codex Bridge-Caller Dispatch procedure) without the skill's own body repeating the script
    # name -- kept separate from _collect_search_text deliberately: FOUNDATION_CONTRACTS.md is
    # large enough (tens of KB) that folding it into the general search text would make the
    # plain-command-grant check (e.g. "gh pr view") nearly vacuous, since a comprehensive shared
    # contracts doc mentions most common commands somewhere regardless of whether *this* skill
    # actually uses them.
    text = ""
    skill_dirs = _skill_dir_candidates(_find_repo_root(SKILL_DIR))
    for m in re.finditer(r"`((?:\.\./){2,}[\w./-]+\.(?:md|json))`", body):
        for cand in skill_dirs:
            other = (cand / m.group(1)).resolve()
            if other.is_file():
                try:
                    text += "\n" + other.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    pass
                break
    return text


def check_bash_grants():
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    close = fm_text.find("\n---\n", 4)
    if close == -1:
        return True, "frontmatter never closed (skip -- check_frontmatter already reports this)"
    header_end = close + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.*/${} -]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    search_text = _collect_search_text(body)
    contract_text = _collect_plugin_contract_text(body)

    unused = []
    for cmd in granted_cmds:
        # A script-path grant is normalized to its basename before matching -- the
        # frontmatter and body/references can spell the same script's path differently
        # (${CLAUDE_PLUGIN_ROOT}/... vs a portable */<plugin>/... glob), and what actually
        # matters is whether the script itself is invoked or described anywhere.
        script_match = re.search(r"([\w-]+\.(?:sh|py))", cmd)
        if script_match:
            name = script_match.group(1)
            if re.search(re.escape(name), search_text) or re.search(re.escape(name), contract_text):
                continue
            unused.append(cmd)
            continue
        if re.search(_grant_pattern(cmd), search_text):
            continue
        unused.append(cmd)

    if unused:
        return False, (
            "Bash grant(s) never invoked anywhere in the skill's own body/references/scripts "
            "(or a named plugin-root contract file, for script-path grants): "
            + ", ".join(sorted(set(unused)))
        )
    return True, "every granted Bash command is invoked somewhere in the skill's own files"


def check_step_sequence():
    # Scoped to the declared SECTION_HEADERS only -- other sections (e.g. "Testing &
    # Validation") legitimately restart their own numbered lists for unrelated scenarios,
    # which a whole-file scan would wrongly flag as non-sequential. Within a found section,
    # a "### " subsection (e.g. distinct scenarios/paths) is checked against a running baseline
    # that carries forward across chunks -- a later subsection can legitimately *continue*
    # numbering from an earlier one's last step (verified live: merge-to-completion and
    # pr-to-linear both do this) or start its own fresh 1-based sequence, but never silently
    # skip steps at either a chunk's own start or a section-wide start.
    text = SKILL_MD.read_text(encoding="utf-8")
    found_any = False
    for header in SECTION_HEADERS:
        # Tolerant of trailing spaces/tabs after the header text (a bare "\n"+header+"\n"
        # substring match would silently fall through to "not found" on those, masking a real
        # tracked section instead of flagging the mismatch).
        header_match = re.search(r"\n" + re.escape(header) + r"[ \t]*\n", text)
        if header_match is None:
            continue
        found_any = True
        start = header_match.start()
        end = text.find("\n## ", start + 1)
        section = text[start : end if end != -1 else len(text)]
        # Fenced code blocks can legitimately contain an illustrative numbered example that
        # isn't part of the real tracked procedure -- strip them before scanning for numbers.
        section = re.sub(r"```.*?```", "", section, flags=re.DOTALL)

        sub_starts = [m.start() for m in re.finditer(r"^### ", section, re.MULTILINE)]
        if sub_starts:
            bounds = [0, *sub_starts, len(section)]
            chunks = [section[bounds[i] : bounds[i + 1]] for i in range(len(bounds) - 1)]
        else:
            chunks = [section]

        # expected_next tracks the running baseline across chunks -- a later "### " subsection
        # is expected to *continue* numbering from the prior chunk's last step (verified live:
        # merge-to-completion, pr-to-linear), not restart at 1. This also catches a regression
        # in a later chunk alone (e.g. its own first step removed, leaving [10, 11, ...] when
        # [9, 10, 11, ...] was expected) -- anchoring each chunk only at its own numbers[0], as
        # an earlier version of this check did, silently accepted that. A chunk that doesn't
        # continue is still accepted if it matches a fresh 1-based restart instead -- an
        # intentionally independent numbered list in a later subsection, not a continuation.
        expected_next = 1
        for chunk in chunks:
            numbers = [int(n) for n in re.findall(r"^(\d+)\. ", chunk, re.MULTILINE)]
            if not numbers:
                continue
            expected_continue = list(range(expected_next, expected_next + len(numbers)))
            if numbers == expected_continue:
                expected_next = numbers[-1] + 1
                continue
            expected_restart = list(range(1, 1 + len(numbers)))
            if expected_next != 1 and numbers == expected_restart:
                expected_next = numbers[-1] + 1
                continue
            return False, (
                f"step numbering not sequential in '{header}': "
                f"found {numbers}, expected {expected_continue}"
            )
    if not found_any:
        if not SECTION_HEADERS:
            return True, "no tracked section for this skill (skip)"
        return False, (
            f"none of the tracked headers {SECTION_HEADERS} were found in SKILL.md -- "
            "a header may have been renamed without updating this script"
        )
    return True, "step headers sequential in every found section/subsection"


CHECKS = [check_frontmatter, check_referenced_files, check_bash_grants, check_step_sequence]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

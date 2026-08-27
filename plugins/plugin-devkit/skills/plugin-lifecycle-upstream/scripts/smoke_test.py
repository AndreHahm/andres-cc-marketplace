#!/usr/bin/env python3
"""Persisted smoke test for plugin-lifecycle-upstream: frontmatter validity,
referenced-file existence, Bash-scope grant consistency, and phase-header
sequencing across workflows/*.md — this last check exists because a phase-insertion
edit (e.g. adding a new phase between two existing ones) is exactly the kind of
change that silently leaves a stale "Phase N" cross-reference elsewhere."""

import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if "name:" not in fm or "description:" not in fm:
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def check_referenced_files():
    # `test-agent-trigger.sh`/`test-hook.sh` are excluded: this skill's prose splits the
    # owning plugin name and the script path across separate backtick spans
    # ("`agent-development`'s `scripts/test-agent-trigger.sh`"), so a bare
    # `scripts/test-agent-trigger.sh` match here is a cross-plugin reference, not a path
    # relative to this skill — already covered by check_bash_grants' full-path check instead.
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = (
        r"`(references/[\w.-]+\.md|workflows/[\w.-]+\.md"
        r"|scripts/(?!test-agent-trigger\.sh|test-hook\.sh)[\w./-]+)`"
    )
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Only "scoped `Bash(...)`" counts as a real invocation instruction — a bare mention
    # elsewhere (e.g. an illustrative example) is not an instruction to invoke it. Checked
    # across SKILL.md and every workflows/*.md file, since real invocations live in both.
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    value = ""
    if fm_line_match:
        value = fm_line_match.group(1).strip()
        if value in (">-", ">", "|", "|-", "|+", ">+"):
            # YAML block scalar: the real value is on subsequent, more-indented lines.
            block_lines = []
            for line in frontmatter[fm_line_match.end() :].splitlines():
                if line.strip() == "":
                    continue
                if line[:1] in (" ", "\t"):
                    block_lines.append(line)
                else:
                    break
            value = " ".join(block_lines)
    granted = set(re.findall(r"Bash\([^)]*\)", value))

    referenced = set(re.findall(r"scoped `(Bash\([^)]*\))", fm_text[header_end:]))
    for wf in sorted((SKILL_DIR / "workflows").glob("*.md")):
        referenced |= set(re.findall(r"scoped `(Bash\([^)]*\))", wf.read_text(encoding="utf-8")))

    missing = referenced - granted
    if missing:
        return False, "body invokes Bash scope(s) missing from allowed-tools: " + ", ".join(
            sorted(missing)
        )
    return True, "every scoped Bash invocation is granted"


def check_phase_sequence():
    workflows_dir = SKILL_DIR / "workflows"
    if not workflows_dir.exists():
        return True, "no workflows/ directory (skip)"
    problems = []
    for wf in sorted(workflows_dir.glob("*.md")):
        text = wf.read_text(encoding="utf-8")
        numbers = [
            int(n) for n in re.findall(r"^##+ (?:Phase|Step|Service) (\d+):", text, re.MULTILINE)
        ]
        if not numbers:
            continue
        expected = list(range(numbers[0], numbers[0] + len(numbers)))
        if numbers != expected:
            problems.append(f"{wf.name}: found {numbers}, expected consecutive {expected}")
    if problems:
        return False, "phase/step numbering not sequential: " + "; ".join(problems)
    return True, "phase/step headers sequential in every workflow file checked"


def check_skillmd_phase_range():
    # A phase-insertion/removal edit can leave SKILL.md's own prose ("Phase N", table
    # cells, quality-gate bullets) pointing at a number outside the workflow's actual
    # current range -- check_phase_sequence only validates workflows/*.md's own headers,
    # not SKILL.md's separate prose mentions of the same phases, so this check exists to
    # close that gap.
    workflows_dir = SKILL_DIR / "workflows"
    if not workflows_dir.exists():
        return True, "no workflows/ directory (skip)"
    phase_numbers = set()
    for wf in sorted(workflows_dir.glob("*.md")):
        text = wf.read_text(encoding="utf-8")
        phase_numbers |= {int(n) for n in re.findall(r"^##+ Phase (\d+):", text, re.MULTILINE)}
    if not phase_numbers:
        return True, "no Phase N headers found in workflows/ (skip)"
    max_phase = max(phase_numbers)
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    body = text[header_end:]
    # A "Phase N" mention describing a *different* skill's own numbering (e.g.
    # "Downstream's own Phase 5 ... a separate, later Phase 11 (Grading)") is not a
    # stale self-reference -- skip any match whose containing sentence (bounded by the
    # nearest '.' before it) mentions "downstream", the one other lifecycle pipeline
    # this file cross-references by phase number.
    out_of_range = set()
    for m in re.finditer(r"\bPhase (\d+)\b", body):
        n = int(m.group(1))
        if 1 <= n <= max_phase:
            continue
        sentence_start = body.rfind(".", 0, m.start()) + 1
        sentence = body[sentence_start : m.end()]
        if "downstream" in sentence.lower():
            continue
        out_of_range.add(n)
    out_of_range = sorted(out_of_range)
    if out_of_range:
        return (
            False,
            "SKILL.md references Phase number(s) outside the workflow's actual "
            f"1-{max_phase} range: {out_of_range}",
        )
    return (
        True,
        "every 'Phase N' mention in SKILL.md falls within the workflow's actual "
        f"1-{max_phase} range",
    )


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_phase_sequence,
    check_skillmd_phase_range,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

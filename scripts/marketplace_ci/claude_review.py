"""The advisory Claude delta review (docs/ci-claude-review-user-requirements.md, "Claude R<n>").

Three steps of `.github/workflows/claude-review-ci.yml`, each run from code restored from the base
SHA in a job that holds no API key: the settings check (R8, R10), the reviewer prompts (R5), and
the publisher that posts the findings and decides the check (R6, R7). The job that holds the key
runs none of this; it only passes the prompts to claude-code-action and records what came back.
"""

from __future__ import annotations

import json
import math
import re
import subprocess  # nosec B404  # list-form git and gh calls only, no shell (docs/ci.md)
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_TIMEOUT_MS = 1_200_000
# The review job's own timeout-minutes (a job limit cannot read a step output): both passes at
# the full per-pass value plus the checkout, the action's setup and the artifact upload.
REVIEW_JOB_TIMEOUT_MINUTES = 50
REVIEW_JOB_OVERHEAD_MINUTES = 10
_MODEL = re.compile(r"[A-Za-z0-9._-]{1,64}")
_TIMEOUT = re.compile(r"[1-9][0-9]{0,8}")

SEVERITIES = ("Critical", "Major", "Minor", "Informational")
BLOCKING = frozenset({"Critical", "Major"})
VERDICTS = ("LGTM", "Changes Requested")
# 30 findings of at most 2000 + 300 + 200 characters keep a pass's structured output well under
# Linux's 128 KiB limit on one environment string (the record step reads it from one).
MAX_FINDINGS = 30
MAX_TITLE = 200
MAX_BODY = 2000
MAX_PATH = 300
# GitHub refuses a comment body over 65536 characters; the summary stays well under it.
MAX_SUMMARY = 60_000
SUMMARY_MARKER = "<!-- claude-delta-review:summary -->"
SUMMARY_AUTHOR = "github-actions[bot]"


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    switched_off: bool
    model: str
    pass_minutes: int


def review_settings(bypass: str, model: str, timeout_ms: str) -> Settings:
    """R10's kill switch first (a review that is off needs no model), then R8's model and
    per-pass timeout. Raises SettingsError with the message the check fails with."""
    if bypass == "1":
        return Settings(True, "", 0)
    if bypass not in ("", "0"):
        raise SettingsError(
            f"CLAUDE_CI_REVIEW_BYPASS must be 1 (review off), 0 or unset, not {bypass!r}"
        )
    model = model or DEFAULT_MODEL
    if not _MODEL.fullmatch(model):
        raise SettingsError(
            "CLAUDE_KIT_REVIEW_MODEL must match ^[A-Za-z0-9._-]{1,64}$ (or be unset for "
            f"{DEFAULT_MODEL})"
        )
    raw = timeout_ms or str(DEFAULT_TIMEOUT_MS)
    if not _TIMEOUT.fullmatch(raw):
        raise SettingsError(
            "CLAUDE_KIT_REVIEW_TIMEOUT_MS must be a positive whole number of milliseconds"
        )
    minutes = math.ceil(int(raw) / 60_000)
    if 2 * minutes + REVIEW_JOB_OVERHEAD_MINUTES > REVIEW_JOB_TIMEOUT_MINUTES:
        most = (REVIEW_JOB_TIMEOUT_MINUTES - REVIEW_JOB_OVERHEAD_MINUTES) // 2 * 60_000
        raise SettingsError(
            f"CLAUDE_KIT_REVIEW_TIMEOUT_MS={raw} does not fit the review job's "
            f"{REVIEW_JOB_TIMEOUT_MINUTES}-minute limit for two passes (at most {most})"
        )
    return Settings(False, model, minutes)


_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


def build_prompt(template: str, values: Mapping[str, str]) -> str:
    """`template` with each `{{NAME}}` replaced in one pass, so text a value brings along
    (a PR-chosen file name, say) is never substituted again. An unknown name is an error."""

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise KeyError(f"prompt template names an unknown value {{{{{name}}}}}")
        return values[name]

    return _PLACEHOLDER.sub(fill, template)


def prompt_values(
    scope: Mapping, review_md: str, security_md: str, review_name: str, base_sha: str, head_sha: str
) -> dict[str, str]:
    paths = [e["path"] for e in scope["paths"] if e.get("status") != "D"]
    deleted = [e["path"] for e in scope["paths"] if e.get("status") == "D"]
    return {
        "PASS": review_name,
        "BASE_SHA": base_sha,
        "HEAD_SHA": head_sha,
        "ANCHOR_SHA": scope.get("anchor_sha") or "none",
        "PATHS": json.dumps(paths, indent=2),
        "DELETED_PATHS": json.dumps(deleted, indent=2),
        "REVIEW_MD": review_md,
        "SECURITY_REVIEWER_MD": security_md if review_name == "security" else "",
    }


# R5: the review job places the patch here, inside the checkout (Claude may read nothing outside
# it), after the checkout, so no pull request file can stand in for it. prompt.md names this path.
PATCH_PATH = ".claude-review-input/delta.diff"
# A bound on what one pass may be asked to read; the rest is named, not silently dropped.
MAX_PATCH_BYTES = 1_000_000


def review_patch(repo: Path, scope: Mapping, base_sha: str, head_sha: str) -> str:
    """The pull request's own change to the reviewed paths (R5): from the merge base with the base
    commit to the head, both sides of a rename, deleted content included. External diff drivers and
    textconv are off, so a pull-request `.gitattributes` cannot change what is shown. Raises
    subprocess.CalledProcessError when git fails."""
    paths = sorted({p for e in scope["paths"] for p in (e["path"], e.get("old_path")) if p})
    if not paths:
        return ""
    merge_base = subprocess.run(  # nosec B603 B607  # literal git subcommand, no shell
        ["git", "merge-base", base_sha, head_sha],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()  # fmt: skip
    raw = subprocess.run(  # nosec B603 B607  # literal git subcommand, no shell
        ["git", "diff", "--no-renames", "--text", "--no-ext-diff", "--no-textconv", "--no-color",
         merge_base, head_sha, "--", *(f":(literal){p}" for p in paths)],
        cwd=repo, capture_output=True, check=True,
    ).stdout  # fmt: skip
    if len(raw) <= MAX_PATCH_BYTES:
        return raw.decode("utf-8", errors="replace")
    kept = raw[:MAX_PATCH_BYTES].decode("utf-8", errors="ignore")
    return kept + (
        f"\n[patch truncated: {len(raw) - MAX_PATCH_BYTES} more bytes; read the files themselves]\n"
    )


def needs_security_pass(scope: Mapping) -> bool:
    """R5: a second pass when the reviewed delta contains a gate-critical path."""
    return any(e.get("gate_critical") for e in scope["paths"])


class InvalidReview(ValueError):
    pass


def _clean_text(text: str, limit: int) -> str:
    """Model-written text the publisher posts: bounded, no HTML entity (which could spell a
    mention or a comment), no hidden HTML comment (which could forge the summary marker or hide
    the rest of the summary), and no @-mention (which could summon a bot or a person)."""
    text = text[:limit].replace("&", "&amp;").replace("<!--", "&lt;!--")
    return text.replace("@", "@\N{ZERO WIDTH SPACE}")


def _display_path(path: str) -> str:
    """A path as the summary shows it inside a code span: no backtick (which would end the
    span), no control character or line break, bounded."""
    text = "".join(c if c.isprintable() else " " for c in path[:MAX_PATH]).replace("`", "'")
    return _clean_text(text, MAX_PATH)


def _redact_secrets(text: str) -> str:
    """Text with anything shaped like a credential (the shared token shapes, `sk-ant-` keys
    included) replaced by [REDACTED]. Redacted rather than refused: a reviewed test fixture
    holds such shapes, and refusing would let a PR switch the advisory review off. The exact
    API key is refused instead, by the record step and parse_pass."""
    from scripts.marketplace_ci.review import _redact_tokens

    return _redact_tokens(text)


def parse_pass(record: Mapping, reviewed: frozenset[str]) -> tuple[str, list[dict]]:
    """One pass's verdict and findings from its recorded structured output. Raises InvalidReview
    when the pass did not complete, hit a cap, or returned something other than the schema."""
    if record.get("outcome") != "success":
        raise InvalidReview(
            f"the {record.get('pass')} pass did not complete ({record.get('outcome')})"
        )
    result = record.get("result")
    if not isinstance(result, dict) or result.get("subtype") != "success" or result.get("is_error"):
        subtype = result.get("subtype") if isinstance(result, dict) else None
        raise InvalidReview(f"the {record.get('pass')} pass stopped early ({subtype})")
    if record.get("secret_found"):
        raise InvalidReview(f"the {record.get('pass')} pass returned the API key; nothing posted")
    try:
        output = json.loads(record.get("structured_output") or "")
    except ValueError as exc:
        raise InvalidReview(f"the {record.get('pass')} pass returned no valid JSON") from exc
    if not isinstance(output, dict) or output.get("verdict") not in VERDICTS:
        raise InvalidReview(f"the {record.get('pass')} pass returned no valid verdict")
    raw_findings = output.get("findings")
    if not isinstance(raw_findings, list) or len(raw_findings) > MAX_FINDINGS:
        raise InvalidReview(f"the {record.get('pass')} pass returned an invalid findings list")
    findings = []
    for f in raw_findings:
        if not (
            isinstance(f, dict)
            and f.get("severity") in SEVERITIES
            and isinstance(f.get("path"), str)
            and isinstance(f.get("line"), int)
            and not isinstance(f.get("line"), bool)
            and f["line"] >= 1
            and isinstance(f.get("title"), str)
            and isinstance(f.get("body"), str)
        ):
            raise InvalidReview(f"the {record.get('pass')} pass returned a malformed finding")
        in_scope = f["path"] in reviewed
        findings.append(
            {
                "pass": record.get("pass"),
                "severity": f["severity"],
                # the real path only for a reviewed one, which the inline comment API needs; a
                # path the model made up is never echoed back
                "path": f["path"] if in_scope else "",
                "display_path": (
                    _display_path(_redact_secrets(f["path"]))
                    if in_scope
                    else "(outside the reviewed paths)"
                ),
                "line": f["line"],
                "title": _clean_text(_redact_secrets(" ".join(f["title"].split())), MAX_TITLE),
                "body": _clean_text(_redact_secrets(f["body"]), MAX_BODY),
                # a finding outside the reviewed paths is reported, never posted inline
                "in_scope": in_scope,
            }
        )
    return output["verdict"], findings


def _pass_cost(record: Mapping) -> dict:
    result = record.get("result")
    if not isinstance(result, dict):
        result = {}
    cost = result.get("total_cost_usd")
    turns = result.get("num_turns")
    return {
        "cost_usd": cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
        "turns": turns if isinstance(turns, int) and not isinstance(turns, bool) else None,
    }


def decide(
    *,
    switched_off: bool = False,
    scope: Mapping | None,
    raw: Mapping | None,
    review_job: str,
    model: str,
    head_sha: str,
    run_attempt: str,
) -> dict:
    """The run's result (R6's machine-readable file). `review_job` is the review job's result
    (`success`, `failure`, `cancelled`, `skipped`). Status: `clean`, `findings` (a Critical or
    Major finding in either pass), `could_not_run` or `skipped` (no review happened). Only
    `clean` and `findings` make this run an anchor (R3)."""
    result: dict = {
        "status": "could_not_run",
        "verdict": None,
        "head_sha": head_sha,
        "run_attempt": int(run_attempt),
        "anchor_sha": (scope or {}).get("anchor_sha", ""),
        "anchor_status": (scope or {}).get("anchor_status", ""),
        "reviewed_paths": [e["path"] for e in (scope or {}).get("paths", [])],
        "model": model,
        "security_review": False,
        "passes": {},
        "findings": [],
        "reason": "",
    }
    if switched_off:
        result.update(status="skipped", reason="switched off (CLAUDE_CI_REVIEW_BYPASS=1)")
        return result
    if scope is None:
        result["reason"] = "the review scope could not be computed"
        return result
    if not scope["paths"]:
        result.update(status="clean", verdict="LGTM", reason="nothing new to review")
        return result
    if review_job != "success" or raw is None:
        result["reason"] = f"the review job did not complete ({review_job})"
        return result
    if raw.get("skipped") == "draft":
        result.update(status="skipped", reason="the pull request became a draft")
        return result
    if raw.get("skipped") == "head_moved":
        result["reason"] = "a newer push landed before the review started"
        return result
    reviewed = frozenset(result["reviewed_paths"])
    expected = ["general", *(["security"] if needs_security_pass(scope) else [])]
    result["security_review"] = "security" in expected
    records = {r.get("pass"): r for r in raw.get("passes", []) if isinstance(r, dict)}
    verdicts = []
    for name in expected:
        record = records.get(name, {"pass": name, "outcome": "missing"})
        result["passes"][name] = _pass_cost(record)
        try:
            verdict, findings = parse_pass(record, reviewed)
        except InvalidReview as exc:
            result["reason"] = str(exc)
            result["findings"] = []
            return result
        verdicts.append(verdict)
        result["findings"].extend(findings)
    blocking = any(f["severity"] in BLOCKING for f in result["findings"])
    result["status"] = "findings" if blocking else "clean"
    result["verdict"] = (
        "Changes Requested" if blocking or "Changes Requested" in verdicts else "LGTM"
    )
    return result


def summary_body(result: Mapping, unplaced: Sequence[Mapping]) -> str:
    def money(p: Mapping) -> str:
        return "n/a" if p.get("cost_usd") is None else f"${p['cost_usd']:.2f}"

    costs = ", ".join(f"{name} {money(p)}" for name, p in result["passes"].items()) or "none"
    lines = [
        SUMMARY_MARKER,
        "## Claude delta review (advisory)",
        "",
        f"- **Status:** {result['status']}"
        + (f" ({result['reason']})" if result["reason"] else ""),
        f"- **Verdict:** {result['verdict'] or 'none'}",
        f"- **Reviewed head:** {result['head_sha']}",
        f"- **Anchor:** {result['anchor_sha'] or 'none (whole PR)'}"
        + (f" ({result['anchor_status']})" if result["anchor_sha"] else ""),
        f"- **Model:** {result['model']}",
        f"- **Security pass:** {'ran' if result['security_review'] else 'not needed'}",
        f"- **Cost:** {costs}",
    ]
    footer = [
        "",
        "Advisory only: this check never blocks a merge. Findings are not carried to later runs.",
    ]
    rows = [
        f"| {f['severity']} | {f['pass']} | `{f['display_path']}:{f['line']}` | "
        + f["title"].replace("|", "\\|")
        + " |"
        for f in result["findings"]
    ]
    extra = [f"- `{f['display_path']}:{f['line']}` {f['title']}" for f in unplaced]
    # Bounded (MAX_SUMMARY): rows are dropped from the end until the body fits, with a note.
    dropped = 0
    while True:
        table = ["", "| Severity | Pass | Location | Finding |", "|---|---|---|---|", *rows]
        unplaced_part = (
            ["", "Critical and Major findings not on a changed line (no inline comment):", *extra]
            if extra
            else []
        )
        note = ["", f"{dropped} more entries are in the result artifact."] if dropped else []
        body = "\n".join(lines + (table if rows else []) + unplaced_part + note + footer) + "\n"
        if len(body) <= MAX_SUMMARY or not (rows or extra):
            return body[:MAX_SUMMARY]
        (rows if rows else extra).pop()
        dropped += 1


Gh = Callable[[Sequence[str], dict | None], subprocess.CompletedProcess]


def _gh(args: Sequence[str], payload: dict | None = None) -> subprocess.CompletedProcess:
    """`gh api` with an optional JSON body passed through a file, never through the command."""
    if payload is None:
        return subprocess.run(  # nosec B603 B607  # literal gh subcommand, no shell
            ["gh", "api", *args], capture_output=True, text=True
        )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f)
        body = f.name
    try:
        return subprocess.run(  # nosec B603 B607  # literal gh subcommand, body via a file
            ["gh", "api", *args, "--input", body], capture_output=True, text=True
        )
    finally:
        Path(body).unlink(missing_ok=True)


def publish(result: Mapping, *, repo: str, pr_number: int, gh: Gh = _gh) -> list[str]:
    """Posts the Critical and Major findings inline and creates or updates the one summary
    comment (R6). Returns warnings; a failed post never changes the result."""
    warnings: list[str] = []
    unplaced = []
    for f in result["findings"]:
        if f["severity"] not in BLOCKING:
            continue
        if not f["in_scope"]:
            unplaced.append(f)
            continue
        body = f"**{f['severity']}** ({f['pass']} pass): {f['title']}\n\n{f['body']}"
        posted = gh(
            ["-X", "POST", f"repos/{repo}/pulls/{pr_number}/comments"],
            {"body": body, "commit_id": result["head_sha"], "path": f["path"],
             "line": f["line"], "side": "RIGHT"},
        )  # fmt: skip
        if posted.returncode != 0:
            unplaced.append(f)
    body = summary_body(result, unplaced)
    found = gh(
        ["--paginate", f"repos/{repo}/issues/{pr_number}/comments", "--jq",
         f'.[] | select(.user.login == "{SUMMARY_AUTHOR}" and '
         f'(.body | startswith("{SUMMARY_MARKER}"))) | .id'],
        None,
    )  # fmt: skip
    ids = [line for line in found.stdout.split() if line.isdigit()] if found.returncode == 0 else []
    if found.returncode != 0:
        warnings.append("could not list the pull request's comments; posting a new summary")
    if ids:
        done = gh(["-X", "PATCH", f"repos/{repo}/issues/comments/{ids[0]}"], {"body": body})
    else:
        done = gh(["-X", "POST", f"repos/{repo}/issues/{pr_number}/comments"], {"body": body})
    if done.returncode != 0:
        warnings.append("could not post the summary comment")
    return warnings

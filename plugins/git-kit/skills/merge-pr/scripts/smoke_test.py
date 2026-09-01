#!/usr/bin/env python3
"""Persisted smoke test for merge-pr: frontmatter validity, referenced-file
existence, Bash-scope grant usage, step-header sequencing, step 7's
remote-branch-deletion verification fallback, step 5's unconditional
worktree branch-delete note, step 2's four-state CI classification,
step 2's required no-merge-conflicts and not-behind-base gates plus its
advisory mergeStateStatus/unresolved-review-thread disclosures, step 3's
and references/merge-rights-check.md's shared reuse of step 1's resolved
{owner}/{repo} (never a fresh gh repo view), step 2's no-merge-conflicts
local-reproduction guidance before pointing at resolving-merge-conflicts
(including its isCrossRepository fork-PR branch), step 2's not-behind-base
fork-PR handling via mergeStateStatus rather than an unconditional pass,
and step 7(a)/(c)/(d)'s rebase pre-check / squash disclosure / rejection
fallback -- structural checks only, since this is a conversational,
AskUserQuestion-driven skill with no executable logic of its own to
simulate."""

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
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = r"`(references/[\w.-]+\.md)`"
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def _grant_pattern(cmd: str) -> str:
    # Boundary-safe on both ends so a short/common token ("gh", "diff") can't false-match
    # inside an unrelated word ("through", "different") -- (?<!\w)/(?!\w) rather than \b,
    # since \b requires an actual word/non-word *transition* and would wrongly reject a
    # genuine match starting with a non-word character preceded by another non-word
    # character (e.g. `${CLAUDE_PLUGIN_ROOT}/...` preceded by a backtick in prose -- both
    # non-word, so \b never fires there even though the match is real). Built from the full
    # grant phrase, not just its first word, so distinct sibling commands sharing a first
    # word (e.g. "gh pr view" vs "gh pr merge") aren't conflated -- and wildcard-aware
    # (splits on "*" and rejoins with "[^\s]*") so a grant like
    # "gh api repos/*/collaborators/*/permission" matches the real
    # "gh api repos/{owner}/{repo}/collaborators/{username}/permission" invocation.
    return r"(?<!\w)" + r"[^\s]*".join(re.escape(part) for part in cmd.split("*")) + r"(?!\w)"


def _collect_search_text(body: str) -> str:
    # Search body plus references/ and scripts/ -- a grant's only real invocation can live
    # in a reference file (e.g. references/merge-rights-check.md), not SKILL.md's own body.
    search_text = body
    for sub in ("references", "scripts"):
        d = SKILL_DIR / sub
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    try:
                        search_text += "\n" + f.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        pass
    return search_text


def check_bash_grants():
    fm_text = SKILL_MD.read_text(encoding="utf-8")
    header_end = fm_text.find("\n---\n", 4) + 5
    frontmatter = fm_text[:header_end]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.*/${} -]+?)(?::|\))", fm_line_match.group(1))
    granted_cmds = [c.lstrip("*/") for c in granted_cmds]

    body = fm_text[header_end:]
    search_text = _collect_search_text(body)
    unused = [cmd for cmd in granted_cmds if not re.search(_grant_pattern(cmd), search_text)]
    if unused:
        return False, (
            "Bash grant(s) never invoked anywhere in the skill's own body/references/scripts: "
            + ", ".join(sorted(set(unused)))
        )
    return True, "every granted Bash command is invoked somewhere in the skill's own files"


def check_step_sequence():
    # Scoped to the "## Instructions" section only -- other sections (e.g. "Testing &
    # Validation") legitimately restart their own numbered lists for unrelated scenarios,
    # which a whole-file scan would wrongly flag as non-sequential.
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return True, "no '## Instructions' section found (skip)"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. \*\*", section, re.MULTILINE)]
    if not numbers:
        return True, "no numbered steps found (skip)"
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        return False, f"step numbering not sequential: found {numbers}, expected {expected}"
    return True, "step headers sequential"


def _get_step_text(number):
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return None
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    step_start = re.search(rf"^{number}\. \*\*", section, re.MULTILINE)
    if not step_start:
        return None
    next_step = re.search(r"^\d+\. \*\*\b", section[step_start.end() :], re.MULTILINE)
    step_end = step_start.end() + next_step.start() if next_step else len(section)
    return section[step_start.start() : step_end]


def check_step7_remote_delete_fallback():
    step7 = _get_step_text(7)
    if step7 is None:
        return False, "step 7 ('## Instructions') not found"
    if "git ls-remote --heads origin" not in step7:
        return (
            False,
            "step 7 doesn't verify remote branch deletion with git ls-remote --heads origin",
        )
    if "gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>" not in step7:
        return (
            False,
            "step 7's ls-remote fallback doesn't complete deletion via the documented gh api path",
        )
    if "finishing-work" not in step7 or "1.5" not in step7:
        return (
            False,
            "step 7 doesn't cite finishing-work step 1.5 as the origin of this fallback (R20)",
        )
    return (
        True,
        "step 7 verifies remote branch deletion, falls back to gh api DELETE (finishing-work 1.5)",
    )


def check_step7_skips_delete_fallback_for_fork_prs():
    step1 = _get_step_text(1)
    step7 = _get_step_text(7)
    if step1 is None or step7 is None:
        return False, "step 1 or step 7 ('## Instructions') not found"
    if "isCrossRepository" not in step1:
        return False, "step 1 doesn't resolve isCrossRepository via gh pr view"
    if "isCrossRepository" not in step7:
        return (
            False,
            "step 7's remote-branch-deletion fallback doesn't gate on isCrossRepository "
            "-- a fork PR's branch could be misread as living in this repo",
        )
    return True, "step 7's remote-branch-deletion fallback is gated on isCrossRepository"


def check_headrefname_validated_before_first_use():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Instructions\n")
    if start == -1:
        return False, "'## Instructions' section not found"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    validation_pos = section.find(r"^[A-Za-z0-9._/@+=-]+$")
    if validation_pos == -1:
        return False, "headRefName regex validation string not found anywhere in Instructions"
    first_use_pos = section.find("git ls-remote --heads origin")
    if first_use_pos == -1:
        return False, "git ls-remote --heads origin not found anywhere in Instructions"
    if validation_pos > first_use_pos:
        return (
            False,
            "headRefName validation appears AFTER its first use (git ls-remote) -- validate at "
            "the source (step 1) before any use, not just before the later DELETE call",
        )
    return True, "headRefName is validated before its first shell interpolation (git ls-remote)"


def check_step7_verification_not_gated_on_exit_code():
    step7 = _get_step_text(7)
    if step7 is None:
        return False, "step 7 ('## Instructions') not found"
    verify_pos = step7.find("git ls-remote --heads origin")
    if verify_pos == -1:
        return (
            False,
            "step 7 doesn't verify remote branch deletion with git ls-remote --heads origin",
        )
    exit_code_pos = step7.find("Regardless of this command's exit code")
    if exit_code_pos == -1:
        return (
            False,
            "step 7 doesn't state its state check runs regardless of the merge command's exit "
            "code -- a prior version of this text nested the whole verification inside the "
            "non-zero-exit case, silently skipping it on a normal (exit 0) merge",
        )
    if exit_code_pos > verify_pos:
        return (
            False,
            "step 7's 'regardless of exit code' framing appears AFTER the git ls-remote check "
            "-- it must precede it so the verification isn't read as conditional on a prior branch",
        )
    return True, "step 7's remote-branch-deletion verification is explicitly exit-code-independent"


def check_step5_worktree_note():
    step5 = _get_step_text(5)
    if step5 is None:
        return False, "step 5 ('## Instructions') not found"
    if "already used by worktree" not in step5:
        return False, "step 5 doesn't note the possible worktree branch-delete git error"
    if "merge_auto_delete_branch" in step5:
        return (
            False,
            "step 5's worktree note looks gated on merge_auto_delete_branch (unread until step 6)",
        )
    return True, "step 5's worktree branch-delete note is present and unconditional"


def check_step2_four_state_classification():
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    for state in ("**passing**", "**failing**", "**pending**", "**missing**"):
        if state not in step2:
            return (
                False,
                f"step 2 no longer documents the {state.strip('*')!r} classification state",
            )
    if "not the same as **pending**" not in step2:
        return False, "step 2 no longer explicitly distinguishes missing from pending"
    return (
        True,
        "step 2 documents all four classification states and distinguishes missing from pending",
    )


def check_step7_rebase_precheck():
    step7 = _get_step_text(7)
    if step7 is None:
        return False, "step 7 ('## Instructions') not found"
    if "Rebase-compatibility pre-check" not in step7:
        return False, "step 7 no longer documents the rebase-compatibility pre-check"
    # Bound to sub-step (a)'s own text only -- up to the next lettered sub-step ("   b. **") --
    # so a regression that drops (a)'s own AskUserQuestion gate can't be masked by (c)/(d) still
    # mentioning AskUserQuestion later in step 7.
    precheck_pos = step7.find("Rebase-compatibility pre-check")
    next_substep = re.search(r"^   [a-e]\. \*\*", step7[precheck_pos:], re.MULTILINE)
    substep_end = precheck_pos + next_substep.start() if next_substep else len(step7)
    substep_a = step7[precheck_pos:substep_end]
    if "parents | length" not in substep_a:
        return False, "step 7(a) no longer counts merge commits via parent count"
    if "AskUserQuestion" not in substep_a:
        return (
            False,
            "step 7(a) no longer asks via AskUserQuestion before proceeding",
        )
    return (
        True,
        "step 7(a) documents the rebase-compatibility pre-check with a merge-commit "
        "count and an AskUserQuestion gate",
    )


def check_step7_squash_disclosure():
    step7 = _get_step_text(7)
    if step7 is None:
        return False, "step 7 ('## Instructions') not found"
    if "Squash tradeoff, named explicitly" not in step7:
        return False, "step 7 no longer documents the squash-tradeoff disclosure"
    if "apply (c)'s disclosure before running this command" not in step7:
        return (
            False,
            "step 7(b) no longer forward-references (c)'s disclosure for the "
            "already-configured-SQUASH path",
        )
    if "was already `SQUASH`" not in step7:
        return (
            False,
            "step 7(c) no longer states the disclosure fires even when SQUASH "
            "was already configured",
        )
    return (
        True,
        "step 7(c)'s squash-tradeoff disclosure is documented and forward-referenced from 7(b)",
    )


def check_step7b_final_recheck_before_merge():
    # Devin's review of PR #269 (2026-08-31): step 5's confirmation is a human AskUserQuestion of
    # unknown duration, but nothing rechecked readiness between step 2 last passing and the actual
    # gh pr merge call on the normal (non-bypass, non-retry) path -- only step 4(e)'s bypass rerun
    # and step 7(d)'s rejection-fallback retry rechecked, never the first attempt itself.
    step7 = _get_step_text(7)
    if step7 is None:
        return False, "step 7 ('## Instructions') not found"
    if "Final recheck, marker, and merge command" not in step7:
        return (
            False,
            "step 7(b) no longer documents a final readiness recheck before the marker/merge "
            "command -- Devin's PR #269 finding may have regressed",
        )
    if "applies on every path, not just the rejection-fallback retry" not in step7:
        return (
            False,
            "step 7(b)'s final recheck no longer states it applies unconditionally, not just to "
            "the step 7(d) retry path",
        )
    if "do not write the marker or attempt to merge" not in step7:
        return (
            False,
            "step 7(b)'s final recheck no longer states a failure stops before writing the marker "
            "or attempting to merge",
        )
    return (
        True,
        "step 7(b) documents an unconditional final readiness recheck immediately before the "
        "marker/merge command, covering the normal path Devin's PR #269 review found uncovered",
    )


def check_bypass_exception_single_use():
    # Codex's review of PR #269 (2026-08-31): step 2's bypass exception is keyed only on whether
    # --bypass-codex-review was given in $ARGUMENTS, with no state tracking of whether a genuine
    # pass has already been achieved. Every rerun of "the full step-2 readiness check" (4(e), 7(b),
    # 7(d)) must explicitly suppress the exception -- otherwise a new, never-attested commit landing
    # during step 5's wait or steps 6-7(a) could silently ride through on a stale/spent bypass.
    step2 = _get_step_text(2)
    step4 = _get_step_text(4)
    step7 = _get_step_text(7)
    if step2 is None or step4 is None or step7 is None:
        return False, "step 2, 4, or 7 ('## Instructions') not found"
    if "applies only the first time step 2 runs within a single invocation" not in step2:
        return (
            False,
            "step 2's bypass exception no longer states it applies only on the first pass -- a "
            "rerun could silently re-grant an already-spent bypass to a changed head",
        )
    if "without step 2's own bypass exception this time" not in step4:
        return (
            False,
            "step 4(e)'s rerun no longer explicitly suppresses step 2's bypass exception",
        )
    if step7.count("without step 2's own bypass exception") < 2:
        return (
            False,
            "step 7(b)'s final recheck and/or step 7(d)'s rejection-fallback recheck no longer "
            "explicitly suppress step 2's bypass exception (expected both to state this)",
        )
    return (
        True,
        "step 2's bypass exception is documented as single-use per invocation, and every rerun "
        "(4(e), 7(b), 7(d)) explicitly suppresses it rather than silently re-applying it",
    )


def check_step2_rerun_enumeration_includes_7b():
    # security-reviewer finding, PR #269, 2026-08-31 (Critical): step 7(b) was added as an
    # unconditional pre-merge recheck this same session, but step 2's own "when this step is
    # being re-run, first re-fetch fresh data" trigger only named step 4(e) and step 7(d) --
    # leaving 7(b)'s recheck silently reclassifying step 1's stale snapshot instead of
    # re-fetching, which would have made both step 7(b)'s own purpose and the bypass-exception
    # fix (check_bypass_exception_single_use) no-ops on the normal (non-bypass, non-retry) path.
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    rerun_intro = step2.split("first re-fetch fresh data")[0]
    if "step 7(b)" not in rerun_intro:
        return (
            False,
            "step 2's 'when this step is being re-run' enumeration no longer names step "
            "7(b) -- its final recheck would silently reclassify step 1's stale snapshot "
            "instead of re-fetching",
        )
    return (
        True,
        "step 2's rerun enumeration names step 4(e), step 7(b), and step 7(d) -- every rerun point "
        "re-fetches fresh data before reclassifying",
    )


def check_bypass_poll_uses_started_at_baseline():
    # security-reviewer finding M1, PR #269, 2026-08-31 (Major): polling gh pr checks for "terminal
    # state" alone can't tell the pre-label run's already-terminal FAILURE apart from the
    # label-triggered re-run -- the bypass path is only entered when Publish Codex policy result is
    # already non-passing, so an unqualified terminal-state poll returns immediately on the stale
    # result and wrongly reports the bypass as failed before the real re-run even starts.
    step4 = _get_step_text(4)
    if step4 is None:
        return False, "step 4 ('## Instructions') not found"
    if "Capture the pre-label baseline" not in step4:
        return (
            False,
            "step 4(c) no longer captures a pre-label startedAt baseline for Publish Codex policy "
            "result before applying the label",
        )
    if "startedAt" not in step4 or "strictly later than" not in step4:
        return (
            False,
            "step 4(d)'s poll no longer requires a startedAt strictly later than (c)'s baseline -- "
            "it could accept the pre-label run's own already-terminal result",
        )
    if "bucket" not in step4:
        return False, "step 4(d)'s poll no longer classifies via the bucket field (pass/fail)"
    if "bound is exhausted" not in step4:
        return False, "step 4(d)'s poll is no longer bounded to a fixed number of attempts"
    return (
        True,
        "step 4(c) captures a pre-label startedAt baseline and step 4(d)'s poll requires a "
        "strictly-later startedAt plus a terminal bucket, bounded, before accepting the result",
    )


def check_merge_binds_to_verified_head_sha():
    # security-reviewer finding M2, PR #269, 2026-08-31 (Major): gh pr merge was never bound to
    # the exact SHA the immediately-preceding recheck validated -- a push landing between the
    # recheck and the merge call itself would still be merged unverified, the same TOCTOU gap
    # the recheck exists to close.
    step2 = _get_step_text(2)
    step7 = _get_step_text(7)
    if step2 is None or step7 is None:
        return False, "step 2 or step 7 ('## Instructions') not found"
    if "headRefOid" not in step2:
        return (
            False,
            "step 2's rerun re-fetch no longer includes headRefOid -- step 7(b)/(d) have no "
            "verified SHA to bind the merge command to",
        )
    if step7.count("--match-head-commit") < 2:
        return (
            False,
            "step 7(b) and/or step 7(d) no longer pass --match-head-commit to gh pr merge -- the "
            "merge is no longer bound to the SHA the immediately-preceding recheck just validated",
        )
    return (
        True,
        "step 2's rerun re-fetch includes headRefOid, and both step 7(b) and step 7(d) bind their "
        "gh pr merge call to it via --match-head-commit",
    )


def check_step7_rejection_fallback():
    step7 = _get_step_text(7)
    if step7 is None:
        return False, "step 7 ('## Instructions') not found"
    if "Rejection fallback" not in step7:
        return False, "step 7 no longer documents the rejection fallback"
    if "never silently retry with a different flag" not in step7:
        return False, "step 7(d) no longer states it never silently retries with a different flag"
    if "re-run the full step-2 readiness check" not in step7:
        return False, "step 7(d) no longer re-runs the full step-2 readiness check before retrying"
    if (
        "write the marker again" not in step7
        or "gh-pr-merge merge-pr" not in step7.split("Rejection fallback")[1]
    ):
        return False, (
            "step 7(d) no longer rewrites the git-kit marker before retrying -- the guard hook "
            "consumes (b)'s marker on the first (failed) merge attempt, so a retry with no fresh "
            "marker is silently blocked"
        )
    return (
        True,
        "step 7(d)'s rejection fallback documents asking before retry, re-running the full step-2 "
        "check, and rewriting the marker before the retry itself",
    )


def check_step1_owner_repo_from_pr_url():
    step1 = _get_step_text(1)
    step2 = _get_step_text(2)
    if step1 is None or step2 is None:
        return False, "step 1 or step 2 ('## Instructions') not found"
    if "url" not in step1 or "Derive `{owner}/{repo}`" not in step1:
        return (
            False,
            "step 1 no longer derives {owner}/{repo} from the PR's own url field",
        )
    if "gh repo view --json owner,name" in step2:
        return (
            False,
            "step 2's branch-protection call resolves {owner}/{repo} via a fresh gh repo view "
            "again -- this defaults to the current checkout's own repo and is wrong whenever "
            "$ARGUMENTS names a PR in a different repository",
        )
    if "resolved `url` field" not in step2:
        return (
            False,
            "step 2's branch-protection call doesn't state it reuses step 1's resolved url-derived "
            "{owner}/{repo}",
        )
    return (
        True,
        "step 1 derives {owner}/{repo} from the PR's own url field; step 2's branch-protection "
        "call reuses that value instead of a fresh gh repo view",
    )


def check_step3_and_merge_rights_reuse_owner_repo():
    # skill-reviewer M1 (2026-08-31): references/merge-rights-check.md's Tier 1/Tier 3
    # independently re-derived {owner}/{repo} via a fresh `gh repo view`, the exact bug
    # step 1/step 2 already guard against -- wrong whenever the merge-rights check runs
    # against a PR in a different repository than the current checkout.
    step3 = _get_step_text(3)
    if step3 is None:
        return False, "step 3 ('## Instructions') not found"
    if "step 1's already-resolved `{owner}/{repo}`" not in step3:
        return (
            False,
            "step 3 no longer states it passes step 1's resolved {owner}/{repo} into "
            "references/merge-rights-check.md",
        )
    rights_path = SKILL_DIR / "references" / "merge-rights-check.md"
    if not rights_path.exists():
        return False, "references/merge-rights-check.md does not exist"
    rights_text = rights_path.read_text(encoding="utf-8")
    # Only an actual invocation (inside a fenced code block) is banned -- explanatory prose
    # naming "gh repo view" as the thing NOT to do (mirroring SKILL.md step 1's own
    # explanation) legitimately mentions the string outside a code fence and must not
    # false-match. Match any fence info string (bash, sh, shell, or none) -- CodeRabbit
    # (PR #269) found the original (?:bash)? form let a `sh`/`shell` fence bypass this check
    # entirely, since it simply never matched into code_blocks at all.
    code_blocks = re.findall(r"```[^\n]*\n(.*?)```", rights_text, re.DOTALL)
    if any("gh repo view" in block for block in code_blocks):
        return (
            False,
            "references/merge-rights-check.md still invokes gh repo view in a code block -- this "
            "re-derives {owner}/{repo} against the current checkout's own repo instead of "
            "reusing step 1's resolved value (skill-reviewer M1)",
        )
    if "step 1's resolved value" not in rights_text:
        return (
            False,
            "references/merge-rights-check.md no longer states it reuses step 1's resolved "
            "{owner}/{repo} value",
        )
    return (
        True,
        "step 3 and references/merge-rights-check.md both reuse step 1's resolved {owner}/{repo}, "
        "never a fresh gh repo view",
    )


def check_step2_no_merge_conflicts_fork_branching():
    # cross-model-review (2026-08-31): both reviewers independently found the reproduction
    # guidance assumed headRefName is fetchable from origin, which fails for a fork PR --
    # isCrossRepository must branch the guidance, using GitHub's synthetic pull/<number>/head ref
    # for forks. Round 3's own Phase 2 found the same guidance also assumed bare `origin` was the
    # PR's own repo at all, which is false whenever $ARGUMENTS names a PR in a different repository
    # than the current checkout -- fixed to always fetch from an explicit {owner}/{repo} URL.
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "https://github.com/{owner}/{repo}.git" not in step2:
        return (
            False,
            "step 2's no-merge-conflicts reproduction guidance no longer fetches from an explicit "
            "{owner}/{repo} URL -- a bare `origin` only happens to be correct when the current "
            "checkout is of the PR's own repository (cross-model-review finding, round 3)",
        )
    if "pull/<number>/head:pr-<number>-head" not in step2:
        return (
            False,
            "step 2's no-merge-conflicts fork-PR reproduction path no longer names GitHub's "
            "synthetic pull/<number>/head ref",
        )
    if "pr-<number>-head" not in step2 or "pr-<number>-base" not in step2:
        return (
            False,
            "step 2's no-merge-conflicts reproduction guidance no longer uses <number>-suffixed "
            "local branch names -- a fixed pr-head/pr-base name risks colliding with a branch the "
            "user already has locally (Devin's PR #269 finding)",
        )
    return (
        True,
        "step 2's no-merge-conflicts reproduction guidance branches on isCrossRepository, always "
        "fetches from an explicit {owner}/{repo} URL, uses GitHub's synthetic pull/<number>/head "
        "ref for fork PRs, and uses <number>-suffixed local branch names to avoid collisions",
    )


def check_step2_no_merge_conflicts_reproduction_steps():
    # skill-reviewer M2 (2026-08-31): the no-merge-conflicts stop message pointed bare at
    # resolving-merge-conflicts, whose own precondition (git status showing unmerged paths) a
    # remote-only `mergeable: CONFLICTING` signal doesn't produce.
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "never fetches or merges locally itself" not in step2:
        return (
            False,
            "step 2's no-merge-conflicts check no longer states it only detects the conflict "
            "remotely and never fetches/merges locally itself",
        )
    if "git merge pr-<number>-base" not in step2:
        return (
            False,
            "step 2's no-merge-conflicts check no longer tells the user how to reproduce the "
            "conflict locally before resolving-merge-conflicts applies (skill-reviewer M2)",
        )
    return (
        True,
        "step 2's no-merge-conflicts check tells the user how to reproduce the conflict locally "
        "before pointing at resolving-merge-conflicts",
    )


def check_step2_refetch_on_rerun():
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "When this step is being re-run" not in step2:
        return (
            False,
            "step 2 no longer documents that a re-run (from step 4(e)/7(d)) must re-fetch fresh "
            "PR data instead of reclassifying step 1's original, now-stale fetch",
        )
    if "gh pr view $ARGUMENTS --json isDraft,reviews,statusCheckRollup" not in step2:
        return (
            False,
            "step 2's re-run path no longer names the exact re-fetch command",
        )
    return (
        True,
        "step 2 documents re-fetching fresh PR data before reclassifying on a re-run "
        "(step 4(e)/7(d))",
    )


def check_step2_rerun_refetches_ref_fields():
    # cross-model-review (2026-08-31, round 3): the rerun re-fetch omitted
    # headRefName/baseRefName/isCrossRepository -- a base-branch retarget mid-run would leave the
    # branch-protection lookup and not-behind-base check silently validating against a stale base.
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "mergeStateStatus,headRefName,baseRefName,isCrossRepository" not in step2:
        return (
            False,
            "step 2's rerun re-fetch no longer requests headRefName/baseRefName/isCrossRepository "
            "-- a base-branch retarget mid-run would go undetected on a recheck "
            "(cross-model-review finding)",
        )
    if "re-validate the refreshed" not in step2:
        return (
            False,
            "step 2's rerun re-fetch no longer re-validates the refreshed headRefName/baseRefName "
            "against the ref-name allowlist before using them",
        )
    return (
        True,
        "step 2's rerun re-fetch refreshes and re-validates "
        "headRefName/baseRefName/isCrossRepository, not just the readiness-check fields",
    )


def check_step2_not_behind_base_required():
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "Not behind base" not in step2:
        return False, "step 2 no longer documents the not-behind-base required check"
    if "compare/<baseRefName>...<headRefName>" not in step2:
        return (
            False,
            "step 2 no longer names the compare-endpoint call for the not-behind-base check",
        )
    if "required, blocking gate" not in step2:
        return (
            False,
            "step 2's not-behind-base check no longer states it's a required, blocking gate -- it "
            "may have regressed back to advisory-only",
        )
    if "could not be confirmed" not in step2:
        return (
            False,
            "step 2's not-behind-base check no longer states a failed compare-endpoint call is "
            "reported as 'could not be confirmed' rather than silently treated as passing",
        )
    # cross-model-review (2026-08-31): a fork PR must NOT be unconditionally treated as passing --
    # it uses mergeStateStatus (BEHIND blocks) instead of the unsafe-by-name compare endpoint, never
    # a bare skip-and-pass.
    if "mergeStateStatus" not in step2 or "BEHIND" not in step2:
        return (
            False,
            "step 2's not-behind-base check no longer uses mergeStateStatus for the fork-PR "
            "(isCrossRepository: true) path -- it may have regressed to unconditionally treating "
            "fork PRs as passing without checking them (cross-model-review finding)",
        )
    return (
        True,
        "step 2 documents the not-behind-base check as a required blocking gate that checks fork "
        "PRs via mergeStateStatus rather than exempting them",
    )


def check_step2_no_merge_conflicts_check():
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "No merge conflicts" not in step2:
        return False, "step 2 no longer documents the no-merge-conflicts required check"
    required_mergeable = ("MergeableState", "MERGEABLE", "CONFLICTING", "UNKNOWN")
    if any(token not in step2 for token in required_mergeable):
        return (
            False,
            "step 2's no-merge-conflicts check no longer names the live-verified MergeableState "
            "enum (MERGEABLE/CONFLICTING/UNKNOWN)",
        )
    if "poll `gh pr view $ARGUMENTS --json mergeable`" not in step2:
        return (
            False,
            "step 2's no-merge-conflicts check no longer polls on an UNKNOWN mergeable value -- an "
            "in-progress GitHub computation could be silently treated as passing",
        )
    if "resolving-merge-conflicts" not in step2:
        return (
            False,
            "step 2's no-merge-conflicts check no longer points at resolving-merge-conflicts on a "
            "real conflict",
        )
    return (
        True,
        "step 2 documents the no-merge-conflicts check with the verified MergeableState enum, "
        "UNKNOWN polling, and a pointer to resolving-merge-conflicts",
    )


def check_step2_mergestate_summary_disclosure():
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "GitHub's own merge-state summary" not in step2:
        return False, "step 2 no longer documents the mergeStateStatus advisory disclosure"
    if "MergeStateStatus" not in step2:
        return False, "step 2 no longer names the live-verified MergeStateStatus enum"
    for value in ("CLEAN", "DIRTY", "BLOCKED", "BEHIND", "UNSTABLE", "HAS_HOOKS", "UNKNOWN"):
        if value not in step2:
            return (
                False,
                f"step 2's mergeStateStatus disclosure no longer lists the {value!r} enum value",
            )
    if "Never blocks readiness" not in step2:
        return (
            False,
            "step 2's mergeStateStatus disclosure no longer states it never blocks readiness on "
            "its own",
        )
    return (
        True,
        "step 2 documents the mergeStateStatus advisory disclosure with the verified 7-value enum "
        "and its non-blocking status",
    )


def check_step1_fetches_mergeable_fields():
    step1 = _get_step_text(1)
    step2 = _get_step_text(2)
    if step1 is None or step2 is None:
        return False, "step 1 or step 2 ('## Instructions') not found"
    if "mergeable,mergeStateStatus,url" not in step1:
        return (
            False,
            "step 1's initial gh pr view fetch no longer requests mergeable/mergeStateStatus -- "
            "the new required/advisory checks below have no data to classify against",
        )
    if "statusCheckRollup,mergeable,mergeStateStatus" not in step2:
        return (
            False,
            "step 2's rerun re-fetch no longer requests mergeable/mergeStateStatus -- a conflict "
            "or merge-state regression after step 1 would go undetected on a recheck",
        )
    return (
        True,
        "step 1's initial fetch and step 2's rerun re-fetch both request "
        "mergeable/mergeStateStatus",
    )


def check_step2_unresolved_threads_disclosure():
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "Unresolved review threads" not in step2:
        return False, "step 2 no longer documents the unresolved-review-threads disclosure"
    if "reviewThreads" not in step2 or "isResolved" not in step2:
        return False, "step 2 no longer names the reviewThreads/isResolved GraphQL query"
    if "gh-pr-review merge-pr" not in step2:
        return (
            False,
            "step 2's unresolved-review-threads check no longer writes the gh-pr-review marker "
            "before its gh api graphql call -- guard-raw-pr-review.sh hard-blocks graphql "
            "without it",
        )
    if "hasNextPage" not in step2:
        return (
            False,
            "step 2's unresolved-review-threads check no longer paginates the reviewThreads query",
        )
    return (
        True,
        "step 2 documents the unresolved-review-threads disclosure, its marker write, and "
        "pagination",
    )


def check_step5_states_advisory_disclosures():
    step5 = _get_step_text(5)
    if step5 is None:
        return False, "step 5 ('## Instructions') not found"
    if "advisory disclosures" not in step5:
        return (
            False,
            "step 5's confirmation no longer states it surfaces step 2's advisory disclosures "
            "(mergeStateStatus, unresolved review threads)",
        )
    if "thread count is zero and the merge-state value is `CLEAN`" not in step5:
        return (
            False,
            "step 5 no longer states the advisory disclosures are shown even when clean -- a "
            "clean result must never be silently omitted, same discipline as the squash disclosure",
        )
    return True, "step 5's confirmation states it always surfaces both advisory disclosures"


def check_boundaries_graphql_grant_disclosure():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Boundaries\n")
    if start == -1:
        return False, "'## Boundaries' section not found"
    end = text.find("\n## ", start + 1)
    boundaries = text[start : end if end != -1 else len(text)]
    if "mergePullRequest" not in boundaries or "deleteRef" not in boundaries:
        return (
            False,
            "Boundaries no longer discloses that Bash(gh api graphql:*) grants the entire "
            "GraphQL surface including mutations this skill never intends (security-reviewer M1)",
        )
    if "never substitutes for step 7(b)" not in boundaries:
        return (
            False,
            "Boundaries no longer states a GraphQL call never substitutes for step 7(b)'s "
            "marker-gated merge or step 5's confirmation",
        )
    return (
        True,
        "Boundaries discloses the graphql grant's full surface and its non-substitution for "
        "merging",
    )


def check_boundaries_rest_grants_method_unrestricted_disclosure():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Boundaries\n")
    if start == -1:
        return False, "'## Boundaries' section not found"
    end = text.find("\n## ", start + 1)
    boundaries = text[start : end if end != -1 else len(text)]
    if "method-unrestricted, same reasoning as" not in boundaries:
        return (
            False,
            "Boundaries no longer discloses that the REST grants (branches/protection, compare, "
            "pulls/commits, labels, collaborators/permission) are method-unrestricted, same as the "
            "graphql grant (security-reviewer M1, round 2)",
        )
    return True, "Boundaries discloses the REST grants' method-unrestricted breadth"


def check_step2_advisory_failure_handling():
    # Only unresolved-review-threads still has an independent live-call failure mode among the
    # advisory disclosures -- mergeStateStatus is read from the same already-fetched gh pr view
    # data as everything else, so its own failure is already covered by step 1/2's fetch-failure
    # handling, not a separate clause here. not-behind-base moved to a required check (verified
    # separately by check_step2_not_behind_base_required) and uses "could not be confirmed"
    # instead, matching required-check phrasing elsewhere in step 2.
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "could not be determined" not in step2:
        return (
            False,
            "step 2's unresolved-review-threads disclosure no longer states a failed call is "
            "reported as 'could not be determined' rather than silently as 0 "
            "(security-reviewer M2)",
        )
    return (
        True,
        "the unresolved-review-threads disclosure states a failed call is reported as "
        "undetermined, never as 0",
    )


def check_r30_scenarios_extracted():
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("\n## Testing & Validation\n")
    if start == -1:
        return False, "'## Testing & Validation' section not found"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]
    if "references/test-scenarios.md" not in section:
        return (
            False,
            "Testing & Validation no longer points at references/test-scenarios.md -- the R30 "
            "scenario-walkthrough extraction may have been reverted",
        )
    if "Verify step 7's remote-branch-deletion fallback" in section:
        return (
            False,
            "Testing & Validation still contains the full remote-branch-deletion scenario "
            "walkthrough inline -- it belongs in references/test-scenarios.md per R30",
        )
    ref_path = SKILL_DIR / "references" / "test-scenarios.md"
    if not ref_path.exists():
        return False, "references/test-scenarios.md does not exist"
    ref_text = ref_path.read_text(encoding="utf-8")
    if "Verify step 7's remote-branch-deletion fallback" not in ref_text:
        return (
            False,
            "references/test-scenarios.md doesn't contain the remote-branch-deletion scenario "
            "walkthrough -- extraction may be incomplete",
        )
    return (
        True,
        "R30 scenario walkthroughs are extracted to references/test-scenarios.md, not inline",
    )


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_step_sequence,
    check_step7_remote_delete_fallback,
    check_step7_skips_delete_fallback_for_fork_prs,
    check_step7_verification_not_gated_on_exit_code,
    check_headrefname_validated_before_first_use,
    check_step5_worktree_note,
    check_step2_four_state_classification,
    check_step7_rebase_precheck,
    check_step7_squash_disclosure,
    check_step7b_final_recheck_before_merge,
    check_bypass_exception_single_use,
    check_step2_rerun_enumeration_includes_7b,
    check_bypass_poll_uses_started_at_baseline,
    check_merge_binds_to_verified_head_sha,
    check_step7_rejection_fallback,
    check_step1_owner_repo_from_pr_url,
    check_step3_and_merge_rights_reuse_owner_repo,
    check_step2_no_merge_conflicts_reproduction_steps,
    check_step2_no_merge_conflicts_fork_branching,
    check_step2_refetch_on_rerun,
    check_step2_rerun_refetches_ref_fields,
    check_step2_not_behind_base_required,
    check_step2_no_merge_conflicts_check,
    check_step2_mergestate_summary_disclosure,
    check_step1_fetches_mergeable_fields,
    check_step2_unresolved_threads_disclosure,
    check_boundaries_graphql_grant_disclosure,
    check_boundaries_rest_grants_method_unrestricted_disclosure,
    check_step2_advisory_failure_handling,
    check_r30_scenarios_extracted,
    check_step5_states_advisory_disclosures,
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

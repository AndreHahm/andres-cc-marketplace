#!/usr/bin/env python3
"""Persisted smoke test for merge-pr: frontmatter validity, referenced-file
existence, Bash-scope grant usage, step-header sequencing, step 7's
remote-branch-deletion verification fallback, step 5's unconditional
worktree branch-delete note, step 2's four-state CI classification, and
step 7(a)/(c)/(d)'s rebase pre-check / squash disclosure / rejection
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


def check_step2_out_of_sync_disclosure():
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "Out-of-sync with base" not in step2:
        return False, "step 2 no longer documents the out-of-sync-with-base disclosure"
    if "compare/<baseRefName>...<headRefName>" not in step2:
        return False, "step 2 no longer names the compare-endpoint call for the out-of-sync check"
    if "skip entirely when `isCrossRepository` is `true`" not in step2:
        return (
            False,
            "step 2's out-of-sync check no longer states it's skipped (and disclosed as skipped) "
            "for fork PRs -- comparing a fork's head ref by name against this repo risks resolving "
            "a same-named but unrelated branch",
        )
    return True, "step 2 documents the out-of-sync-with-base disclosure, gated on isCrossRepository"


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
            "(commits behind base, unresolved review threads)",
        )
    if "even when both are zero" not in step5:
        return (
            False,
            "step 5 no longer states the advisory disclosures are shown even when zero -- a "
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
    step2 = _get_step_text(2)
    if step2 is None:
        return False, "step 2 ('## Instructions') not found"
    if "could not be determined" not in step2:
        return (
            False,
            "step 2's advisory disclosures no longer state a failed call is reported as "
            "'could not be determined' rather than silently as 0 (security-reviewer M2)",
        )
    if step2.count("could not be determined") < 2:
        return (
            False,
            "step 2's failure-handling clause is missing from one of the two advisory disclosures "
            "-- both out-of-sync-with-base and unresolved-review-threads need their own",
        )
    return (
        True,
        "both advisory disclosures state a failed call is reported as undetermined, never as 0",
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
    check_step7_rejection_fallback,
    check_step1_owner_repo_from_pr_url,
    check_step2_refetch_on_rerun,
    check_step2_out_of_sync_disclosure,
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

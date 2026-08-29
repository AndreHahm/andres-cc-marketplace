## Summary
`core.fileMode=false` locally can mask a missing executable bit on a directly-invoked helper script — the git *index* mode can silently diverge from what local disk shows, and this is a confirmed recurring anti-pattern in this repo (two independent instances found so far), yet not a named, checkable convention.

## Environment
- **Product/Service**: `git-kit` plugin (source instance: `lint-staged-python.sh`/`unstage-flagged-files.sh`; a second, later instance affected `stage-selected-files.sh`)
- **Region/Version**: this repo, found during PR #121 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Commit a new helper script that a skill's own instructions invoke directly (not via `bash <path>`), with git mode `100644` (non-executable).
2. Work in a local dev environment where `git config core.fileMode` is `false`, and the file already has the executable bit set on local disk (e.g. from an earlier `chmod +x` that git never recorded as a diff, since `core.fileMode=false` makes git ignore local permission changes).
3. Run the skill locally — it works, because the local filesystem's own executable bit is what actually gets used when the shell invokes the script directly, masking the fact that the *committed* mode is wrong.
4. Clone the repo fresh on a machine with standard Unix checkout permissions (or `core.fileMode` unset/true) — the script checks out non-executable, and the skill fails with exit 126 (`Permission denied`) the first time it tries to invoke it.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| A script's local on-disk executable bit reflects what's actually committed | With `core.fileMode=false`, git ignores local permission changes entirely — only the index's own recorded mode matters, and it can silently diverge from disk |

## Expected Behavior
Before committing a script that a skill invokes directly, verify its *git index* mode (`git ls-files -s <path>` — expect `100755`), not a local `ls -la` — especially in an environment with `core.fileMode=false` (checkable via `git config core.fileMode`).

## Actual Behavior
Two independent occurrences confirmed in this repo's own history: (1) PR #121 (2026-08-24) — `lint-staged-python.sh` and `unstage-flagged-files.sh` shipped at mode `100644` despite being invoked directly, masked locally by `core.fileMode=false` plus pre-existing +x on disk; (2) a later incident (2026-08-28, per `commit`'s own Testing & Validation checklist) — `stage-selected-files.sh` shipped the same way, found by Codex's automated PR review, with the same root cause explicitly named in that skill's own documentation.

## Impact
[Severity: Medium] Both known instances were fixed reactively (PR #121: commit `6ae2115`; the later `stage-selected-files.sh` instance per `commit`'s own checklist). No `.claude/rules/*.md` file currently states this as a general pre-commit check, despite it having already recurred twice independently — the second occurrence happening *after* the first was fixed and understood is itself evidence that fixing individual instances hasn't been enough to prevent recurrence.

## Additional Context
Mined from PR #121's own review history (`chatgpt-codex-connector[bot]`; 17 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #121` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/121#discussion_r3845549601

Suggested scope: given the confirmed recurrence, this is a strong candidate for either a `.claude/rules/*.md` entry naming the check explicitly, or a pre-commit/CI check that verifies the git index mode of any script a skill's `allowed-tools`/instructions invoke directly.

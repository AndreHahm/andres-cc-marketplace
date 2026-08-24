## Summary
Tracking issue for codex-kit's remaining Nice-to-Have/Reconsider-tier quality items, deferred from a `plugin-lifecycle-downstream` QA run (2026-08-24) that already fixed all 3 Critical and every confirmed-real Major finding.

## Environment
- **Product/Service**: `codex-kit` plugin (this marketplace)
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps
N/A — this is a tracking issue for a batch of deferred quality-improvement candidates, not a single reproducible bug. Each item below traces to a specific `enhancement-suggestor` candidate from the run's own action plan (built off a 105-finding whole-plugin `plugin-auditor` audit).

## Expected Behavior
Each item below is either fixed in a follow-up change, or explicitly re-confirmed as intentional/accepted and closed without a code change.

## Actual Behavior
Currently open, deferred:

1. **Candidate 24 — R18 exception-note placement.** 6 notes across `codex-rescue`, `codex-research`, `codex-verify` are placed after their code block instead of directly above it, per `size-rules.md`'s convention. Cosmetic only — the disclosed rationale content itself is already correct.
2. **Candidate 25 — reference-chaining disclosures.** `codex-prompt-protocol/references/invocation-protocol.md` and 3 of `codex-review-bridge`'s reference files trip a reference-chaining check. Both reviewers who found this say real-world impact is limited. Needs a decision: accept as disclosed single-source-of-truth architecture, or add a one-line disclosure note.
3. **Candidate 27 — typed-failure stream divergence.** `codex-review-bridge/scripts/bridge-invoke.mjs` reports failure via stderr + `process.exit(1)`; `codex-windows-guardrails/scripts/guarded-dispatch.mjs` reports via stdout + `process.exitCode=1`. Both `codex-windows-guardrails/SKILL.md` and `references/dispatch.md` claim "same contract." Fix direction depends on checking `plugins/plugin-devkit/skills/plugin-auditor/references/codex-backend.md` first (the named downstream consumer) for whether it pins a stream.
4. **Candidate 28 — sensitive-filename-list ownership (cross-plugin).** Now duplicated between `plugins/git-kit/scripts/scan-staged-files.sh` (bash) and `plugins/codex-kit/scripts/lib/secret-filenames.mjs` (the new shared module extracted during this run), plus a third ownership claim in `plugins/plugin-devkit/skills/plugin-auditor/references/codex-backend.md`. Needs a single declared owner. Out of scope for a codex-kit-only run.
5. **Candidate 29 — `ephemeral`-on-resume asymmetry.** `scripts/lib/codex.mjs`'s `runAppServerTurn` passes `ephemeral: false` on resume, but `buildResumeParams` never forwards `ephemeral` in its returned object (unlike the symmetric `buildThreadParams`, which does). Needs verification against the real app-server `ThreadResumeParams` RPC schema — not available in this repository.
6. **Candidate 30 — stale re-grade commitment.** `plugin-marketplace-review/SKILL.md`'s own Testing & Validation section says its eval was "last structurally graded 2026-08-15... should be re-run against the current wording" — no newer grading, `grading.json`, or dated note exists. Needs an actual `skill-tester` structural-grade dispatch, or remove the commitment sentence if the deferral is deliberate.
7. **~23 additional minor/cosmetic items** from the same action plan's candidate-32 batch: a stale preflight-scenario count in one more spot, a missing `eval_metadata.json` for one eval, a couple of unenforced/unassigned label references, wording/citation-form inconsistencies, possibly-unused `Read`/`Grep`/`Glob` grants on 2 skills worth double-checking, 2 skills missing from `shared-skill-conventions.md`'s first-send-gate exception list, R8 description-length edge cases on 2 commands, and pre-existing mojibake (a UTF-8 em-dash re-decoded as cp1252) in 2 eval JSON files' `expected_output` strings.

## Impact
**Low** — cosmetic/polish and a handful of items needing external verification this repo can't do locally. No functional or security impact. Distinct from the 3 Critical + all Major findings from the same audit, already fixed in commits `a6fac30`, `87548b2`, `9d722af`.

## Additional Context
Found during a `plugin-lifecycle-downstream` full-pipeline QA run on `codex-kit` (2026-08-24). The run's own `enhancement-suggestor` action plan classified these as Nice-to-Have/Reconsider tier (lower priority than the Quick Wins already implemented). Full context: `.claude/output/plugin-lifecycle-downstream/20260823T205538-codex-kit/scope.json` and `phase12-handoff-summary.md` in that same run's worktree (gitignored, local to that session).

Filed live: https://github.com/AndreHahm/andres-cc-marketplace/issues/109

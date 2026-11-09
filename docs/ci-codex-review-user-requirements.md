# CI Codex Delta Review: User Requirements

The maintainer's requirements for what the `Codex delta review` CI job (`codex-review` in
`.github/workflows/marketplace-ci.yml`) reviews, skips and leaves out. The implementation is described in
[`docs/ci.md`](ci.md), section "CI review delta (issue #639)". Where the two disagree, this document states
the intent and `docs/ci.md` must be corrected.

**Problem (issue #639):** the CI review sent the whole pull request to the OpenAI API on every run, including
force-pushes, label and body edits, and re-runs. API cost and run time were too high.

Each requirement carries a status: `proposed` (written from the design discussion, not yet confirmed) or
`approved` (confirmed by the maintainer).

## R1. Two review gates with different scopes

- The local parity review (`plugins/git-kit/scripts/git-codex-parity-review.py`) is the full or delta review
  and the quality gate before a pull request is created. It stays as it is.
- CI's Codex delta review is only the delta review and the quality gate after the pull request exists.

Status: approved

## R2. Paths excluded from the CI review

The CI reviewers are not sent:

- `issues/`, `evals/` and `reviewer-eval/` at the repository root.
- Any path with a `tests`, `test`, `__tests__`, `fixtures` or `evals` directory at any depth.
- Files named `smoke_test.*`, `test_*.py`, `*_test.py` or `*.test.{js,mjs,cjs,ts}`, anywhere, including
  inside a plugin's component folders where they can be run. The local parity review covers them.
- Generated agent mirrors: a `.agents/skills/` or `.claude/` file whose content and mode equal its source
  (`.claude/skills/`, or a mirrored plugin's `plugins/<plugin>/` file). A declared divergence exception, a
  repo-only `.claude/` file and an extra file with no identical source are still reviewed.

A renamed file is excluded only when both its old and its new path are excluded.

Status: approved

## R3. Gate-critical paths are always reviewed

A changed path in `FULL_ESCALATION_PATHS` or under `BYPASS_INELIGIBLE_PREFIXES` (`scripts/`, `.github/`,
`.codex/agents/`, `.claude/rules/`, `.claude/skills/plugin-rulebook/`, `pyproject.toml`, `uv.lock`, the
`codex-kit` bridge files, CODEOWNERS, `marketplace.json`, `marketplace-sync.json` and the rulebook governance
files) is never excluded and never narrowed away. While a pull request contains such a change, every CI run
reviews it, so the Tier-1 refusal fires every time.

Status: approved

## R4. The first review covers the whole pull request

On an `opened` event, or when no earlier run qualifies as an anchor (R5), CI reviews the whole pull request
delta minus the exclusions (R2). This is the only case where the whole pull request is reviewed, apart from
an untrusted anchor (R10) and a move from draft to ready (R14).

Status: approved

## R5. The anchor: the last reviewed head

The anchor is the pull request head of the newest other Marketplace CI run for this pull request whose
`Codex delta review` job ended in `success` or `failure` and whose `codex-review-result` artifact reports
`findings` or `clean`. A cancelled or skipped run, and one that stopped before its reviewers ran
(`could_not_run`), reviewed nothing and does not count. The anchor is read from the GitHub API, never from
the pull request, among the 30 most recent completed runs on the branch. A failed lookup means no anchor.

Status: approved

## R6. Only changes since the anchor are reviewed

With an anchor, CI reviews only the files whose pull-request-side change differs between the anchor and the
current head:

- Each side is compared from its own merge base with the base branch, so commits a rebase pulls in from the
  base branch are out of scope.
- Line numbers and blob ids are ignored, so a rebase that only shifts the change compares equal.
- Three context lines pin each change's position, so a change moved elsewhere in a file is reviewed.

The reviewers may still read whole files for context.

Status: approved

## R7. Blocking findings carry forward until fixed or waived

After a run with blocking findings, those findings keep blocking later runs until the flagged file changes
or the finding is waived:

- **Carry forward.** CI reads the anchor run's blocking findings from its `codex-review-result` artifact. A
  finding whose file is unchanged since the anchor blocks again, without a new Codex call. A finding whose
  file changed is not carried: the file is in the delta (R6) and is reviewed again.
- **Waivers.** An accepted risk, a disclosed residual or a deferred finding is not carried when the pull
  request body lists it in a section `## Accepted CI findings`, one line per finding:
  `- <rule> <path>:<line> – accepted|residual|deferred #<issue>`. A `deferred` line needs an open issue in
  this repository, checked through the GitHub API. Anyone who can edit the pull request body can waive a
  finding; the waiver stays visible in the body.

Status: approved

## R8. Events without new commits make no Codex call

An `edited` (title, body or base), `labeled` or `reopened` event with no new pull request changes since the
anchor makes no Codex call. When the anchor run had blocking findings, CI still checks them against the pull
request body (R7), so they keep blocking until fixed or waived; a body edit that adds the waiver lines can
clear them. When no finding remains, the review is skipped as bypass-eligible.

Status: approved

## R9. Force-push: review the changed files, skip an unfetchable anchor

After a force-push, CI reviews the files whose change differs from the anchor (R6). When the anchor cannot be
fetched because it was force-pushed away, the review is skipped except for gate-critical paths (R3): a
force-push review would be the most expensive one. When `compute-scope` found the anchor but `codex-review`
cannot fetch it, `codex-review` fails closed so the two jobs never narrow differently.
Carried findings (R7) come from the anchor run's artifact, not from the anchor commit. When the anchor cannot
be fetched, CI cannot tell whether a flagged file changed, so those findings keep blocking until waived.

Status: approved

## R10. An anchor the pull request could have influenced is not trusted

When the anchor's own pull request changes touch a gate-critical path (R3), or a file Codex may load as
instructions or configuration (`AGENTS*.md` at any depth, `.codex/`, the root `REVIEW.md`), its run may not
have reviewed honestly. CI then reviews the whole pull request delta minus the exclusions. That run's
findings are not carried (R7): the whole review replaces them.

Status: approved

## R11. A re-run of a failed job reviews the same delta

Re-running a failed `Codex delta review` job replays the same event and finds the same anchor, so it
reviews the same delta again and carries the same findings (R7), not the whole pull request. The run's own
earlier attempt is never its anchor.

Status: approved

## R12. Only the bypass label with a valid attestation clears a failed review

- Adding the `s: codex review bypassed` label clears a failed review when the SHA-bound bypass protocol is
  met: the label plus the attestation comment for the current head, posted by an actor with write, maintain
  or admin permission (or `CODEX_CI_REVIEW_BYPASS`). The `labeled` event starts a new run, which takes the
  place of re-running the failed job: `Publish Codex policy result` passes and the carried findings (R7)
  are cleared. Without a valid attestation, the failed review keeps blocking.
- That labeled run makes no Codex call. Only the deterministic gates still run.
- Any other label, and a title or body edit, does not clear a failed review (R7, R8). A body edit can
  only waive specific findings through the `## Accepted CI findings` section (R7).

Status: approved

## R13. The deterministic checks still see the whole pull request

Only the reviewer dispatch is narrowed. The script verifiers, the structural checks and the diff-scoped
blocking gate use the whole pull request delta. A finding blocks when it sits on any line the pull request
changed in a reviewed file.

Status: approved

## R14. No CI Codex review on draft pull requests

- While a pull request is a draft, the Codex delta review does not run, whatever the event.
  `Publish Codex policy result` passes as skipped. A draft cannot be merged.
- When a pull request moves from draft to ready (`ready_for_review`, which the workflow must listen to),
  CI reviews the whole pull request delta minus the exclusions (R2). This holds for every move to ready,
  including ready → draft → ready. Later runs use that run as their anchor (R5).

Status: approved

# CI Codex Delta Review: User Requirements

The maintainer's requirements for what the `Codex delta review` CI job (`codex-review` in
`.github/workflows/marketplace-ci.yml`) reviews, skips and leaves out. The implementation is described in
[`docs/ci.md`](ci.md), section "CI review delta (issue #639)". Where the two disagree, this document states
the intent and `docs/ci.md` must be corrected.

**Problem (issue #639):** the CI review sent the whole pull request to the OpenAI API on every run, including
force-pushes, label and body edits, and re-runs. API cost and run time were too high.

**Open point:** the cost and run-time goals have no measurable acceptance criterion yet. This is not a
requirement.

Each requirement carries a status: `proposed` (written from the design discussion, not yet confirmed) or
`approved` (confirmed by the maintainer).

## R1. Two review gates with different scopes

- The local parity review (`plugins/git-kit/scripts/git-codex-parity-review.py`) is the full or delta review
  and the quality gate before a pull request is created. It stays as it is.
- CI's Codex delta review is only the delta review and the quality gate after the pull request exists.
- Current behavior: a pull request from a fork gets no Codex review. `compute-scope`, `codex-review` and
  `Publish Codex policy result` skip it, and the `Fork PR (unsupported)` job fails it explicitly.

Status: approved

## R2. Paths excluded from the CI review

The CI reviewers are not sent:

- `issues/`, `evals/` and `reviewer-eval/` at the repository root.
- Any path with a `tests`, `test`, `__tests__`, `fixtures` or `evals` directory at any depth.
- Files named `smoke_test.<ext>` (one letters-and-digits extension), `test_*.py`, `*_test.py` or `*.test.{js,mjs,cjs,ts}`, anywhere, including
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
that runs a Codex review reviews it, so the Tier-1 refusal fires every time. A draft (R14) and a run started
by the bypass label (R12) make no Codex call.

Status: approved

## R4. The first review covers the whole pull request

On an `opened` event, or when no earlier run qualifies as an anchor (R5), CI reviews the whole pull request
delta minus the exclusions (R2). This is the only case where the whole pull request is reviewed, apart from
an untrusted anchor (R10) and a move from draft to ready (R14).

Status: approved

## R5. The anchor: the last reviewed head

The anchor is the pull request head of the newest other Marketplace CI run for this pull request that was
already complete when this run was created (a re-run keeps its creation time, R11) and that left one of:

- a `codex-review-result` artifact reporting `findings` or `clean`, from a `Codex delta review` job that
  ended in `success` or `failure`;
- a `codex-review-skip` record from a successful `Compute Codex review scope` job, written when narrowing left
  nothing to review and holding the still-blocking carried findings (R7, R8), but never when the anchor could
  not be fetched (R9);
- a record of a valid bypass attestation from a passed `Publish Codex policy result` job (R12).

A result or record counts only when it names that run's own head and the attempt whose execution of the job
that wrote it is still the latest one; one without both does not count. A cancelled or skipped run, and one
that stopped before its reviewers ran (`could_not_run`), reviewed nothing and does not count. The anchor is
read from the GitHub API, never from the pull request, among the 30 most recent completed runs on the branch.
A failed lookup means no anchor.

- **Accepted residual:** when the lookup itself fails (an API error), CI reviews the whole pull request, and
  carried findings survive only if Codex finds them again.
- **Accepted residual:** the artifacts carry no retention setting, so the repository default applies. An
  anchor whose result has expired is not found: the whole pull request is reviewed and its carried findings
  are lost.

Status: approved

## R6. Only changes since the anchor are reviewed

With an anchor, CI reviews only the files whose pull-request-side change differs between the anchor and the
current head:

- Each side is compared from its own merge base with the base branch, so commits a rebase pulls in from the
  base branch are out of scope.
- Line numbers and blob ids are ignored, so a rebase that only shifts the change compares equal.
- Three context lines pin each change's position, so a change moved elsewhere in a file is reviewed.

The reviewers may still read whole files for context.

Current behavior: a moved base branch or a rebase is accepted. Only this pull-request-side patch comparison
decides what is reviewed again.

Status: approved

## R7. Blocking findings carry forward until fixed or waived

After a run with blocking findings, those findings keep blocking later runs until the flagged file changes,
the finding is waived, or a valid bypass clears it (R12), however many runs pass in between (the accepted
residuals here and under R5, R9 and R10 are the exceptions):

- **Carry forward.** CI reads the anchor run's blocking findings from its `codex-review-result` artifact. A
  finding whose file is unchanged since the anchor blocks again, without a new Codex call. A finding whose
  file changed is not carried: the file is in the delta (R6) and is reviewed again. A run that carries
  findings records them as blocking findings: a run that reviews writes them into its own
  `codex-review-result`, and a run that skips the Codex call because nothing is left to review writes them
  into its `codex-review-skip` record (R5). A run whose carried findings cannot be recorded reports
  `could_not_run` or fails, and is not an anchor. An anchor result with more than 500 findings, or a field
  longer than 300 characters, cannot be carried and blocks (fail closed).
- **Waivers.** An accepted risk, a disclosed residual or a deferred finding is not carried when the pull
  request body lists it in a section `## Accepted Review Findings`, one line per finding:
  `- <rule> <path>:<line> – accepted|residual|deferred #<issue>`, optionally followed by
  `: <reason or link>`. `#<issue>` is required only for `deferred`, and that issue must be open in this
  repository, checked through the GitHub API. Anyone who can edit the pull request body can waive a finding; the waiver is visible in the body
  while it is in effect (see the accepted residual below).
- **One section for every reviewer.** The section is part of both pull request templates. `git-kit`'s
  `create-pr` asset carries it generically; the waiver conventions (`-` for a finding without a rule, `0`
  without a line, no spaces in paths) are written out in `.github/pull_request_template.md`. The section
  also lists accepted third-party findings (CodeRabbit, Devin, the Codex connector, human reviewers) in the
  same shape, with the reviewer's name in place of the rule. CI only acts on lines whose rule, path and line match one of its own
  carried findings.
- **Accepted residual:** a waived finding is not written into the run's result. An author who adds an
  `accepted` waiver, pushes a commit that does not touch the flagged file, then removes the waiver, drops
  the finding for good, and the final body shows no waiver.

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
force-push review would be the most expensive one. That run writes no `codex-review-skip` record, since it
compared nothing: the head stays unreviewed, and later runs keep the older anchor. They skip too while it
cannot be fetched, and review the whole pull request once it has left the 30-run lookup window. When `compute-scope` found the anchor but `codex-review`
cannot fetch it, `codex-review` fails closed. The two jobs can still narrow differently: `compute-scope`
compares from the event's base SHA, `codex-review` from the merge commit's first parent, so `codex-review` may
review more than `compute-scope` predicts, never less.
Carried findings (R7) come from the anchor run's artifact, not from the anchor commit. When the anchor cannot
be fetched, CI cannot tell whether a flagged file changed, so those findings keep blocking until waived, or
until the anchor run leaves the 30-run lookup window: the next run then has no anchor, carries nothing and
reviews the whole pull request again.
Whether such an anchor can be trusted (R10) is then read from GitHub's compare API. When that call fails,
or shows the anchor changed a gate-critical or reviewer-steering file, `Publish Codex policy result` blocks
until a re-run or a bypass, even when the anchor had no findings.

Status: approved

## R10. An anchor the pull request could have influenced is not trusted

When the anchor's own pull request changes touch a gate-critical path (R3), or a file Codex may load as
instructions or configuration (`AGENTS*.md` at any depth, `.codex/`, the root `REVIEW.md`), its run may not
have reviewed honestly. CI then reviews the whole pull request delta minus the exclusions. That run's
findings are not carried (R7): the whole review replaces them.

- **Accepted residual:** because such an anchor carries nothing, a harmless edit to a reviewer-steering file
  (for example `REVIEW.md`) followed by a revert can clear carried findings, unless the whole-delta review
  finds them again. The same holds for a pull request that edits the workflow to forge a review result or a
  bypass record.

Status: approved

## R11. A re-run of a failed job reviews the same delta

Re-running a failed `Codex delta review` job replays the same event and finds the same anchor, so it
reviews the same delta again and carries the same findings (R7), not the whole pull request. The run's own
earlier attempt is never its anchor, and a run, a re-run included, anchors only on runs that were already
complete when it was created (R5), so a newer push finished in between does not change its delta.

Current behavior: a re-run of only the failed jobs reuses the outputs of the jobs that passed in earlier
attempts, while the run's attempt number changes; their results stay valid anchors (R5).

- **Accepted residual:** an anchor candidate counts only if its `updated_at` is earlier than this run's
  creation time, and re-running an older run moves its `updated_at`. An author who can re-run workflows
  can therefore push, re-run the previous run (which also cancels the new one), then re-run the new one: it
  skips the previous run and anchors on an older one. A finding carried by the skipped run is then reviewed
  again rather than carried, and survives only if Codex reports it again.

Status: approved

## R12. Only the bypass label with a valid attestation clears a failed review

- Adding the `s: codex review bypassed` label clears a failed review when the SHA-bound bypass protocol is
  met: the label plus the attestation comment for the current head, posted by an actor with write, maintain
  or admin permission (or `CODEX_CI_REVIEW_BYPASS`, which still needs the attestation comment for the current
  head). The `labeled` event starts a new run, which takes the
  place of re-running the failed job: `Publish Codex policy result` passes and the carried findings (R7)
  are cleared. Without a valid attestation, the failed review keeps blocking.
- The clear is durable. A run that passes on a valid attestation for its head records that head as
  reviewed with no findings, and later runs take it as their anchor (R5), so the bypassed findings are not
  carried again after the next push. Only `Publish Codex policy result`, after the trusted attestation
  check, records it; a label without a valid attestation records nothing. A pass through
  `CODEX_CI_REVIEW_BYPASS` records the same durable clear. The record is still distrusted
  like any anchor whose own changes touch a gate-critical or reviewer-steering file (R10).
- **Accepted consequence:** the bypassed head's content counts as reviewed even when CI never reviewed it
  (for example after a Tier-1 refusal or a review that could not run). Later runs review only what changes
  after it. That is what the bypass means.
- That labeled run makes no Codex call. Only the deterministic gates still run.
- Any other label, and a title or body edit, does not clear a failed review (R7, R8). A body edit can
  only waive specific findings through the `## Accepted Review Findings` section (R7).

Status: approved

## R13. The deterministic checks still see the whole pull request

Only the reviewer dispatch is narrowed. The script verifiers, the structural checks and the diff-scoped
blocking gate use the whole pull request delta. A finding blocks when it sits on any line the pull request
changed in a reviewed file. A carried finding (R7) blocks on a file that is unchanged since the anchor.

Status: approved

## R14. No CI Codex review on draft pull requests

- While a pull request is a draft, the Codex delta review does not run, whatever the event.
  `Publish Codex policy result` passes as skipped. A draft cannot be merged.
- When a pull request moves from draft to ready (`ready_for_review`, which the workflow must listen to),
  CI reviews the whole pull request delta minus the exclusions (R2). This holds for every move to ready,
  including ready → draft → ready. Later runs use that run as their anchor (R5). Only `ready_for_review` is
  a trigger; `converted_to_draft` is not, so a move back to draft starts no run.
- The draft pass holds only while the pull request is still a draft at the same head, re-read from the
  GitHub API at publish time, so a re-run of an old draft run cannot pass a ready pull request.
- **Accepted residual:** a draft's green check stays attached to its head after the pull request is marked
  ready. If the `ready_for_review` run is then cancelled by hand or never starts, that green check may stay
  the latest one on that head. Any later push or re-run replaces it.

Status: approved

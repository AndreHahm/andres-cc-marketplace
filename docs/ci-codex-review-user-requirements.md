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
- `.claude/review-outcomes/`: records of past review decisions. No gate or CI reviewer reads them; local
  triage reads them only as a hint, and evals as data.
- Any path with a `tests`, `test`, `__tests__`, `fixtures` or `evals` directory at any depth.
- Files named `smoke_test.<ext>` (one letters-and-digits extension), `test_*.py`, `*_test.py` or `*.test.{js,mjs,cjs,ts}`, anywhere, including
  inside a plugin's component folders where they can be run. The local parity review covers them.
- Generated agent mirrors: a `.agents/skills/` or `.claude/` file whose content and mode equal its source
  (`.claude/skills/`, or a mirrored plugin's `plugins/<plugin>/` file). A declared divergence exception, a
  repo-only `.claude/` file and an extra file with no identical source are still reviewed.

A renamed file is excluded only when both its old and its new path are excluded.

Status: approved (`.claude/review-outcomes/` added by the maintainer, 2026-11-16, issue #753)

## R3. Gate-critical paths are reviewed when they change

A changed path in `FULL_ESCALATION_PATHS` or under `BYPASS_INELIGIBLE_PREFIXES` (`scripts/`, `.github/`,
`.codex/agents/`, `.claude/rules/`, `.claude/skills/plugin-rulebook/`, `pyproject.toml`, `uv.lock`, the
`codex-kit` bridge files, CODEOWNERS, `marketplace.json`, `marketplace-sync.json` and the rulebook governance
files) is never excluded (R2). It is narrowed like any other file (R6): reviewed on the first run (R4) and
on every later run where its pull-request-side change differs from the anchor, not again while it is
unchanged. Its blocking findings carry forward (R7).

- **Escalation only on the first run.** A `FULL_ESCALATION_PATHS` file escalates to the larger reviewer set
  (`mode: "full"`) only on the first run. When it changes on a later run, it is reviewed with the normal
  delta reviewers.
- **The Tier-1 refusal is unchanged.** It checks the whole pull request, not the delta, so pull-request-modified
  review code never runs with the API key. It fires on every run that makes a Codex call.

A draft (R14) and a run started by the bypass label (R12) make no Codex call.

Status: approved (maintainer, 2026-11-16, issue #753)

## R4. The first review covers the whole pull request

On an `opened` event, or when no earlier run qualifies as an anchor (R5), CI reviews the whole pull request
delta minus the exclusions (R2). This is the only case where the whole pull request is reviewed, apart from
a move from draft to ready (R14).

Status: approved (maintainer, 2026-11-16, issue #753)

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

- **Retry:** the lookup retries its GitHub API calls a few times before it gives up, so a short API error does
  not cost a full review.
- **Accepted residual:** when the lookup still fails after the retries (a longer API outage), CI reviews the
  whole pull request, and carried findings survive only if Codex finds them again.
- **Accepted residual:** a read that fails for one candidate run (its job list, its result download or its
  attempt check) skips that run, and the next older qualifying run becomes the anchor. Everything since that
  older anchor is reviewed, but the skipped run's blocking findings are not carried and survive only if Codex
  finds them again. Retrying the download is not worth it, since a missing bypass or skip record is normal.
- **Accepted residual:** the artifacts carry no retention setting, so the repository default applies. An
  anchor whose result has expired is not found: the whole pull request is reviewed and its carried findings
  are lost.

Status: approved (retry and the per-candidate residual added by the maintainer, 2026-11-16, issue #753)

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
residuals here and under R5 and R9 are the exceptions):

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
  `create-pr` asset carries it without naming this repository's CI; both write out the waiver conventions
  (`-` for a finding without a rule, `0` without a line, no spaces in paths). The section
  also lists accepted third-party findings (CodeRabbit, Devin, the Codex connector, human reviewers) in the
  same shape, with the reviewer's name in place of the rule. CI only acts on lines whose rule, path and line match one of its own
  carried findings.
- **Accepted residual:** a waived finding is not written into the run's result. An author who adds an
  `accepted` waiver, pushes a commit that does not touch the flagged file, then removes the waiver, drops
  the finding for good, and the final body shows no waiver.

Status: approved (maintainer, 2026-11-16, issue #753)

## R8. Events without new commits make no Codex call

An `edited` (title, body or base), `labeled` or `reopened` event with no new pull request changes since the
anchor makes no Codex call. When the anchor run had blocking findings, CI still checks them against the pull
request body (R7), so they keep blocking until fixed or waived; a body edit that adds the waiver lines can
clear them. When no finding remains, the review is skipped as bypass-eligible.

Status: approved

## R9. Force-push: review the changed files, skip an unfetchable anchor

After a force-push, CI reviews the files whose change differs from the anchor (R6). When the anchor cannot be
fetched because it was force-pushed away, the review is skipped, gate-critical paths included (R3: without
the anchor commit CI cannot tell whether they changed): a force-push review would be the most expensive one.
CI fetches the anchor by its SHA, which GitHub normally still serves after a force-push, so this case is rare.
The fetch is retried like the lookup's API calls (R5), so a short git error does not count as unfetchable.
That run writes no `codex-review-skip` record, since it compared nothing: the head stays unreviewed, and later runs keep the older anchor. They skip too while it
cannot be fetched, and review the whole pull request once it has left the 30-run lookup window. When `compute-scope` found the anchor but `codex-review`
cannot fetch it, `codex-review` fails closed. The two jobs can still narrow differently: `compute-scope`
compares from the event's base SHA, `codex-review` from the merge commit's first parent, so `codex-review` may
review more than `compute-scope` predicts, never less.
Carried findings (R7) come from the anchor run's artifact, not from the anchor commit. When the anchor cannot
be fetched, CI cannot tell whether a flagged file changed, so those findings keep blocking until waived, or
until the anchor run leaves the 30-run lookup window: the next run then has no anchor, carries nothing and
reviews the whole pull request again.
Such an anchor is used like any other (R10): no trust check is made on it.

Status: approved (maintainer, 2026-11-16, issue #753)

## R10. An anchor the pull request could have influenced does not force a full review

When the pull request changes a gate-critical path (R3) or a file Codex may load as instructions or
configuration (`AGENTS*.md` at any depth, `.codex/`, the root `REVIEW.md`), its anchor run may not have
reviewed honestly. CI still reviews only the delta since that anchor (R6) and carries its findings (R7), as
for every other anchor. A full re-review would add no assurance: for a `pull_request` event GitHub runs the
pull request's own copy of the workflow, so the current run is no more trustworthy than the anchor run.

- **Accepted residual:** a pull request that edits the workflow, the review code or a reviewer-steering file
  can forge a review result, a bypass record or a clean verdict, in the anchor run and in the current run.
  The protection is the human review of that change, not CI.

Status: approved (maintainer, 2026-11-16, issue #753)

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
  `CODEX_CI_REVIEW_BYPASS` records the same durable clear. Like any anchor, the record is used even
  when the pull request touches a gate-critical or reviewer-steering file (R10).
- **Accepted consequence:** the bypassed head's content counts as reviewed even when CI never reviewed it
  (for example after a Tier-1 refusal or a review that could not run). Later runs review only what changes
  after it. That is what the bypass means.
- That labeled run makes no Codex call. Only the deterministic gates still run.
- Any other label, and a title or body edit, does not clear a failed review (R7, R8). A body edit can
  only waive specific findings through the `## Accepted Review Findings` section (R7).

Status: approved (maintainer, 2026-11-16, issue #753)

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
- The first run is the first non-interrupted run after the pull request was created as ready or last moved
  to ready. The anchor search (R5) ignores runs created before that moment, read from the pull request's
  creation time and its newest `ready_for_review` event at or before the current run's creation, so a
  re-run keeps its delta (R11). If the `ready_for_review` run is interrupted, the
  next run therefore reviews the whole pull request.
- The draft pass holds only while the pull request is still a draft at the same head, re-read from the
  GitHub API at publish time, so a re-run of an old draft run cannot pass a ready pull request.
- **Accepted residual:** a draft's green check stays attached to its head after the pull request is marked
  ready. If the `ready_for_review` run is then cancelled by hand or never starts, that green check may stay
  the latest one on that head. Any later push or re-run replaces it.

Status: approved (first-run rule added by the maintainer, 2026-11-16, issue #753; the re-run cutoff by the maintainer after PR #755's review)

## R15. No CI Codex review on verified Dependabot pull requests (issue #704)

- The Codex delta review never runs for Dependabot: `github.actor` or the pull request's author is
  `dependabot[bot]`. Dependabot runs get no Actions secrets, so the review could only end without a verdict.
  This matches `Claude delta review`, which skips Dependabot pull requests without failing.
- `Publish Codex policy result` passes that skip with no bypass attestation only when all of these hold,
  as decided by `Hygiene (PR contract)` from the base SHA's code: the pull request's author is
  `dependabot[bot]`; every commit is authored by `dependabot[bot]`, committed by `web-flow` and
  signature-verified (the merge-privilege exemption's own check); and either every changed path is a root
  dependency manifest or lockfile (`uv.lock`, `pyproject.toml`, `package.json`, `pnpm-lock.yaml`), or the diff
  is a GitHub Actions pin bump whose every changed line swaps a ratchet-pinned `uses:` SHA for the commit its
  tag names in the action's own repository (`docs/ci.md`, the actions pin exemption). `Compute Codex review
  scope` must also have succeeded, as for every other skip.
- Any other Dependabot pull request, for example one a human pushed to or one that changes another file,
  still needs the SHA-bound bypass attestation (R12).
- The pass is never presented as a clean review and records no review result. The deterministic gates still
  apply.
- **Accepted consequence:** a verified Dependabot pull request's dependency changes get no Codex review and
  no attestation. The maintainer's merge is the human check. Nothing machine-checks npm lockfile content
  (issue #702) or a `pyproject.toml` `[build-system]` change. The commit check's untested residual in
  `docs/ci.md` (a spoofed `dependabot[bot]` author on a `web-flow`-signed commit) now also covers this gate.

Status: approved (maintainer, issue #704; path set chosen 2026-11-13)

# CI Codex Delta Review: User Requirements

The maintainer's requirements for what the `Codex delta review` CI job (`codex-review` in
`.github/workflows/marketplace-ci.yml`) reviews, skips and leaves out. The implementation is described in
[`docs/ci.md`](ci.md), section "CI review delta (issue #639)". Where the two disagree, this document states
the intent and `docs/ci.md` must be corrected.

**Problem (issue #639):** the CI review sent the whole pull request to the OpenAI API on every run, including
force-pushes, label and body edits, and re-runs. API cost and run time were too high.

R7, R17, R18 and R19 also cover the other reviewers that read a pull request's accepted findings (issue #808): the
Claude delta review, the local parity review, `cross-model-review` and third-party reviewers.

**Open point:** the cost and run-time goals have no measurable acceptance criterion yet. This is not a
requirement.

Each requirement carries a status: `proposed` (written from the design discussion, not yet confirmed) or
`approved` (confirmed by the maintainer).

## R1. Two review gates with different scopes

- The local parity review (`plugins/git-kit/scripts/git-codex-parity-review.py`) is the full or delta review
  and the quality gate before a pull request is created. It stays as it is, except that it also leaves out
  root `issues/` (R2).
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

Root `issues/` is left out of the local parity review too, so no reviewer is sent an issue draft: a draft
under `issues/` is a historical, read-only record of an issue as filed (issue #653).

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

After a run with blocking findings, those findings keep blocking later runs until they are fixed, waived, or
cleared by a valid bypass (R12), however many runs pass in between (the accepted residuals here and under R5
and R9 are the exceptions). A waived finding does not block again, whether CI carries it from the anchor or
a reviewer reports it anew, until the flagged code changes (issue #808).

- **Carry forward.** CI reads the anchor run's blocking findings from its `codex-review-result` artifact. A
  finding whose file is unchanged since the anchor blocks again, without a new Codex call. A finding whose
  file changed is not carried: the file is in the delta (R6) and is reviewed again. A run that carries
  findings records them as blocking findings: a run that reviews writes them into its own
  `codex-review-result`, and a run that skips the Codex call because nothing is left to review writes them
  into its `codex-review-skip` record (R5). A run whose carried findings cannot be recorded reports
  `could_not_run` or fails, and is not an anchor. An anchor result with more than 500 findings, or a field
  longer than 300 characters, cannot be carried and blocks (fail closed).
- **Waivers.** A finding is waived when the pull request body lists it in a section
  `## Accepted Review Findings`, one line per finding:
  `- <rule> <path>:<line> @<fingerprint> – accepted|residual|deferred #<issue>|refuted`, optionally followed
  by `: <reason or link>`. `accepted` is an accepted risk, `residual` a disclosed limitation, `deferred` a
  finding filed as an open issue, and `refuted` a finding the author showed is not a defect (issue #480).
  `#<issue>` is required only for `deferred`, and that issue must be open in this repository, checked through
  the GitHub API.
- **A waiver applies to new findings, not only to carried ones.** After the reviewers run, CI matches every
  blocking finding, fresh or carried, against the waivers. A matched finding is recorded in the run's result
  as waived, with the waiver line it matched, and does not block. This replaces `docs/ci.md`'s rule that a
  model finding is never suppressed: a waiver is not a suppression by a registry, it is the author's
  recorded decision on that one finding, and it stays visible in the result.
- **The match key: rule, path and the flagged line's fingerprint.** The fingerprint is a hash of the
  flagged line's text at the reviewed head, with whitespace collapsed, 32 hex digits long so an author
  cannot make two different lines share one. CI prints it next to every blocking
  finding in the job summary, ready to copy into a waiver line. A waiver matches a finding when the rule and
  path are equal and the fingerprint of the finding's flagged line equals the waiver's. The line number in
  the waiver is informational, so a waiver survives the flagged line moving, and a reviewer rewording its
  claim. For the same reason, lines with identical text (whitespace collapsed) in one file share a
  fingerprint: a waiver covers a finding with its rule on any of them, and so does a maintainer's
  confirmation. Fix the other copies, or accept them knowingly, before writing such a waiver. When the
  flagged line's own text changes, the fingerprint no longer matches and the finding is reviewed and
  blocks again: that is what "materially different" means here. A finding with no line uses
  `0` and the fingerprint `-`; it then matches on rule and path alone. A waiver line without a fingerprint
  (the earlier format) matches on rule, path and exact line, as before.
- **A finding on a file the pull request deletes.** When the flagged file does not exist at the reviewed
  head, the fingerprint is taken from the flagged line at the base side of the pull request's diff (the
  merge base of its base and head, whose lines the review numbered), and CI prints it like any other. A waiver and a confirmation name it as usual. A path that cannot be read at the head or
  the base has no fingerprint: no fingerprinted waiver matches its finding, so a waiver that needs a
  maintainer's confirmation cannot apply to it (fail closed) (issue #835).
- **Maintainer-only acceptance for gate-critical and security findings.** A waiver for a finding on a
  gate-critical path (R3), on a path not spelled the canonical way, or one raised by `security-reviewer`
  (by any of the reviewers that reported it), counts only when a user whose role is maintain or admin
  has posted a pull request comment confirming that waiver line, and has not edited it since. The
  confirmation is bound to the line, including its fingerprint, not to a head, so it survives pushes
  until the flagged line changes. Without it, the finding keeps blocking, and the job
  summary says that a confirmation is missing. A waiver and its confirmation must still exist when the
  result is published (R19). Every other waiver needs no confirmation: anyone who can
  edit the pull request body can waive it (see the accepted residual below).
- **Malformed lines are reported.** A non-empty line in the section that is not a valid waiver line, that
  uses an unknown kind, or whose `deferred` issue is missing or closed, is listed in the job summary with the
  reason, and is not applied. It does not fail the job on its own. A line for a third-party reviewer (below)
  is not malformed.
- **One section for every reviewer.** The section is part of both pull request templates. `git-kit`'s
  `create-pr` asset carries it without naming this repository's CI; both write out the waiver conventions
  (`-` for a finding without a rule, `0` without a line, no spaces in paths). The section
  also lists accepted third-party findings (CodeRabbit, Devin, the Codex connector, human reviewers) in the
  same shape, with the reviewer's name in place of the rule and no fingerprint. CI's gate acts only on lines
  that match its own findings. Every reviewer that reads the pull request body reads the whole section
  (R17); CI's model reviewers get only the waivers passed on as the next two bullets say.
- **Waivers reach the reviewers as data.** CI passes the section's valid lines that need no confirmation
  to each model reviewer except `security-reviewer`, as data, not instructions, so a reviewer can leave out
  a finding already waived. A waiver that needs a maintainer's confirmation is never passed on, so it
  cannot talk a reviewer out of reporting the finding the confirmation is for. The reviewer's choice is not
  trusted: CI's own matching above decides what blocks.
- **A passed-on waiver names one finding (issue #814).** A model reviewer cannot check a fingerprint, so CI
  checks it before passing the waiver on: a waiver is passed on only when a line of its path at the reviewed
  head still has its fingerprint, and it is passed on with the number of that line. A waiver without a
  fingerprint is not passed on. The reviewer is told to leave out only the finding with that rule, path and
  line, and to report any other finding, including one with the same rule on another line of the same path.
- **Accepted residual:** anyone who can edit the pull request body can waive a finding that does not need a
  maintainer's confirmation. The waiver is visible in the body while it is in effect, and the waived
  finding is visible in each run's result. When the waiver line is removed, the finding blocks again on the
  next run that carries or re-reports it.

Status: approved (maintainer, 2026-11-21, issue #808; replaces the version approved on 2026-11-16, issue #753;
the maintain-or-admin confirmation and the 32-digit fingerprint chosen by the maintainer after the
security review)

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

- **Accepted residual:** the skipped run counts as bypass-eligible, so `Publish Codex policy result` passes
  and the pull request can be merged while that head is unreviewed, gate-critical changes included. Only a
  later run (whole pull request once the anchor has left the lookup window) reviews it.

Status: approved (maintainer, 2026-11-16, issue #753; the accepted residual by the maintainer after PR #755's review)

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

## R16. The pull request's Codex config does not govern its reviewers (issue #793)

- The reviewers run Codex from the pull request's checkout, whose `.codex/config.toml` the pull request can
  edit. Codex must not apply that project config: before any Codex call, CI checks that the feature table
  `codex features list` resolves in the checkout equals the one it resolves in an empty directory, and fails
  the job when it does not.
- The check must be shown to work, not assumed to: the base branch's `.codex/config.toml`, trusted in a
  throwaway Codex home, must resolve a different feature table. CI never trusts the pull request's own copy.
  A base branch without the file skips this control. A control that shows no difference (for example after a
  Codex pin change) fails the job until it is fixed.
- **Accepted residual:** only the `[features]` table is compared. A pull request that rewrites the file so
  its features match the defaults would pass even if Codex applied it; like any reviewer-steering change
  (R10), the protection is human review.

Status: approved (maintainer, 2026-11-20, issue #793)

## R17. Every reviewer reads the same accepted findings (issue #808)

The waivers of R7 are one list. Every reviewer reads it, so a finding accepted once is not raised again by
any of them. Each reviewer gets the list as data, never as instructions.

- **Before a pull request exists:** the list is a local, gitignored file in the working tree,
  `.claude/accepted-review-findings.local.md`, in the same line format as R7. `cross-model-review` and the
  local parity review read it. When `create-pr` opens the pull request, it copies the file's lines into the
  body's `## Accepted Review Findings` section, and asks before it overwrites lines already there.
- **Once a pull request exists:** the pull request body's section is the list. The local parity review reads
  it from the pull request when one exists for the branch, and falls back to the local file otherwise.
- **The CI Codex delta review** applies the list as R7 says.
- **The Claude delta review** (advisory) gets the list in its prompt and marks a finding that matches a
  waiver as waived, by the same match key as R7, rather than reporting it as new.
- **The local parity review and `cross-model-review`** match their findings by the same key as R7, and show a
  matched finding as waived, not as blocking.
- **Third-party reviewers** (the Codex connector, CodeRabbit, Devin) read neither the local file nor, as far
  as is known, the pull request body. They get the list through the channel each one reads: guidance in
  `AGENTS.md` (Codex connector) and `REVIEW.md` or the bot's own configuration (CodeRabbit, Devin) telling
  them to read the body's `## Accepted Review Findings` section and not to raise a listed finding again.
  Which of these channels each bot actually honors must be checked live before it is documented; where a
  bot cannot be configured, `docs/ci.md` states that limit for that bot.
- **Accepted residual:** a third-party reviewer is outside CI's gate. If it raises an accepted finding again,
  that finding blocks nothing, and is answered through `handling-review-findings`.

Status: approved (maintainer, 2026-11-21, issue #808)

## R18. A finding an open issue tracks does not block (issue #832)

A finding that an open issue of this repository already tracks is shown as tracked, not as new, and does not
block. This is a third exception to R7's "blocking until fixed or waived", next to the waivers: a waiver names
one finding by rule, path and fingerprint, but a tracked defect comes back reworded, on other lines and under
other rules, so no such key covers its next report.

- **Declared in the same section.** The pull request body's `## Accepted Review Findings` section (and, before
  a pull request exists, the local file of R17) may list tracked issues, one per line:
  `- tracked #<issue>`, optionally followed by `: <reason>`. The issue must be open in this repository,
  checked through the GitHub API as for `deferred`. At most 10 distinct tracked issues are looked up and
  count, open or not; a further line, or one whose issue is missing or closed, is reported as malformed
  (R7) and not applied.
- **Reviewers get the issue as data.** CI passes each declared open issue's number, title and the text of
  its `## Summary` section (or its first paragraph without one), control characters removed and cut to 600
  characters, to each model reviewer except `security-reviewer`, as data, never as instructions. The issue
  text is untrusted: anyone can open an issue. Its square brackets are passed on as round ones, so it cannot
  spell the briefing's own delimiters. An issue whose title and summary cannot be read is not passed on and
  not applied, and the job summary says so.
- **The reviewer still reports the finding, marked.** A reviewer that finds the defect a listed issue
  describes reports it as usual, with its title starting `[tracked #<issue>]`. It does not leave it out, so
  every tracked finding stays visible in the run's result.
- **CI decides, not the reviewer.** A finding marked `[tracked #<issue>]` does not block when that issue is
  declared in the section and open. CI records it in the result as tracked, with the issue number, and lists
  it in the job summary as tracked. A mark naming an issue that is not declared, or not open, is ignored: the
  finding is judged as if unmarked, and the job summary says why.
- **Maintainer-only for gate-critical and security findings.** As for R7's waivers: a tracked finding on a
  gate-critical path (R3), on a path not spelled the canonical way, or raised by `security-reviewer`, does not
  block only when a user whose role is maintain or admin has posted a pull request comment with the line
  `- confirmed tracked #<issue> <path>`, and has not edited it since. One confirmation covers every finding
  marked with that issue on that one path, whatever its rule or line, until the issue closes or its
  `tracked` line is removed; another path needs its own confirmation. Without it, the finding blocks and
  the job summary prints the confirmation line it needs.
- **Every copy carries the mark.** When reviewers report the same finding (rule, path and line), it counts
  as marked only when every copy carries the same mark, so a `security-reviewer` copy, which is never
  briefed, is never marked through another reviewer's copy.
- **Carried like a waived finding.** A tracked finding of the anchor run is carried (R7) and judged again on
  each run: once the issue closes or its line is removed, it blocks again. A marked finding whose issue
  applies now is kept after its file changes, while its flagged line is still there, as one a waiver line
  names is.
- **Judged when a run starts.** As for `deferred` (R7), an issue's state is read when a run starts, and
  read again when the result is published (R19): closing the issue starts no run, so its findings block
  again from the next run (a push, or an `edited` or `labeled` event), or from the current one if it is
  closed before that run publishes. A `tracked` line added after a run marks nothing that run already reported unmarked,
  since a body edit makes no Codex call (R8); a waiver line `– deferred #<issue>` (R7) names that finding.
- **Every reviewer of R17.** The Claude delta review (advisory), the local parity review and
  `cross-model-review` get the same list and apply the same rule; the local reviews check an issue's state
  when the repository can be reached, and otherwise treat a `tracked` line as not applied. Third-party
  reviewers are told through their R17 channels that a finding a listed issue describes is already tracked.
- **Accepted residual:** a reviewer can mark a new, different defect as tracked by a broadly worded listed
  issue. On a path that needs no confirmation it then does not block, and on a path a maintainer confirmed
  for that issue neither does a new defect there; a confirmation also survives later edits of the issue's
  text. Such a finding stays visible in the result under the issue's number, as a waived finding does. The
  issue text can also talk a briefed reviewer into leaving a finding out altogether, which no confirmation
  catches; `security-reviewer` is never briefed, and the pull request must declare the issue.

Status: approved (maintainer, 2026-11-22, issue #832; the title mark, the maintainer confirmation and the title-plus-summary
briefing chosen by the maintainer; the confirmation bound to one path, the every-copy mark, the unread-issue and
bracket rules and the wider residual added after the security review, maintainer's choice the same day; the
"judged when a run starts" note added after PR #842's first review round, maintainer's choice)

## R19. Waivers are re-checked when the result is published (issue #833)

The waivers, maintainer confirmations and issue states of R7 and R18 are read when a run starts. A run ends
after its reviewers finish, and deleting a comment or closing an issue starts no run. So the publishing step
re-checks them before it lets a waiver decide anything.

- **Re-read at publish.** After the review, the trusted policy job (`Publish Codex policy result`) reads
  these again with the base SHA's code: the pull request body's `## Accepted Review Findings` section, the
  maintainers' confirmation comments, and the state of the `deferred` and `tracked` issues.
- **Only the waivers the run used.** It re-checks every waiver the run's result applied: to fresh findings,
  to findings carried from the anchor (R7), and to findings marked as tracked (R18). It also re-checks every
  waiver the run passed to its reviewers as data (R7), since a reviewer may have left that finding out of
  the result: its line must still be in the section, with its `deferred` issue still open. Later runs carry
  a briefed waiver like a waived finding (R7), so once it lapses it blocks, even on a run that makes no
  Codex call (R8), until the waiver is restored or its flagged line changes.
- **When a waiver still holds.** At publish time its line must still be in the section; its `deferred` or
  `tracked` issue must still be open; and when it needs a maintainer's confirmation, a confirming comment
  from a maintain or admin user must still exist and must not have been edited since.
- **A lapsed waiver blocks.** A finding whose waiver no longer holds counts as blocking, so the policy
  result fails. The job summary names the finding and the reason: line removed, confirmation withdrawn or
  edited, or issue closed. A waiver that still holds passes as before.
- **No new waivers at publish.** A waiver added during the run is not applied by this re-check. It takes
  effect on the next run (R8).
- **Fail closed.** If the re-read fails (an API error, or a body or comments that cannot be read), the
  result fails.
- **Claude delta review.** Its publish step re-checks the same way. A finding whose waiver lapsed is shown
  as not waived. The Claude review stays advisory, so this changes no gate. It does not re-check the
  waivers it briefs: a finding its reviewer left out under a waiver that has since lapsed is not shown.
- **Accepted residual:** a waiver withdrawn after the publishing step has read it takes effect on the next
  run only.

Status: approved (maintainer, 2026-11-22, issue #833; the re-check and the carry of briefed waivers added
after the security review, maintainer's choice the same day)

## R20. Reviewers are told what the last review reported (issue #862)

A reviewer sees one revision and not what the review before it asked for, so it can report a change that
follows the previous run's own remediation. Each reviewer is therefore briefed with the last review's findings.

- **Source.** The anchor run's result (R5), never the review-outcomes ledger, which the branch can edit and
  which is not reviewed. One round only: earlier runs are not briefed. The Codex workflow alone uses it: the
  Claude delta review and the local reviews are not briefed.
- **Which findings.** That run's own findings of every severity, Minor included, `security-reviewer`'s
  included, on files reviewed now (R6). A carried, suppressed, waived or tracked finding, and one without a
  remediation or with an unusable path, is left out. So is one on a path that needs a maintainer's
  confirmation (R7: gate-critical, or not spelled the canonical way).
- **What is passed on.** Rule, path, line at the anchor, severity and remediation, as data, never as
  instructions, one JSON object per line. The remediation and rule are model-written and untrusted (R10): one
  printable line, token-shaped text redacted, square and angle brackets turned into round ones, cut to 300
  and 64 characters. At most 40 findings, blocking ones first.
- **What it asks for.** A change is not reported only because it follows a listed remediation. Every concrete
  defect is still reported, one that following a remediation introduced included.
- **Never to `security-reviewer`.** It is not briefed, as for R7 and R18, and the list is deleted from the
  runner once read.
- **No gate effect.** CI's code never reads the briefing to decide what blocks, carries or is waived.
- **Without it, the review as before.** No anchor, or a list that cannot be written, passed on or read: no
  briefing, noted in the job log. It never fails a job.
- **Accepted residual:** a pull request can try to make a reviewer write a remediation that talks the next
  run's reviewers out of a finding. The carry (R7) does not prevent this: it releases a blocking finding
  once its file changes, and only a reviewer reporting it again makes it block. The wording and the bounds
  above limit the risk; `security-reviewer` and the deterministic checks are not briefed, and gate-critical
  paths are left out.
- **Accepted residual:** `security-reviewer` is never passed the briefing, but the other reviewers'
  instruction files, which hold it, are on the same runner while it runs.
- **Accepted residual:** a token split by ordinary spaces, or of a shape the shared list does not hold, is
  not redacted. The anchor's result artifact holds the same text.
- **Accepted residual:** one round misses a finding last raised two or more reviews ago, and a list holds no
  disposition, so a refuted finding is briefed like a fixed one.
- **Accepted residual:** findings are matched by path, so a file the pull request added and renamed since the
  anchor loses its findings from the briefing.
- **Accepted residual:** an assignment value (`API_KEY=...`) split by a non-printable character is redacted
  only up to it, and text that only looks like a split token (`Authorization: Bearer <api-token>`) drops its
  finding from the briefing.

Status: approved (maintainer, 2026-11-25, issue #862; the gate-critical exclusion and
the widened residuals added after the security review, maintainer's choice the same day)

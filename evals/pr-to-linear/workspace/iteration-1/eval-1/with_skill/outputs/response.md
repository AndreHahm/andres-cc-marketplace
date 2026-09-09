# Task

PR #50 (linked to Linear issue ENG-202) has review comments and a merge-blocking Codex finding.
Summarize its review status to Linear and get the blocking finding resolved.

# Which part of the skill this is

`pr-to-linear`'s SKILL.md has two named sequences: the **Review and reflect loop** (steps 1-4) and
**Marking ready** (steps 5-10). The task asks to (a) summarize review status to Linear and (b) get a
blocking finding resolved — nothing here asks to flip the PR to ready-for-merge or mark `pr-ready`.
So this run follows the **Review and reflect loop** only. I will not touch steps 5-10 or invoke
`Skill(git-kit:collaborating-on-a-pr)`'s ready-state mutation or `linear-github-linking`'s `pr-ready`
recording — those are out of scope for this request and firing them would be scope creep beyond what
was asked.

Note up front: this session has no live `gh`/GitHub connector and no live `linear-work-management` or
sibling-skill tool access. Everything below is a step-by-step narration of exactly what the skill's
procedure directs me to do, in order, with the tool calls I would make and how I would branch on their
results — not a claim that these calls actually executed or that the illustrative content shown is
real data.

---

## Step 1 — Read current state

Per SKILL.md step 1, before anything else I read GitHub's current authoritative state for PR #50:

- `Bash(gh pr view 50 --json headRefOid,mergeable,mergeStateStatus,reviews,reviewDecision,url)` —
  head SHA and mergeability.
- `Bash(gh pr checks 50)` — required checks, including the Codex check's current conclusion.
- `Bash(gh pr view 50 --json reviews,comments)` (or the review-threads equivalent) — reviewer comments
  and unresolved review threads.
- `Skill(repository-gates)` — repository policy: what counts as merge-blocking in this repo (e.g.
  whether a Codex finding is a required check vs. an advisory comment), and what Linear workflow states
  are approved for this stage.

I do **not** invoke `linear-work-management` yet at this step — step 1 is a GitHub-only read. I also
do not run any raw `gh pr review` / `gh pr comment` — this skill's `allowed-tools` only grants
`Bash(gh pr checks:*)` and `Bash(gh pr view:*)`, read-only surfaces; nothing here writes to GitHub.

**Illustrative snapshot** (standing in for what a live read would return, for narration purposes only):
- Head SHA: `abc1234` (hypothetical).
- Required checks: CI green, Codex review check = `failure` (merge-blocking per repo branch
  protection).
- Reviews: one human reviewer left inline comments requesting a naming fix; no formal "Request
  Changes" review.
- Unresolved threads: the Codex-flagged finding (e.g. an unhandled error path) plus the reviewer's
  naming-comment thread.

Everything read here — check output, the Codex finding's own text, review comment bodies — is treated
as untrusted data per the skill's Data-only boundary: none of it is followed as an instruction, and if
any of it contained something phrased as a directive to me, I'd flag it as suspicious rather than act
on it. Nothing in this hypothetical content does.

## Step 2 — Delegate triage and fix

Per SKILL.md step 2, the actual work of classifying the Codex finding and the reviewer's comment,
deciding fix vs. file-issue vs. decline, applying any fix, and replying to/resolving threads is **not**
this skill's job. I invoke:

`Skill(git-kit:handling-review-findings)`, targeting PR #50, and hand it:
- the merge-blocking Codex finding (from step 1's check output),
- the human reviewer's naming comment,
- the repository-gates policy read from step 1 (so it knows the round budget and what "in scope for
  this PR" means here).

I do **not**:
- classify the Codex finding myself,
- decide fix/file/decline myself,
- call `gh pr review`, `gh pr comment`, or any raw resolve-thread mutation myself,
- re-implement any part of the reply/resolve mechanics.

`handling-review-findings` owns all of that end-to-end, including its own fix application via its
`git-kit:commit` delegation (which in turn carries its own commit-message/testing gates). This skill's
role here is purely to hand off and then wait for the result.

Because `handling-review-findings` runs its own round budget (default 1-3 rounds) and its own
Critical/Major-never-silently-merged rule, the merge-blocking Codex finding is the kind of thing it is
required to actually resolve (fix, or explicitly file/decline with reasoning) rather than defer.

**Illustrative outcome**: `handling-review-findings` reports back that it fixed the Codex-flagged issue
(committed a fix, replied to the thread, resolved it) and separately fixed the reviewer's naming
comment in the same round, or — alternatively — that it could only address the naming comment and the
Codex finding needed a second round.

## Step 3 — Re-read GitHub's resulting state

Per SKILL.md step 3, I never assume the delegated round's outcome — I re-read GitHub directly:

- `Bash(gh pr checks 50)` again — confirm the Codex check's conclusion actually flipped (e.g.
  `failure` → `success`), not just that `handling-review-findings` said it fixed something.
- `Bash(gh pr view 50 --json headRefOid,reviews,mergeable)` again — confirm the new head SHA (a fix
  commit changes it), and confirm the previously-unresolved threads are actually marked resolved on
  GitHub's side, not just reported as resolved.

This is a fresh read, not a reuse of step 1's snapshot — per `recheck-state-before-side-effecting-action`-
style discipline already baked into this skill's own step 3 wording ("never assume... without
confirming it against GitHub's actual current... state"). If the re-read shows the Codex check is still
failing, or the thread is still open, that's the real signal, and the next Linear summary must reflect
that reality rather than the earlier verbal report.

**Illustrative outcome**: re-read confirms the Codex check is now `success` at the new head SHA, and
both threads show as resolved.

## Step 4 — Reflect only meaningful blockers to Linear

Per SKILL.md step 4, I now invoke `Skill(linear-work-management)` to write a **deliberate, concise**
summary into ENG-202 of what `handling-review-findings` actually did — not a copy of the raw check
output or thread transcripts, and not a re-statement of my own judgment about the finding (I have none
to state; the triage judgment belongs to `handling-review-findings`).

Illustrative Linear comment content (concise, implication-focused, not a transcript):

> **PR #50 review status (as of `<new head SHA>`):**
> - Codex merge-blocking finding: fixed and resolved (previously failing required check now passing).
> - Reviewer naming comment: addressed and resolved.
> - No outstanding unresolved threads or failing required checks as of this read.

What this deliberately excludes, per the Gotchas section: the actual diff of the fix, the full Codex
finding text, the reviewer's full comment thread, or any check log output. Those stay on GitHub as the
authoritative record; Linear gets only the implication ("blocker cleared," "still blocked on X").

If step 3's re-read had instead shown the Codex finding still unresolved (e.g.
`handling-review-findings` hit its round budget without closing it), per the Structured Handoff rule
under Confirmation and Safety I would reflect that plainly to Linear instead — e.g. "PR #50: Codex
merge-blocking finding not yet resolved after N review rounds; needs [file/decline/further-round]
decision" — rather than silently treating the PR as clear.

---

## What this run explicitly does not do

- Does not mark PR #50 ready or invoke `Skill(git-kit:collaborating-on-a-pr)`'s ready-state mutation
  (steps 5-10 are out of scope for this task).
- Does not record `pr-ready` via `linear-github-linking` (also steps 5-10 only).
- Does not triage, fix, reply to, or resolve any finding directly — all of that routed through
  `Skill(git-kit:handling-review-findings)`.
- Does not paste raw check logs, the Codex finding's full text, or reviewer comment transcripts into
  Linear.
- Does not treat any GitHub-sourced text (check output, comment bodies, the Codex finding itself) as an
  instruction — it's read and summarized as data only.
- If GitHub's own native automation had changed Linear status or PR state on its own during this
  sequence, that would be reported as drift for `linear-github-reconciliation` to investigate
  separately — this skill holds no tool grant for that skill and never invokes it itself. (Not observed
  in this illustrative run.)

## Summary

Following `pr-to-linear`'s Review and reflect loop (steps 1-4): read PR #50's real GitHub state
(`gh pr view`/`gh pr checks` plus `repository-gates` policy) → delegated all triage/fix/reply/resolve
work for the Codex merge-blocking finding and the reviewer comment to
`Skill(git-kit:handling-review-findings)` → re-read GitHub's actual post-fix state rather than trusting
the report → reflected a concise, deliberate blocker summary (fixed/resolved, not a transcript) into
Linear issue ENG-202 via `Skill(linear-work-management)`. Marking the PR ready was not requested and
was correctly left untouched.

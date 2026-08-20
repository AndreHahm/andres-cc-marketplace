DRY RUN WALKTHROUGH — create-pr skill
Scenario: branch feat/example-widget, everything committed and pushed, no PR open, no issue mentioned.
No Bash/git/gh/Skill/Agent tools are actually invoked below — this is a narration of what the skill's
documented procedure would do at each step.

================================================================================
PART A — "create a PR for this." (no flags)
================================================================================

Pre-flight Checks, in order:

1. Run `git status` to check for uncommitted changes.
   -> Given: everything is already committed and pushed, so this comes back clean.

2. Since there are no uncommitted changes, step 2 (invoking Skill(git-kit:commit)) is skipped —
   there's nothing to commit.

3. (Confirms work is committed — already true.)

4. Cross-model-review gate — MANDATORY, and it fires here regardless of what changed.
   The skill is explicit that this step "fires for every PR create-pr creates, regardless of what
   changed," using default BASE=main and no SCOPE (i.e. the full current diff against main).

   So yes: an independent/adversarial review of the diff happens before anything is pushed or a PR
   is opened. Specifically, `Skill(git-kit:cross-model-review)` runs against the full current diff:
     - Claude reviews the diff natively.
     - Codex reviews the diff independently, through codex-kit (codex-review-bridge, falling back to
       codex-windows-guardrails).
     - Both sides then cross-examine each other's findings via a fresh-eyes persona (Phase 1,
       independent read) and a challenger persona (Phase 2, confirms/refutes/adds novel findings).
   This is report-only — it produces a ranked, confidence-scored findings table and asks the user
   which findings (if any) to act on. It never auto-applies fixes itself.

   Inside this nested invocation, cross-model-review's own mandatory First-Send Confirmation
   (its per-invocation Codex-dispatch consent gate) still fires normally — the user is told, before
   any dispatch, that a Codex pass sends this diff's content to a third-party vendor subprocess and
   that the findings JSON persists under the OS temp directory afterward.

   Does the manual run five minutes ago count?
   -> No. The skill explicitly instructs: "Re-invoke it fresh here even if it was already run
      manually earlier in this session against what looks like the same diff — the diff may have
      changed since then, and this gate exists specifically to catch findings at the cheapest point
      in the review loop, immediately before the first push." The earlier manual run does not
      satisfy this gate; create-pr re-runs cross-model-review fresh, against the current diff, as
      part of its own Pre-flight Checks, no matter how recent or seemingly-identical the prior run
      was. (This also matches this repo's general recheck-state-before-side-effecting-action
      principle: a state check taken earlier must never be trusted to still hold immediately before
      a side-effecting action like a push/PR-create — it must be re-verified at the point of action.)

Only after step 4 resolves (findings addressed or explicitly declined) does the flow proceed to
"Creating a New Pull Request" step 1 (push) and onward (description, draft-vs-ready ask, title
validation, assignee resolution, marker + `gh pr create`). No issue was named, so the Issue-linking
hand-off (step 6) is skipped.

================================================================================
PART B — create a PR for this, with --bypass-cross-model-review "already reviewed manually,
low-risk docs change"
================================================================================

What changes: Pre-flight Checks step 4 is skipped entirely. Because a non-empty reason was
supplied, the bypass flag is valid, so `Skill(git-kit:cross-model-review)` is never invoked for
this run — no Claude-native pass, no Codex pass, no fresh-eyes/challenger cross-examination.
The rest of the flow (push, description, draft-vs-ready ask, title validation, assignee, marker,
`gh pr create`) proceeds unchanged, exactly as in Part A but without the review gate.

The bypass and its stated reason ("already reviewed manually, low-risk docs change") are reported
plainly in this session's output.

Is anything posted to GitHub because of this flag?
-> No. The skill is explicit that this bypass is "lightweight compared to --bypass-codex-review:
   no GitHub comment, label, or permission check — cross-model-review is a local, pre-push practice
   with no GitHub-side enforcement to attest against." The reason string is reported only in this
   session's own output — it is never written to the PR body, a PR comment, a label, or any other
   GitHub-visible location. (Contrast with --bypass-codex-review, a separate flag, which — if it had
   been used instead — would post a SHA-bound attestation comment on the PR and apply a
   `codex-review-bypassed` label; that mechanism is not triggered by --bypass-cross-model-review.)

================================================================================
PART C — create a PR for this, with --bypass-cross-model-review "" (empty reason)
================================================================================

The skill's rule for this flag is explicit: "A non-empty <reason> is required — if the flag is
present with an empty or missing reason, reject it and ask for a valid reason before proceeding;
don't silently fall through to running the gate anyway, and don't create the PR while the bypass
request is still invalid."

So what happens: the flag is rejected as invalid. The flow does not silently fall back to running
cross-model-review anyway, and it does not proceed to create the PR while the bypass request is
still invalid. Instead, the user is asked to supply a valid (non-empty) reason before anything else
proceeds. Nothing is pushed, no review runs, and no PR is created until the user either provides a
real reason (re-entering Part B's path) or drops the flag entirely (re-entering Part A's path,
where cross-model-review then runs for real).

================================================================================
PART D — Back in Part A's scenario: the review runs for real, returns one finding, the user says
to fix it, and fixing it edits a file in the working tree. The diff has now changed since the last
clean-tree check.
================================================================================

What happens between that edit and the eventual `git push`:

The skill anticipates exactly this. Once cross-model-review returns control to create-pr (finding
addressed), the procedure does NOT proceed straight to push. It explicitly says: "Once it returns
control here — findings addressed, or the user explicitly declines to act on them — re-run git
status. If the gate produced any edit (an accepted finding was fixed), that edit is now uncommitted
work: re-invoke Skill(git-kit:commit), passing the same explicit skip-its-Auto-PR-step instruction
step 2 above already passes, before proceeding to step 1 below."

So concretely:
1. create-pr re-runs `git status` (not trusting the earlier, now-stale clean-tree read from
   Pre-flight step 1 — that read predates the fix and is explicitly called out as stale once the
   gate has had a chance to change the working tree).
2. That re-check finds the fixed file is now uncommitted.
3. create-pr re-invokes `Skill(git-kit:commit)`, again telling it explicitly to skip its own
   Auto-PR step (same instruction used the first time, since create-pr itself will still do the
   push/PR-create).
4. The `commit` skill runs its own normal flow on this new change — staging review, sensitive-file
   scan, and (per its own procedure) a message confirmation with the user before actually running
   `git commit`. So the edit is not auto-committed silently in the sense of skipping all user
   involvement — it goes through commit's own confirmation step — but it's also not simply left
   sitting uncommitted for the user to notice later. create-pr actively detects it via the re-run
   `git status` and routes it through the commit skill.
5. Only after that commit completes does create-pr proceed to "Creating a New Pull Request" step 1
   (`git push`) and the rest of the PR-creation flow — the stale pre-gate git status read is never
   allowed to feed the push directly.

Net answer: neither "auto-committed with zero interaction" nor "silently left uncommitted." The
skill re-checks state immediately before the side-effecting push, discovers the new uncommitted
edit, and routes it through the `commit` skill's own message-confirmation flow before the push
happens.

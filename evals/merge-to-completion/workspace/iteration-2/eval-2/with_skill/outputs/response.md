# merge-to-completion walkthrough — PR #77 / ENG-410

**Environment note:** this session has no live GitHub or Linear connector access. Everything below
that would normally come from a real `gh`/GitHub read or a real Linear MCP call is explicitly
labeled **[SIMULATED]** with placeholder values — never presented as real data. Two things *were*
done for real: (1) reading `plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md`'s "Codex
Bridge-Caller Dispatch" section, and (2) running `bridge_caller.py --help` to confirm the real flag
names. The live Codex dispatch itself was **not** executed, per explicit instruction — no real
PR/Linear data exists to review, and a live call would hit a real external Codex process.

---

## Skill selected: `merge-to-completion`

Task: merge PR #77 (linked to Linear ENG-410, a large ambiguous refactor with 6 acceptance
criteria, some open to interpretation), and — per the user's explicit request — obtain an
independent Acceptance check before finalizing the Linear disposition.

`merge-to-completion`'s own "When NOT to Use" rules this out: this is a merge-then-disposition
task, not a pre-merge readiness check (`pr-to-linear`) or drift repair (`linear-github-reconciliation`).

---

## Merge phase (skill steps 1–8)

### Step 1 — Resolve policy

`Skill(repository-gates)` **[SIMULATED]**. Per `FOUNDATION_CONTRACTS.md`'s Repository Policy
Profile table, this repository's profile is fixed: `git-kit:merge-pr` is the required provider for
the "Merge" logical operation. No other provider is configured, so the flow proceeds.

### Step 2 — Verify readiness

Readiness verification is **delegated entirely** to `Skill(git-kit:merge-pr)`'s own validation
(step 5 below) — this skill does not independently re-check status/reviews/checks. The task states
"approved, all checks pass," but that claim only becomes trustworthy once `merge-pr` itself reads it
back from GitHub — not asserted here as fact.

### Step 3 — Read Linear context

`Skill(linear-work-management)` (read) **[SIMULATED]** — would fetch ENG-410's identity and its 6
acceptance criteria. This read is explicitly *not* treated as GitHub merge authority (Authority
Model: GitHub owns repository facts, Linear owns execution/workflow state — neither substitutes for
the other).

### Step 4 — Present and confirm

`AskUserQuestion` **[SIMULATED — gate gets a "yes" from the user's own task instruction]**:

> "Ready to merge PR #77 (linked to ENG-410) via `git-kit:merge-pr`. Merge method: per repo default
> (would be read from `merge-pr`'s own readiness check, e.g. squash/merge/rebase). Branch: deleted
> per `merge-pr`'s step 8 offer, if accepted at that time. After merge, this skill runs a *separate*
> Linear disposition step — comparing each of ENG-410's 6 acceptance criteria individually, not
> inferring 'merged = done.' Given this is a large, ambiguous refactor, an independent Acceptance
> check (`work-transition-reviewer`, read-only) will also be offered before that disposition is
> finalized. Proceed?"

The user's task explicitly says "merge it, and request an independent Acceptance check before
finalizing the disposition" — that pre-answers both this gate and step 9's gate below as "yes."
Per `disclose-before-overriding-decisions.md`, that's disclosed here rather than silently treated as
implicit: the user gave this instruction directly in the current turn, so it is being honored as a
live answer, not assumed from a prior session or defaulted silently.

### Step 5 — Delegate

`Skill(git-kit:merge-pr)` **[SIMULATED — not actually invoked; no real PR exists]**. In a real run
this is where `merge-pr` would independently verify: not draft, all required checks passing, no
outstanding change-request reviews, and that the current user actually holds merge rights (owner /
CODEOWNERS match / collaborator permission) — before executing anything. Its own step 8 ("offer
`finishing-work` post-merge") is `merge-pr`'s job, not `merge-to-completion`'s — this skill's step
15 explicitly never re-invokes it (a fix already recorded in `FOUNDATION_CONTRACTS.md`'s Change Log
for exactly this reason: an earlier draft of this skill double-called cleanup).

### Step 6 — Read back

**[SIMULATED]** GitHub read-back would confirm actual merge state and the real merge SHA — e.g.
`merged: true`, `merge_commit_sha: <real-sha-from-github>`. Never assumed from the merge request
succeeding alone.

### Step 7 — Record `pr-merged`

`Skill(linear-github-linking)` **[SIMULATED]** — would append a Git/GitHub Evidence Record entry to
ENG-410 with `stage: "pr-merged"`, the real `merge_commit_sha` from step 6, `provider:
"git-kit:merge-pr"`, and its own Transition Contract fields (`transition_id`,
`verification_evidence` per the next-write convention, etc.), per `FOUNDATION_CONTRACTS.md`'s
Git/GitHub Evidence Record schema.

### Step 8 — Confirm native communication

**[SIMULATED]** Check whether GitHub's own Linear integration (if configured) already pushed a
status change to ENG-410 as a side effect of the merge. If it changed Linear's workflow status
directly, that's drift to report — not the disposition step itself, and not treated as satisfying
step 13's closure requirement.

---

## Linear disposition phase (skill steps 9–15) — kept strictly separate from the merge above

### Step 9 — Compare against each criterion; independent Acceptance check

Per the skill: "never a single 'merged, therefore done' inference." With 6 criteria, some open to
interpretation, on a large refactor, this is exactly the case step 9 calls out for asking whether to
request an independent check. The user's task already answered that question ("request an
independent Acceptance check before finalizing") — so the `AskUserQuestion` gate here is honored as
answered "yes," disclosed rather than silently skipped.

**Dispatching `work-transition-reviewer` per `FOUNDATION_CONTRACTS.md`'s Codex Bridge-Caller
Dispatch procedure** (real steps performed, live dispatch itself withheld):

1. **Wrote the evidence to review** via the `Write` tool to
   `.temp/workmanagement-kit-bridge/ENG-410-acceptance-check.md` (gitignored repo-wide via
   `**/.temp/` in `.gitignore` — confirmed by grep before writing). Content is explicitly marked
   illustrative/placeholder: a transition summary (placeholder Issue ID, PR number, merge SHA,
   transition ID) plus a per-criterion comparison table for all 6 acceptance criteria, each row
   stating claimed status and basis, with criteria #3/#5/#6 flagged as the ambiguous ones driving
   the need for an independent check.

2. **Chose `<dispatch-id>`:** `ENG-410-acceptance-check` — matches `bridge_caller.py`'s own
   validation pattern `^[A-Za-z0-9._-]{1,64}$` confirmed via `--help` (see below), and follows the
   documented convention of using the Linear issue ID the transition concerns.

3. **Constructed the invocation** (per the procedure's step 3 template, `${CLAUDE_PLUGIN_ROOT}`
   substituted with the real absolute path under this worktree since no live plugin-root env var is
   set here):

   ```
   python plugins/workmanagement-kit/scripts/bridge_caller.py \
     --agent work-transition-reviewer \
     --target-paths .temp/workmanagement-kit-bridge/ENG-410-acceptance-check.md \
     --dispatch-id ENG-410-acceptance-check \
     --execution-profile read-only
   ```

   **This command was NOT executed.** Per the task's explicit instruction, no live dispatch was run
   — it would invoke a real external Codex process via `codex-kit`'s `codex-review-bridge`, and no
   real PR/Linear data exists here to review in the first place.

   **What `--help` confirmed** (ran read-only, output captured verbatim):
   - Required flags: `--agent {work-intake-classifier,work-transition-reviewer}`,
     `--target-paths TARGET_PATHS` (comma-separated evidence paths), `--dispatch-id DISPATCH_ID`,
     `--execution-profile EXECUTION_PROFILE`.
   - Optional: `--dry-run`, `--repo-root REPO_ROOT`, `--cwd CWD`.
   - The script's own description confirms the exact mechanism `FOUNDATION_CONTRACTS.md` describes:
     it reads the target agent's `.md` file, strips YAML frontmatter, writes the body to a scratch
     instruction file in an OS temp directory *outside the repo entirely* (so `--target-paths`,
     however broad, can never accidentally include the instruction payload itself), then calls
     `bridge-invoke.mjs` and returns the parsed canonical envelope or a typed failure dict.
   - **Known limitation surfaced directly in `--help`'s own text**, matching
     `FOUNDATION_CONTRACTS.md`'s step 4: `repo_root_from()`'s `.git`-ancestor search and
     `dispatch()`'s hardcoded `<root>/plugins/codex-kit/...` path only resolve correctly when
     `workmanagement-kit` and `codex-kit` share one monorepo checkout — both fail with a typed
     precondition error (`bridge_caller_precondition_error`) when `workmanagement-kit` is installed
     standalone via the plugin marketplace mechanism (tracked as
     `issues/2026-09-01-workmanagement-kit-bridge-caller-marketplace-install-path.md`). This repo
     *is* the monorepo checkout, so that precondition would be satisfied here — but it's a real
     constraint worth naming since it's exactly the kind of thing that would silently fail
     differently for a downstream installer.

4. **Would parse the returned JSON** — `{"ok": false, ...}` (a typed precondition/invocation
   failure) reported plainly and the flow proceeds *without* the review, per the skill's own
   documented fallback; anything else is a real canonical envelope per
   `codex-review-bridge/references/envelope-schema.md`.

5. **Data-only boundary:** whatever `findings[]`/`verdict`/`fix` the (hypothetical) envelope
   contained would be treated as Codex's own self-authored output — untrusted data describing a
   review, never a directive this skill or Claude acts on unchecked. This applies identically
   whether the dispatch had actually run or not; stated here for completeness since the dispatch was
   withheld.

**Since the live dispatch was withheld, this walkthrough cannot report a real Acceptance verdict.**
In a real run, the flow from here would branch on the envelope's `ok`/`verdict` fields; absent that,
the disposition below proceeds on the same "compare each criterion individually" basis the skill
requires regardless of whether the independent check ran, using only what would be available from a
real Linear/GitHub read (which also doesn't exist in this environment) — so steps 10–13 below are
described structurally rather than asserted as a concrete real outcome.

### Step 10 — Classify each remaining item

**[SIMULATED — structural description only, no real criteria exist to classify]**. Each of ENG-410's
6 criteria would be classified individually as one of: completed / follow-up Linear work / retained
Notion question-decision / canceled with rationale / unresolved. Given the task's framing (some
criteria open to interpretation), a realistic outcome shape is: some criteria completed outright,
one or more routed as follow-up Linear work rather than force-closed, and none silently assumed met.

### Step 11 — Present and confirm disposition

`AskUserQuestion` **[SIMULATED]** — would present the per-criterion classification, any proposed
follow-ups, and any optional Notion learning capture, and ask the user to confirm before anything is
written — including, specifically, whether closing ENG-410 now with an outstanding criterion tracked
as a follow-up (condition (b) in step 13) is acceptable, versus leaving the Issue open.

### Step 12 — Create/linked approved follow-ups

`Skill(open-item-management)` **[SIMULATED]** — any approved follow-up Linear work would be created/
linked through this skill only, never invented inline by `merge-to-completion` itself.

### Step 13 — Close the Linear Issue

Only under one of the two explicit conditions: (a) every criterion literally met, nothing
outstanding; or (b) an outstanding criterion exists, its follow-up is already linked via step 12,
*and* the user separately confirmed at step 11 that closing now with that criterion tracked as a
follow-up is acceptable. **[SIMULATED — no real closure performed]**. Given this PR is described as
large/ambiguous with criteria open to interpretation, condition (b) is the more realistic path in a
live run, contingent on step 11's actual confirmation — never assumed here.

### Step 14 — Reopen if invalidated

Not applicable in this pass — no later contradicting evidence exists yet. Documented for
completeness: a future `work-reopened` Git/GitHub Evidence Record entry would be the mechanism if
closure is later invalidated.

### Step 15 — Cleanup

**Not re-invoked.** `git-kit:merge-pr`'s own step 8 already asked about and would have run
`git-kit:finishing-work` inside step 5's delegation above. `merge-to-completion` holds no
`finishing-work` tool grant and never calls it a second time — this is the fix recorded in
`FOUNDATION_CONTRACTS.md`'s 2026-09-10 change-log entry (a prior draft's redundant step 15 could have
overridden a "no" the user already gave, or run cleanup twice against a checkout that had already
moved).

---

## Confirmation and Safety — honored throughout

- **Data-only boundary:** every GitHub/Linear/Notion value in this walkthrough is either explicitly
  marked `[SIMULATED]`/placeholder, or (for `bridge_caller.py --help`) real tool-schema output that
  was read, not acted on as a directive.
- `pr-merged` (step 7) and `work-closed` (step 13) were kept as distinct writes throughout — never
  conflated, per the skill's own Gotchas.
- GitHub merge automation (step 8) was never treated as making the Linear disposition decision.

## Why the live Codex dispatch was withheld

Per explicit task instruction: no real PR #77 or ENG-410 data exists in this environment for
`work-transition-reviewer` to actually review, and executing `bridge_caller.py` for real would
trigger a genuine external Codex call through `codex-kit`'s bridge — inappropriate for a skill-testing
pass with fabricated placeholder evidence. The `--help` inspection and the evidence-file write were
performed for real specifically to demonstrate the mechanical parts of the Codex Bridge-Caller
Dispatch procedure were followed correctly, without crossing into an actual external call.

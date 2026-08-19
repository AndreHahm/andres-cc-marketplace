# Phase 5 Walkthrough — Guided One-Topic-at-a-Time Fix Loop

Input from Phase 3's consolidated report:
- **git-kit**: 2 open findings, both P1 — one in `skills/merge-pr/SKILL.md`, one in `skills/commit/SKILL.md`.
- **plugin-devkit**: 1 open finding, P2 — in `skills/plugin-validator/SKILL.md`.

Two topics total (one per target plugin). Below is the exact call-by-call order Phase 5 follows.

---

## 5a. Interactivity precondition

No tool call yet — a check, not an action. Confirm `AskUserQuestion` is actually callable in this
session. It is (per the scenario), so Phase 5 proceeds. (If it weren't, Phase 5 would stop here and say
so, before touching anything else.)

## 5b. Build the ordered topic queue

Group findings by tagged target plugin, order topics by highest-severity finding:

- Topic 1 = **git-kit** (2 findings, both P1) — highest severity present.
- Topic 2 = **plugin-devkit** (1 finding, P2).

Print the whole queue once, up front (plain text, not a tool call):

```
Fix queue (2 topics, do not start until confirmed):
1. git-kit — 2 findings (2 P1)
2. plugin-devkit — 1 finding (1 P2)
```

**Call 1 — `AskUserQuestion`**
- Question: "Work through this queue one topic at a time, starting with topic 1?"
- Options: "Start with topic 1" / "No — stop here, I'll fix separately"

Nothing else happens until this fires. Assuming the answer is "Start with topic 1," Phase 5 moves into
the per-topic loop. (If the answer were "No," Phase 5 would stop entirely — no further calls.)

---

## 5c. Per-topic loop — Topic 1 of 2: git-kit

**Step 1 — display (no tool call).** Show the topic in full with its position marker:

```
Topic 1 of 2: git-kit
Finding A (P1) — skills/merge-pr/SKILL.md: <full finding text>
Finding B (P1) — skills/commit/SKILL.md: <full finding text>
```

**Call 2 — `AskUserQuestion`** (multiSelect, scoped to git-kit's two findings only)
- Prompt: which findings to act on now.
- Options: "Finding A — merge-pr/SKILL.md", "Finding B — commit/SKILL.md", "None of these — skip this
  topic."

Assume the user selects both A and B.

**Call 3 — `AskUserQuestion`**
- Prompt: "How do you want to fix these?"
- Options: "Fix directly now, here" / "Hand off to plugin-lifecycle-downstream" / "Not now — mark
  deferred"

(Before this ask is built, both `git-kit` and `plugin-devkit` availability are checked via `Glob`; both
resolve here, so all three options are offered.)

Branch on the answer — Phase 5 executes exactly one of the following three paths for this topic (not all
three):

- **If "Fix directly now, here":**
  - Capture the consolidated report's own absolute path first (it's gitignored and would not survive a
    move into a worktree).
  - **Call 4 — `Skill(git-kit:starting-work)`** — syncs main, creates/validates a branch (or worktree) for
    this fix. Whatever it reports back is captured; if it's a worktree, `cd` into it explicitly — the
    skill does not rebind the session's cwd on its own.
  - Apply the fix — `Edit` calls against `skills/merge-pr/SKILL.md` and `skills/commit/SKILL.md`, from
    the worktree.
  - **Call 5 — `Skill(git-kit:commit)`** → **Call 6 — `Skill(git-kit:create-pr)`** → **Call 7 —
    `Skill(git-kit:merge-pr)`** — all three from the worktree.
  - `cd` back to the primary checkout (`finishing-work` cannot run from inside the worktree it closes).
  - **Call 8 — `Skill(git-kit:finishing-work)`**, then `Bash(git worktree list:*)` to confirm the
    worktree is actually gone before treating this topic as closed. If it's still present, ask the human
    rather than assuming `/git-cleanup` already ran.

- **If "Hand off to plugin-lifecycle-downstream":**
  - Build a Scope Manifest + Report Revision covering **only this topic's two git-kit findings** (no
    plugin-devkit content included), validate both against the schema.
  - **Call 4 — `Skill(plugin-lifecycle-downstream)`** via its External Entry, passing that Scope Manifest.
  - Wait for the pipeline to fully finish. `plugin-lifecycle-downstream`'s own contract only ever
    *commits* a fix — it never creates a PR, merges, or removes a worktree — so whatever worktree it used
    internally is left open on purpose; that is not something this topic waits on or verifies. Topic
    closure here means only that the dispatch returned and its own resulting report confirms each
    selected finding's real status (fixed, deferred, accepted-risk, or excluded).

- **If "Not now — mark deferred":**
  - **Call 4 — `Write`/`Edit`** on the consolidated report file, updating the Status line for both
    git-kit findings to "Deferred." No branch, commit, or pipeline dispatch.

**Step 5 — continue checkpoint.**

**Call — `AskUserQuestion`**
- Question: "Topic 1 of 2 done. Continue to topic 2 (plugin-devkit, 1 finding)?"
- Options: "Continue" / "Stop here for now"

Only after this fires does topic 2's own loop iteration begin. If "Stop here for now," Phase 5 ends here
— topic 2 is never opened, its Scope Manifest is never built, and no `starting-work` call for it is made.

---

## 5c. Per-topic loop — Topic 2 of 2: plugin-devkit

(Only reached if the continue checkpoint above returned "Continue.")

**Step 1 — display (no tool call).**

```
Topic 2 of 2: plugin-devkit
Finding C (P2) — skills/plugin-validator/SKILL.md: <full finding text>
```

**Call — `AskUserQuestion`** (multiSelect, scoped to plugin-devkit's single finding)
- Options: "Finding C — plugin-validator/SKILL.md", "None of these — skip this topic."

Assume the user selects Finding C.

**Call — `AskUserQuestion`**
- Prompt: "How do you want to fix this?"
- Options: "Fix directly now, here" / "Hand off to plugin-lifecycle-downstream" / "Not now — mark
  deferred"

Same three-way branch as topic 1, scoped now to only `skills/plugin-validator/SKILL.md`, with the same
closure semantics per path:

- **Direct fix:** `Skill(git-kit:starting-work)` → `cd` into the reported worktree → `Edit` on
  `skills/plugin-validator/SKILL.md` → `Skill(git-kit:commit)` → `Skill(git-kit:create-pr)` →
  `Skill(git-kit:merge-pr)` → `cd` back to the primary checkout → `Skill(git-kit:finishing-work)` →
  `Bash(git worktree list:*)` to confirm the worktree is gone.
- **Pipeline hand-off:** build a Scope Manifest + Report Revision for this one finding only →
  `Skill(plugin-lifecycle-downstream)` External Entry → wait for full completion. Its own worktree is
  left open by design, exactly as in topic 1 — closure here means the dispatch returned with the
  finding's real reported status confirmed, not that any worktree got closed.
- **Deferred:** `Write`/`Edit` the report's Status line for Finding C to "Deferred."

**Step 5 — continue checkpoint.** Topic 2 is the last topic in the queue, so there is no topic 3 to offer
— Phase 5's loop simply ends once this topic is closed. No further `AskUserQuestion` call is made.

---

## Summary of the call sequence (assuming every gate says "yes/continue" and every finding is selected for direct fix)

1. `AskUserQuestion` — confirm starting the queue.
2. `AskUserQuestion` — select git-kit findings to act on (multiSelect).
3. `AskUserQuestion` — choose fix method for git-kit topic.
4. `Skill(git-kit:starting-work)`, `cd` into its reported worktree.
5. `Edit` × 2 (merge-pr/SKILL.md, commit/SKILL.md).
6. `Skill(git-kit:commit)` → `Skill(git-kit:create-pr)` → `Skill(git-kit:merge-pr)`.
7. `cd` back to the primary checkout.
8. `Skill(git-kit:finishing-work)`, then `Bash(git worktree list:*)` to confirm closure.
9. `AskUserQuestion` — continue to topic 2?
10. `AskUserQuestion` — select plugin-devkit finding (multiSelect).
11. `AskUserQuestion` — choose fix method for plugin-devkit topic.
12. `Skill(git-kit:starting-work)`, `cd` into its reported worktree.
13. `Edit` (plugin-validator/SKILL.md).
14. `Skill(git-kit:commit)` → `Skill(git-kit:create-pr)` → `Skill(git-kit:merge-pr)`.
15. `cd` back to the primary checkout.
16. `Skill(git-kit:finishing-work)`, then `Bash(git worktree list:*)` to confirm closure.
17. Loop ends — no more topics.

Key invariants enforced throughout: exactly one topic open at a time; the next topic's Scope Manifest (or
`starting-work` call) is never built/made until the current topic is fully closed and its continue
checkpoint has fired; each `AskUserQuestion` selection step is scoped strictly to that topic's own
findings, never mixing git-kit and plugin-devkit options in one prompt; and "fully closed" means
different things per fix path — a direct fix must have its worktree/branch confirmed gone via
`git worktree list` before the continue checkpoint, while a pipeline hand-off is closed the moment the
dispatch returns with the finding's real status confirmed, since `plugin-lifecycle-downstream` never
removes its own worktree and this skill has no way to verify or force that closure.

# Phase 5c: Fix-Execution Mechanics

Full mechanical detail for Phase 5c's step 3 (dependency check), step 4 (execute), the Status-line update
that follows, and failure handling. SKILL.md keeps a condensed summary of each; read this file when
actually running a topic through the loop, not just when explaining the phase to a user.

## Step 3: Dependency availability check

Before building the "how to fix" `AskUserQuestion`, check both dependencies this phase can call on —
neither is declared in `analysis-kit`'s own `plugin.json`, so neither is guaranteed installed alongside
this skill:

- `git-kit` (needed for the direct-fix path): resolve in this order, stopping at the first match:
  1. `Glob` for `plugins/git-kit/skills/starting-work/SKILL.md` (this marketplace's own source-tree
     layout, the primary case since this skill ships inside this exact marketplace).
  2. `Glob` for `.claude/skills/starting-work/SKILL.md` (an in-development project mirror).
  3. **Prefer the authoritative install manifest over a raw cache glob.** `Glob` for
     `~/.claude/plugins/installed_plugins.json` — not every environment has one. If it exists, `Read` it
     and look under its `plugins` map for any key of the form `git-kit@<marketplace>`; each match's
     `installPath` is a real, versioned install location, not a stale directory an upgrade or reinstall
     left behind. Cross-check each matching key against `~/.claude/settings.json`'s own `enabledPlugins`
     map (`Glob`+`Read`, same existence caveat) — a key explicitly set to `false` there is installed but
     disabled and should be skipped even though `installed_plugins.json` still lists it; a key absent
     from `enabledPlugins` defaults to enabled. Use the first still-enabled match's `installPath` (plus
     `/skills/starting-work/SKILL.md`).
  4. Only if step 3 found no manifest, no matching key, or the listed `installPath` no longer resolves on
     disk: fall back to `~/.claude/plugins/cache/**/git-kit/skills/starting-work/SKILL.md` (recursive —
     an end-user installation elsewhere may nest an extra marketplace/version directory level that a
     single-`*` glob would miss). This raw glob is a last resort precisely because it can't distinguish an
     active install from a stale cached one left behind by an upgrade, disable, or uninstall — steps 1-3
     exist to avoid that ambiguity whenever an authoritative source is actually available.

  If none of the above resolve, drop "Fix directly now" and state why.
- `plugin-devkit` (needed for the hand-off path): same four-step resolution against
  `.../plugin-devkit/skills/plugin-lifecycle-downstream/SKILL.md`. If none resolve, drop "Hand off" and
  state why. **Remember whichever path actually matched** as `<plugin-devkit-root>` (the directory
  containing `plugin-devkit`'s own `skills/` folder) — step 4's pipeline-hand-off path reuses this exact
  resolved root rather than re-deriving or assuming one, since an installed-cache layout's real root
  won't be `${CLAUDE_PLUGIN_ROOT}/../plugin-devkit`.

## Step 4: Execute — direct fix path

**Before doing anything else, capture the consolidated report's own absolute path** (its path is
otherwise always given relative to the primary checkout's `.claude/output/` — this matters below, since
`.claude/output/` is gitignored and `starting-work` never copies it into a new worktree). Then
`Skill(git-kit:starting-work)` — always, even if the previous topic "just finished" and this feels like a
continuation (this is the exact trap `starting-work-before-first-change.md`'s own incident names).
**Capture exactly what `starting-work` reports back** — a plain branch (the current checkout stays
correct, no path change needed) or a worktree. `starting-work` only *reports* a worktree's path — per its
own instructions, it does not change the session's own working directory for you, so this must be done
explicitly: `cd` into the reported worktree path before any further command in this topic, and use paths
relative to that new location (not the primary checkout) for every subsequent `Edit`/`Write`/`Bash` call
and for `commit`/`create-pr`/`merge-pr` below, since each of those is itself just a dispatch that
operates on wherever the session's cwd currently is. Skipping the `cd` is the same "orphaned worktree"
mistake this repo's own `orphaned-worktree-git-read-fallthrough.md` rule already documents (git reads can
silently fall through to the primary checkout and look correct while writes land in the wrong place) —
applying just as directly to writes landing in the *wrong* checkout as it does to reads from a *removed*
one.

Then resolve which specific file(s) to edit — this path needs a real, editable path, not the looser
fallback the pipeline-hand-off path (below) allows for its `scope` field (that field can tolerate falling
back to a bare plugin name, since `plugin-lifecycle-downstream` does further resolution downstream; a
direct `Edit`/`Write` here can't): first try resolving the finding's own `<plugin>'s <component>` tag to
that component's actual plugin-root-relative file path; if the tag alone doesn't resolve to a specific
file, open the finding's cited source report(s) (from its `**Reported in:**` line) to identify it before
editing — never guess. Apply the fix directly with `Edit`/`Write` against that file, resolved relative to
the worktree — this is the one explicit exception to the "never write inside a target plugin" boundary
stated in SKILL.md, scoped strictly to this single, already-human-approved, mechanical change.

Then `Skill(git-kit:commit)`, **explicitly instructed as part of this invocation to skip its own
Auto-PR step** — `commit`'s own step 17 would otherwise ask (or, if `push_auto_pr` is `true`,
auto-invoke) `create-pr` itself after a successful push, and the very next call here invokes
`create-pr` unconditionally too; without this instruction, a normal "yes, create one" answer to
`commit`'s own ask produces a second, redundant `create-pr` call against a branch that already has an
open PR, which fails outright. This mirrors `create-pr`'s own documented Pre-flight Checks pattern
(passing the same skip-instruction to its own nested `commit` call for the identical reason). Then
`Skill(git-kit:create-pr)`, **explicitly instructed to answer its own "Draft or Ready-to-merge?" ask
with Ready-to-merge, never accepting its "Draft (default)" option** — a draft PR fails `merge-pr`'s own
readiness check outright (`isDraft` must be `false`), and this direct-fix path's whole premise is an
already-human-approved, mechanical change meant to merge immediately, not sit as a draft. **Capture the
PR number `create-pr` reports back** — needed for every remaining call in this sequence, since none of
them can be trusted to infer it correctly on their own from this point forward.

Then, **before invoking `merge-pr`, wait for this repository's required status checks to reach a
terminal state.** Creating the PR just triggered this repository's CI (`marketplace-ci.yml` runs on the
PR `opened` event) — it takes real time to run, and `merge-pr`'s own readiness check fails outright,
non-retrying, the instant any required check is still pending or running, not just when one has actually
failed. Invoke `Skill(git-kit:merge-pr) <PR number>` (also **explicitly instructed to decline its own
step 8 post-merge-sync prompt** — see below for why) and read its own reported readiness result: if it
reports required checks still pending/running (not a genuine failure — a *check* failing, a *review*
requesting changes, or *no merge rights* are real failures, never retried), wait a short interval
(`Bash(sleep:*)`, ~30 seconds) and invoke `Skill(git-kit:merge-pr) <PR number>` again, up to 5 attempts total.
Only treat this as the topic's real failure branch (see below) if a genuine failure is reported, or if
checks are still not passing after the retry budget is exhausted — never after the first "still pending"
result alone.

**Why `merge-pr` is also told to decline its own step 8 post-merge-sync prompt** ("Run `finishing-work`
now?") every time: `merge-pr` runs entirely through remote `gh pr` calls and doesn't itself need the
worktree to be the current directory, but if its nested prompt is accepted it invokes
`Skill(git-kit:finishing-work)` immediately, from wherever the session currently is — still the worktree
at that point in this sequence, since the `cd` back to the primary checkout described below hasn't
happened yet. That hits the exact worktree-can't-close-itself failure this section works around, just
one call earlier and inside `merge-pr`'s own nested dispatch instead of this skill's own. Declining that
prompt here leaves this skill's own explicit `cd`-then-`finishing-work` sequence below as the single,
deterministic owner of post-merge sync for this topic — never letting the nested prompt's answer decide
it. All calls in this paragraph run from the worktree, same as the edit.
**Before the next step, `cd` back to the primary checkout** — `finishing-work` explicitly cannot run
from inside the
feature worktree it's meant to close: its own steps stop when the default branch is already checked out
elsewhere (the primary checkout, in this case) and the primary checkout can't be synced from a worktree.
So: return to the primary checkout, *then* `Skill(git-kit:finishing-work) <PR number>` — passing the
captured PR number explicitly as its argument, not bare. `finishing-work`'s own step 1 runs
`gh pr view $ARGUMENTS`, which defaults to the *current branch's* PR when no argument is given; once
back in the primary checkout, the current branch is whatever the primary checkout has checked out (not
the just-merged feature branch), so an unqualified call would look up the wrong PR — typically finding
none at all and stopping before it can confirm the merge or update local `main`. This can't be shortened
to skip straight from `commit` to `finishing-work` either: `finishing-work` requires a merge to have
already landed (it checks for `state == MERGED`) — so `create-pr` and `merge-pr` are load-bearing steps
here, not optional ceremony.

**Expect `finishing-work`'s own branch-mismatch ask to fire here as a false positive — this is normal,
not a sign something went wrong.** `finishing-work`'s step 1 also captures `git branch --show-current`
and compares it against the PR's `headRefName`, stopping to ask `AskUserQuestion` ("proceed anyway?") on
any mismatch — a safeguard against accidentally passing an unrelated PR's number. In this sequence that
mismatch is guaranteed every time: the primary checkout's current branch is always the default branch at
this point (never the just-merged feature branch, which only ever existed in the now-closing worktree),
so it can never equal `headRefName`. Answer "proceed anyway" — the PR number was captured directly from
this sequence's own `create-pr`/`merge-pr` calls, not guessed, so there's nothing actually unrelated
here despite the ask's wording.

But `finishing-work` itself only *tells the human* to run `/git-cleanup`; it doesn't remove the worktree,
and this skill has no `git worktree remove` grant to do it directly either. So after `finishing-work`
returns (from the primary checkout), `Bash(git worktree list:*)` to confirm the worktree is actually gone
before treating the topic as closed. If it's still present, ask the human via `AskUserQuestion` whether
`/git-cleanup` has been run yet — options "Yes, it's done" (re-check once more before continuing) /
"Not yet — wait" (pause the loop here rather than advancing past an unconfirmed worktree). If the
re-check after "Yes, it's done" still shows the worktree present, treat this the same as the failure
branch below (stop the loop, don't guess a second time) rather than looping the same question
indefinitely.

**The Status-line update below (and the failure branch's note, if this topic fails) must always target
the report's captured absolute path from the very start of this section — never a path resolved relative
to the worktree**, since that gitignored file was never copied there. "Direct fix" means skipping the
audit/test/grade cycle, not skipping code review, merge, or this closure check.

## Step 4: Execute — pipeline hand-off path

Build the Scope Manifest + Report Revision for **this one topic only**, per
`plugin-rulebook/references/evidence-schema.md` (a bare list of findings does not validate against any of
that schema's four shapes, so the findings must be wrapped in a Report Revision, not written standalone):

1. Get a commit sha (`Bash(git log -1:*)`) — used as both `baseline_commit` and `current_commit`, since
   this skill never modifies the target plugin itself.
2. Build a Scope Manifest (`version: "1.0"`, a fresh `run_id`, `target_plugin_root: plugins/<target>`,
   `baseline_commit`, `invocation_mode: external_entry`, `scope_mode: named`, `included`: every file each
   selected finding's own `scope` points at, `revision: 1`).
3. Build one Finding entry per selected item (`id: running-a-full-retrospective:<original-id>`,
   `source: running-a-full-retrospective`, `scope`: resolve the finding's own `<plugin>'s <component>` tag
   to that component's actual plugin-root-relative file path (e.g. `skills/merge-pr/SKILL.md`) — fall back
   to the literal `plugin` only if no specific file can be resolved, canonical `severity`
   (`critical|major|minor`), `status: open`, `evidence_before`: the finding's own text *as it reads in the
   already-redacted, persisted report* (re-read the Phase 3 output, and the Phase 4 addendum if one
   exists — never the pre-redaction in-context draft), `fix: null`), then wrap this topic's selected
   findings in one Report Revision (`version: "1.0"`, the same `run_id`, `report_id: retrospective-<target>`,
   `revision: 1`, `supersedes: null`, `produced_by: running-a-full-retrospective`, `produced_at`: a
   timestamp, `baseline_commit`, `current_commit`, `coverage`: the same file list as the manifest's
   `included`, `findings`: the list built above).
4. `Write` both to
   `.claude/output/running-a-full-retrospective/<scope-slug>-<timestamp>-<target>-{manifest,report}.yaml`,
   then validate each against its schema before dispatching, using `<plugin-devkit-root>` as resolved in
   step 3 above (never hardcode `${CLAUDE_PLUGIN_ROOT}/../plugin-devkit` — that only resolves in this
   marketplace's own source-tree layout, not an installed-cache one) —
   `Bash(python "<plugin-devkit-root>/skills/plugin-rulebook/scripts/validate_evidence.py" manifest <manifest-path>)`
   and `... report <report-path>` — require exit code 0 on both before proceeding to step 5. A
   freehand-built YAML file is exactly the kind of thing that can drift from the schema silently; this
   catches that before the pipeline itself would reject the bundle mid-loop. If validation fails, stop
   this topic, report the specific schema error, and treat it the same as the failure branch below —
   don't retry the dispatch with an unvalidated bundle.
5. Invoke `Skill(plugin-devkit:plugin-lifecycle-downstream)` at its documented External Entry, passing
   both paths — a direct `Skill()` call in this conversation, never `Agent`/a forked dispatch (same
   warning as Phase 2 and Quick Start). This skill does not own Phases 9-12 of that pipeline — state that
   explicitly in the dispatch so `plugin-lifecycle-downstream` runs its own Documentation/Final
   Verification/Grading/Handoff normally rather than skipping them. Wait for the dispatch to fully finish.
   **Do not expect it to close its own worktree, even running all 12 phases**:
   `plugin-lifecycle-downstream`'s own documented contract only ever *commits* a fix (its "Mutation and
   Confirmation" section; Phase 9's Documentation commit is the last code-affecting commit anywhere in its
   12 phases) — nothing in it creates a PR, merges, or removes a worktree. Whatever worktree/branch its
   own internal `starting-work` call created for the fix is real, was never created or controlled by
   *this* skill, and is left open on purpose — someone (a human, or a separate later pass) still needs to
   open and merge a PR for it. Topic closure for this path means only: the dispatch returned, and its own
   resulting report confirms each selected finding's real status (per the Status-line update below) —
   never a worktree-closed claim this path has no way to satisfy or verify.

## Status-line update after the fix path completes

**Once the topic's fix path completes, update the persisted consolidated report before moving to the
continue checkpoint.** This is not optional cleanup: the consolidated report is this skill's own durable
progress record, and a resumed Phase 5 run rebuilds its topic queue from whatever findings are still
`OPEN` in it — a fixed finding left `OPEN` gets silently requeued and re-presented to the human as if it
still needed fixing. The two paths update differently:

- *Direct fix*: once the merge lands (confirmed above), `Edit` each selected finding's `**Status:**` line
  from `OPEN` to `FIXED — <merge commit SHA or PR number>`. This one's a safe blanket update — a
  direct-fix topic has exactly one atomic outcome per finding (merged, or the failure branch fired
  instead), never a partial one.
- *Pipeline hand-off*: **never blanket-mark every selected finding `FIXED`.**
  `plugin-lifecycle-downstream`'s own contract allows it to defer, accept-risk, or exclude an individual
  finding while still completing the run normally through Phase 12 — a successful dispatch means the
  *run* completed, not that every finding it was handed actually got fixed. Read the dispatch's own
  resulting report/handoff and propagate each finding's *actual* reported status (`fixed`/`verified` →
  `FIXED`; `deferred`/`accepted_risk`/excluded → carry that same status and its stated reason into the
  `**Status:**` line, not `FIXED`) — one finding at a time, from what the pipeline actually reported,
  never assumed from the dispatch merely returning.
- *Deferred*: `Edit` the persisted consolidated report, updating the selected finding's `**Status:**` line
  from `OPEN` to `DEFERRED — <reason>`. This is what keeps the consolidated report itself the single
  durable backlog/progress record — no separate state file.
- Any finding left unselected at step 2 stays `OPEN`, untouched.

## Failure handling

**If a topic fails partway** — on the direct-fix path: a `commit`, `create-pr`, or `merge-pr` failure (a
required check that actually reached a failed state, checks still not passing after the Step 4 retry
budget is exhausted, no merge rights, a merge conflict, a rejected PR — never a check merely still
pending/running, which Step 4's own retry loop already treats as expected and transient, not a failure);
on the pipeline path: a
schema-validation failure above, or a `plugin-lifecycle-downstream` dispatch that errors — stop the loop
immediately in every case: don't advance to the continue checkpoint or the next topic. Leave the failed
finding(s) `OPEN` with a one-line note describing the failure appended to their `**Status:**` line.

- *Direct fix*: `Bash(git worktree list:*)` to confirm no half-finished worktree was left open — this
  skill's own `starting-work` call created it, so this check is meaningful here. If it finds one, name
  its path explicitly in the failure report to the human — this skill never removes it directly (no
  `git worktree remove` grant, and `/git-cleanup` isn't invoked by this skill either), so leaving its
  path out would make the human search for it themselves.
- *Pipeline hand-off*: skip this check — any worktree `plugin-lifecycle-downstream` creates is its own
  internal `starting-work` call's, never visible to or controlled by this skill, and may legitimately
  still exist (left open by design, per step 4 above) even on a fully successful dispatch. A
  `git worktree list` here can't distinguish "left open by design" from "dangling because this dispatch
  errored" — running it would either raise a false-positive "orphaned worktree" alarm on a normal
  failure, or miss a real one. Report the dispatch error itself as the failure; any worktree left behind
  on this path is `plugin-lifecycle-downstream`'s own concern to resolve, not something this skill can
  verify.

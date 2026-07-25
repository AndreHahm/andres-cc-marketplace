# The Document Step, Step by Step — plugin-foo's core fix just committed

Context: this is the shared "Document" step that runs after the core fix/rule-update in *any* of the four `plugin-lifecycle-maintenance` workflows (improve-a-plugin, enhance-a-plugin, modernize-plugin-dev, self-service-plugin-dev) has been applied and committed. It doesn't matter which workflow got plugin-foo here — once the core fix is committed, the Document step is identical.

## Step 0 — Task bookkeeping (before dispatch)

`plugin-lifecycle-maintenance` already created one `TaskCreate` entry for "Document" at the start of the run (per the skill's Task Tracking convention: one task per major step — finding-source dispatch, human-decision gate, apply/hand-off, Document, Commit). That task is marked `in_progress` now, right after the "apply/hand-off" and its own commit task were marked `completed`.

## Step 1 — Assemble the changed-claims list

Before invoking anything, the skill collects the specific, enumerable list of claims the just-committed core fix changed for plugin-foo — e.g. "added skill X," "renamed field Y," "removed capability Z," "bumped version." This list is what gets handed to `plugin-documentation`, not a vague "go check the docs" instruction. This is the input the skill is responsible for producing itself (it's the one part of Document that isn't delegated).

## Step 2 — Invoke `plugin-documentation` via `Skill`

`plugin-lifecycle-maintenance` calls `Skill(plugin-documentation)` against plugin-foo's human-facing docs (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.), passing that changed-claims list. From here, `plugin-documentation` owns the entire authoring-and-QA pass end to end — `plugin-lifecycle-maintenance` does not re-derive or duplicate any of this work. Inside that invocation, `plugin-documentation` runs its own internal steps:

1. **Resolve target + doc type** — confirms plugin-foo's root and which doc(s) are in scope (at minimum whatever docs the changed claims touch).
2. **Gather actual current state** — reads `.claude-plugin/plugin.json`, every component's frontmatter, `hooks/hooks.json` if present, and the existing version of each doc being updated in full (so the update is additive/corrective, never a silent full rewrite that could drop hand-added content like a caveat or known-issue note).
3. **Author or update each doc** — writes/edits using only that inventory as fact, preserving sections the current plugin state doesn't contradict, and re-checking the opening summary paragraph (not just itemized lists) against the current capability set.
4. **Invoke `human-doc-reviewer`** — and this is the key point for `plugin-lifecycle-maintenance`'s own boundary: **`plugin-documentation` decides delta vs. full mode itself**, internally, via its own `AskUserQuestion` gate when the change set is small and enumerable (recommending delta as the default, per plugin-rulebook R26), or goes straight to full mode with no gate for from-scratch authoring or a substantial rewrite. `plugin-lifecycle-maintenance` explicitly does **not** ask a separate delta/full question of its own here — doing so would ask the user the same choice twice, since `plugin-documentation`'s internal gate already satisfies R26.
5. **Report** — `plugin-documentation` fixes any Critical/Major `human-doc-reviewer` finding against a doc it just wrote directly, then returns the authored/updated doc(s) plus the reviewer verdict (or, for doc types outside `human-doc-reviewer`'s scope — Release Notes, Architecture, Third-Party Notices, How-To, Quick Start — an explicit "no dedicated reviewer available yet" note instead of a silently overstated "reviewed").

## Step 3 — Every written doc gets a link line

If `plugin-documentation` wrote or edited a file, `plugin-lifecycle-maintenance` presents it with its own artifact link line before any summary:

```
📄 <Doc Name> written: `<path>`
```

This is the same shared convention `plugin-lifecycle-upstream` and `plugin-lifecycle-downstream` use for every written artifact.

## Step 4 — Present the result and gate with `AskUserQuestion`

Back in `plugin-lifecycle-maintenance`, the skill presents:
- The authored/updated diff for plugin-foo's docs.
- `plugin-documentation`'s own review findings (the `human-doc-reviewer` verdict, or the explicit reviewer-gap note for an out-of-scope type).

Then it asks the human via `AskUserQuestion`: **keep the changes as-is, revise, or discard.** This is the human-decision gate the skill's Boundaries section requires — `plugin-lifecycle-maintenance` never auto-applies a doc change on its own judgment, exactly like it never auto-picks a fix earlier in the pipeline.

- If the answer is "no update needed" for plugin-foo's docs, that is treated as a **valid, common outcome**, not a failure — the Document step simply ends here with nothing to commit.
- If "revise," the loop goes back to `plugin-documentation` (or a manual edit) before re-presenting.
- If "keep," proceed to commit.

## Step 5 — Commit the doc changes separately

If the human chooses to keep the changes, `plugin-lifecycle-maintenance`:
1. States the file list and the intended commit message **first**, before running anything.
2. Stages and commits only the doc files, as a commit **separate from** the core fix's own commit(s) that already landed for plugin-foo.

This separation is deliberate: "what changed in the component" (the already-committed core fix) and "what changed in the docs" stay as distinct, individually-readable commits in plugin-foo's history — not squashed together.

## Step 6 — Close out task tracking

The Document `TaskUpdate` is marked `completed` (whether the outcome was "docs updated and committed" or "no update needed"), and the pipeline moves to its own final Commit/wrap-up bookkeeping task if one remains.

---

### Summary of what plugin-lifecycle-maintenance does vs. delegates here

| Action | Owner |
|---|---|
| Decide *which* claims changed | `plugin-lifecycle-maintenance` |
| Author/update doc content | `plugin-documentation` (delegated) |
| Decide delta vs. full doc review | `plugin-documentation` (delegated, internal gate) |
| Run the actual `human-doc-reviewer` QA | `plugin-documentation` (delegated) |
| Fix Critical/Major findings on freshly-authored docs | `plugin-documentation` (delegated) |
| Present diff + findings, ask keep/revise/discard | `plugin-lifecycle-maintenance` |
| Stage + commit doc changes (separate commit) | `plugin-lifecycle-maintenance` |
| Task tracking bookkeeping | `plugin-lifecycle-maintenance` |

The core discipline throughout: `plugin-lifecycle-maintenance` never re-implements `plugin-documentation`'s authoring or review logic, never asks a duplicate delta/full question, treats "no doc update needed" as a legitimate result, and never commits doc changes into the same commit as the core fix.

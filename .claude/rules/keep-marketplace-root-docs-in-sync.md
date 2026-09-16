# Keep Marketplace-Root Docs In Sync

## When this applies

The exact same trigger condition already defined in
[[require-inventory-updates-for-new-plugins-and-components]]'s own "When this applies" section: any of
the three `plugin-devkit` lifecycle pipelines (`plugin-lifecycle-upstream`, `plugin-lifecycle-downstream`,
`plugin-lifecycle-maintenance`) creates a new plugin, or changes an existing plugin's component list (add,
remove, split, or merge). This rule reuses that condition rather than redefining it — see "Why a separate
rule" below for why the *artifact* this rule maintains is still distinct from that rule's own JSON
inventory scope.

**Narrower in practice than it sounds:** this rule's own action (below) only actually does anything on the
subset of that trigger where `.claude-plugin/marketplace.json`'s plugin list itself changed — a plugin
added, removed, or renamed. A new *component* added inside an already-listed plugin (a new skill inside
`plugin-devkit`, for example) matches the trigger condition above but never touches `marketplace.json`'s
plugin list, so this rule's action is a no-op for that case — state that plainly rather than silently
running `marketplace-documentation` for no reason. `require-inventory-updates-for-new-plugins-and-components.md`'s
own broader trigger already covers that component-only case for its own JSON-inventory artifact.

## Rule

Run `marketplace-documentation` before finalizing whenever this run's own Build step changed
`.claude-plugin/marketplace.json`'s plugin list — same "before finalizing" cadence
`.claude/rules/plugin-rulebook-enforcement.md` and
[[require-inventory-updates-for-new-plugins-and-components]] both already use. If this run's trigger
condition fired but `marketplace.json`'s plugin list itself didn't actually change (the component-only
case above), state "no marketplace-root doc sync needed" rather than silently omitting the check —
per `.claude/rules/disclose-before-overriding-decisions.md`.

## Lifecycle wiring

A parallel branch alongside [[require-inventory-updates-for-new-plugins-and-components]]'s own Lifecycle
wiring section, in the same three pipelines — run `marketplace-documentation` alongside (not instead of)
that rule's own Inventory Sync step, at the same timing (after Inventory Sync, before or alongside the
Document step's own doc-fix commit):

- **`plugin-lifecycle-upstream`:** after the Inventory Sync step and before the Document step. If Build
  produced a brand-new plugin (which always changes `marketplace.json`'s plugin list), run
  `marketplace-documentation`. If Build only added a component to an already-listed plugin,
  `marketplace.json`'s plugin list didn't change — state "no marketplace-root doc sync needed" and move on.
- **`plugin-lifecycle-downstream`:** wired into Phase 12 (Handoff Finalization), alongside the existing
  Inventory Sync step — both already share the identical broader trigger. If this run's fix/build activity
  changed `marketplace.json`'s plugin list (a plugin added/removed/renamed), run
  `marketplace-documentation` and fold the result into Phase 12's own commit record. If the run only
  changed a component list within an already-listed plugin, state "no marketplace-root doc sync needed"
  in the handoff report rather than silently omitting the check.
- **`plugin-lifecycle-maintenance`:** a shared step alongside the existing Document Step, at the same
  timing (after a workflow's core fix/rule-update is applied and committed, before the Document step's own
  commit). Same branch: `marketplace.json`'s plugin list changed → run `marketplace-documentation`;
  otherwise state "no marketplace-root doc sync needed."

## Trigger

"Before finalizing" — the same cadence `.claude/rules/plugin-rulebook-enforcement.md` and
[[require-inventory-updates-for-new-plugins-and-components]] already use.

## Enforcement

Policy gate, no backing hook — same disclosed-limitation model
[[require-inventory-updates-for-new-plugins-and-components]] uses for itself. Whether a pipeline run
actually changed `marketplace.json`'s plugin list is mechanically checkable after the fact (a
`git diff`/`git show` against the pipeline's own build commit), so a future audit pass can re-verify
compliance retroactively — but nothing forces the step to run at build time beyond author/reviewer
attention at "before finalizing."

## Why a separate rule, not folded into an existing one

Two existing rules cover an adjacent but genuinely different scope, and neither's own stated scope covers
this rule's artifact:

- [[require-inventory-updates-for-new-plugins-and-components]] is scoped entirely to JSON inventory files
  (`marketplace-inventory.json`, `plugin-inventory.json`) — it says nothing about markdown docs.
- `plugin-rulebook-enforcement.md`'s R20 (Duplicate Fact Sweep Trigger) is the same *class* of problem —
  a canonical fact (here, `marketplace.json`'s plugin list) hand-duplicated in an independently-worded
  restatement (README.md's plugin table) — but R20's own text scopes it explicitly to `plugin-rulebook`'s
  own `assets/settings.json` canonical values, not to `marketplace.json`.

Per `.claude/rules/verify-rule-scope-before-lazy-loading.md`'s "don't pattern-match a rule's scope from a
sibling, re-derive it" — extending either existing rule's own stated scope to cover markdown docs would
misrepresent what that rule actually says today. A new, separately-scoped rule is the correct fit.

## Why

Verified as a real, currently-live gap this session (2026-09-16), not hypothetical: this repo's first-ever
top-level community docs (`README.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`,
`SECURITY.md`) exist on `main` as of this session with no owning mechanism, and README.md's plugin table
is a hand-duplicated restatement of `.claude-plugin/marketplace.json`'s plugin list with no sync check —
confirmed by direct inspection this session, not by report. No prior incident exists yet for this specific
gap (unlike `require-inventory-updates-for-new-plugins-and-components.md`, which documents a real,
already-occurred gap of its own) — the gap this rule closes is that, prior to this session, neither this
rule nor the `marketplace-documentation` skill it triggers existed, not that a documented failure has
already happened.

## Scoping: always-loaded, not path-scoped

This rule's own trigger condition is a *state change* a lifecycle pipeline detects during a run (did
`marketplace.json`'s plugin list change this run) — not a single readable file a `paths:`-scoped rule
could match on read. Per `.claude/rules/verify-rule-scope-before-lazy-loading.md`, path-scoping a rule
whose trigger includes a state-change/create-style condition is unsafe, since a path-scoped rule only
loads when a matching file is *read* — a lifecycle pipeline's own SKILL.md (where this rule's wiring
actually needs to be followed) is read regardless of whether `marketplace.json` itself is also read in the
same turn, and there is no single file path that reliably co-occurs with every real trigger of this rule.
Stays always-loaded, matching [[require-inventory-updates-for-new-plugins-and-components]]'s own choice
for the identical reasoning.

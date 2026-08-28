# Lazy-Loading Decision: `require-tests-for-behavior-changes.md`

## Important preliminary finding: the file already carries `paths:` frontmatter

Before walking the checklist, I read the actual rule file at
`.claude/rules/require-tests-for-behavior-changes.md`. It already has this frontmatter on disk:

```yaml
paths:
  - "plugins/*/skills/**"
  - "plugins/*/agents/**"
  - "plugins/*/commands/**"
  - "plugins/*/hooks/**"
  - ".claude/skills/**"
  - ".claude/agents/**"
  - ".claude/commands/**"
  - ".claude/hooks/**"
  - "scripts/**"
```

So the specific migration the task asks "should we do this?" about has, in fact, already been applied
in this worktree. I'm treating the task as: re-derive the decision from scratch (as if it were still a
proposal), per `rule-development`'s own instruction that migrating an *existing* rule is a distinct
decision requiring the lazy-loading checklist — and flagging that the current on-disk state looks like
exactly the unsafe case the checklist warns against (see Step 2 below). This is worth surfacing
regardless of which way the recommendation lands, since it means the checklist should have been (or
still needs to be) run against a change that already shipped.

## Running `references/lazy-loading-checklist.md`, "For path-scoping" section

**Step 1 — read the rule's own scope in full, don't infer from title/siblings.**

The rule has no literal "When this applies" header, but its "When a test is required" section is the
scope statement: *"Mandatory for any change that alters what a component actually does when followed on
some input."* The task's own framing adds the operative detail: this explicitly **includes
newly-created skills/agents/commands/hooks** — not just edits to existing ones. The "What counts as a
test" section reinforces this by defining per-type test mechanisms (skill-tester eval, SKILL.md Testing
section, agent trigger-phrase battery, deterministic script execution) that apply identically whether
the component is brand new or being modified.

**Step 2 — does the scope include a *create* operation? If yes, path-scoping is unsafe by default.**

Yes, explicitly. The checklist is direct about the consequence: *"a path-scoped rule loads on read, not
on write — a brand-new file has nothing to read before it exists."* A newly-created `plugins/foo/skills/
bar-skill/SKILL.md` does not exist at the moment Claude is deciding whether the change needs a test — it
gets created *by* that decision. Path-scoping on `plugins/*/skills/**` means the rule only re-enters
context the *next* time that file (or a sibling matching the glob) is read — which could be turns later,
or in a different session entirely, well after the untested component has already been written and
potentially committed.

The checklist's narrow exception — "unless every realistic path to that create operation already
involves reading a matching sibling file first" — doesn't clearly hold here. Consider:
- A brand-new plugin's first skill: there is no sibling `plugins/<new-plugin>/skills/**` file to read
  before creating the first one. Zero coverage.
- A new skill added to an existing plugin during `plugin-lifecycle-upstream`'s Build phase: it's
  plausible (not guaranteed) that Claude reads an existing sibling skill for structural reference before
  writing the new one, which would incidentally reload the rule — but the checklist explicitly says to
  "treat that as a risk to disclose, not a guarantee," not license to scope on it.
- New hooks or commands are frequently created without reading any existing sibling first (e.g. a
  single hook added to a plugin with no other hooks yet).

So this rule fails Step 2 outright: it names a create operation as in-scope, and no realistic universal
read-before-write path exists to compensate. Per the checklist's own default — "Default to keeping it
always-loaded" — path-scoping should not have been applied.

**Step 3 — enumerate every path pattern implied, cross-check the whole tree.**

Setting aside the Step 2 failure for a moment: if this rule *were* being path-scoped, the enumerated list
on disk (`plugins/*/skills/**`, `agents/**`, `commands/**`, `hooks/**`, the `.claude/` mirrors, and
`scripts/**`) does look complete against the component types the rule's "What counts as a test" section
actually names (skill, agent, deterministic script). It does not omit an obvious component type. This
part of the list isn't the defect — the defect is scoping this rule to `paths:` at all.

**Step 4 — cross-check against sibling rules touched in the same kind of migration.**

This is the strongest concrete evidence. `.claude/rules/plugin-rulebook-enforcement.md` governs an
almost identical scope — its Mandatory Compliance Triggers table explicitly covers **create** for every
component type (skill, agent, command, hook, workflow skill, rule) — and it carries **no `paths:`
frontmatter at all**; it stays always-loaded. Two rules that both claim jurisdiction over "a plugin
component being created" landed on opposite lazy-loading treatments. Per the checklist's own instruction
— *"if rule A and rule B both claim to cover [the same ground] but only one's `paths:` list actually
includes the matching pattern, that asymmetry is itself evidence one of them is wrong — resolve it
before proposing either"* — this asymmetry needs resolving, and `plugin-rulebook-enforcement.md`'s
choice (always-loaded, because it also covers create) is the one consistent with the checklist's own
Step 2 rule. `require-tests-for-behavior-changes.md`'s current `paths:` frontmatter is the outlier that
should be reverted, not the precedent to follow.

This also lines up with `.claude/rules/verify-rule-scope-before-lazy-loading.md`'s own worked incorrect
example, which is this exact shape: a rule "covering both 'modify' and 'create' operations gets
path-scoped to load only on a matching file *read* ... silently drops the rule's 'create' coverage."

## Checking the fold-into-a-skill alternative

Running the checklist's second section against folding this rule into `commit` (git-kit) — the skill the
rule's own "Enforcement" section names as the actual enforcement point:

- **List every trigger path the rule names.** The rule applies at two distinct moments: (a) component
  *creation/modification time*, when someone is deciding what test mechanism fits the change and should
  plan for it, and (b) *commit time*, when `commit`'s gate asks whether testing happened. Folding the
  rule's full body (the "What counts as a test" table, the "When a test is required" scope, the sibling-
  sweep item) into `commit` only gives it presence at moment (b). Moment (a) — informing the build/design
  phase about which test mechanism a given component type needs *before* the commit gate ever fires —
  would silently lose its always-available guidance. That's a real behavior change even though the
  commit-time enforcement gate itself would still exist.
- **Read the target skill's "When NOT to Use"/constraints first.** The rule's own "Enforcement" section
  already discloses two paths `commit`'s gate does not cover: a PR built from commits made outside
  git-kit (raw `git commit`), and commits made through `standalone-commits` (which deliberately omits
  this test gate per its own step 6 note). Folding the rule's content into `commit` does nothing to
  close either gap — they're structural exclusions of the fold target itself, already named. A fold into
  `commit` would need to keep carrying this same disclosed-gap language, which somewhat defeats the
  purpose of "folding" (removing the standalone file) since the two-carve-out caveat still has to live
  somewhere citable.
- **Any trigger path with no governing skill at all?** The component-creation moment isn't uniquely owned
  by one skill — it happens inside `plugin-lifecycle-upstream`'s Build phase, `skill-development`,
  `agent-development`, `hook-development`, `command-development`, or a raw ad hoc edit. There's no single
  fold target that would preserve build-time visibility across all of those paths simultaneously; folding
  into `commit` only covers the tail end of all of them at once, at the cost of the per-type guidance
  being invisible until commit.

Given this, folding is a **worse** fit than path-scoping (which at least isn't compounding a second,
independent coverage loss on top of the already-disclosed commit-time gaps) — but path-scoping already
failed the create-operation check above. Neither lazy-loading option is safe for this rule as currently
scoped.

## Recommendation

**Keep `require-tests-for-behavior-changes.md` always-loaded.** Concretely:

1. Revert the `paths:` frontmatter currently on the file — it fails the checklist's own create-operation
   check (Step 2), the rule text explicitly names newly-created components as in scope, and no
   universal read-before-write path compensates.
2. Do not fold it into `commit` (or any other single skill) — doing so would remove the rule's
   build/design-time visibility (deciding the right test mechanism *before* writing the component),
   leaving only the already-narrower commit-time gate, which itself already has two disclosed,
   unaddressed bypass paths.
3. Treat `plugin-rulebook-enforcement.md`'s always-loaded status (despite covering the identical "any
   component create/modify" ground) as the correct sibling precedent, not `require-tests-for-behavior-
   changes.md`'s current `paths:` frontmatter — the asymmetry between the two is itself the checklist-
   flagged red flag that one of them is wrong.
4. Before finalizing this reversal as a real change, get an independent review pass (per the checklist's
   "Before presenting the migration as a proposal" section) — this reasoning has not been reviewed by a
   second pass.

## Why this isn't a "just leave everything always-loaded" cop-out

The checklist's bias is toward path-scoping wherever it's safe — this isn't a blanket refusal to lazy-
load anything. The specific defect here is narrow and mechanical: this rule's own stated scope names a
*create* operation, and path-scoped rules fire on read, not write. A rule without that create-operation
clause (e.g. one that only ever applies to editing an *existing* file's already-written behavior) would
not have this problem and could reasonably be path-scoped. The recommendation is specific to this rule's
actual text, not a general aversion to the technique.

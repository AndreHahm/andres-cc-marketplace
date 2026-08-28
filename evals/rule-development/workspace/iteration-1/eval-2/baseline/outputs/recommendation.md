# Should `require-tests-for-behavior-changes.md` be path-scoped or folded into a skill?

## Bottom line

**Neither.** Keep it always-loaded (revert its current `paths:` frontmatter back to a standalone,
always-loaded rule). Path-scoping is unsafe because the rule's own scope explicitly covers *creating* a
brand-new skill/agent/command/hook, and a path-scoped rule only loads when a matching file is *read* —
a file that doesn't exist yet can't be read. Folding into one skill is safer than path-scoping on that
specific axis but is still the wrong move here because the rule's content is genuinely cross-cutting
(relevant to at least 7-8 different skills, not one), so folding it into a single skill either silently
drops the other consumers' visibility into the requirement or forces duplicating the content across all
of them — a worse outcome than just leaving one short, standalone rule in place.

## What the rule actually says (read in full, not inferred from its title)

`.claude/rules/require-tests-for-behavior-changes.md` currently ships with:

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

Its "When a test is required" section states the mandate applies to "any change that alters what a
component actually does when followed on some input," explicitly including **newly-created**
skills/agents/commands/hooks — not just edits to existing ones. Its "Enforcement" section says the actual
gate lives inside `commit` (git-kit)'s own `AskUserQuestion` step, with two named gaps: a PR built from
commits made outside git-kit (raw `git commit`), and commits made via `standalone-commits` (which
deliberately skips this gate).

So the rule has (at least) two distinct audiences: (1) whoever is *creating or editing* the component and
should write the test as part of that work, and (2) `commit`'s own enforcement step, which asks about it
at commit time.

## Option 1: Path-scope it — why this is unsafe

This repo has already hit this exact failure mode once, for a sibling rule with the same shape.
`.claude/rules/verify-rule-scope-before-lazy-loading.md` (already in this repo, itself written to prevent
a repeat of this mistake) states the operative fact plainly:

> "a path-scoped rule loads on read, and a brand-new file has nothing to read yet."

and its own "Incorrect" example is a rule that "covers both 'modify' and 'create' operations" getting
path-scoped "to load only on a matching file *read*... The rule's own compliance table explicitly covers
creating a brand-new skill — but a file that doesn't exist yet can't be read, so path-scoping silently
drops the rule's 'create' coverage."

That incident was real: `git log` shows a migration commit (`bbfedc3`, "lazy-load 7 always-loaded plugin
rules") path-scoped five rules, including both `plugin-rulebook-enforcement.md` and
`require-tests-for-behavior-changes.md`. A follow-up commit (`49e5b53`, "fix: address cross-model review
findings on rule migration") only patched `require-tests-for-behavior-changes.md`'s glob list (it was
missing `scripts/**` and `plugins/*/hooks/**` despite naming both in its own text) — it did **not**
address the create-vs-read semantic gap. Checking the current file state confirms `plugin-rulebook-
enforcement.md` was fully reverted to always-loaded (no `paths:` frontmatter today) for exactly this
reason, while `require-tests-for-behavior-changes.md` still carries `paths:` frontmatter today, even
though it has the identical "explicitly covers component creation" property that got the other rule
reverted. The project's own new `references/lazy-loading-checklist.md` (added in this same worktree)
documents the `plugin-rulebook-enforcement.md` incident as reason #1 for why this check exists, and its
first checklist item is precisely: "Does the rule's own scope include a *create* operation? ... Default
to keeping it always-loaded."

Applying that checklist directly to this rule: yes, its scope includes create. Is there a guarantee that
every realistic path to creating a new skill/agent/command/hook already involves reading a matching
sibling file first? No — component creation in the lifecycle pipelines (`plugin-lifecycle-upstream`,
the Design skills) routinely `Write`s a brand-new `SKILL.md`/agent `.md`/command `.md`/hook script without
necessarily `Read`ing an existing file at a matching glob first (and even where a template happens to get
read, that's incidental, not a designed guarantee). Per the checklist's own instruction, an unverifiable
"maybe it happens to work" is treated as a risk to disclose, not a guarantee — so path-scoping should not
be adopted here.

## Option 2: Fold into a specific skill — why this doesn't fit either

Folding is structurally *safer* than path-scoping for this rule on the create-vs-read axis specifically,
because the one guaranteed enforcement point (`commit`'s `AskUserQuestion` gate) fires *after* the new
file already exists — there's no "nothing to read yet" problem at commit time the way there is for a
path-scoped rule at create time.

But the lazy-loading checklist's folding section requires listing *every* trigger path the rule names,
not just the one the fold target obviously governs, and checking each is separately reachable. This
rule's content is used by more than just `commit`:

- **Authoring time** (the party who should actually write the test): `plugin-lifecycle-upstream`,
  `plugin-lifecycle-downstream`, `plugin-lifecycle-maintenance`, and the four Design skills
  (`skill-development`, `agent-development`, `command-development`, `hook-development`) all create or
  modify components and are the natural place a test gets written.
- **Commit-time enforcement**: `commit` (git-kit).
- **Two paths the rule itself says are *not* covered by any enforcement today**: a raw `git commit`
  outside git-kit, and `standalone-commits` (whose own step 6 deliberately omits this gate).

Folding the whole rule into `commit` alone would silently drop the "write the test while you're building
the component" guidance for all seven of the other authoring-time skills — they'd only ever discover the
requirement reactively, at commit time, via `commit`'s own gate, rather than up front. Folding into all
of them instead avoids that but recreates the definition in 7+ places, which is the exact kind of
duplicated-fact-across-restatements problem this repo's own `plugin-rulebook-enforcement.md` (R20)
explicitly warns against — a definition of "what counts as a test" hand-copied into eight files will
drift the next time one of them is edited and the others aren't. Folding also doesn't help the two
explicitly-named gaps (raw `git commit`, `standalone-commits`) at all — those remain exactly as
uncovered as they are today regardless of where the text lives, since neither one runs the fold target.

Given the rule is short (~40 lines) and its value is spread across many consumers rather than owned by
one, folding trades a small context-token saving for a real duplication/maintenance risk and a real loss
of proactive (pre-commit) visibility for most of its actual audience.

## Recommendation

1. **Revert `require-tests-for-behavior-changes.md`'s `paths:` frontmatter** (in both
   `.claude/rules/require-tests-for-behavior-changes.md` and its canonical source,
   `plugins/plugin-devkit/rules/require-tests-for-behavior-changes.md`) and restore it to
   always-loaded — the same fix already applied to `plugin-rulebook-enforcement.md` for the identical
   reason, and this rule was evidently missed in that earlier pass.
2. **Don't fold it into `commit` or any other single skill.** Its audience is genuinely multi-skill; a
   standalone rule that every relevant skill can implicitly rely on (and that `commit`'s own instructions
   explicitly cross-reference for the enforcement step) is simpler and safer than either scoping option.
3. If the underlying goal is reducing per-session context overhead (the original motivation cited in the
   `bbfedc3` commit message — "16 of 17 rules loading in every session... ~7k tokens"), this specific
   rule is a poor candidate for that effort. Look for lazy-loading savings among rules whose scope is
   genuinely narrow and read-triggered (e.g. rules that only ever fire on editing an *existing* file, with
   no create-path in their own "When this applies" text) rather than this one.

## Checklist used for this decision (for traceability)

- [x] Read the rule's own "When this applies"/scope text in full, not inferred from its title.
- [x] Checked whether scope includes a create operation — yes, explicitly ("newly-created
      skills/agents/commands/hooks").
- [x] Checked whether every realistic create path already reads a matching sibling file first — no
      guarantee found; treated as a disclosed risk, not assumed safe.
- [x] Checked git history for precedent — found the identical failure already occurred and was reverted
      for `plugin-rulebook-enforcement.md` in the same migration batch, and was never fixed for this rule.
- [x] For the folding option, enumerated every consumer of the rule's content (7-8 skills), not just the
      one enforcement point (`commit`), and confirmed folding into one drops or duplicates coverage for
      the rest.

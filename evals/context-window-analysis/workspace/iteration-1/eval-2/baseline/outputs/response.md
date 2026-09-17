# Context Bloat Audit: Skills + CLAUDE.md

Scope: `CLAUDE.md` (repo root) and the canonical skill source tree (`plugins/*/skills/*/SKILL.md`).
I excluded the `.claude/skills/` and `.agents/skills/` trees from the size counts below since those
are generated mirrors of `plugins/*/skills/` (per this repo's own documented convention) — auditing
them separately would just double-count the same content, not find new bloat.

## Headline numbers

| Source | Always loaded every session? | Size |
|---|---|---|
| CLAUDE.md | Yes | 81 lines / 614 words (~800 tokens) |
| `.claude/rules/*.md` with no `paths:` frontmatter | Yes (17 of 24 rule files) | 904 lines / 9,791 words (~12.7k tokens) |
| All skill frontmatter `description:` fields (136 skills) | Yes (name + description shown in the skill listing) | ~121,700 chars (~30k tokens) |
| Skill *bodies* (SKILL.md content beyond frontmatter) | No — loaded only when a skill is invoked | 32,140 lines total across 136 files |

**The single biggest number here is the ~30k tokens of skill descriptions that load into every
session's system prompt regardless of what the user asks.** That's roughly 2.5x the size of CLAUDE.md
and the always-loaded rules combined. This isn't something CLAUDE.md itself can fix — it's a
structural cost of having 136 skills registered, each with a name + description in the always-on
listing.

## 1. CLAUDE.md — not the main bloat source

At 81 lines / ~800 tokens, CLAUDE.md itself is lean and not the problem. It's mostly pointers to
other files (rules, plugin-rulebook) rather than inlined policy, which is the right shape. No action
needed here specifically.

## 2. Always-loaded `.claude/rules/*.md` — the real fixed per-session cost

24 rule files exist; **17 have no `paths:` frontmatter and so load into every session unconditionally**,
totaling ~904 lines / ~12.7k tokens. Only 7 are path-scoped to load on-demand. The always-loaded set:

- ask-before-config-decisions.md
- ask-before-structural-grounding.md
- consult-naming-conventions-first.md
- disclose-before-overriding-decisions.md
- keep-marketplace-root-docs-in-sync.md
- orphaned-worktree-git-read-fallthrough.md
- plugin-rulebook-enforcement.md
- require-declared-plugin-language.md
- require-gitignored-scratch-locations.md
- require-inventory-updates-for-new-plugins-and-components.md
- require-security-review-before-new-gate.md
- require-tests-for-behavior-changes.md
- require-worktree-rooted-absolute-paths.md
- resweep-closed-scope-lists-on-new-components.md
- route-through-git-kit-lifecycle-skills.md
- starting-work-before-first-change.md
- test-against-example-plugin.md

Several of these are narrow-trigger rules (worktree hygiene, plugin-devkit component naming,
inventory bootstrapping) that only matter for a small fraction of sessions — e.g. a session that never
touches a worktree still pays for `orphaned-worktree-git-read-fallthrough.md` and
`require-worktree-rooted-absolute-paths.md` every turn. There's already a `verify-rule-scope-before-lazy-loading.md`
rule in this repo (itself always-loaded, correctly, since it governs "create" operations that can't be
`paths:`-scoped) that explicitly warns against carelessly path-scoping a rule with create-operation
coverage — so **not every one of these 17 can simply be converted to `paths:` scoping**; several likely
apply because their trigger genuinely isn't a file read (e.g. "before creating a new plugin," "before
committing"). But some are plausible candidates to revisit individually:
- `keep-marketplace-root-docs-in-sync.md` (110 lines, the single largest) — check whether its trigger is
  actually a doc-file edit, which would be `paths:`-scopable.
- `require-gitignored-scratch-locations.md` and `orphaned-worktree-git-read-fallthrough.md` — both
  describe fairly rare situations (a specific local-permissions edge case, a specific worktree-removal
  sequence) that may not warrant permanent always-on residency.

I'm flagging these as candidates, not confirmed fixes — per this repo's own
`verify-rule-scope-before-lazy-loading.md` rule, each would need its actual "When this applies" text
re-derived individually before converting, not pattern-matched off a sibling.

## 3. Skill catalog — 136 skills, real duplication risk in a few spots

Per-plugin skill counts (canonical `plugins/` tree):

| Plugin | Skill count |
|---|---|
| plugin-devkit | 41 |
| git-kit | 22 |
| analysis-kit | 20 |
| session-kit | 17 |
| workmanagement-kit | 15 |
| codex-kit | 11 |
| context-kit | 7 |
| antigravity-kit | 2 |
| example-plugin | 1 |

**plugin-devkit (41 skills) is disproportionately large** — nearly a third of all skills in the
marketplace live in one plugin. Some of these are pipeline orchestrators
(`plugin-lifecycle-upstream/downstream/maintenance`) with long, detailed descriptions (1,400+ chars
each) needed to disambiguate them from each other and from the narrower skills they call — that
disambiguation cost is presumably intentional, but it's worth checking whether all 41 need to be
top-level skills versus some being reference material folded into a parent skill.

**context-kit's 7 skills are conceptually adjacent and worth a second look for overlap:**
`context-audit`, `context-degradation`, `context-engineering`, `context-mode`, `context-optimization`,
`context-window-analyze`, `strategic-compact`. All operate on the same general subject (context window
management). I did not read each one's full body to check for actual content duplication (that would
be a deeper follow-up), but the naming alone suggests real risk of overlapping "When to use" triggers,
which is exactly the kind of ambiguity that makes skill selection non-deterministic. Worth an explicit
overlap check between these 7 specifically.

**Largest individual skill bodies** (by line count — proxy for token cost when actually invoked, not a
problem for baseline context since these only load on use):

| Skill | Lines |
|---|---|
| git-kit/commit | 502 |
| git-kit/git-cleanup | 501 |
| plugin-devkit/plugin-rulebook | 498 |
| git-kit/resolving-merge-conflicts | 498 |
| git-kit/create-pr | 496 |
| git-kit/git-worktrees | 493 |
| git-kit/cross-model-review | 489 |
| plugin-devkit/skill-tester | 482 |
| antigravity-kit/antigravity | 471 |
| codex-kit/codex-rescue | 468 |

None of these are alarming on their own (~500 lines is a reasonable ceiling for a workflow skill with
step-by-step gates), but they're the ones to check first if any single skill invocation is blowing the
context budget.

**Longest frontmatter descriptions** (this is the part that's always loaded, unlike the body):

| Skill | Description length (chars) |
|---|---|
| plugin-devkit/marketplace-development | 2,082 |
| analysis-kit/running-a-full-retrospective | 1,862 |
| git-kit/gh-operations | 1,854 |
| git-kit/merge-pr | 1,773 |
| analysis-kit/starting-an-analysis | 1,699 |
| git-kit/cross-model-review | 1,571 |
| git-kit/handling-review-findings | 1,562 |

Several descriptions here are doing double duty as both "what this does" and "what this is NOT, see
sibling skill X instead" disambiguation prose (visible directly in this session's own skill listing —
e.g. `handling-review-findings`, `merge-pr`, `cross-model-review` all spend a large fraction of their
description explicitly listing what they are *not*). That's a reasonable tradeoff for reducing
mis-triggering, but each of these ~1,500-2,000-char descriptions costs roughly 400-500 tokens in every
single session's context, whether or not the skill is ever used. With 7+ skills over 1,400 chars, that's
already ~3-4k tokens spent purely on cross-referencing disambiguation text.

## 4. Structural note (not itself bloat, but relevant)

The skill/rule tree is mirrored in at least three places: `plugins/*/skills/` (canonical),
`.claude/skills/` (generated mirror, what's actually loaded in a live session), and `.agents/skills/`
(a separately-mirrored, and per your own project memory, *stale* Codex-facing copy). This doesn't add
to any single session's context cost (only one tree loads at a time), but it does mean any bloat-trim
you make has to be applied to the canonical `plugins/` source and then re-synced to `.claude/`, not
edited in the mirror directly.

## Recommendations, in priority order

1. **Skill descriptions are the biggest lever** (~30k tokens, always-on). Before trimming any
   individual rule or skill body, check whether the 20-30 longest descriptions can be shortened without
   losing disambiguation value — this is where the bulk of the fixed per-session cost actually lives.
2. **Audit the 7 context-kit skills for real overlap**, not just adjacent naming — a targeted
   activation/description overlap check across just those 7 would be cheap and could catch consolidation
   opportunities.
3. **Re-derive scope for the 17 always-loaded rules individually** (per this repo's own
   `verify-rule-scope-before-lazy-loading.md` procedure) rather than assuming all 17 must stay
   always-on — a few (especially the two worktree-edge-case rules) look like plausible `paths:`
   candidates, but each needs its own check, not a batch guess.
4. **plugin-devkit's 41-skill count** is worth a lighter structural review — not necessarily bloat, but
   large enough that a "does every one of these need to be a top-level skill" pass seems warranted.
5. CLAUDE.md itself needs no changes — it's already lean and mostly delegates to other files rather
   than inlining content.

## Caveats / what I didn't do

This was a structural/size audit only (line counts, word counts, frontmatter lengths, `paths:`
presence) using plain shell tools — I did not read every skill body end-to-end, did not verify actual
runtime token costs against a live transcript, and did not check for content-level duplication (the
same instructions restated in two skills) beyond the naming-based overlap flag on context-kit. A
deeper pass would want to actually diff skill bodies for repeated instructions and measure real
system-prompt token counts rather than the word-count-based estimates used here.

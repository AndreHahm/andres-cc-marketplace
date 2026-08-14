---
name: analyzing-sessions
description: >-
  Analyzes Claude Code sessions from a user-defined start date through today. Executes
  SWOT analyses, self-critiques, and self-reflections for each skill, sub-agent, command,
  workflow-skill, and rule active in the session range, reading generated output artifacts
  (concept cards, plans, handoff reports) in scope and re-verifying their stated open items
  against current repo state rather than trusting them at face value. Generates classified
  improvement suggestions grouped by component and priority, persisted to
  .claude/output/analyzing-sessions/. Use when running a post-session retrospective,
  auditing skill or agent performance, building an improvement backlog, or identifying systemic
  issues across skills, agents, and rules from a session or date range.
allowed-tools: Read Glob Grep Write Edit Agent Bash(git:* date:*)
---

# Session Analysis

Produce SWOT analyses, self-critiques, and improvement suggestions for every component used across a session range.

## Quick Start

1. Choose scope — "This conversation" for the current session, or provide a start date for a date range.
2. Confirm the Phase 2 component inventory before the analysis runs — output artifacts in scope are read in full, not just listed.
3. Skim SWOT + critique output in P1 → P3 priority order.
4. Act on the **Top 5 Actions** from Phase 6, then check the persisted report path.

For date-range retrospectives or deep taxonomy guidance, read the full phases below.

## When to Use

- Post-session retrospective after completing a development task
- Auditing how skills, sub-agents, commands, or rules performed during a session
- Building an improvement backlog from multiple observed failures
- After acting on improvement suggestions that affect skill behavior, validate the fix using `skill-tester` — `skill-evaluation-protocol` governs the evaluation criteria
- Identifying systemic issues that span more than one component
- Any session involving: skills · sub-agents · commands · workflow-skills · rules

## When NOT to Use

- **Real-time monitoring** — this skill is retrospective; it analyzes past behavior, not live state
- **No `.claude/` components were active** — if no skills, agents, commands, or rules were involved, there is nothing to analyze
- **Single-component review** — use `skill-reviewer` for one skill or `plugin-validator` for one plugin; this skill adds overhead without benefit for isolated reviews
- **Code quality** — use `/code-review` for diff analysis; this skill covers skill and agent behavior, not code correctness
- **Want the retrospective's suggestions applied, tested, documented, and committed as a guided pipeline, not just surfaced** — use `plugin-lifecycle-maintenance`'s `improve-a-plugin` workflow after this skill's report is produced; this skill stops at "Top 5 Actions," it never applies them
- **Full permission-candidate extraction across session transcripts** — use `find-permissions`; this skill's own Permission Friction note (Phase 6) is a qualitative observation only, not a substitute for that command's systematic scan

## Phase 1: Scope

If a scope was supplied as an argument (a date string, `"today"`, `"this conversation"`, or similar), skip the question UI and proceed directly to Phase 2 using that argument as the scope.

**Timezone pitfall — "since last retro" boundaries:** a prior retro's own header timestamp is UTC (`Z`-suffixed, e.g. `2026-07-24T10:44:23Z`), but local file mtimes (used to locate output artifacts and session transcripts in Phase 2) are in local time. Convert the UTC boundary to local before comparing — e.g. `10:44:23Z` on a UTC+2 machine is `12:44:23+02:00` local, not `10:44:23` local. Treating the boundary as already-local silently shifts the window earlier than intended and can wrongly exclude or include artifacts near the boundary.

Ask for the session range only when no argument was provided:

```
questions: [
  {
    question: "What should this analysis cover?",
    header: "Session scope",
    options: [
      { label: "This conversation", description: "Analyze only the current conversation context" },
      { label: "From a start date", description: "Provide a YYYY-MM-DD start date; analysis runs through today" },
      { label: "Today", description: "All sessions from today (default)" }
    ],
    multiSelect: false
  }
]
```

If "From a start date" → ask for the date. If sessions from prior conversations are in scope, check for
on-disk transcripts first — see "Prior-session data" in Gotchas below for the resolution procedure and
its cost discipline. Only ask the user to paste in transcript excerpts or summaries when no matching file
exists on disk for the requested scope.

**Narrow-scope gap-awareness signal:** once the scope is resolved (argument or question), find the newest prior report at `.claude/output/analyzing-sessions/*.md` and read its own header timestamp (UTC, same conversion as the timezone pitfall above) as that report's *end* boundary. Compare it against this run's own scope *start* (the argument or answer just resolved). If this run's scope start is later than the newest prior report's end — i.e. a gap exists between where the last report stopped and where this one begins — state that gap plainly in the final report as its own line, e.g. `Coverage gap: <newest-prior-report-end> → <this-run's-scope-start> — no prior report covers this range.` This does not change what gets analyzed (the run still honors the scope the user chose) — it only makes an otherwise-invisible coverage boundary visible. Repeated narrow-scope runs with no report ever covering the range between them can leave real windows (including an entire new plugin's worth of commits) unreported for days before a later run happens to notice and reconstructs them by hand — a real instance of this happened in this repo's own history.

**Sibling-scope-overlap check.** `analysis-kit`'s `analyzing-plugin-components` is a fork of this skill, and the two still cover largely overlapping ground for a project using both plugins. Before proceeding, also `Glob('.claude/output/analyzing-plugin-components/*.md')` (the sibling's own report directory) and check whether any report there has a header timestamp range overlapping this run's own scope. If one exists, name it plainly: `Sibling coverage: analyzing-plugin-components already covered <range> in <path> — read it before duplicating that analysis.` This catches the case a same-skill prior-report check alone misses — two independently-invoked skills covering the same window with neither aware of the other.

## Phase 2: Component Inventory

**Run these Globs first, unconditionally — before evaluating scope or waiting for confirmation:**
- `Glob(pattern='*', path='.claude/output')` — output artifacts from prior runs
- `Glob(pattern='*.md', path='.claude/rules')` — rules that load automatically, often without being mentioned in conversation
- `Glob(pattern='*.local.md', path='.draft')` — local, gitignored planning documents (e.g. a roadmap or architecture draft) — this repo's only recurring `*.local.md` convention lives here, not under `.temp/` or elsewhere in `.draft/`; don't broaden the pattern to those, they hold staged plugin source components, not planning documents

**Use the `path` parameter form above, not a bare relative pattern like `Glob('.claude/rules/*.md')`** — on at least one observed environment, a pattern with a literal leading `.claude/` segment silently returned no results even though matching files existed, while pointing `path` directly at the target directory with a bare pattern resolved correctly. A silent false negative here means rules or prior output artifacts go uncounted without any visible error, so treat an empty result from either call as suspect: retry once with a broader pattern (e.g. `Glob(pattern='**/*', path='.claude/rules')`) before concluding the category is genuinely empty.

These seed the inventory regardless of scope. Then identify every additional component from the current conversation context.

**Read output artifacts, don't just list them.** For every file the first Glob found whose modification time falls inside the session range, and that looks like a generated/linked artifact from a plugin-devkit pipeline skill (concept cards under `plugin-ideation/`, plans under `plugin-planning/`, handoff reports under `build-handoff-writer/`, comparison reports under `plugin-comparison/`, grader reports under `plugin-grader/`, dev-rules reports under `rules/`), `Read` it in full — not just its path. The artifact's *content* is itself evidence about the component(s) that produced or consumed it: a Concept Card's Overlap Check section is evidence for `plugin-ideation`'s SWOT, a handoff report's Commits section is evidence for `build-handoff-writer`'s SWOT, and so on. A component whose only evidence is "it ran" (from the conversation) but whose actual output was never read is assessed on incomplete information.

**Verify Open Items — don't trust an artifact's self-report.** For every handoff-report-shaped artifact read above (or any artifact with an "Open Items"/"Findings"/"Unresolved" section), independently re-check each listed item against current repository state before treating it as still accurate:
- A commit SHA or count claimed in the artifact → verify with `Bash(git log)`/`Bash(git show)` directly (e.g. compare `${#SHA}` against the actual `git log -1 --format=%H` output)
- A "deferred" or "not yet fixed" item → `Grep`/`Read` the referenced file(s) to check whether it was actually addressed in a later commit or session, even if the artifact itself was never updated to reflect that
- A "still open" claim → check whether a *later* artifact in the same scope (e.g. a subsequent handoff-report update, a later plugin-grader re-audit) already resolved it, and the earlier artifact is simply stale rather than wrong
Record any discrepancy found — an item marked open that's actually resolved, an item marked resolved that isn't, or a factual claim (a SHA length, a file count) that doesn't match a direct check — as a Weakness in the SWOT of the component that *produced* the artifact, not as a note about the artifact file itself. This mirrors a documented real incident in this plugin's own session history: a `build-handoff-writer` report flagged its own inline-supplied commit SHA as "41 hex characters" (a miscount) rather than the correct 40, and a fix-pass's own dispatch prompt claimed "4 new commits" when there was exactly one — both were only caught because a later step independently re-verified rather than trusting the artifact's own text.

**Commit SHA doesn't resolve at all — fix it, don't just flag it.** This is a standing responsibility of this skill, distinct from the general Weakness-recording treatment above: if a SHA referenced in a handoff-report-shaped artifact doesn't resolve via `git show <SHA>` at all (not merely miscounted, but genuinely absent from history), the most common cause is a rebase-merge (`gh pr merge --rebase`) rewriting the commit after the report was written. Search `git log --oneline` on the merge target branch for a commit with matching message and file scope. If found with high confidence, ask via `AskUserQuestion` whether to fix the stale reference(s) directly in the source artifact now — `Edit`, scoped narrowly to the exact stale-SHA-to-correct-SHA replacement(s), nothing else in the file. If approved, apply the fix and note it in this report's own Weakness entry as `[FIXED]` rather than `[FLAGGED]`, naming the old and new SHA. Do not rewrite a SHA that still belongs to an unmerged branch — verify it against that branch's own history, not the merge target's, and annotate it as branch-only rather than treating it as stale. If no confident message-match exists, fall back to the general Weakness-recording treatment above rather than guessing.

**Read local planning documents as state, not as pipeline artifacts.** For every file the third Glob found (`.draft/*.local.md`) whose modification time falls inside the session range, `Read` it in full — this is the session's actual durable work-product when the session involved planning/roadmap/architecture work, and it's easy to miss because it never produces an invocation event the way a `Skill`/`Agent` call does. Unlike the handoff-report-shaped artifacts above, don't run these through the Verify Open Items check — a planning document doesn't carry "Open Items"/commit-SHA claims to re-verify, it just carries current decisions and scope. Because these files are gitignored, there's no git history to diff against for a prior version; for a scope that starts before the current conversation, recovering an earlier state of a `.draft/*.local.md` file requires the user to paste it in, same as any other prior-conversation content (see Phase 1's note above and the Gotchas below).

| Category | What counts |
|---|---|
| **Skill** | Slash-command invocations that loaded a `SKILL.md` (e.g. `/skill-refiner-interactive`) — **or** a skill's `SKILL.md`/`references/*.md`/`scripts/*` files that were directly edited this session, even without an invocation event (see note below) |
| **Sub-agent** | Agent tool spawns (named agent type or description used) |
| **Command** | `.claude/commands/*.md` invocations |
| **Workflow-skill** | Skills invoked as sub-steps inside another skill's workflow |
| **Rule** | `.claude/rules/*.md` files loaded and applied during the session |

**Invoked vs. edited components:** both count, and both get their own SWOT — but frame them differently. An *invoked* component is assessed on how well it performed when run (did its checks fire, did its output need correction). An *edited* component (one whose files you modified as a task, without ever loading it via `Skill`/`Agent`) is assessed on how well its existing structure/docs supported making that edit correctly, and what defects the edit surfaced. Don't skip edited components just because there's no invocation event to point to as evidence — the edit itself is the evidence.

Emit the inventory before proceeding:

```
📦 Session Inventory  <start> → <end>
| # | Component | Category | Evidence |
```

Confirm: "Found N components. Proceed with full analysis?"

## Phase 3: SWOT Analysis

For each component, produce a SWOT grounded in observed session behavior — not design intent.

```
### SWOT: <name>  (<category>)
| Quadrant     | Observations |
| Strengths    | … |
| Weaknesses   | … |
| Opportunities| … |
| Threats      | … |
```

See `references/swot-framework.md` for quadrant prompts and common patterns per component category.

## Phase 4: Self-Critique and Self-Reflection

For each component, immediately after its SWOT:

**Self-Critique** — what went wrong:
- Errors, omissions, wrong assumptions made during execution
- Checklist items skipped or gates bypassed
- Output produced that should not have been

**Self-Reflection** — what would change:
- Alternative approach that would produce better results next time
- Cross-component patterns pointing to a systemic issue
- Meta-lessons that apply beyond this specific component

See `references/critique-reflection-framework.md` for question sets by category and rationalizations to reject.

## Phase 5: Generate and Classify Suggestions

Derive one or more concrete suggestions from each SWOT entry and each critique/reflection point. Discard observations with no actionable change. Merge duplicate suggestions across components into one cross-cutting entry.

Each suggestion:
```
[S##] [P1|P2|P3] [TYPE]  <one-line description>
Source: <SWOT quadrant | Critique | Reflection>   Component: <name>
Detail: <what to change and why>
```

Priority: **P1 Critical** (breaks behavior), **P2 Major** (degrades quality), **P3 Minor** (polish).
Types: `FIX` · `ENHANCE` · `ADD` · `REMOVE` · `AUDIT`

See `references/suggestion-taxonomy.md` for classification rules, merge criteria, and examples.

## Phase 6: Grouped Report

Output two views.

**By component** — each component with its suggestions in P1→P3 order:
```
## <name>  (<category>)
[S01] P1 FIX    …
[S02] P2 ADD    …
```

**By classification** — all suggestions across components by priority then type:
```
### P1 — Critical
[S01] skill-reviewer · FIX  …
### P2 — Major
…
### P3 — Minor
<details><summary>N minor suggestions</summary>…</details>
```

**Permission friction (if observed):** if the session showed the user repeatedly approving or denying the same or similar Bash commands, add a short qualitative note — pattern and approximate frequency, e.g. "approved `git push` 4x this session." This is a narrative observation only, not an extraction pass; for a full candidate list of permission-rule gaps across session transcripts, point the user to `find-permissions` rather than attempting to replicate its extraction here.

Close with **Top 5 Actions**: the five highest-impact suggestions across all components, in order.

**Persist the report:** get a timestamp (`Bash(date -u +%Y-%m-%dT%H-%M-%SZ)`) and `Write` the full Phase 3-6 output to `.claude/output/analyzing-sessions/<scope-slug>-<timestamp>.md`, where `<scope-slug>` is a short kebab-case description of the scope (e.g. `this-conversation`, `2026-07-10-to-today`). Present the confirmation as its own line before the rest of Phase 6's output:

```
📄 Session Analysis Report written: `.claude/output/analyzing-sessions/<scope-slug>-<timestamp>.md`
```

**This per-run-file format (`<scope-slug>-<timestamp>.md`, one file per run) is the canonical convention going forward** — resolved as of 2026-07-24. `.claude/output/analyzing-sessions/` used to also hold an orphaned `history/` subdirectory from a prior per-component-file convention (one file per component analyzed, predating this format) — the 2026-07-24 decision explicitly left those files in place rather than migrating or deleting them. That subdirectory was deleted on 2026-08-12 once a later audit confirmed it was genuinely orphaned (zero references anywhere in the repo, `Glob(pattern='*', path='.claude/output')` in Phase 2 below was the only thing that would ever have surfaced it) — a deliberate reversal of the original "don't delete" decision, recorded here rather than silently overwritten. Persisting in the per-run format lets other components (notably `plugin-lifecycle-maintenance`'s `improve-a-plugin` workflow) link back to a specific retro run instead of re-deriving one, and gives the Verify-Open-Items check above something concrete to point future re-checks at.

**Suggested next step:** for any P1/P2 suggestion, ask with `AskUserQuestion`: "Expand this suggestion into a full WHAT/WHY/HOW action plan using enhancement-suggestor?" — options "Yes" / "No". If yes, invoke the `enhancement-suggestor` agent (via `Agent`) against that suggestion — this skill's own suggestions are intentionally terse (one line + Detail) for cross-component scanning. Never invoke it without asking first.

## Testing & Validation

After Phase 6, verify these gates before presenting output as final:

- [ ] Inventory names at least one component per category present in the session
- [ ] Every SWOT quadrant has at least one observation (no empty rows)
- [ ] Every P1 suggestion names a specific file, section, or step in its Detail field
- [ ] Top 5 Actions are drawn from P1 first; P2 entries appear only when no P1 remain
- [ ] No two suggestions share the same Detail description — merge duplicates before emitting
- [ ] Every output artifact found in scope (concept cards, plans, handoff reports, comparison/grader/dev-rules reports) was actually `Read`, not just listed by path
- [ ] Every Open Items entry found in a re-checked artifact was independently re-verified against current repo state, not copied forward as still-accurate
- [ ] Every non-resolving commit SHA found in a re-checked artifact was searched for a rebase-merge match and, if found, offered to the user as a direct fix — not just recorded as a Weakness and left stale
- [ ] Any `.draft/*.local.md` planning document modified in scope was `Read` for its current state, not just listed
- [ ] The report was persisted to `.claude/output/analyzing-sessions/` and its path confirmed with the standard `📄 ... written:` line
- [ ] A date-range scope always checks `~/.claude/projects/` for on-disk transcripts first (including sibling worktree-scoped directories) — the user is only asked to paste transcripts when no matching file exists on disk
- [ ] A narrow scope's gap-awareness check (Phase 1) ran, and any real uncovered window it found is stated plainly in the report — never silently absorbed into the narrow scope's own boundary

## Gotchas

- **Absence of evidence ≠ absence of use.** Rules in `.claude/rules/` load automatically — check the directory even if they were never mentioned in conversation.
- **`.draft/*.local.md` planning documents are gitignored, so they have no git history to fall back on.** If a scope needs a *prior* version of one (not just its current state), there's no `git log`/`git show` to recover it — same limitation as "Prior-session data" below, ask the user to paste it.
- **Weakness vs. Threat confusion.** Weaknesses are internal to the component (a missing gate, a wrong threshold). Threats are external (a stale dependency, an upstream change that will break the component). Do not cross-file them.
- **Over-suggestion.** Not every observation earns a suggestion. If two components produced the same fixable pattern, emit one cross-cutting suggestion, not two identical ones.
- **Prior-session data — check on-disk transcripts before asking the user to paste anything.** Session
  transcripts are stored at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, where `<encoded-cwd>`
  replaces every path separator, drive-letter colon, and literal dot with `-` (full encoding rule and
  fallback-matching procedure: `.claude/commands/find-permissions.md`'s Step 1-2 — don't restate it here,
  follow it). **Also check sibling directories** for the same project: a session run inside a git worktree
  of this repo is recorded under its own encoded directory (e.g.
  `<repo>--claude-worktrees-<topic>` or `<repo>-<worktree-dir-name>`, depending on the worktree's actual
  path), not inside the primary checkout's directory — `Glob('~/.claude/projects/*')` and match on the
  repo's leaf folder name as a prefix, not just the exact primary-checkout encoding, and state which
  directories were selected before proceeding. Filter candidates by mtime against the requested date
  range, then run a **cheap `Grep` pre-filter before any full `Read`** (this is what keeps cost bounded —
  see `plugin-lifecycle-maintenance`'s `self-service-plugin-devkit.md` Service 1 for the same pattern
  applied to a narrower plugin-devkit-only scope). For a transcript too large to read directly, delegate
  the digest extraction to a background `Agent` dispatch rather than reading it inline in this
  conversation. Only when no matching transcript file exists on disk for the requested scope does this
  fall back to asking the user to paste transcripts or summaries.
- **Self-referential sessions.** When `analyzing-sessions` is itself one of the components being analyzed, the assessment is inherently limited — the skill cannot objectively observe its own execution from outside. Note this explicitly in the SWOT weakness quadrant rather than producing inflated self-assessments.
- **Don't trust an artifact's own "Open Items" section at face value.** A handoff report (or similar) reflects what its author believed was true at write time — it is not re-verified just by existing. Treat every "still open" or "resolved" claim as a hypothesis to check against current repo state (Phase 2's Verify Open Items step), not a fact to relay forward. An artifact that's wrong about its own open items is itself a finding about the component that produced it, not noise to filter out.
- **Verify prior-state claims before writing them into a commit message or report — including this skill's own.** A claim like "this is new" or "X didn't exist before" is a testable assertion about current repo state, the same category as an artifact's Open Items claim above. This skill's own persistence feature was once introduced with exactly this unverified claim ("prior versions only ever showed the report in chat") — false, since an older per-component-file convention already existed on disk and was never checked for first. `Glob`/`Read` the relevant directory before asserting novelty, whether the claim is about another component or about this one.

## Reference Guide

| File | Purpose | When to read |
|---|---|---|
| `references/swot-framework.md` | Quadrant prompts and category-specific patterns | Phase 3 |
| `references/critique-reflection-framework.md` | Question sets per category; rationalizations to reject | Phase 4 |
| `references/suggestion-taxonomy.md` | Priority tiers, type definitions, merge rules, examples | Phase 5 |
| `enhancement-suggestor` agent | Expands a single P1/P2 suggestion into a full classified WHAT/WHY/HOW plan | Phase 6, on request |
| `.claude/output/analyzing-sessions/` | Where this skill's own reports are persisted, one file per run | Phase 6 (write), Phase 2 of a later run (read, if in scope) |
| `plugin-lifecycle-maintenance`'s `improve-a-plugin` workflow | Typical downstream consumer — takes this skill's persisted report and drives it through a human-decision gate into an applied, committed fix | After this skill's report is produced |

# Development Mode

Mode: Active development in a Claude Code plugin marketplace/devkit repo
Focus: Implementation, coding, building or modifying plugin components

You are in active development mode, in a repo whose own product is Claude Code plugins/skills/agents/
hooks/rules. The repo's own governance (CLAUDE.md, `.claude/rules/`) is always loaded — this profile
tunes *how* to move through it, not what it says.

## Behavioral Profile

- **Primary tools**: Write, Edit, Bash (tests/builds), the git-kit lifecycle skills
- **Secondary tools**: Read, Glob, Grep (to understand before modifying)
- **Risk tolerance**: Medium — write confidently, verify before finalizing a plugin component
- **Verbosity**: Low — brief explanations, focus on the change and the verification step
- **Decision style**: Act on clear requirements; ask only when genuinely ambiguous, or when a rule
  names an explicit `AskUserQuestion` gate

## Repo-Specific Operating Sequence

1. **Before the first edit of new work**: `Skill(git-kit:starting-work)` — never edit directly on
   `main`/`master` and retrofit a branch later (`starting-work-before-first-change.md`).
2. **All git/GitHub operations** go through the matching git-kit lifecycle skill (`commit`,
   `create-pr`, `collaborating-on-a-pr`, `merge-pr`, `finishing-work`) instead of the raw
   `git`/`gh` command, even when the raw command would work (`route-through-git-kit-lifecycle-skills.md`).
3. **Scratch/temp/test output**: session scratchpad or an existing gitignored location (`.draft/`,
   `.temp/`) — never the repo root, and never a plugin's own shippable directory
   (`require-gitignored-scratch-locations.md`; CLAUDE.md's "No Scratch Files at Repo Root").
4. **Before finalizing** any create/modify/rename/delete of a skill, agent, command, hook, or rule:
   run `Skill(plugin-rulebook)` (or dispatch the type-matched `*-reviewer` / `plugin-auditor` for a
   fuller pass). R1-R32 outranks CLAUDE.md and inline preference for naming/language/formatting/
   tool-scoping decisions on that component (`plugin-rulebook-enforcement.md`).
5. **New plugin, or a new component in a plugin with never-inventoried state**: sync
   `marketplace-inventory` then `plugin-inventory` before finalizing, with explicit
   `AskUserQuestion` approval before any `bootstrap` write. **New component in an already-inventoried
   plugin**: that plugin's own `plugin-inventory check` before finalizing
   (`require-inventory-updates-for-new-plugins-and-components.md`).
6. **Any behavior change** to a skill/agent/rule needs a test before it's done — a `skill-tester` eval,
   a persisted `scripts/smoke_test.*`, `agent-development`'s trigger-phrase battery, or direct execution
   against fixtures, matching the component type (`require-tests-for-behavior-changes.md`). `commit`
   gates on this via `AskUserQuestion` — don't silently mark "N/A" without that gate having run.
7. **New plugin**: declare one scripting language (Python or JS/TS) in its README/CONTRIBUTING at
   creation time; keep later scripts consistent with it (`require-declared-plugin-language.md`).
8. **New security-relevant gate** (auth/permission/bypass/trust-boundary check): dispatch
   `security-reviewer` against it before the first commit — don't defer to a later, unrelated audit
   (`require-security-review-before-new-gate.md`).
9. **In a worktree-bound session**: root every absolute `Read`/`Edit`/`Grep` path under the worktree
   segment, never the main checkout's path — this discipline does not reliably survive context
   compaction, so re-confirm explicitly after one (`require-worktree-rooted-absolute-paths.md`). After a
   worktree is removed mid-session, don't trust `git status`/`git log` alone as proof the session can
   write to the primary checkout — cross-check with a plain filesystem listing
   (`orphaned-worktree-git-read-fallthrough.md`).
10. **Never silently** override an already-made `AskUserQuestion` decision, skip a documented workflow
    phase, or change existing behavior — disclose it even when the change looks small or obviously
    correct (`disclose-before-overriding-decisions.md`).

## Guidelines

- For any file you'll modify, read it first.
- Make the smallest change that satisfies the requirement — no speculative abstraction, no unrelated
  cleanup (CLAUDE.md §2–3).
- Run tests/linters after every meaningful change; don't accumulate untested modifications.
- Commit messages: subject line + a short WHY (≤5 lines) — no bulleted changelog body, even for a large
  batched fix.
- Use `AskUserQuestion` (never a free-text "type yes/no") for any proceed/cancel/choice gate; for a list
  of related decisions, ask one at a time, not batched.
- When uncertain between two approaches, briefly state both and proceed with the simpler one.

## Output Style

- Concise, action-oriented — lead with the change or command, brief rationale after
- Use `file:line` references over prose descriptions
- Surface the next actionable step (including which gate/skill/check still needs to run) at the end

## Anti-Patterns

- Do NOT hand-roll a `git`/`gh` command when a git-kit lifecycle skill already covers the operation.
- Do NOT write scratch/test files to the repo root or into a plugin's own shippable tree.
- Do NOT finalize a new/changed skill/agent/command/hook/rule without an actual `Skill(plugin-rulebook)`
  (or equivalent agent) invocation — a recollection of an earlier check doesn't count.
- Do NOT skip the inventory-sync step for a new plugin or component.
- Do NOT assume a tool/API/language behaves as its name suggests — verify against its real schema/
  docs/a live call before writing an instruction that depends on it
  (`verify-tool-behavior-before-instructing.md` — this repo's single largest source of avoidable
  review rounds).
- Do NOT over-engineer or ask permission for obvious implementation choices.

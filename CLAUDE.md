# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Marketplace-Specific: Plugin Naming Convention

Unlike the guidelines above, this section is specific to this marketplace, not a portable rule.

Plugin names use `<domain>-kit` or `<domain>-devkit` — exactly one hyphen, placed immediately before the `kit`/`devkit` suffix, regardless of whether the domain itself is one word or several (e.g. `git-kit`, `plugin-devkit`, `python-devkit`).

**Not yet decided:** which suffix (`-kit` vs. `-devkit`) or prefix applies when — that requires first defining the actual list of suffixes/prefixes and their intended meaning. Tracked as an open item in `plugin-rulebook`'s `references/naming-conventions.md`; not implemented as a rulebook check until that list exists.

## Marketplace-Specific: No Scratch Files at Repo Root

Never write temporary, test, or scratch files to the repository root. Always use the session's scratchpad directory instead — watch for bare relative filenames (e.g. `Write("test-output.json", ...)`), which silently resolve to the current working directory (often the repo root) rather than the scratchpad.

**Why:** an untracked file at repo root is unnecessary clutter even when it can be deleted normally, and on machines where local permissions deny `rm` at the repo root (a personal/local setting, not a project-wide guarantee — check your own environment rather than assuming), such a file becomes permanent since it can't be cleaned up afterward at all. This has independently happened in at least two separate sessions under that exact local-permission constraint (a plugin-devkit session, and a scratch file left by an `analysis-kit` build's own smoke testing), confirming it's a recurring failure mode worth preventing outright, not one-off bad luck. Enforcement here is prose-only (no backing hook blocks a repo-root write) — a deliberate, disclosed tradeoff, not an oversight.

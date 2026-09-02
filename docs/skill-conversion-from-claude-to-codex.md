# Skill Conversion from Claude to Codex

How this repo actually converts `.claude/skills/` into `.agents/skills/` today, verified live against
the current code and working tree (2026-09-02) — not a description of intended behavior, a record of
what running it actually produced. See [`codex-skills-schema.md`](codex-skills-schema.md) for the
target schema this conversion should be producing.

## What's registered

[`.claude/marketplace-sync.json`](../.claude/marketplace-sync.json)'s `codex_exports.skills` lists
exactly **one** skill: `plugin-marketplace-review`. Every other skill under `.claude/skills/` (93
total in this repo) is not exported to Codex at all.

## How the registered skill is converted

`scripts/marketplace_ci/conversion.py`'s `plan_exports()` copies every file under a registered
skill's directory to `.agents/skills/<name>/` **byte-for-byte** — no frontmatter validation, no field
stripping, no schema adaptation, and no `agents/openai.yaml` generation. This is a materially
different code path from `.codex/agents/*.toml` export conversion (`convert_agent()`), which does
validate frontmatter against an allowed-key list and transform the content — see
[`codex-subagents-schema.md`](codex-subagents-schema.md).

Verified live: `diff -rq .claude/skills/plugin-marketplace-review .agents/skills/plugin-marketplace-review`
produced no output — the two directories are byte-identical.

**Consequence:** whatever Claude-specific frontmatter fields or tool references a registered skill's
`SKILL.md` happens to contain pass straight through to the Codex-facing copy, unexamined. In this
case it's low-risk by circumstance, not by design — `plugin-marketplace-review` has
`disable-model-invocation: true` and no `Bash`/`Skill` execution grant in its `allowed-tools`, so it's
inert as an invocable capability under either platform. Nothing in the conversion pipeline itself
checks for or enforces that; a future registered skill with an execution grant or an
`AskUserQuestion`/`Skill(...)` reference in its body would export unchanged, with no signal that those
don't work the same way — or at all — under Codex (see `codex-skills-schema.md`'s "Tool availability
differs" section).

Also worth noting: `plugin-marketplace-review`'s own `allowed-tools` is written as a YAML list
(`["Read", "Grep", "Glob"]`) rather than the base spec's documented space-separated string format
(confirmed elsewhere in this repo, e.g. `agent-development`'s `allowed-tools: Read Grep Skill ...`) —
an inconsistency within this repo's own skills, independent of the Codex-export question, not
something this conversion step normalizes either way.

## Stale, unregistered content under `.agents/skills/`

`.agents/skills/` currently contains 55 directories on disk. Only 1 (`plugin-marketplace-review`) is
registered. The other 54 — `agent-development`, `commit`, `starting-work`, and every other skill name
that appears there — are **not touched by the live conversion pipeline in either direction.**
`plan_exports()` only ever considers `registry.skills` (the registered list); an on-disk directory
with no matching registry entry is simply never visited by a normal `check-codex-exports` or
`convert-codex-exports` run.

Verified live: `uv run python -m scripts.marketplace_ci check-codex-exports` reports `OK` — a clean
pass — with all 54 stale directories still present. This isn't a bug in the check; it's checking the
registered set only, by design (`plan_exports(repo, registry, previous=None)` uses the default
`bootstrap=False`, which skips the "does this on-disk destination have a canonical source at all?"
scan entirely).

The only thing that surfaces this drift is the separate `repair-all --bootstrap` command, which is
**never invoked by CI** (`.github/workflows/marketplace-ci.yml` calls plain `check-all`, not
`repair-all --bootstrap`) and exists as a manual, on-demand tool only. Run live:

```
uv run python -m scripts.marketplace_ci repair-all --bootstrap
```

reported exactly **376 files** across the 54 unregistered directories as
`warn: ... no canonical source found for this destination; requires manual classification` — flagged
as informational warnings, not blocking failures (`_report()` in `__main__.py` only treats a
non-`warn` operation as a problem).

**This content predates the current plain-copy mechanism.** Spot-checking
`.agents/skills/agent-development/SKILL.md` against the canonical
`.claude/skills/agent-development/SKILL.md` shows systematic text substitution — "Claude Code" →
"Codex", "Claude decides based on description" → "Codex decides based on description", and so on,
throughout the frontmatter description and body. Today's `plan_exports()` never does text
substitution; it only ever copies bytes verbatim. This confirms the 54 stale directories were produced
by some earlier, different, no-longer-active process — not by the code currently in this repo — and
have simply never been reconciled or removed since.

## Summary of open items (not fixed by this document)

This document is a verification record, not a fix — per this session's task scope, these are
disclosed as findings rather than silently patched:

1. **No schema/field adaptation on skill export.** A registered skill's Claude-only frontmatter
   fields (`argument-hint`, `disable-model-invocation`, `hooks`, `model`) and any
   Claude-tool-specific body content export unchanged, with no check for whether they mean anything
   — or anything safe — under Codex.
2. **54 stale, unregistered directories under `.agents/skills/`**, invisible to every check CI
   actually runs, confirmed to originate from a retired conversion approach. Candidates for either
   registering (if still wanted as Codex exports) or removing (if genuinely abandoned) via
   `repair-all --bootstrap`'s own reconciliation flow.
3. **No `agents/openai.yaml` support** in the conversion pipeline — not needed unless a registered
   skill wants ChatGPT-desktop-specific presentation or an explicit `allow_implicit_invocation`
   policy, but the pipeline has no path to add one today even if a skill needed it.

## Related

- [`codex-skills-schema.md`](codex-skills-schema.md) — the target schema (base spec + Codex's own
  support) this conversion should be producing against.
- [`codex-subagents-schema.md`](codex-subagents-schema.md) — the sibling `.codex/agents/*.toml`
  export, which *does* validate and transform frontmatter, for contrast.
- [`codex-review-configuration.md`](codex-review-configuration.md) — the third Codex integration
  point in this repo (`AGENTS.md`'s `## Code Review Rules`).

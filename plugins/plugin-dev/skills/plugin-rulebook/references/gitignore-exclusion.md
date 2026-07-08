# Gitignore Exclusion Procedure

Any reviewer agent that resolves files via `Glob` — whether scanning broadly across a plugin/project or falling back to a by-name search for a single target — must exclude gitignored paths from the result before reviewing them.

## Why this matters

Gitignored directories typically hold draft, imported, backup, or not-yet-shipped content — e.g. `to-implement/`, `.rulebook/`, `.backup/`, `.planned/`, `.merged/`. Reviewing this content alongside the plugin's real, shipped components produces noise: stale-content findings that don't reflect what the plugin actually ships, and false external-reference findings from draft imports that were never meant to be cleaned up yet. It can also cause a by-name Glob fallback to resolve to the wrong copy — e.g. a draft `to-implement/agents/skill-reviewer.md` sitting alongside the real `agents/skill-reviewer.md` — which is the same shadow-copy hazard R19 already guards against for canonical path resolution.

## Procedure

1. Read the nearest applicable `.gitignore` file(s) — start at the repository root; also check for a nested `.gitignore` inside the target plugin/component directory if one exists.
2. Parse each non-comment, non-blank line as a pattern. A leading `!` negates (re-includes) a path that an earlier pattern matched.
3. Before including any file or directory found via `Glob` in the review, check it against the parsed patterns — a pattern ending in `/` matches that directory and everything under it; a `**/name/` pattern matches `name` at any depth.
4. Exclude every match unless a later `!`-negation pattern re-includes it.

## Tool-constraint caveat

Reviewer agents in this plugin only have `Read`/`Grep`/`Glob` — no `Bash`, so no `git check-ignore`. This procedure is therefore pattern-matching against `.gitignore`'s literal text, not a full reimplementation of git's ignore semantics. In particular, a path that's already tracked/staged in git despite matching an ignore pattern (git doesn't retroactively un-track it) will still be excluded here, since there's no way to check the git index without `Bash`. If this distinction matters for a specific review, label it `⚠️ Unverified: possible git-tracked exception to a gitignore pattern` rather than asserting the exclusion is authoritative.

## Authoring Side: Never Reference a Gitignored Path as a Live Dependency

The procedure above governs what a reviewer *scans*. This section governs what a component's own instructions may *claim exists*: no skill, script, agent, rule, hook, command, or reference file may direct Claude to read, run, or otherwise depend on a path that is gitignored — a `to-implement/` draft, a `.rulebook/` audit report, `.claude/output/` artifacts, `.backup/`/`.planned/`/`.merged/` content, or similar.

This is a distinct failure mode from the scanning concern above: it doesn't require a broad Glob to surface — a single hardcoded reference in a component's own body (e.g. "read `${CLAUDE_PLUGIN_ROOT}/RULES.md` as a format reference") is enough to violate it, and it's wrong even if the path happens to resolve today, because gitignored content is explicitly not part of the shipped surface and can be deleted at any time without that being a breaking change to the plugin.

**A gitignored path being named as an *output* a command writes to is not a violation** — `.claude/output/` exists precisely so commands can write ephemeral reports there; `--output-dir .claude/output/rules` in a command's own argument defaults is fine. The violation is specifically treating a gitignored path as something that must already exist and be *read* as a dependency.

`external-references-reviewer`'s Step 5 resolvability check already catches one instance of this pattern (a `<namespace>:<component>` reference that doesn't Glob-resolve is **Broken**) — treat a reference that resolves only inside a gitignored directory the same way: **Broken**, Critical, even though it technically resolves, because gitignored content is not a stable dependency.

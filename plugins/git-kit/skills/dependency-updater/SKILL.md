---
name: dependency-updater
description: >-
  Scan a project's package manifests across ecosystems (Python, JavaScript/npm, Rust, Go) for outdated dependencies, detect version conflicts across a monorepo, and propose updates with explicit confirmation before applying any change. Use when checking for outdated dependencies, planning a dependency bump, auditing dependency freshness, or asked to update packages across a repo or monorepo.
allowed-tools: Glob, Read, Edit, Bash(uv:*), Bash(pip:*), Bash(npm:*), Bash(cargo:*), Bash(go:*), Bash(git diff:*), Bash(git status:*)
---

# Dependency Updater

Discover a project's package manifests, check each ecosystem for outdated dependencies, flag version conflicts across a monorepo, and propose specific updates — never applying anything without confirmation.

This skill has no dependency on any other plugin. The optional security-advisory step (step 5) is self-contained: it only runs an ecosystem's own advisory tool if one is available, and is skipped entirely otherwise.

## Instructions

1. **Discover manifests**: use `Glob` to find package manifests across the repo, including nested workspace members (e.g. `**/pyproject.toml`, `**/requirements*.txt`, `**/package.json`, `**/Cargo.toml`, `**/go.mod`). In a monorepo, a manifest can exist at the root and again under each package/plugin directory — collect all of them, not just the first match.
2. **Check each ecosystem found** for outdated dependencies:
   - Python: `uv pip list --outdated` if the project uses `uv` (a `uv.lock` is present), otherwise `pip list --outdated`
   - JavaScript/npm: `npm outdated`
   - Rust: `cargo outdated` (if the `cargo-outdated` subcommand isn't installed, note that and skip — don't fail the whole scan over one missing tool)
   - Go: `go list -u -m all`
3. **Build a per-ecosystem table**: package, current version, latest version, and update type (patch/minor/major) inferred from semver.
4. **Detect version conflicts**: within the same ecosystem, the same dependency pinned to different versions across manifests in the repo (common in monorepos where each package pins independently). Flag these separately from ordinary outdated-version findings — they need a compatible-version decision, not just a bump.
5. **Security advisories (optional)**: if the ecosystem has its own advisory tool readily available (e.g. `npm audit`, `pip-audit` if installed), offer to run it and fold any findings into the table. Skip silently if no such tool is available — do not treat this as a failure, and do not reach for any external plugin or service to fill the gap.
6. **Present findings**: show the full table grouped by ecosystem, with major-version bumps and cross-manifest conflicts called out most prominently — those carry the highest risk of breaking changes.
7. **Confirm which updates to apply**: use `AskUserQuestion` — options should include at minimum "patch/minor only" (lower risk), "all including major" (higher risk), "let me pick specific packages," and "none, just report." Never apply an update the user hasn't approved.
8. **Apply approved updates**: edit each manifest's version pin directly (`Edit`). Batch by ecosystem.
9. **Regenerate lockfiles**: for each ecosystem with edited manifests, ask for a second, separate confirmation before running the install/lock command (`npm install`, `uv lock`, `cargo update`, `go mod tidy`) — this mutates lockfiles and can pull in transitive changes beyond what was approved in step 7, so it gets its own gate rather than riding along with step 7's approval.
10. **Show the result**: which files changed (`git status`/`git diff`), old → new version per package actually applied.
11. **Remind, don't run, tests**: dependency bumps — especially major ones — can break builds or behavior. Tell the user to run their test suite before committing; don't run it automatically, since test commands vary per project and can be slow.

## Monorepo Consistency

When the same dependency is bumped across multiple manifests in one pass, keep every occurrence on the same resolved version — don't leave some manifests updated and others on the old pin. If a conflict (step 4) can't be resolved to one compatible version across all manifests that need it, surface that explicitly rather than picking one silently.

## What This Skill Does NOT Do

- Does not install *new* dependencies — it only updates versions of dependencies already present in a manifest.
- Does not migrate code for breaking API changes introduced by a major bump — it reports the bump, the user (or a separate coding pass) handles the migration.
- Does not run the project's test suite or CI checks.
- Does not depend on any other plugin, agent, or hook — every step above uses only this repo's own manifests and each ecosystem's own CLI tooling.

---
description: >-
  Classify candidate permissions from find-permissions, and audit every existing
  settings.local.json/settings.json entry, for risky or destructive commands that
  belong in ask or deny instead of allow.
argument-hint: "[--candidates <path>] [--output-dir <dir>]"
allowed-tools: Read Write Bash(mkdir:*) Bash(date:*)
model: opus
---

Verify a candidate report from find-permissions (if provided) and audit all existing permission entries for risk, producing a classification report consumed by apply-permissions: $ARGUMENTS

> **Invocation:** Run as `/verify-permissions` in the Claude Code prompt. This command cannot be invoked via `Skill()` — it must be triggered as a slash command or followed manually.

> **Pipeline:** Step 2 of 3. Reads a candidate report from `/find-permissions` (optional — omitting `--candidates` runs an existing-entries-only audit), writes a verified classification report consumed by `/apply-permissions`.

**Safety-vs-autonomy default:** a command classified `deny` stays blocked even in headless (`claude -p`) mode, where nothing can answer an `ask` prompt. Anything genuinely destructive is classified `deny`, never `ask` — `ask` is reserved for commands that are fine with a human present but shouldn't run unattended.

---

## Step 1: Parse Arguments

| Argument | Required | Default | Notes |
|---|---|---|---|
| `--candidates <path>` | No | — | Path to a `find-<timestamp>.md` report from `/find-permissions`. If omitted, this run only audits existing entries. |
| `--output-dir` | No | Same directory as `--candidates`, else `.claude/output/permissions` | Where to write the classification report |

## Step 2: Load Inputs

If `--candidates` is given, read that file's `## Candidates` table in full.

Read `.claude/settings.local.json` and `.claude/settings.json`'s `permissions.allow`/`deny`/`ask` arrays (each may be absent — treat as empty). Every `Bash(...)` entry currently in `allow` is in scope for reclassification; entries already in `ask`/`deny` are assumed intentionally placed and are only re-flagged if Step 3 finds them clearly over-restrictive (e.g. a fully read-only command sitting in `deny` for no apparent reason) — treat that as a rare, explicitly-noted exception, not a routine check.

## Step 3: Classify by Risk

For every candidate pattern (from Step 2's file, if any) and every existing `allow` entry, classify into exactly one tier. This table operationalizes CLAUDE.md's own "Executing actions with care" categories — it is not an independent taxonomy:

| Tier | Criteria | Representative patterns |
|---|---|---|
| `deny` | Destructive, hard-to-reverse, or unsafe to ever run unattended | `rm -rf`, `git push --force`/`-f`, `git reset --hard`, `git clean -f`, `git branch -D`, `DROP`/`TRUNCATE` (SQL), `kill -9`/`taskkill /F`, `sudo *`, piping remote content into a shell (`curl … \| sh`, `curl … \| bash`), writes to credential/secret-shaped paths (`.env`, `.pem`, `id_rsa`, `.aws`, `.npmrc`), `docker system prune`, `terraform destroy`, `kubectl delete`, force-pushing tags |
| `ask` | Reversible but consequential, visible to others, or affects shared state | Non-force `git push`, `gh pr merge`/`gh pr create`, `npm publish`, writes to a non-sandboxed database, `git commit --amend` on a shared branch, anything that posts/notifies externally |
| `allow` | Reversible, local-only, low blast radius | Read-only commands (`git status`, `git diff`, `git log`, `ls`, `cat`), linting/testing/build commands scoped to the repo, file operations confined to the repo or scratchpad |

For each classification, record a one-line reason citing the specific criterion matched (not just the tier name).

**Do not silently downgrade an existing `ask`/`deny` entry to `allow`** unless Step 3's own criteria clearly show it was over-restrictive — this is the same asymmetric caution `verify-dev-rules`' "Automatic safeguard" applies to its own more/less restrictive gap comparisons: a false positive that loosens a deliberate restriction is worse than a false negative that leaves an over-cautious entry in place for a human to review later.

## Step 4: Re-check Before Finalizing

For every non-`allow` classification (both new candidates and reclassified existing entries), re-confirm the cited criterion actually matches the command text — don't trust Step 3's own pass from memory. Check for contradictions: no two rows should classify the same normalized pattern differently. Drop or downgrade to `ask` any `deny` classification whose criterion doesn't hold up on re-check, and note why.

## Step 5: Write Classification Report

Get a timestamp (`Bash(date -u +%Y-%m-%dT%H-%M-%SZ)`), create the output directory if needed, and write:

```markdown
# Permission Verification Report

Classifies candidate permissions (if provided) and audits existing settings.local.json/settings.json entries for risk.
**Generated:** {YYYY-MM-DD} | **Candidates input:** {path, or "none — existing-only audit"} | **Entries audited:** {n}

## New Candidates (from find-permissions)
| Pattern | Classification | Reason | Frequency |
|---|---|---|---|

## Existing Entries Requiring Reclassification
| File | Current Bucket | Pattern | Recommended Bucket | Reason |
|---|---|---|---|---|

## Unchanged (Correctly Classified)
{n} entries reviewed, already correctly classified — not enumerated here.

## Summary
New candidates: {n} (allow: {n}, ask: {n}, deny: {n}) | Reclassifications: {n} | Unchanged: {n}
```

Write to `{output-dir}/verify-<timestamp>.md`.

## Step 6: Confirm Output

Print:
```
Verification report written: {output-dir}/verify-<timestamp>.md
New candidates: {n} | Reclassifications: {n}

Next: /apply-permissions --report {output-dir}/verify-<timestamp>.md
```

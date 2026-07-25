---
description: >-
  Scan past session transcripts for Bash commands with no matching permission rule
  and produce a candidate report consumed by verify-permissions.
argument-hint: "[--recent <n>|--session <id>|--all] [--output-dir <dir>]"
allowed-tools: Read Write Glob Bash(mkdir:*) Bash(date:*) Bash(pwd:*) Bash(jq:*) Bash(ls:*)
model: sonnet
---

Scan one or more past session transcripts for Bash commands that have no matching entry in the current permission configuration, and write a candidate report: $ARGUMENTS

> **Invocation:** Run as `/find-permissions` in the Claude Code prompt. This command cannot be invoked via `Skill()` — it must be triggered as a slash command or followed manually.

> **Pipeline:** Step 1 of 3 in the permissions pipeline: `/find-permissions` (this command) → `/verify-permissions` (classify candidates and existing entries by risk) → `/apply-permissions` (write confirmed entries). Each step reads the previous step's output. Independent of this pipeline: `/trim-permissions` (dedup/subsumption cleanup, run any time) and `analyzing-sessions` (general retrospectives — this command's own scan is the primary data source for permission candidates; a recent `analyzing-sessions` report in scope is read only as corroborating narrative context, per its own Permission Friction note).

**Scope note:** This command covers **past, completed sessions only** — "post-session retros," per its own purpose. It does not read the current, still-open conversation's own transcript file mid-session; run it after the session you want analyzed has ended.

**Coverage note:** v1 scope is `Bash(...)` commands only — the dominant source of permission friction, and the same scope `trim-permissions` already covers. Other tool types (`WebFetch`, MCP tools, etc.) are not extracted; the report states this explicitly rather than silently omitting it.

---

## Step 1: Parse Arguments

| Argument | Required | Default | Notes |
|---|---|---|---|
| `--recent <n>` | No | `3` | Analyze the N most-recently-modified session transcripts for this project |
| `--session <id>` | No | — | Analyze one specific session transcript by ID instead of `--recent` |
| `--all` | No | — | Analyze every session transcript for this project |
| `--output-dir` | No | `.claude/output/permissions` | Where to write the candidate report |

`--session` and `--all` each override `--recent` if present; `--session` takes precedence if both are given.

## Step 2: Locate Session Transcripts

Session transcripts are stored at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, where `<encoded-cwd>` replaces every path separator (`/` or `\`), drive-letter colon, and literal dot in the current working directory's absolute path with `-` (e.g. `C:\Dev\Repos\my-project` → `C--Dev-Repos-my-project`).

1. Compute the expected encoded directory name from `pwd`.
2. `Glob('~/.claude/projects/*')` and confirm a directory matching the computed name exists. If not found exactly, fall back to matching the directory whose name contains the repo's leaf folder name, and state which directory was selected before proceeding — do not guess silently among multiple candidates.
3. Within that directory, select transcript file(s) per Step 1's resolved mode: the N most-recent by mtime (`ls -t`), the one matching `--session`, or all files.
4. If `--all` resolves to more than 10 files, print the count and ask for confirmation before proceeding — this can be slow and produce a noisy report.

## Step 3: Extract Bash Commands

For each selected transcript file, extract every Bash `tool_use` command:

```
jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and .name=="Bash") | .input.command' <file>
```

Collect all extracted commands across all selected files, tagged with their source session file.

## Step 4: Normalize and Diff Against Current Permissions

For each extracted command, derive its normalized permission-rule form the same way `trim-permissions` reasons about entries: the command's own first token plus any fixed prefix up to its first variable argument (e.g. `git commit -m "fix bug"` → candidate pattern `Bash(git commit:*)`, or a broader existing `Bash(git:*)` if that grouping is already used in `settings.local.json`).

Read `.claude/settings.local.json` and `.claude/settings.json`'s `permissions.allow`/`deny`/`ask` arrays (each may be absent — treat as empty). For each normalized candidate pattern, check whether it is already covered — exact match, or subsumed by an existing broader wildcard in either file (same subsumption logic as `trim-permissions` Step 2.B). Keep only candidates **not** already covered by any existing rule — these are the ones that most likely triggered a permission prompt.

Group kept candidates by normalized pattern, with: frequency (count across all selected sessions), first/last seen session file, and 1-2 example full commands.

## Step 5: Corroborate with analyzing-sessions (Optional)

`Glob('.claude/output/analyzing-sessions/*.md')` for reports whose timestamp falls within the scanned sessions' date range. If any exist, `Read` their Permission Friction note (if present) and attach it to the report as corroborating narrative context — this never changes which candidates are kept from Step 4, it only adds qualitative color (e.g. "user commented on repeated approval friction for X").

## Step 6: Write Candidate Report

Get a timestamp (`Bash(date -u +%Y-%m-%dT%H-%M-%SZ)`), create the output directory if needed (`mkdir -p`), and write:

```markdown
# Permission Candidates Report

Scanned {n} session transcript(s) for Bash commands with no matching current permission rule.
**Generated:** {YYYY-MM-DD} | **Scope:** {recent N / session ID / all} | **Sessions:** {list of files}
**Coverage:** Bash commands only (v1) — other tool types not scanned.

## Candidates
| Pattern | Frequency | Sessions | Example |
|---|---|---|---|
| `Bash(git commit:*)` | 5 | session-abc, session-def | `git commit -m "fix bug"` |

## Corroborating Context (if any)
{analyzing-sessions Permission Friction excerpts, or "None found in scope."}

## Summary
Candidates found: {n} | Sessions scanned: {n} | Commands extracted: {n} total, {n} unique patterns
```

Write to `{output-dir}/find-<timestamp>.md`.

## Step 7: Confirm Output

Print:
```
Candidate report written: {output-dir}/find-<timestamp>.md
Candidates found: {n}

Next: /verify-permissions --candidates {output-dir}/find-<timestamp>.md
```

# Companion Invocation Protocol

Shared reference for codex-kit's task/review skills. Read on demand when launching
the companion script, when the inline ANALYZE rules in a SKILL.md don't cover an
edge case, or when an error needs categorization.

References below cite function/constant **names** in codex-kit's own bundled
`scripts/codex-companion.mjs` and `scripts/lib/*.mjs`, not line numbers — line
numbers drift the moment either file is edited, while a function/constant name
stays valid until the function itself is renamed. Everything below was verified
directly against the current source at the time of this revision.

---

## 1. Resolve the companion

```bash
CODEX_COMPANION="${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs"
```

`CODEX_COMPANION` resolves directly to codex-kit's own bundled
`codex-companion.mjs` path inside the user's plugin install. If the Codex CLI
itself isn't installed or runnable, calls fail with `"Codex CLI is not
installed or is missing required runtime support..."` (see §6) — this is the
`setup` error category. Redirect the user to `/codex-kit:setup` and stop.

---

## 2. Verified flag whitelists per subcommand

Every flag below was verified against `codex-companion.mjs`. "Documented"
means it appears in `printUsage`'s output; "parser-only" means it is accepted
by `parseCommandInput` (which wraps `lib/args.mjs`'s `parseArgs`) but not
printed in usage.

### `review` (`handleReviewCommand`)

| Flag | Type | Status | Honored? |
|------|------|--------|----------|
| `--base <ref>` | value | documented | yes |
| `--scope <auto\|working-tree\|branch>` | value | documented | yes |
| `--model <m>` | value | parser-only | **yes** — threaded through `executeReviewRun` → `runAppServerReview` → `startThread({ model })` in `lib/codex.mjs`. Passed as a per-call companion flag directly; not written to `config.toml` unless the skill/command explicitly offers `--persist`. |
| `--cwd <path>` | value | parser-only | yes |
| `--json` | bool | parser-only | yes |
| `--effort <level>` | value | parser-only | **yes** — registered in `handleReviewCommand`'s `valueOptions` and threaded through the same `executeReviewRun` → `runAppServerReview` → `startThread({ effort })` path. |
| `--background` | bool | documented in `printUsage` | **NO — silent no-op** (see §3) |
| `--wait` | bool | documented in `printUsage` | **NO — silent no-op** (see §3) |
| (positional focus text) | — | — | **rejected** by `validateNativeReviewRequest` |

### `adversarial-review` (`handleReviewCommand`, same handler)

Identical `valueOptions`/`booleanOptions` as `review`. The only difference:
adversarial does NOT call `validateNativeReviewRequest`, so positional focus
text IS accepted (joined with spaces via `positionals.join(" ")`).

**Neither** review nor adversarial has `--commit` or `--uncommitted`. To
review a specific commit, use `--base <sha>~1 --scope branch`.

### `task` (`handleTask`)

| Flag | Type | Status | Notes |
|------|------|--------|-------|
| `--write` | bool | documented | enables code changes |
| `--background` | bool | documented | **honored** — calls `enqueueBackgroundTask` |
| `--resume-last` | bool | documented | resume most recent completed task |
| `--resume` | bool | documented | alias for `resume-last` |
| `--fresh` | bool | documented | opposite of resume; mutually exclusive with resume/resume-last |
| `--json` | bool | parser-only | structured output |
| `--model <m>` | value | documented | accepts `spark` alias (`MODEL_ALIASES` maps it to `gpt-5.3-codex-spark`) |
| `--effort <level>` | value | documented | one of `VALID_REASONING_EFFORTS`: `{none, minimal, low, medium, high, xhigh}` |
| `--cwd <path>` | value | parser-only | |
| `--prompt-file <path>` | value | **parser-only** (not in `printUsage`) | read via `readTaskPrompt` |
| `--wait` | — | **NOT REGISTERED** | silently pushed to positionals → **prompt corruption**, see §3 |

### `status` (`handleStatus`)

| Flag | Type | Status | Notes |
|------|------|--------|-------|
| `--wait` | bool | parser-only | **honored** — calls `waitForSingleJobSnapshot` |
| `--timeout-ms <ms>` | value | parser-only | default `DEFAULT_STATUS_WAIT_TIMEOUT_MS = 240000` |
| `--poll-interval-ms <ms>` | value | parser-only | default `DEFAULT_STATUS_POLL_INTERVAL_MS = 2000` |
| `--all` | bool | documented | list all jobs |
| `--json` | bool | documented | |
| (positional jobId) | — | — | required when using `--wait` |

### `result` (`handleResult`)

| Flag | Type | Notes |
|------|------|-------|
| `--json` | bool | |
| `--cwd <path>` | value | |
| (positional jobId) | — | optional — resolves latest if omitted |

### `cancel` (`handleCancel`)

| Flag | Type |
|------|------|
| `--json` | bool |
| (positional jobId) | — |

### `transfer` (`handleTransfer`)

| Flag | Type | Notes |
|------|------|-------|
| `--source <path>` | value | Claude session `.jsonl` to import. Falls back to `CODEX_KIT_TRANSCRIPT_PATH` env (`resolveClaudeSessionPath` in `lib/claude-session-transfer.mjs`) when omitted. |
| `--json` | bool | |
| `--cwd <path>` | value | Accepted by `handleTransfer`'s `valueOptions` but **not shown in `printUsage`'s transfer line** — don't copy the usage line as the full flag set. |

No `--model`/`--effort`/`--wait`/`--background` — transfer has no prompt and completes synchronously (≤2 min), so none of those concepts apply. Result payload includes `threadId` and `resumeCommand` (`codex resume <threadId>`) rendered verbatim by `renderTransferResult`.

### 2a. `normalizeArgv` quirk

`normalizeArgv` re-tokenizes input via `splitRawArgumentString`
**only when `argv.length === 1`**. An old broken pattern like

```bash
node "$CODEX_COMPANION" task "$ARGUMENTS"
```

(a single arg containing spaces) goes through this hidden re-split path
that **looks** like it works but is fragile — quoting rules diverge from
the shell and edge cases break silently.

codex-kit's task/review skills always invoke the companion with **multi-arg
form** (`task --background --json`), so this branch never fires. Never pass
`$ARGUMENTS` as a single quoted blob.

---

## 3. The truth about `--wait` and `--background`

This is the single most important thing to understand about the companion.

### `status --wait <jobId>` — REAL

- `handleStatus`'s `booleanOptions` includes `wait`.
- Handler honors it via `waitForSingleJobSnapshot`.
- Uses `DEFAULT_STATUS_WAIT_TIMEOUT_MS = 240000`, safely under
  Bash's 300s tool timeout.
- This is the **only** universal wait mechanism in the companion.

### `review --wait`, `adversarial-review --wait` — SILENT NO-OP

- `handleReviewCommand`'s `booleanOptions` includes both `background` AND
  `wait`, so the parser accepts them.
- BUT `handleReviewCommand` **never reads** `options.wait` or
  `options.background` — it unconditionally calls `runForegroundCommand`.
- Both flags are silent no-ops. Review / adversarial-review always run in
  the foreground.
- `printUsage` still advertises `review [--wait|--background]` — this is a
  known cosmetic inconsistency in the usage text, not a behavior contract.

### `task --wait` — SILENT PROMPT CORRUPTION

- `handleTask`'s `booleanOptions` is
  `["json", "write", "resume-last", "resume", "fresh", "background"]`.
  **No `wait`.**
- `parseArgs` (`lib/args.mjs`) does NOT raise an unknown-flag error for a
  long-form flag outside `valueOptions`/`booleanOptions`. It silently pushes
  the token into `positionals`.
- `readTaskPrompt` does `positionals.join(" ")` and uses that
  as the task prompt body.
- Result: Codex receives the literal string `"--wait"` as part of its task
  prompt. No stderr. No exit code. Silent prompt corruption.

The same silent-corruption path applies to **any** unknown flag passed to
**any** companion subcommand, because `parseArgs` has no "unknown flag"
mode for long-form flags. This is not a task-specific footgun; it's the
parser's contract.

**There is no companion-side safety net.** Phase 1 ANALYZE whitelisting in
each skill is the only line of defense.

---

## 4. Two invocation patterns

codex-kit's task/review skills use exactly two patterns to run the companion.

### Pattern A — review / adversarial-review

The companion's `--background` is a no-op here, so we use Claude's own Bash
`run_in_background=true` to keep the wrapper alive past Bash's 300s
per-call timeout. Poll primarily via `BashOutput`, not `/codex-kit:status` —
the companion still tracks this run as a job internally (see §5), so
`/codex-kit:status --all` remains a useful side channel if the primary
`BashOutput`-based poll ever needs cross-checking.

```bash
set -o pipefail
CODEX_COMPANION="${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs"

mkdir -p "${CLAUDE_PLUGIN_DATA}/tmp"
TS=$(date +%s%N)
OUT_FILE="${CLAUDE_PLUGIN_DATA}/tmp/review-${TS}.json"
ERR_FILE="${CLAUDE_PLUGIN_DATA}/tmp/review-${TS}.log"
echo "OUT_FILE=$OUT_FILE"
echo "ERR_FILE=$ERR_FILE"

# Launch via Bash run_in_background=true (Claude-side).
# Replace <literal ...> with values from Phase 1.
node "$CODEX_COMPANION" review --json \
  --base "<literal clean base from Phase 1>" \
  > "$OUT_FILE" 2> "$ERR_FILE"
```

**Phase 3 polling spec** (do not improvise):

| Item | Value |
|------|-------|
| Tool | `BashOutput` — never `ps`, `kill`, or state JSON reads |
| Cadence | 30 seconds between polls (60s acceptable for very long reviews) |
| Termination | `BashOutput` response field `status === "completed"` (NOT stdout content matching — payload format may change) |
| Total cap | 30 minutes (review p99 ≈ 20 min; 30 min gives headroom) |
| Cap exceeded | `wait-timeout` (§6) → `KillShell` the bash_id → if `$OUT_FILE` is non-empty and parses as JSON treat as partial result, otherwise `recovery-impossible` |
| `$OUT_FILE` empty after exit | Companion crashed / SIGKILLed. Read `$ERR_FILE`, categorize, save `<type>-<ts>-failed.md` |
| `$OUT_FILE` non-JSON | `unexpected-format` (§6). Show raw stderr verbatim, abort |

Claude must remember the bash_id **and** the absolute `$OUT_FILE` /
`$ERR_FILE` paths printed in Phase 1 — they are needed in Phase 3/4. Bash
spawns a fresh shell per call, so local variables do not persist; always
reuse the literal paths you captured from stdout.

### Pattern B — task family (rescue / verify / research)

The companion's `--background` IS honored for `task`. It returns a job
payload immediately, then polls via `status --wait`.

**Step 1 — set up paths and temp file naming:**

```bash
set -o pipefail
CODEX_COMPANION="${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs"

mkdir -p "${CLAUDE_PLUGIN_DATA}/tmp"
TS=$(date +%s%N)
PROMPT_FILE="${CLAUDE_PLUGIN_DATA}/tmp/<skill>-prompt-${TS}.txt"
JOB_JSON_FILE="${CLAUDE_PLUGIN_DATA}/tmp/<skill>-job-${TS}.json"
echo "PROMPT_FILE=$PROMPT_FILE"
echo "JOB_JSON_FILE=$JOB_JSON_FILE"
```

(Assemble `$PROMPT_FILE` next — see §8 for the blind-payload pattern.)

**Step 2 — launch via stdin pipe and capture the job ID.** NEVER pass a
positional arg — `readTaskPrompt` does `positionalPrompt ||
readStdinIfPiped()`, so a positional silently short-circuits stdin and
drops the entire blind payload:

```bash
cat "$PROMPT_FILE" | node "$CODEX_COMPANION" task --background --json \
  > "$JOB_JSON_FILE" 2> "${JOB_JSON_FILE}.stderr" \
  || { echo "task launch failed:" >&2; cat "${JOB_JSON_FILE}.stderr" >&2; exit 1; }

# Capture jobId — use node (already a dependency) to avoid host-python assumptions
JOB_ID=$(node -e 'const fs=require("fs");try{const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));if(!j.jobId)throw new Error("no jobId");process.stdout.write(j.jobId);}catch(e){process.stderr.write("JOB_ID parse failed: "+e.message+"\n");process.exit(1);}' "$JOB_JSON_FILE") \
  || { echo "raw companion stdout:" >&2; cat "$JOB_JSON_FILE" >&2; exit 1; }
echo "JOB_ID=$JOB_ID"
```

**Step 3 — poll, then fetch the result.** Each call blocks ≤4 min (well
under Bash's 300s limit). Re-call until status is `"completed"` or
`"failed"`. Cap at 6 iterations (24 min) total:

```bash
node "$CODEX_COMPANION" status --wait "$JOB_ID" \
  --timeout-ms 240000 --json

node "$CODEX_COMPANION" result "$JOB_ID" --json
```

`status --wait` returns a snapshot with `waitTimedOut: true` when the
deadline hits but the job is still running. Re-call in that case. On the
cap, surface as `wait-timeout` (§6).

---

## 5. Job ID capture

- Always pass `--json` to commands whose output you intend to parse. The
  rendered text format is not stable across releases.
- Parse jobId with `node -e '...'` (already a runtime dependency). Do NOT
  grep / regex the rendered output.
- **Pattern A:** there is no `jobId` field in the review/adversarial-review
  JSON *payload* — the relevant identifier there is `payload.threadId`, at
  the top level of the `$OUT_FILE` payload, in the same location for both
  `review` and `adversarial-review`. This does **not** mean the companion
  skips job tracking for these calls: `handleReviewCommand` still creates
  and persists a job record (`review-<id>`) exactly like `task` does, so
  the run is visible via `/codex-kit:status --all` while it's running and
  after it completes. That companion-side job ID is simply never returned
  to the caller in the payload the way `task --background`'s `jobId` is —
  Claude has no need for it, since Pattern A polls via Claude's own
  `run_in_background`/`BashOutput` bash_id instead, not via
  `status --wait <jobId>` (see §4).
- **Pattern B:** jobId is in the immediate response from
  `task --background --json` as `{"jobId": "...", "status": "queued", ...}`.
- **Always set `set -o pipefail`** before any `cat file | node ...` or
  similar pipeline. Without it, a failing left side (e.g., missing
  `PROMPT_FILE`) sends 0 bytes into the companion, which then throws
  `"Provide a prompt, a prompt file, piped stdin, or use --resume-last."`
  (see `requireTaskRequest`) — masking the real root cause.

---

## 6. Error categorization

All verbatim strings below were verified against `codex-companion.mjs` and
its `lib/*.mjs` modules. Never retry silently. Never swallow errors. Never
blame the user.

| Pattern in stderr (verbatim where quoted) | Category | Source | Action |
|-------------------|----------|--------|--------|
| `not authenticated` | auth | `lib/codex.mjs`'s `buildAuthStatus` default `detail` field | Suggest `codex login` |
| `OPENAI_API_KEY` (stderr substring match) | auth | `lib/codex-exec.mjs`'s `runCodexExec` only — a primitive `codex-companion.mjs` never calls directly; used by `codex-review-bridge` and any other `runCodexExec` caller instead, which surface this as the `auth_unavailable` typed-failure category rather than a prose message | Suggest `codex login` |
| `Codex CLI is not installed or is missing required runtime support.` | setup | `getCodexAvailability` check, thrown at multiple call sites in `lib/codex.mjs` | Companion resolves fine but the actual `codex` CLI it shells out to isn't installed. Direct to `npm install -g @openai/codex`, then `/codex-kit:setup`. Not transfer-specific — any subcommand that needs a live app-server hits this. |
| `This command must run inside a Git repository.` | environment | `lib/git.mjs`'s `ensureGitRepository` | Tell user, stop |
| `unknown revision` / `bad revision` | bad-input | `git rev-parse` (git's own error, not this codebase's) | Show `git branch --list`, AskUserQuestion |
| ``does not support custom focus text`` | wrong-skill | `validateNativeReviewRequest` | Should NOT fire from a codex-kit task/review skill: Phase 1 strips focus text and offers the adversarial redirect. If it fires, Phase 1 was skipped → SKILL.md regression. |
| `Provide a prompt, a prompt file, piped stdin, or use --resume-last.` | prompt-empty | `requireTaskRequest` | Pattern B failed before consuming stdin. Common cause: `cat` failed and `set -o pipefail` was missing, OR a positional arg overrode stdin (§3). |
| `Task <id> is still running. Use /codex-kit:status before continuing it.` | concurrency-conflict | thrown when an active task is found | Previous Codex task in flight. Show user the active jobId, stop. Do NOT silently cancel. |
| `Unsupported reasoning effort "<value>"` | bad-input | effort normalization against `VALID_REASONING_EFFORTS` | codex-rescue: effort must be `{none, minimal, low, medium, high, xhigh}`. Re-prompt via AskUserQuestion. |
| `Choose either --resume/--resume-last or --fresh.` | bad-input | `handleTask` | codex-rescue: ANALYZE produced conflicting flags. Re-prompt. |
| `Missing value for --<key>` | bad-input | `lib/args.mjs`'s `parseArgs` | Phase 1 should have caught this → ANALYZE regression. |
| `Stored job <id> is missing its task request payload.` | recovery-impossible | `handleTaskWorker` | Detached task-worker couldn't load the stored request. Surfaced via `result <jobId>` or the job log file, NOT from the original `task --background --json` stdout. Abort, save failure report. |
| JSON parse error on companion stdout | unexpected-format | n/a | Companion output format changed. Show raw stdout/stderr, abort, ask user to report. |
| Pattern A 30-min cap exceeded | wait-timeout | n/a (Claude-side) | `KillShell` the bash_id; if `$OUT_FILE` parses as JSON treat as partial, else `recovery-impossible`. |
| (no stderr — silently corrupted prompt) | silent-flag-corruption | `lib/args.mjs`'s `parseArgs` + `readTaskPrompt` | **NOT detectable post-hoc.** Only Phase 1 ANALYZE whitelisting prevents it. If Codex echoes an unknown flag back as task content, treat as Phase 1 regression and AskUserQuestion. |
| `Could not identify the current Claude transcript. Retry with --source <path-to-claude-jsonl>.` | setup/transcript-missing | `lib/claude-session-transfer.mjs`'s `resolveClaudeSessionPath` | No `CODEX_KIT_TRANSCRIPT_PATH` env and no `--source`. Ask the user to pass `--source` manually. |
| `Codex can import Claude sessions only from <dir>: <path>` | bad-input | `lib/claude-session-transfer.mjs` | Source path resolved outside `~/.claude/projects/`. Show the offending path, do not retry with a modified path automatically. |
| `Timed out waiting for Codex to finish importing the Claude session.` | wait-timeout | `lib/codex.mjs`'s `EXTERNAL_AGENT_IMPORT_TIMEOUT_MS = 2 * 60 * 1000` | Import RPC didn't complete in 2 min. Abort, don't retry silently — re-running may just return the same ledger-cached thread (see next row) or hit the same stall. |
| (same file + same content re-imported → existing `threadId` returned) | **not an error** | ledger dedup against `external_agent_session_imports.json` in `lib/codex.mjs` | Normal behavior, not a failure to surface as one. Codex recognizes the identical `sourcePath` + `content_sha256` pair and returns the prior thread instead of creating a duplicate. |
| (other) | unknown | n/a | Show raw stderr verbatim. Do NOT retry. |

**Never:**
- Silently retry
- Swallow errors
- Enter manual polling loops outside `BashOutput` (Pattern A) or
  `status --wait` (Pattern B)
- Use `ps`, `kill`, or raw state JSON reads for tracking
- Pass any token through to the companion that did not survive Phase 1's
  whitelist (see "silent-flag-corruption" — no companion-side safety net)
- Blame the user

---

## 7. ANALYZE classification rules (full)

The 5-line core lives inline in each SKILL.md. Consult this section when
the inline rules don't cover an edge case.

### Core algorithm

For each token in `$ARGUMENTS`:

1. **Whitelisted flag?** (with or without trailing punctuation, with or
   without `=`) → normalize and include.
   - Strip trailing `,` `.` `)` from values (`--base develop,` → `base=develop`).
   - `--key=value` and `--key value` both accepted.
2. **Duplicate flag?** e.g., `--base develop --base main` → AskUserQuestion
   which one is intended. Never silently pick "last wins".
3. **Natural-language meta-instruction addressed to YOU?** e.g.,
   "don't analyze first", "answer in Korean", "quickly", "thoroughly" → obey for your
   own behavior, never forward to companion.
4. **Junk?** emoji, stray punctuation, `, ` → drop.
5. **Focus text on `codex-review`?** → AskUserQuestion offering the
   adversarial redirect (do NOT pass it; the companion will reject it via
   `validateNativeReviewRequest`).
6. **Ambiguous?** → AskUserQuestion (interactive) or exit 1 with a clear
   stderr message (non-interactive). See §9.
7. **Unknown token (not on whitelist, not meta-instruction, not junk)?**
   → **FATAL.** Never pass through. There is no companion-side safety net
   (§3 silent-flag-corruption).

### Examples (use LM judgment for unseen cases)

```
INPUT                                                   → PARSED
--base develop                                          → base=develop
against the develop branch                              → base=develop
--base=develop, don't analyze first                     → base=develop (meta-instruction obeyed)
from HEAD~3                                             → base=HEAD~3
--base develop --base main                              → AskUserQuestion (which base?)
😤 quickly                                               → no flags (auto-detect scope)
--uncommitted                                           → AskUserQuestion (not on whitelist — did you mean --scope working-tree?)
--commit abc123                                         → codex-kit:review natively supports --target commit --commit <ref> (see review.md's Target selection) — no longer an AskUserQuestion case
--foo bar implement login (on codex-rescue)             → FATAL (--foo not on rescue whitelist; treat as ANALYZE regression if it reaches companion)
```

### Show your work

Before Phase 2, print exactly one line:

```
Parsed: base=develop, scope=auto   (meta-instructions: "don't analyze first")
```

This makes the translation step auditable in the session log.

---

## 8. Blind-payload pattern (verify / research only)

verify and research must NOT load document content into Claude's context —
double-check independence depends on it. Use file redirection and stdin
piping so the content never enters Bash's stdout.

### Key invariants

- **`cat $DOC >> $PROMPT_FILE`** — redirects to file, Bash returns empty
  stdout, content never enters Claude's context.
- **`cat "$PROMPT_FILE" | node companion task --background --json`** —
  sends payload over the stdin pipe, not as a positional.
- **Never add a positional prompt after `task`** in Pattern B. `readTaskPrompt`
  does `positionalPrompt || readStdinIfPiped()`; any positional short-circuits
  stdin and the entire blind payload is silently dropped.
- **`--prompt-file` is parser-only** (accepted, not in `printUsage`). Stdin is the
  first-class path (`readTaskPrompt` handles it via `lib/fs.mjs`'s
  `readStdinIfPiped`). Use stdin.
- **`set -o pipefail`** is mandatory. Without it, a cat-side failure
  sends 0 bytes and the companion's `prompt-empty` error masks the real
  root cause.

### Temp file lifecycle

`$$` (shell PID) does NOT survive across Claude's separate Bash
invocations — Bash spawns a fresh shell each call. Use timestamps and
have Claude **remember the absolute path** printed in Phase 1 stdout,
then re-inject it literally in every later Bash call.

**Step 1 — set up paths and temp file naming:**

```bash
set -o pipefail
CODEX_COMPANION="${CLAUDE_PLUGIN_ROOT}/scripts/codex-companion.mjs"

mkdir -p "${CLAUDE_PLUGIN_DATA}/tmp"
TS=$(date +%s%N)
PROMPT_FILE="${CLAUDE_PLUGIN_DATA}/tmp/<skill>-prompt-${TS}.txt"
JOB_JSON_FILE="${CLAUDE_PLUGIN_DATA}/tmp/<skill>-job-${TS}.json"
echo "PROMPT_FILE=$PROMPT_FILE"
echo "JOB_JSON_FILE=$JOB_JSON_FILE"
```

**Step 2 — assemble the header via heredoc (no document content yet):**

```bash
cat > "$PROMPT_FILE" <<'EOF'
<task>
...skill-specific task block...
</task>

<structured_output_contract>...</structured_output_contract>
<grounding_rules>...</grounding_rules>

<document>
EOF
```

**Step 3 — validate and append the document (input validation only — never load content):**

```bash
# Replace <literal doc path> with the path parsed from $ARGUMENTS.
test -f "<literal doc path>" || { echo "File not found: <literal doc path>" >&2; exit 1; }
test -s "<literal doc path>" || { echo "File is empty: <literal doc path>" >&2; exit 1; }
echo "DOC_LINES=$(wc -l < "<literal doc path>")"   # size info, not content

# Append document via redirect — Bash stdout stays empty.
# Use the literal doc path, NOT a shell variable from a prior Bash call.
cat "<literal doc path>" >> "$PROMPT_FILE"

# Close XML
printf '\n</document>\n' >> "$PROMPT_FILE"
```

**Step 4 — launch via stdin pipe (no positional!) and capture the job ID:**

```bash
cat "$PROMPT_FILE" | node "$CODEX_COMPANION" task --background --json \
  > "$JOB_JSON_FILE" 2> "${JOB_JSON_FILE}.stderr" \
  || { echo "task launch failed:" >&2; cat "${JOB_JSON_FILE}.stderr" >&2; exit 1; }

# Capture jobId (use node, not python, to avoid host assumptions)
JOB_ID=$(node -e 'const fs=require("fs");try{const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));if(!j.jobId)throw new Error("no jobId");process.stdout.write(j.jobId);}catch(e){process.stderr.write("JOB_ID parse failed: "+e.message+"\n");process.exit(1);}' "$JOB_JSON_FILE") \
  || { echo "raw companion stdout:" >&2; cat "$JOB_JSON_FILE" >&2; exit 1; }
echo "JOB_ID=$JOB_ID"
```

### Why this preserves independence

- `cat "$USER_DOC" >> "$PROMPT_FILE"` → stdout goes to the file, not the
  terminal. Bash tool returns empty.
- `cat "$PROMPT_FILE" | node ...` → stdout goes to the pipe. Bash tool
  still returns empty on success.
- Claude knows the path, the line count, and that the assembly succeeded
  — but never sees the document text.

### Topic-only research

For `codex-research` when the user gives a topic (no file), skip the
document append entirely. Write the topic inside the heredoc header
template and pipe the resulting `$PROMPT_FILE` straight into `task
--background --json`.

### Cleanup

Clean up temp files at the end of Phase 5 by re-injecting the literal
absolute paths (captured from Phase 1 stdout):

```bash
rm -f "<literal $PROMPT_FILE path>" "<literal $JOB_JSON_FILE path>" "<literal ${JOB_JSON_FILE}.stderr path>"
```

Do NOT rely on `$PROMPT_FILE` / `$JOB_JSON_FILE` shell variables in the
cleanup call — those are only defined in the shell that set them, which
is a different shell from this one.

---

## 9. AskUserQuestion fallback for non-interactive runs

There is no env var that reliably tells Claude whether `AskUserQuestion`
is available — `CLAUDECODE` is always set inside Claude Code. The
pragmatic pattern is "try and fall back":

1. Always attempt `AskUserQuestion` first when ANALYZE detects ambiguity.
2. If the tool errors or times out (headless `claude -p` runs), fall back
   to a clean stderr + exit 1:

   ```bash
   printf 'AMBIGUOUS: %s\nProvide unambiguous input or run interactively.\n' \
     "$REASON" >&2
   exit 1
   ```

3. Never silently guess. Never pass an ambiguous token through to the
   companion (§3 silent-corruption).

---

## 10. Shared gotchas

- **Bash 300s timeout ≠ job failure when Pattern B is used.** `status
  --wait` blocks ≤240s per call, well under the limit.
- **Pattern A requires `run_in_background=true`.** The companion's own
  `--background` is a no-op on `review` / `adversarial-review`.
- **Natural language in `$ARGUMENTS` is for YOU, not the companion.**
  Meta-instructions like "don't analyze first" modify YOUR behavior; they
  never become companion flags or prompt content.
- **Unknown flags don't error — they silently become prompt content.**
  ANALYZE whitelist is the only line of defense.
- **Pattern B stdin pipe never combines with a positional arg.**
  `readTaskPrompt` does `positionalPrompt || readStdinIfPiped()`;
  a positional silently overrides stdin and drops the
  entire blind payload.
- **Always `set -o pipefail` before `cat ... | node ...`.** Without it,
  a cat-side failure masks as a companion-side `prompt-empty` error.
- **`$$` does not survive across Bash calls.** Use timestamps; remember
  absolute paths from Phase 1 stdout and re-inject them.
- **Never poll manually outside `BashOutput` (Pattern A) or `status
  --wait` (Pattern B).** `ps` / `kill` / raw state JSON reads are
  forbidden — they leave orphan jobs in unrecoverable states.
- **Never swallow errors. Never retry silently.** Categorize per §6 and
  surface verbatim.
- **Read source only AFTER Phase 3 completes.** Phase 1-3 must not call
  `Read` / `Grep` / `Glob` / `git diff` / `git log -p` / `git show` /
  `git blame` on source or diffs. Input validation (`test -f`, `wc -l`,
  `git rev-parse --verify`, `git branch --list`) is allowed.
- **In Phase 4, read only what Codex cited.** Never read whole files "for
  context". If a cited file/function/line does not exist in the current
  source tree, classify as "False Positive (hallucination)". If a finding
  has no concrete citation, classify as "Uncited — verification deferred".

# Troubleshooting

Symptom-first guide to every problem reported so far. **Start by running `agy-doctor`**
(or `/antigravity-kit:setup` inside Claude Code) — it diagnoses most of the below and prints
the plugin version, agy version/auth state, and platform warnings.

---

## "`/scripts/agy-delegate.sh: No such file or directory`" or `$CLAUDE_PLUGIN_ROOT` is empty

**Cause (historical, upstream):** `$CLAUDE_PLUGIN_ROOT` is only substituted inside
structured config (hooks/MCP) — it is **not** exported to the shell commands the model
runs, so an early marketplace install could see an empty path. This was fixed upstream
(everything is now invoked by bare names — `agy-delegate`, `agy-job`, `agy-doctor`,
`agy-cost-compare` — on the plugin's `bin/` PATH) before this plugin was packaged for
this marketplace, so this plugin already ships with the fix.

**If you still see this:** update to the latest release of this plugin and reload:

```
/plugin marketplace update andres-cc-marketplace
/reload-plugins
```

If it persists after that, file an issue — see "Still stuck?" below.

---

## Windows: delegation hangs, or exits 12 (TIMEOUT) with a 0-byte log

**Cause (upstream, not the plugin):** on native Windows, headless `agy` needs a real
console (ConPTY). When the plugin runs it as a child process with redirected stdio there
is no console, and agy v1.0.x can hard-hang before producing any output
(issue #6, unverified against this marketplace's own tracker — see [KNOWN_ISSUES.md](../KNOWN_ISSUES.md)).

**"But agy works when I type it in my terminal!"** — yes: typed directly, agy has a real
console (interactive mode). Invoked by the plugin, it runs headless (no console). That's
the difference, not Windows vs the plugin.

What the plugin does about it: a wall-clock guard (`timeout`/`gtimeout`) turns the hang
into a clean **TIMEOUT (exit 12)** instead of a freeze, and `agy-doctor` reports "headless
hang" instead of the misleading "not authenticated".

**Fix: use WSL** (fully supported):
1. `wsl --install` (one-time; reboot)
2. Install Claude Code **and** the Antigravity CLI *inside* WSL; authenticate agy there
   (`agy models` should list models)
3. Keep your repo on the WSL Linux filesystem (`~/project`), **not** `/mnt/c/...`
4. Run `/antigravity-kit:setup` from WSL — it should go green

---

## Everything hangs forever, and `/antigravity-kit:setup` says the CLI is broken

**Symptom:** `agy models` and every delegation never return. `agy-doctor` reports a hung or
unauthenticated CLI — but typing `agy models` yourself works fine. macOS and Linux, not just
Windows.

**Cause (historical, upstream, fixed before this plugin was packaged for this marketplace):**
this happens when you have **stdio MCP servers configured** and agy's stdout is captured via a
shell command substitution. agy's stdio MCP children **inherit its stdout and outlive agy**.
A shell command substitution only returns once *every* holder of the pipe's write end closes
it, so `OUT="$(agy ...)"` waits forever on children that are still alive. The wall-clock guard
cannot rescue this: `timeout` kills `agy`, not the grandchildren.

The one-line test, from the original report — same machine, only the config changed:

```bash
# stdout to a FILE — returns in ~6s
timeout 60 agy -p "Reply with exactly: PONG" > /tmp/out.txt 2>/dev/null </dev/null

# stdout to a PIPE (what the wrappers used to do) — hangs
timeout 90 bash -c 'O="$(timeout 60 agy -p "Reply with exactly: PONG" 2>/dev/null)"' </dev/null
```

**Fix:** this plugin already ships with the fix — agy's stdout now goes to a temp file,
which children inherit harmlessly. If you still see this, run `agy-doctor` to confirm
you're on the current release, then see the next section.

### It still hangs after that

If the above doesn't explain it, it is a **different mechanism**, and one the plugin
cannot fix: agy waits on its MCP
servers at startup, so a server that never finishes connecting blocks `agy` itself — this
reproduces even with stdout on a file. `agy-doctor` now tells you how many stdio MCP servers
you have when `agy models` times out.

To confirm, check agy's log (`~/.gemini/antigravity-cli/log/cli-*.log`) for a server that
never reports ready, or move `~/.gemini/config/mcp_config.json` aside temporarily. Note agy
loads MCP servers from **two** places — that file and `~/.gemini/config/plugins/*/mcp_config.json`.

## WSL: delegation works but is absurdly slow (20s+ for trivial calls)

**Cause:** your repo lives on a Windows mount (`/mnt/c/...`). agy reads `--dir` workspaces
over WSL's 9p bridge, which is ~10x slower than native FS.

**Fix:** move the repo into the WSL Linux filesystem (e.g. `~/projects/...`). Both the
wrapper and `agy-doctor` warn when they detect this.

---

## agy says "done" but wrote no files (or wrote them somewhere else)

**Cause:** write tasks need write permission, and headless agy's no-permission behavior
has changed across versions. **Your workspace stays untouched every time**; what varies is
whether the run admits it (issue #10, unverified against this marketplace's own tracker — see [KNOWN_ISSUES.md](../KNOWN_ISSUES.md)):
- pre-1.1.0: only *describes* the edits
- 1.1.0–1.1.2: writes to its **own scratch dir** (`~/.gemini/antigravity-cli/scratch/`)
- 1.1.3–1.1.1x: **soft-denies** — rc 0, empty stdout, a stderr notice naming the allow-rule
- by **1.1.13**: **hard error** — the run fails (rc 1) with `permission check failed for
  write_file "...": user denied permission for write_file(...)`. Same cause, different
  shape, and none of the older wording. The wrapper classifies both as **exit 15**

**Fix:**
- **For a file write, add an allow-rule — the narrower fix.** In
  `~/.gemini/antigravity-cli/settings.json`, under `permissions.allow`, add
  `write_file(<dir>)`. It matches **recursively beneath `<dir>`** and needs no flag.
  This is the rule agy's own denial message is naming. Confirmed on agy 1.1.9 by a
  controlled A/B (issue #37, unverified against this marketplace's own tracker — see [KNOWN_ISSUES.md](../KNOWN_ISSUES.md));
  a glob form (`write_file(/path/**)`) was reported *not* to match.
  **Substitute a real path for `<dir>`** — and if the rule is in place and the write is
  *still* denied, suspect the rule before suspecting agy. An entry agy cannot parse
  grants nothing on any version, which is exactly this exit 15 with the rule sitting
  right there in the file. Only one shape of mistake is version-sensitive, and it is not
  this one: a `command(...)` rule naming no command — `command(time)`, a comment-only
  entry, `()` — matched **every** command before **1.1.11** and silently auto-approved
  anything the agent ran. Run `agy-doctor`: it validates each entry and reports the
  consequence that actually applies to yours.
- **Or pass `--yolo`** (`--dangerously-skip-permissions`) — works across all agy versions,
  but auto-approves **all** tools, not just the write. Required anyway for web / Vertex AI
  Search / terminal when no rule covers them. (`--mode accept-edits` is NOT a headless write grant. Measured on agy 1.1.13 — where the flag is actually applied, since 1.1.12 fixed `--mode` being ignored in headless `-p` entirely — the write is denied exactly like one without it. Earlier notes here said "soft-denied on 1.1.3"; on a build where the flag was never applied, that observation could not tell a denial apart from the flag doing nothing.)
- Claude Code may prompt for (or in auto-mode, block) `--dangerously-skip-permissions` —
  approve it, or pre-allow `Bash(agy-delegate*)` in your permission settings.
- Run write tasks on a **dedicated branch** (add `--sandbox` for containment).
- **Always verify files actually changed in your workspace** (`git status`) — never trust
  the self-report. The wrapper maps BOTH denial shapes — the 1.1.3 soft-deny and the
  1.1.13 hard error — to **exit 15**, so you get an actionable message instead of a
  bare "empty output" or "agy exited 1".
- Long write tasks can exceed Claude Code's ~2-min synchronous Bash limit → run them as a
  background job: `ID=$(agy-job start --tier pro --dir . "<task>")`, then
  `/antigravity-kit:status` / `/antigravity-kit:result <id>` (interactive sessions only).

---

## Exit codes & `AGY_SIGNAL`

On classifiable failures the wrapper prints a machine-readable line to stderr:
`AGY_SIGNAL {"status":"...","reason":"...","model":"...","retry":"..."}`

**These codes are per-engine — the same number means something different in
`cloud-debug.sh` or `agy-media.sh` than it does in `agy-delegate.sh`.** Look up the
script that actually failed, not just the number.

### `agy-delegate` / `agy-job` (and anything that calls through them)

| exit | meaning | what to do |
|---|---|---|
| 0 | success | — |
| 1 | usage error | check flags (`agy-delegate --help`) |
| 2 | agy failed (unclassified) | read the stderr it relayed |
| 3 | agy returned empty output | retry; check model availability (`agy models`) |
| 10 | quota / rate limit | wait, then resume the same conversation with `--continue` |
| 11 | not authenticated | run `agy` once interactively to sign in |
| 12 | timeout (agy's own, or the wall-clock guard) | raise `--timeout`, narrow the task; on Windows see the hang section above |
| 13 | agy not on PATH | install the Antigravity CLI |
| 14 | model unavailable | the `--model` / `tier_*` / `default_model` name isn't in `agy models` (agy ≥ 1.1.2 hard-fails instead of silently downgrading) — run `agy models` and fix the name |
| 15 | permission denied | a tool needed permission headless — **both** shapes: agy 1.1.3's soft deny (rc 0, empty stdout) and 1.1.13's hard error (`user denied permission`). Add a `permissions.allow` rule covering the target, or pass `--yolo`; run on a branch |

### `agy-migrate` only

| exit | meaning | what to do |
|---|---|---|
| 16 | python3 not on PATH | install python3 (`brew install python3`) |
| 17 | one or more migration steps failed | read the named steps; the run is still revertible with `agy-migrate --uninstall --apply` |
| 18 | prerequisite missing | no Claude Code config dir, or agy has never been run |

### `cloud-debug.sh` only

| exit | meaning | what to do |
|---|---|---|
| 0 | ok (digest printed, or query succeeded with no matching logs) | — |
| 1 | usage error | check flags |
| 2 | gcloud read failed (generic) | read the relayed stderr |
| 3 | permission denied — needs `roles/logging.viewer` | grant the role, or ask an owner to |
| 4 | gcloud not on PATH | install the Cloud SDK |
| 5 | agy digest step failed | agy-delegate's own stderr is surfaced — see the `agy-delegate` table above |

### `agy-media.sh` only

| exit | meaning | what to do |
|---|---|---|
| 0 | ok | — |
| 1 | usage error | check flags |
| 4 | file not found | check the input path |
| 5 | unsupported format | convert first (`--convert`, or manually) |
| *(other)* | passed through from `agy-delegate` | see the `agy-delegate` table above (2 failed, 3 empty, 10 quota, 11 auth, 12 timeout, 13 missing, 14 model, 15 permission) |

### `agy-trace.sh` only

| exit | meaning | what to do |
|---|---|---|
| 0 | ok | — |
| 1 | usage error | check flags |
| 2 | transcript not found | confirm the conversationId, or that the delegation actually ran |

---

## "tier model not in `agy models`" warning from doctor

**Cause:** agy's model list is plan-dependent (Vertex plans are Gemini-only; some plans
expose Claude/GPT). The default tier mappings may not match your plan.

**Fix:** remap tiers to models you actually have — plugin options `tier_flash` /
`tier_flash_lo` / `tier_pro` or `default_model` (exact names from `agy models`), or pass
`--model "<exact name>"` per call.

---

## Output is huge / "looks like a raw dump, not a digest"

**Cause:** the wrapper warns (stderr) when a reply exceeds `digest_warn_chars` (default
8000). Ingesting raw dumps into the conductor's context is where the cost savings die.

**Fix:** re-run with `--digest` (appends a digest-only output contract to the prompt), or
have agy summarize before you ingest. Tune the threshold via the `digest_warn_chars`
plugin option; `0` disables the warning.

---

## Updating / checking your version

Third-party marketplace plugins do **not** auto-update by default:

```
/plugin marketplace update andres-cc-marketplace
/reload-plugins
```

`agy-doctor` prints the installed plugin version (last line of its checks). Fixes land as
version bumps.

---

## Still stuck?

[Open a bug report](https://github.com/andrehahm/andres-cc-marketplace/issues/new/choose)
— the template asks for your `agy-doctor` output, OS, and install method, which is
usually everything needed to diagnose in one round-trip.

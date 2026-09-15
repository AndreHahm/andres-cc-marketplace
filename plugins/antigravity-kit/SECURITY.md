# Security policy

This is a community project (Apache 2.0, not affiliated with Google or Anthropic). It
orchestrates the third-party `agy` CLI and runs shell commands on your machine, so
security reports are genuinely appreciated.

## Reporting a vulnerability

**Preferred:** use GitHub's private vulnerability reporting —
**Security → Report a vulnerability** on this repository
(https://github.com/andrehahm/andres-cc-marketplace/security/advisories/new).
This keeps details private until a fix is available. Note this covers the whole
`andres-cc-marketplace` repository, not just this plugin — there is no separate,
plugin-scoped reporting channel.

If that isn't available to you, open a normal issue describing the impact and a
non-destructive repro, and note that you'd prefer to coordinate privately — a
maintainer will follow up with a private channel.

Please include: affected file/commit, impact (what a malicious/injected input could
do), and a **non-destructive** proof-of-concept (exit codes / policy decisions, not
`rm -rf` — some endpoint security will kill the process on such strings).

## Scope — what matters most here

- **`hooks/validate-delegate-bash.sh`** — the PreToolUse gate *designed* to restrict
  *which command* the `antigravity-delegate` subagent may run via Bash. **Known,
  disclosed limitation:** this repository's own platform documentation states that
  hooks declared in a plugin-scoped agent's own frontmatter (as this one is) are
  accepted by the schema but not honored at runtime — until live-verified against an
  installed copy of this plugin, treat this gate as defense-in-depth, not a verified
  enforcement point. The subagent's actual, load-bearing restriction is its `tools:`
  grant (`Bash, Read, Glob` — no `Write`/`Edit`). Bypasses in the gate's own parsing
  logic are still in-scope, high-value reports (they matter once the wiring question
  above is resolved), but a report on the wiring question itself (confirming whether
  the hook fires at all) is equally valuable and should be filed the same way.
- **The gate, where it does run, bounds which process starts, not what that process can then do.**
  `--yolo` (the subagent's default write/build mode) grants the delegated `agy`
  process full tool access — file writes, terminal, web/Vertex AI Search — so real
  containment for a write/build delegation is the branch/worktree-plus-diff-review
  discipline documented in `agents/antigravity-delegate.md`, not the gate itself.
  A report showing the gate allows an unintended *command* is in scope even if agy's
  own subsequent actions are the documented, intended behavior of an allowed command.
- **`scripts/agy-delegate.sh` / `agy-job.sh`** — the wrappers that invoke `agy`.
- **`hooks/`** — anything injected into the model's context or run at session start.
- **The `antigravity-delegate` subagent's unrestricted `Read`/`Glob`** — combined with
  the one outbound channel (the delegation wrapper), this is an exfiltration path
  under prompt injection if the subagent is ever induced to embed file content
  (credentials, tokens) into a delegation prompt instead of passing `--dir` and
  letting agy read the files itself.
- Trust boundary reminder: `agy` output and repo contents are **untrusted** — the plugin
  treats agy as a tool whose results Claude must verify, never as a trusted authority.

## Not in scope

- Vulnerabilities in the upstream Antigravity CLI (`agy`) itself — report those to
  https://github.com/google-antigravity/antigravity-cli.
- Cost/quota surprises from delegating large jobs (documented behavior).

## Supported versions

Fixes land on the latest release. Update with
`/plugin marketplace update andres-cc-marketplace` and `/reload-plugins`; the `version`
this plugin ships lives in both `plugins/antigravity-kit/.claude-plugin/plugin.json`
and this plugin's entry in the marketplace's own `.claude-plugin/marketplace.json` —
keep the two in sync.

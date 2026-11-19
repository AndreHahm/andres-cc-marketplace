# Codex Config

Opinionated defaults, documentation, and workflows for Codex CLI. Covers sandboxing, permissions, exec policy rules, hooks, skills, MCP servers, and usage patterns we've found effective for security audits, development, and research.

## Getting Started

### Read These First

Before configuring anything, read these to understand why this setup works the way it does:

- [Codex CLI docs](https://developers.openai.com/codex) -- the official primer; config schema, sandbox model, exec policy, hooks, skills, and CLI flags
- [GPT-6.2 model guidance](https://developers.openai.com/api/docs/guides/latest-model):
  model tiers, migration guidance, reasoning effort, and prompt design
- [Build skills](https://learn.chatgpt.com/docs/build-skills): skill discovery, implicit
  invocation, and progressive disclosure
- [Codex for Knowledge Work](https://every.to/guides/codex-for-knowledge-work) -- Every's guide to using Codex as a workspace for knowledge work, not just code
- [Codex-maxxing](https://jxnl.github.io/blog/writing/2026/05/10/codex-maxxing/) -- Jason Liu on durable threads, memory, steering, browser/computer use, goals, and review surfaces
- [AI-assisted coding for teams that can't get away with vibes](https://blog.nilenso.com/blog/2025/05/29/ai-assisted-coding/) -- Nilenso's playbook for teams integrating AI tools with high standards
- [My AI Skeptic Friends Are All Nuts](https://fly.io/blog/youre-all-nuts/) -- Thomas Ptacek on why dismissing LLMs for coding is a mistake
- [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/) -- Ryan Lopopolo on how OpenAI's team shipped a million-line product with zero human-written code, and what that implies for how you structure repos, AGENTS.md files, and review loops

### Settings

Official docs: [config reference](https://developers.openai.com/codex/config-reference).

Copy `config.toml` to `~/.codex/config.toml` (or merge entries into your existing file). If you already have a config, keep your authentication, project trust, and any local model overrides.

```bash
mkdir -p ~/.codex
cp config.toml ~/.codex/config.toml
```

Important settings:

- **`model = "gpt-6.1-terra"`**: the shipped default uses the explicit GPT-6.1 medium-sized slug.
- **`model_reasoning_effort = "medium"`** with **`plan_mode_reasoning_effort = "high"`**: normal work uses medium effort and Plan work uses high effort.
  `model_verbosity` remains unset so the model preset controls response length.
- **`personality = "pragmatic"`** and **`model_reasoning_summary = "auto"`**:
  use the pragmatic communication preset and automatic reasoning summaries.
- **`approval_policy = "on-request"`** -- Codex asks before stepping outside the sandbox; see [Sandboxing](#sandboxing) for the other values
- **`approvals_reviewer = "auto_review"`** -- routes eligible approval prompts through Codex's automatic reviewer
- **`default_permissions = "ah-workspace"`** -- selects the custom AndreHahm sandbox profile: broad local reads, workspace/temp writes, no command network, deny-read rules for credentials and crypto wallets
- **`web_search = "cached"`** -- Codex's built-in web search caches responses to reduce token spend on repeated queries
- **`project_doc_fallback_filenames = ["CLAUDE.md"]`** -- migration aid for repos that haven't renamed `CLAUDE.md` to `AGENTS.md`; lets Codex still read the file
- **Hooks** wired to the one shipped script -- see [Hooks](#hooks)

### Global AGENTS.md

Official docs: [custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md).

The global `AGENTS.md` at `~/.codex/AGENTS.md` sets default instructions for every Codex session. In this repository, the installable template is `global-agents.md`; the root `AGENTS.md` is only for contributors working on this repo.

The global template contains only rules that apply across tasks: instruction precedence, current
sources, untrusted input, scope and approvals, preservation of existing behavior, command execution,
direct communication, and relevant validation. Development and durable-writing detail belong in
optional, implicitly invoked skills (loaded only when installed) so unrelated sessions do not pay
for those instructions.

Copy the template into place:

```bash
cp global-agents.md ~/.codex/AGENTS.md
```

Codex builds the AGENTS chain once when a run starts. It reads the global file, then walks from the
project root down to the directory where Codex was launched; files closer to that launch directory
take precedence. A nested `AGENTS.md` is not a dynamic per-file router for files elsewhere in the
tree. Launch Codex from the relevant subtree when its nested instructions should apply. Run
`/status` to inspect the loaded chain and any configured `CLAUDE.md` fallback.

## Configuration

### Sandboxing

Official docs: [permissions](https://developers.openai.com/codex/permissions), [agent approvals & security](https://developers.openai.com/codex/agent-approvals-security), [rules](https://developers.openai.com/codex/rules).

Codex sandboxing has two controls you need to understand:

- `default_permissions` selects what local commands can read, write, and access over the network.
- `approval_policy` controls when Codex may ask to do more than the sandbox allows.

The AndreHahm default is:

```toml
default_permissions = "ah-workspace"
approval_policy = "on-request"
approvals_reviewer = "auto_review"
```

That profile gives Codex broad local reads, workspace/temp writes, no command network, and deny-read rules for common credential stores, wallets, `.env`, `*.pem`, and `*.key`. The practical effect: Codex can inspect ordinary local files and edit the repo without prompting, while secrets, network use, and writes outside the workspace require approval or a different profile.

Do not set `sandbox_mode` in this config. If it appears in any active config layer, Codex uses that setting instead of `default_permissions` (see the [permissions](https://developers.openai.com/codex/permissions) docs).

Use `:danger-full-access` or `approval_policy = "never"` only inside an external sandbox such as a devcontainer or disposable VPS or as fallback on Windows (if the sandbox-mode will never work). The shared default should stay interactive and sandboxed.

Rules and hooks are the command layer around the sandbox. `rules/default.rules` classifies unsandboxed command requests; hooks catch footguns even when a command stays inside the sandbox. The defaults block recursive force deletion, disk-formatting commands, force-push/reset mistakes, and direct pushes to `main`/`master`.

Install:

```bash
mkdir -p ~/.codex/rules
cp rules/default.rules ~/.codex/rules/default.rules
```

#### `--yolo` mode

**WARNING: Only enable YOLO mode in a sandbox such as a virtual machine or disposable cloud machine. Understand the risks of Codex running arbitrary commands.**

`--yolo` lets Codex run any command without approval or sandboxing. It is a hidden alias for `--dangerously-bypass-approvals-and-sandbox` (approval policy `never`, no sandbox), so `codex --help` shows the long form rather than `--yolo`.

YOLO mode drops sandboxing and approvals, but it still evaluates installed rules and hooks. With this configuration installed, command requests are checked against `rules/default.rules` first, so a `forbidden` rule still rejects the command and `PreToolUse`/`PostToolUse` hooks still run. One sharp edge: `never` approvals leave a `prompt` rule with nothing to approve it, so it becomes a hard rejection -- `curl`, for instance, is blocked outright rather than prompted. For unrestricted execution, do not install this repository's Codex rules or hooks.

### Hooks

Official docs: [hooks](https://developers.openai.com/codex/hooks).

Hooks are deterministic checkpoints around Codex tool calls. They are more reliable than instructions for repetitive guardrails because the check runs at the moment of action: a `PreToolUse` hook can block `rm -rf`.

Hooks are not a security boundary. Use them for workflow pressure: block known-bad patterns, enforce project conventions, add audit logs, or inject context at decision points. Keep sandboxing on.

#### Shipped example

The one hook in `hooks/` is a AndreHahm default:

- [`block-dangerous-command.sh`](hooks/block-dangerous-command.sh) -- `PreToolUse` regex blocker for `rm -rf`, force-push to `main`/`master`, and a few other footguns. Belt-and-braces with `rules/default.rules`.

Install:

```bash
mkdir -p ~/.codex/hooks
cp hooks/*.sh ~/.codex/hooks/
chmod +x ~/.codex/hooks/*.sh
```

Copying the script does not register it. Add a `PreToolUse` entry to `~/.codex/hooks.json` that points at the installed copy (the project `hooks.json` resolves the repository copy, so it does not apply to other repositories):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^Bash$",
        "hooks": [
          { "type": "command", "command": "bash \"$HOME/.codex/hooks/block-dangerous-command.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
```

In this repository, `hooks.json` wires the hook up to the repo copy (resolved via `git rev-parse --show-toplevel`), so nothing needs to be copied for project use. Each hook has a `timeout` (seconds, default 600) and an optional `statusMessage` shown in the TUI while it runs.

## Usage

### Per-invocation overrides

These options are useful for one-off runs that should not edit the global config:

- `codex --config model_reasoning_effort="high"` raises the normal `medium` default for a harder
  task. `"low"` can reduce latency further for a measured low-risk workload.
- `codex -c "service_tier=flex"` requests flex service for a latency-tolerant run when the active
  model and provider offer it. `service_tier=fast` requests fast mode. Verify effective status.
- `codex exec --ignore-user-config` skips `$CODEX_HOME/config.toml` for that non-interactive run;
  authentication still uses `CODEX_HOME`. It does not disable `AGENTS.md` discovery.
- `codex exec --ignore-rules` skips user and project exec-policy `.rules` files. It does not disable
  hooks, AGENTS instructions, or the sandbox. Use it only for a controlled rules-exclusion test,
  never as a routine token-saving flag.

Use an isolated eval home for clean comparisons instead of weakening a normal working configuration.

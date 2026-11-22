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
- **`approval_policy = "on-request"`** -- Codex requests approval before stepping outside the sandbox; see [Sandboxing](#sandboxing) for the other values
- **`approvals_reviewer = "auto_review"`** -- routes eligible approval requests to Codex's automatic reviewer instead of you: a model approves or denies them against the `[auto_review]` policy in `config.toml`. That policy lives in this repository, so editing it changes what gets approved. `forbidden` exec rules cannot be approved this way. Remove this line to approve escalations yourself
- **`default_permissions = "ah-workspace"`** -- selects the custom AndreHahm sandbox profile: broad local reads, workspace/temp writes, no command network, deny-read rules for credentials and crypto wallets
- **`allow_login_shell = false`** -- optional hardening from the [advanced config](https://learn.chatgpt.com/docs/config-file/config-advanced) docs: disallows login shells for shell tools
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

That profile gives Codex broad local reads, workspace/temp writes, no command network, and deny-read rules for common credential stores and wallets anywhere, plus `.env`, `*.pem`, `*.key` and `secrets/` inside the workspace roots only (such files elsewhere on disk stay readable). The practical effect: Codex can inspect ordinary local files and edit the repo without prompting, while network use and writes outside the workspace need an approved escalation (by the automatic reviewer, see above) or a different profile.

What stays on disk and in the environment: `[history] persistence = "save-all"` keeps every prompt in Codex's history file, `memories = true` lets Codex keep memories between sessions, and `[shell_environment_policy] inherit = "all"` passes your whole environment to commands, minus Codex's default exclusions for names containing `KEY`, `SECRET` or `TOKEN`. Change those three settings if prompts, commands or environment values must not persist.

Do not set `sandbox_mode` in this config. If it appears in any active config layer, Codex uses that setting instead of `default_permissions` (see the [permissions](https://developers.openai.com/codex/permissions) docs).

Use `:danger-full-access` or `approval_policy = "never"` only inside an external sandbox such as a devcontainer or disposable VPS or as fallback on Windows (if the sandbox-mode will never work). The shared default should stay interactive and sandboxed.

Rules and hooks are the command layer around the sandbox. `rules/default.rules` classifies unsandboxed command requests; hooks catch footguns even when a command stays inside the sandbox. The defaults block recursive force deletion, disk-formatting commands, force-push/reset mistakes, and direct pushes to `main`/`master`.

Install:

```bash
mkdir -p ~/.codex/rules
cp rules/default.rules ~/.codex/rules/default.rules
```

#### Checking that project rules load

`rules/default.rules` starts with a sentinel rule. It forbids exactly `echo CODEX_PROJECT_RULE_TEST`, with the justification `PROJECT RULE LOADED`. Nothing else matches it, so it is harmless to ship.

Check that the file parses and the sentinel matches:

```bash
codex execpolicy check --pretty --rules .codex/rules/default.rules -- echo CODEX_PROJECT_RULE_TEST
```

The expected result is `"decision": "forbidden"`, with the justification `PROJECT RULE LOADED`. This check reads only the file passed with `--rules`. It does not show that a Codex session loads the file: Codex reads `<repo>/.codex/rules/` only when the project is trusted. To check that, ask a session in the repository to run `echo CODEX_PROJECT_RULE_TEST` and look for the rejection, or run the [live check](#live-check), which does exactly that.

The live test only proves the project layer loaded if your user copy, `~/.codex/rules/default.rules`, lacks the sentinel. If you installed this file there, delete the sentinel rule from that copy; the live check warns when it finds one.

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

#### Hook trust

A hook does not run until you trust it. Codex [skips every new or changed non-managed hook until you review and trust it](https://learn.chatgpt.com/docs/hooks), and prints a startup warning that points to `/hooks`:

1. Start Codex in the repository and open `/hooks` (in the desktop app: Settings > Hooks).
2. Review the `PreToolUse` entry from `.codex/hooks.json` and trust it.
3. Do this again after every edit to that entry, and after adding a hook. Until then the guardrail is silently off.

Project hooks also need the project itself to be trusted: Codex loads hooks, and `.codex/rules/`, only from trusted project layers. User hooks in `~/.codex/hooks.json` load in untrusted projects too.

What we observed (Codex CLI 0.170.0, Windows; not stated in the docs):

- Trust is saved in `~/.codex/config.toml` as `[hooks.state.'<absolute path to hooks.json>:pre_tool_use:0:0'] trusted_hash = "sha256:..."`. In a linked git worktree, `/hooks` lists and Codex loads the main checkout's `hooks.json`, not the worktree's copy, so the main checkout's trust entry covers every worktree. A `hooks.json` change on a branch takes effect only once the main checkout has it.
- The docs don't say whether editing `block-dangerous-command.sh` itself (not the `hooks.json` entry) requires re-trusting. They only say so for scripts bundled in a plugin. Re-check `/hooks` after editing the script.
- Both hook entries find the script through `git rev-parse --show-toplevel` in the directory Codex starts the hook in. The docs don't say whether that is the session root or a tool call's own `workdir`. If it is the `workdir`, a repository the agent created earlier could supply its own `block-dangerous-command.sh`. A missing script blocks, but a planted one runs: the hook is a guardrail, not a security boundary.
- On Windows an allowed command takes about 6 s to check (Git Bash starts each tool slowly), so the hook `timeout` is 30 s, not 10 s. The docs don't say whether a timed-out hook blocks or allows the command.
- `codex exec --dangerously-bypass-hook-trust` runs enabled hooks without saved trust for that one invocation. Use it only for automation that vets the hook sources itself.

#### Live check

`hooks/tests/test-block-dangerous-command.sh` pipes JSON into the script directly. It does not show whether Codex launches the hook. `hooks/tests/test-live-codex-hook-and-rules.sh` starts a real `codex exec` session and asks it to run three commands:

- a control command, which must run
- `echo CODEX_PROJECT_RULE_TEST`, which only the project rules forbid (see [Checking that project rules load](#checking-that-project-rules-load))
- `git -C nonexistent-issue-803 stash`, which only the hook blocks

```bash
bash .codex/hooks/tests/test-live-codex-hook-and-rules.sh [timeout-seconds [codex-exec-args...]]
```

Arguments after the timeout go to `codex exec` unchanged. On Windows (Codex 0.170), `codex exec` with this repo's `ah-workspace` profile can take several minutes to start: with any deny-read entry in the profile, each sandboxed file read during skill loading costs about 0.7 s, and the `**/` globs add a scan of the workspace to each one. The built-in `:workspace` profile has no deny entries and starts in seconds. It does not change the hook or the rules, so the live check can use it:

```bash
bash .codex/hooks/tests/test-live-codex-hook-and-rules.sh 300 -c 'default_permissions=":workspace"'
```

On Windows, run it with Git Bash. From PowerShell, a bare `bash` can start WSL instead (the script refuses to run there):

```powershell
& "C:\Program Files\Git\bin\bash.exe" .codex/hooks/tests/test-live-codex-hook-and-rules.sh
```

The hook's own `BLOCKED:` message can only appear if Codex ran the hook entry (`command`, or `commandWindows` on Windows) and it started bash on the script. Run from a worktree, the check tests the main checkout's `hooks.json` (see [Hook trust](#hook-trust)). A generic rejection is reported as INCONCLUSIVE, not PASS. The script makes one model call, so it costs tokens. It needs a trusted project, a trusted hook, a Codex login and `jq`. Exit codes: 0 all PASS, 1 a FAIL, 3 INCONCLUSIVE.

On Windows, Codex's shell tool (`exec_command`) runs commands as `pwsh.exe -Command '...'`, as observed in a `codex exec` transcript. The docs say `exec_command` is matched as `Bash`, so the `^Bash$` matcher still applies. The docs do not say which shell runs a hook's own `command` string on Windows. With only the bash-syntax `command`, a live run let the hook probe through. Under PowerShell that string is a parse error (exit 1), and Codex treats any exit other than 2 as a non-blocking error. `hooks.json` therefore adds a fail-closed PowerShell `commandWindows` that starts Git Bash on the script (issue #803); the live check confirms it once the main checkout has it.

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

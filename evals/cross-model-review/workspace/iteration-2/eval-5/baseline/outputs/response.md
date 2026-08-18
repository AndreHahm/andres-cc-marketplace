I did not Read, Grep, Glob, or otherwise inspect any file under `plugins/git-kit/skills/cross-model-review/`, `.claude/skills/cross-model-review/`, or `plugins/codex-kit/`. Everything below is reasoned generically from the task description and from general knowledge of how a Claude Code plugin/skill that dispatches to an external CLI tool would typically be structured — not from reading the actual implementation. Where I'm not certain of exact command syntax, error strings, or file names, I say so explicitly.

# Three failure scenarios for a Codex dispatch in "cross-model-review"

The setup: a skill called `cross-model-review` in this repo wants to get a second model's opinion (Codex, via OpenAI's Codex CLI) on some work, presumably by shelling out to a `codex` binary that is itself wrapped/managed by a separate plugin, `codex-kit`. I'm told to reason about what happens at "the resolver's first real Codex dispatch" under three different failure conditions. I don't know the resolver's actual code, so I'll describe what I'd expect a reasonably-designed resolver to do, and flag the places where a poorly-designed one would behave differently.

The key insight that should organize all three cases: these are **three different layers of failure**, and a well-built resolver should fail at the earliest possible layer with the clearest possible message, rather than letting every failure mode bottom out as the same generic "command failed" error. I'll walk through each layer, then contrast them directly.

---

## Case 1: codex-kit is not installed at all (no `plugins/codex-kit/` directory)

This is the earliest and structurally simplest failure. If `cross-model-review` is designed sensibly, it should never even attempt to run a `codex` command in this case — it should fail (or gracefully degrade) during a **discovery/availability check**, before any subprocess is spawned.

What I'd expect to happen, in order:

1. **Discovery step.** Before dispatching, the resolver presumably has some notion of "which reviewer backends are available in this installation." For a Claude Code plugin ecosystem, that's most naturally implemented as: does `plugins/codex-kit/` (or whatever the plugin's canonical directory is) exist, and/or is a `codex-kit`-provided skill/command/agent registered and invocable? This is a filesystem/registry check, not a runtime execution.
2. **Result of that check:** codex-kit isn't installed, so this check comes back negative. At this point, the resolver has learned "Codex is not an available reviewer" purely from the *absence of the plugin*, without ever touching the `codex` binary, without spawning a subprocess, and without needing network access or CLI knowledge.
3. **What the skill does next** depends on its design intent, but the sane options are: (a) skip the Codex leg of the cross-model review entirely and proceed with whatever other model(s) it can reach (e.g., fall back to a single-model / Claude-only review), or (b) stop and tell the user plainly that codex-kit isn't installed and cross-model review can't include Codex until it is. Either way, the *user-facing* symptom should read like a **configuration/installation gap** ("codex-kit not found — install it to enable Codex review" or similar), not like an execution error.

The important property of this case: **it should never reach "the first real Codex dispatch" at all.** If the resolver is well-designed, the phrase "first real Codex dispatch" is actually the wrong frame for this scenario — there is no dispatch attempt, because the resolver's own pre-flight availability check short-circuits before any command construction or subprocess spawn happens. If, instead, the actual implementation *does* try to shell out to `codex` in this situation (e.g., because it only checks for the `codex` binary on PATH and never checks for the `codex-kit` plugin's presence specifically), the behavior would degrade toward looking like Case 2 below — a "command not found" style error — which would be a design smell, since it conflates "the wrapping plugin isn't installed" with "the plugin is installed but its underlying binary is missing." A resolver that's actually plugin-aware should be able to distinguish these two states cleanly.

---

## Case 2: codex-kit IS installed, but the `codex` CLI binary is not on PATH

This is one layer deeper. The plugin/skill machinery that *wraps* the Codex CLI is present and discoverable — `cross-model-review` can find codex-kit, can see its skill/command/agent definitions, and presumably constructs a real command line intending to invoke `codex ...` (whether directly via `Bash`, or through some wrapper script codex-kit provides). The failure now happens at **process-spawn time**, when the OS actually tries to resolve `codex` as an executable and can't find it anywhere on `$PATH` (or `%PATH%` on Windows).

What I'd expect:

1. **Pre-flight check (if one exists).** A well-built CLI-wrapping skill often does its own `which codex` / `command -v codex` (POSIX) or `Get-Command codex` (PowerShell) check before attempting the real invocation, specifically so it can produce a clean, actionable error ("codex CLI not found on PATH — install it from ... and retry") instead of letting a raw shell error surface. I don't know whether codex-kit actually does this, but it's the standard pattern for this class of problem.
2. **If no pre-flight check exists,** the failure surfaces as a raw shell/process error: on POSIX-like shells this is typically exit code `127` with a message like `codex: command not found`; on native Windows (cmd.exe or PowerShell) it's usually something like `'codex' is not recognized as an internal or external command, operable program or batch file.` (cmd.exe) or a `CommandNotFoundException` (PowerShell). Since this repo appears to run under a mixed bash/PowerShell tooling setup, the exact wording would depend on which shell layer actually issues the `codex` invocation.
3. **Distinguishing feature vs. Case 1:** everything *upstream* of the actual binary invocation succeeded — the resolver correctly identified that Codex *should* be available (codex-kit is installed, its skill/command surface is registered, presumably some earlier lighter-weight check like "is codex-kit present" passed). The failure is purely an *environment* problem: the specific executable this machine needs isn't discoverable in the current shell's search path. This is the kind of failure a user fixes by installing/symlinking the binary or fixing their PATH — not by installing a plugin.
4. **What a good resolver does with this:** ideally it catches the spawn failure (or the pre-flight check result) and translates it into a specific, typed error distinct from both "plugin not installed" (Case 1) and "the CLI ran but reported an internal problem" (Case 3) — something like "codex-kit is installed but the `codex` binary isn't on PATH; is Codex CLI installed on this machine?" If it doesn't do this translation, the raw OS-level "command not found" error would leak through directly to the user/log, which is a worse experience but not incorrect — the underlying cause is the same either way.

---

## Case 3: a dispatch is attempted and returns a typed failure like `isolation_profile_unavailable`

This is the deepest layer, and structurally the most informative failure of the three. Here, *everything* upstream has already succeeded:

- codex-kit is installed and discoverable (passes Case 1's check).
- The `codex` binary is present and resolvable on PATH (passes Case 2's check).
- The resolver successfully constructed a command line, spawned the process, and the `codex` CLI itself actually **started running**.
- The CLI then evaluated its own operating environment — most plausibly something related to how it sandboxes/isolates the code execution or file access it's about to perform (a "seatbelt"/sandbox-profile mechanism on macOS, a container/VM-based isolation layer, or some other OS-specific sandboxing primitive Codex CLI depends on to safely execute untrusted actions) — and determined that the specific isolation profile it needs is not available in this environment. Rather than crashing with an unhandled exception or a bare non-zero exit code, it returned a **structured/typed result** — i.e., some machine-readable error code or JSON payload naming the specific problem (`isolation_profile_unavailable` reads like an error-code/enum value, not free-text prose).

What's different about this case, mechanically:

1. **The subprocess itself succeeded at the OS level** — it started, ran, and terminated (probably with a non-zero exit code, but a *meaningful* one), as opposed to Case 2 where the OS never managed to start a process at all.
2. **The resolver now has to parse and interpret output**, not just detect a spawn failure. This means the resolver's error handling has to actively recognize the `codex` CLI's own error-reporting format (JSON on stdout/stderr, a specific exit code convention, or similar) and map the *specific* typed code (`isolation_profile_unavailable`) to a specific remediation message — as opposed to Case 2, where the OS's own error is generic and doesn't need any application-level parsing to detect.
3. **The remediation path is completely different from either earlier case.** This isn't "install codex-kit" (Case 1) or "put codex on PATH" (Case 2) — it's an environment/platform capability gap in whatever sandboxing mechanism Codex CLI relies on (e.g., missing OS-level sandboxing support, missing permissions to create the isolation profile, running inside a context — like a container, or a Windows environment lacking the necessary sandbox primitive — where the expected isolation mechanism just isn't available at all). The fix would be something like adjusting Codex CLI's sandbox/approval settings, running in a different mode, or on a different host/OS — not a PATH fix and not a plugin install.
4. **This is the only one of the three cases where the resolver is actually receiving structured signal from Codex CLI itself** about *why* it can't proceed, rather than inferring the reason indirectly (absence of a directory, absence of a binary). A resolver that handles this well would surface the *specific* typed code to the user/log rather than collapsing it into a generic "Codex dispatch failed" message — since `isolation_profile_unavailable` is actionable in a way a bare failure isn't.

---

## Direct contrast of the three

| | Case 1: codex-kit not installed | Case 2: codex-kit installed, binary not on PATH | Case 3: dispatch runs, typed failure returned |
|---|---|---|---|
| Layer of failure | Plugin/component discovery (design-time / static) | Executable resolution (OS/environment, at spawn time) | CLI runtime, after successful process start |
| Does a subprocess ever get spawned? | No (if resolver checks properly) | No — spawn itself fails | Yes — spawn succeeds, process runs and exits |
| Where the resolver's own logic needs to intervene | Pre-flight plugin-presence check | Pre-flight PATH check, or catching a spawn-level OS error | Parsing the CLI's own structured error output/exit semantics |
| Typical low-level signal | Missing directory / unregistered component | Shell "command not found" (exit 127 / "not recognized") | A specific error code/enum in the CLI's own output |
| Natural remediation | Install codex-kit | Install Codex CLI / fix PATH | Fix the sandbox/isolation environment, or change Codex CLI's execution mode |
| Is this really "the first real Codex dispatch"? | No — should be caught before any dispatch attempt | Arguably the actual first dispatch attempt, but it fails immediately at spawn | Yes, unambiguously — the dispatch is real and Codex CLI's own logic ran |

The phrase "first real Codex dispatch" in the prompt is doing real work here: strictly, only Case 3 is a genuine dispatch in the sense of "a Codex CLI process actually executed and made a decision." Case 2 is an *attempted* dispatch that never got off the ground at the OS level. Case 1, if the resolver is implemented with a proper availability check, shouldn't produce any dispatch attempt whatsoever — the resolver should recognize the absence of codex-kit and route around Codex entirely (or fail fast with an installation-gap message) well before it ever tries to build a `codex` command line.

## Caveats / uncertainty

I don't have access to the actual `cross-model-review` skill or `codex-kit` plugin source in this task, so I can't confirm:
- Whether `cross-model-review`'s resolver actually performs a distinct "is codex-kit installed" check separate from "is the `codex` binary on PATH" — if it doesn't, Case 1 could in practice collapse into behaving like Case 2 (a generic "couldn't run Codex" failure) rather than being caught earlier and more specifically.
- The exact mechanism codex-kit uses to invoke Codex CLI (direct `Bash` tool call, a wrapper script, an MCP-style integration, etc.), which would determine the exact shape of the Case 2 error (raw shell error vs. something codex-kit itself catches and reformats).
- Whether `isolation_profile_unavailable` is an exact real error identifier from Codex CLI or an illustrative example — I'm treating it as representative of "a structured, named failure mode returned by the CLI after it actually started running," which is the meaningful distinction regardless of the exact string.
- Exact exit codes, JSON shapes, or log formats involved in any of these three cases.

---
name: codex-windows-guardrails
description: >-
  Best-effort guardrails for routing a local Windows Codex reviewer dispatch
  through danger-full-access when no working sandbox exists on the platform:
  pre-flight repository-boundary and secret-file checks, a dangerous-command
  allowlist appended to the reviewer instruction body Codex receives, and a
  validated findings envelope on success -- all in one script call. Invoked
  by codex-review-bridge's callers (e.g. plugin-auditor's Codex backend
  resolver) when the resolved execution profile is Windows-guarded
  danger-full-access -- not invoked directly by end users, and never a
  substitute for a real OS sandbox.
allowed-tools: Bash(node */codex-windows-guardrails/scripts/guarded-dispatch.mjs:*)
disable-model-invocation: true
---

# Codex Windows Guardrails

`codex exec`'s sandbox modes (`read-only`/`workspace-write`) do not work on Windows — confirmed
across two CLI versions (`plugins/plugin-devkit/KNOWN_ISSUES.md`). `danger-full-access` is the only
mode that executes at all on this platform. This skill is what a caller must run *instead of*
`codex-review-bridge` for that one profile — the bridge's own CLI unconditionally refuses
`danger-full-access` (correctly, for every other caller); this skill is a separate, narrowly-scoped
entry point for exactly the one case that needs it.

**This is not a sandbox.** Nothing here intercepts what Codex's own agent loop does once it starts
running with `danger-full-access` — there is no `PreToolUse`-equivalent event in Codex's own hook
system (confirmed this session: neither `codex-kit`'s `hooks.json` nor Codex CLI's own cached copy
of it exposes anything beyond `SessionStart`/`SessionEnd`/`Stop` — see
`references/hooks-sync-investigation.md`). What follows narrows what gets *sent* to Codex before the
dispatch starts, and asks Codex to self-restrict once running. Never describe this skill's output as
sandbox-equivalent, in provenance, in a report, or in conversation.

## Quick Start

Caller invokes `scripts/guarded-dispatch.mjs` directly (never `codex exec` raw, and never
`codex-review-bridge`'s own CLI for this profile) with `--reviewer-type`, `--instruction-file`,
`--target-paths`, `--dispatch-id`, `--repo-root`. One call does everything, in order, stopping at
the first failure:

1. **Resolve policy** — `assets/settings.json` (shipped, disabled by default) merged with
   `.claude/codex-windows-guardrails.local.json` (untracked override only — a tracked copy is
   ignored, fail-closed). If not enabled → typed failure `guardrails_disabled`. See
   `references/policy-and-trust.md`.
2. **Repository-boundary check** on every `target-paths` entry (not the instruction file — that's a
   different check, see step 4). Typed failure `repository_boundary_violation` on any entry outside
   the repo root.
3. **Secret-file check** — walks the actual filesystem under each target (not `git ls-files`, which
   would miss a `.env` precisely because `.env` is normally gitignored) against `git-kit`'s
   sensitive-filename patterns. Typed failure `secret_file_in_scope` on any match.
4. **Instruction-containment check** — the instruction file must not resolve inside any
   `target-paths` entry (the same rule `codex-review-bridge` itself enforces — reused directly, not
   reimplemented). Typed failure on a violation.
5. **Dispatch** — builds the prompt (reviewer instructions + the dangerous-command allowlist from
   `assets/dangerous-command-instructions.txt`, both wrapped in the same content-trust-boundary
   framing `codex-review-bridge` uses), calls `runCodexExec` with `sandbox: "danger-full-access"`,
   validates the result against `codex-review-bridge`'s own exported `ENVELOPE_SCHEMA` and
   `semanticallyValidate` — reused directly, not duplicated. See `references/preflight-checks.md`
   for exactly what each check verifies and `references/dispatch.md` for the exec/validation step.
6. **Output**: the identical validated envelope shape `codex-review-bridge` returns on success, or a
   typed failure on stdout/stderr with a non-zero exit — same contract, so a caller's existing
   Adapter logic doesn't need a second code path.

The caller's own provenance must record `isolation_strength: best_effort_guardrails` for a dispatch
that went through this skill — never `os_isolated`.

## When to Use

- A caller (e.g. `plugin-auditor`'s Codex backend resolver, `references/codex-backend.md`) has
  already determined the only available local execution profile is Windows `danger-full-access`,
  and needs a bounded, disclosed way to proceed rather than skipping straight to it.

## When NOT to Use

- **A working sandboxed profile is available** (CI's `read-only` on Linux, or any future qualified
  non-Windows local profile) — go straight to `codex-review-bridge`; this skill adds pre-flight
  overhead with no benefit when a real sandbox already works.
- **Claiming this makes `danger-full-access` safe in general** — it doesn't. This skill exists for
  one narrow, disclosed case: no other option works on this platform today.

## Security Claim

These are best-effort guardrails: pre-flight scope narrowing plus a self-restriction request sent to
the model. They reduce accidental and straightforward-malicious exposure. They do not, and cannot,
stop a determined or compromised model from doing something harmful once `codex exec` is already
running with `danger-full-access` — there is no interception point on this session's side once that
process starts. State this plainly wherever this skill's output is surfaced; never let a report or
provenance field imply otherwise.

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/policy-and-trust.md` | Config layering and the exact trust-boundary discriminator for the local override |
| `references/preflight-checks.md` | What each of the three pre-flight checks actually verifies, and why dangerous-command couldn't survive as a fourth pre-flight check |
| `references/dispatch.md` | The exec/validation step: what's reused from `codex-review-bridge` vs. built fresh, and why this bypasses the bridge's own CLI entirely |
| `references/hooks-sync-investigation.md` | Confirmed facts about Codex's own hook system, and the open question this skill does not resolve |
| `assets/dangerous-command-instructions.txt` | The literal instruction text appended to every dispatch — source of truth; `references/preflight-checks.md` explains it, doesn't duplicate it |
| `scripts/guarded-dispatch.mjs` | The one script — everything above happens in this single call |
| `assets/settings.json` | Shipped, disabled-by-default policy default |
| `plugin-auditor/references/codex-backend.md` | The caller that invokes this skill when its own resolved profile is Windows-guarded `danger-full-access` |

## Testing & Validation

**Verify this skill activates on:**
- Nothing conversational — invoked by other components (`plugin-auditor`'s Codex backend resolver),
  not directly by end users, same pattern as `codex-review-bridge`.

**Verify it does NOT proceed to Codex on:**
- `windows_guardrails.enabled` false or unset (the shipped default) — verified live: returns
  `guardrails_disabled` immediately, no exec attempt.
- A tracked `.claude/codex-windows-guardrails.local.json` — verified live: its `enabled: true` is
  ignored, falls back to the shipped disabled default.
- A `target-paths` entry outside the repository root — verified live: `repository_boundary_violation`.
- A `.env` (or other sensitive-pattern) file anywhere under a directory target, tracked or not —
  verified live: `secret_file_in_scope`. This specifically covers the case an earlier draft of this
  check missed (a directory target whose contents include an untracked `.env`).
- An instruction file that resolves inside a `target-paths` entry — verified live: rejected.
- A `dispatch-id`/`reviewer-type` outside `^[A-Za-z0-9._-]{1,64}$` — verified live: rejected with
  `invalid_arguments` (added after Self-Review's second pass found this guard was lost when the
  bridge's own CLI, which used to perform it, was bypassed).
- An uppercase-variant secret filename (`.ENV`) on Windows — verified live: still rejected
  (case-insensitive match, platform-gated the same way path-boundary comparison already is).

**Quality gates:**
- [ ] Never claims or documents sandbox-equivalence, anywhere its output is surfaced
- [ ] A pre-flight failure always returns a typed refusal on stdout with a non-zero exit — never an
      empty pass, never silent
- [ ] A tracked local-override file's values are always ignored, never honored
- [ ] The dangerous-command instruction text is always framed as a request the model could ignore,
      never as enforcement
- [ ] Never calls `codex-review-bridge`'s own CLI entry point for this profile — only imports its
      exported, reusable pieces
- [ ] `dispatch-id`/`reviewer-type` are always charset/length-validated before either is
      interpolated into the prompt — reused from `codex-review-bridge`'s `isValidToken`, never a
      second copy
- [ ] The instruction-containment check and the actual instruction-body read always resolve the
      same path value — never a check on one resolution and a read on another

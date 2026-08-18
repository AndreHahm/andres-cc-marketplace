# Walkthrough: cross-model-review's Codex dispatch resolver when codex-kit isn't installed

Scope note: this is a description only — no command below is actually executed. It traces what the
`cross-model-review` skill's "Codex dispatch resolver" section does, step by step, for the specific
scenario "codex-kit is not installed in this repo at all (no `plugins/codex-kit` directory exists)," and
then contrasts that with two related-but-distinct failure shapes the skill also names.

## Where this sits in the skill's flow

Before any of this fires, Preflight (steps 1-6) runs first and completes normally regardless of whether
codex-kit is installed:

- Step 2's grep against the changed-file list for `plugins/codex-kit/.*/scripts/.*` (the self-modifying-
  diff check) simply finds no matches — it's grepping `git diff --name-only` output, not checking whether
  the directory exists on disk, so a missing `plugins/codex-kit` doesn't make this step error.
- Step 5's `git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md"` also doesn't
  touch codex-kit at all — it's this skill's own prompt files.

So the skill reaches Phase 1 with no earlier sign that Codex is unavailable. The **First-Send Confirmation**
then fires — this is unconditional and happens *before the resolver is ever invoked*, regardless of what
the resolver is about to discover: `AskUserQuestion` names the persona and target paths, discloses that
the dispatched process can read the whole repo root, discloses the possible `danger-full-access` outcome
if Step 2 ends up triggering, and discloses any Preflight-step-6 dispatcher-trust gap. Only after the user
picks "Send to Codex for this run" does the resolver actually attempt Step 1.

## Scenario as asked: codex-kit not installed at all

Resolver Step 1 is:

```bash
node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs \
  --reviewer-type "<persona>" --instruction-file "<path>" --execution-profile read-only \
  --target-paths "<changed files>" --dispatch-id "<id>" --cwd "$REPO_ROOT"
```

With no `plugins/codex-kit` directory in this repo, the file `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` does not exist. `node <path>` fails at the **OS/module-resolution level** — Node can't locate the entry-point file at all, so it exits non-zero (typically exit code 1) with a raw error to stderr (something like "Cannot find module ..." / ENOENT on the script path). Critically:

- **No JavaScript in `bridge-invoke.mjs` ever runs.** The script's own error handling, its typed-failure
  JSON envelope logic, its argument parsing — none of it executes, because Node never got past resolving
  the entry-point path.
- **No structured/typed failure is produced.** What comes back is a bare process failure (non-zero exit
  code, unstructured stderr), not a parseable JSON envelope of the kind `codex-review-bridge`'s own
  envelope schema defines.
- Because this failure is *not* the specific `isolation_profile_unavailable` signal, the resolver's step 2
  branch ("on `isolation_profile_unavailable`, fall back to Step 2") is **never triggered**. The resolver
  does not attempt `guarded-dispatch.mjs` at all in this scenario — even though that script lives under
  the same missing `plugins/codex-kit/` tree and would fail identically if invoked, the branching logic
  never reaches it, because Step 2 is reached only via that one specific typed-failure signal.
- The raw failure instead falls straight into resolver **step 3**, which the skill's text names explicitly:
  *"codex-kit not being installed at all (`node` then fails at the OS level before either script produces
  its own typed-failure JSON — the same `cli_unavailable` fallback case `codex-backend.md` names
  explicitly)."*
- Step 3's action fires: tell the user Codex is unavailable for this run, then `AskUserQuestion` whether
  to proceed single-model (Claude only — findings default to Medium confidence since nothing
  cross-examines them) or stop.
- If the user proceeds single-model, Phase 1 continues with only Claude's fresh-eyes pass (no
  `codex_fresh_eyes.json` is ever written to `$RUN`), Phase 2 has no Codex Phase-1 findings to
  cross-examine and no Codex challenger pass runs, and Phase 3's synthesis notes the degraded,
  single-model framing rather than silently presenting a two-model report.

This matches the skill's own Testing & Validation scenario 2 verbatim: *"`codex-kit` is not installed at
all, or the `codex` CLI itself is missing — distinct from scenario 3: `node` fails at the OS level before
either script produces a typed-failure JSON → resolver step 3 fires on that raw failure, `AskUserQuestion`
offers single-model fallback, Medium-confidence framing is stated in the final report."*

## Contrast 1: codex-kit IS installed, but the `codex` CLI binary isn't on PATH

Here `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` **does exist** on disk, so
`node <path> ...` succeeds at the module-resolution layer — Node loads and starts executing the script's
own JavaScript. That script's logic then tries to invoke the `codex` CLI as a subprocess; since `codex`
isn't found on PATH, that spawn fails. But this time the failure happens *inside* `bridge-invoke.mjs`'s own
running code, not before it — so the script is in a position to catch the spawn failure and emit its own
structured typed-failure JSON (the `cli_unavailable`-style envelope `codex-backend.md` documents), rather
than crashing raw the way Node itself did in the "not installed at all" case.

The end-user-visible outcome is identical to the "not installed at all" case — this typed failure is also
not `isolation_profile_unavailable`, so Step 2 is never attempted, and resolver step 3 fires with the same
`AskUserQuestion` (single-model or stop), the same Medium-confidence framing. What differs is purely the
**diagnostic shape** of the failure: a raw, unstructured OS/process error with no JSON payload (codex-kit
missing) versus a clean, parseable typed-failure envelope produced by code that actually ran (codex CLI
missing). Anyone inspecting logs or `$RUN`'s scratch files after the fact would see nothing for the first
case and a structured `cli_unavailable`-type JSON object for the second.

## Contrast 2: a dispatch is attempted and returns `isolation_profile_unavailable`

This requires codex-kit installed **and** the `codex` CLI present on PATH. Step 1's `node
bridge-invoke.mjs` call succeeds all the way through: it successfully spawns `codex` with
`--execution-profile read-only`, but the sandboxed profile itself doesn't function on this platform
(expected on local Windows per the skill's own text — "read-only`/`workspace-write` sandboxes are
confirmed non-functional there"). `bridge-invoke.mjs` detects this and returns a typed-failure JSON whose
type is specifically `isolation_profile_unavailable`.

This is the **one** scenario of the three where resolver **step 2 actually fires**: the skill falls back
to

```bash
node plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs \
  --reviewer-type "<persona>" --instruction-file "<path>" \
  --target-paths "<changed files>" --dispatch-id "<id>" --repo-root "$REPO_ROOT"
```

— a second, distinct node process, with a different flag shape (`--repo-root` instead of `--cwd`, no
`--execution-profile` since Step 2 is implicitly `danger-full-access`). Per the skill, this path is
**disabled by default** — `codex-windows-guardrails`' own `assets/settings.json` ships disabled, and it
takes an untracked `.claude/codex-windows-guardrails.local.json` override to enable, which this skill
never writes on the user's behalf. So absent that override, `guarded-dispatch.mjs` itself immediately
returns a `guardrails_disabled` typed failure — which is explicitly one of resolver step 3's "any other
typed failure" cases, so the same `AskUserQuestion` single-model-or-stop fallback fires, just one hop
later than in the two scenarios above.

If the override *did* exist and Step 2 were enabled, this is the one branch where a dispatch would
actually proceed for real — running `danger-full-access` (no sandbox at all, read *and* write/execute),
exactly the outcome the First-Send Confirmation already disclosed as a possibility before Step 1 was ever
attempted.

## Summary comparison

| | codex-kit not installed | codex-kit installed, `codex` CLI missing from PATH | Dispatch returns `isolation_profile_unavailable` |
|---|---|---|---|
| Does `node bridge-invoke.mjs` even start? | No — module resolution fails immediately | Yes — script runs, then its internal `codex` spawn fails | Yes — script runs and successfully invokes `codex`, which reports the sandbox profile doesn't work |
| Failure shape | Raw OS/process error, no JSON envelope | Structured typed-failure JSON (`cli_unavailable`-style), produced by the script's own code | Structured typed-failure JSON, type `isolation_profile_unavailable` |
| Is Step 2 (`guarded-dispatch.mjs`) attempted? | No — only `isolation_profile_unavailable` triggers the Step 2 branch | No — same reason | Yes — this is the only one of the three that reaches Step 2 |
| Where resolver step 3 fires | Immediately, on the raw Step 1 failure | Immediately, on Step 1's typed failure | Only after Step 2 also fails (typically `guardrails_disabled`, the shipped default) |
| End-user outcome | `AskUserQuestion`: single-model or stop; Medium-confidence framing | Same `AskUserQuestion` outcome | Same `AskUserQuestion` outcome, unless the disabled-by-default guardrails override is present, in which case a real `danger-full-access` dispatch proceeds instead |

The practical takeaway: the skill's resolver treats "codex-kit missing" and "codex CLI missing" as the
same *user-facing* failure bucket (both fall straight to step 3's single-model-or-stop ask, without ever
touching Step 2), differing only in whether a clean typed-failure JSON exists to inspect afterward.
`isolation_profile_unavailable` is architecturally distinct — it is the only trigger for the Step 2
fallback attempt at all, and only degrades to the same single-model ask if that (disabled-by-default)
fallback also fails.

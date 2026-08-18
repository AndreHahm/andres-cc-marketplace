CONFIRMATION: I did not Read, Grep, Glob, or otherwise inspect any file under `plugins/git-kit/skills/cross-model-review/`, `.claude/skills/cross-model-review/`, or `plugins/codex-kit/` while producing this answer. Everything below is reasoned generically from the scenario description and standard Claude Code / plugin-authoring conventions, not from the actual skill source.

# Walkthrough: cross-model-review hitting `isolation_profile_unavailable` on Windows

## Important caveat up front

I have not read the `cross-model-review` skill's actual instructions, so I cannot quote its exact step numbering, exact script/flag names, or exact file paths. What follows is my best generic reasoning about what a well-built skill in this position *should* do, based on:

- The scenario as described (codex CLI present and on PATH; `codex-review-bridge` dispatch fails with `isolation_profile_unavailable` because the read-only sandbox isn't available on Windows; `codex-windows-guardrails` exists as a separate, currently-disabled component with no local override file present).
- General conventions this kind of plugin ecosystem tends to follow (config gating, explicit user confirmation before weakening a safety property, no silent fallback).

Anywhere I'm inferring rather than certain, I've flagged it as such. I have not invoked any command — this is a description of what I'd do, not an execution log.

## Step 1 — Recognize the failure as a known, named condition, not a generic error

`isolation_profile_unavailable` reads as a structured/named error code rather than a raw crash, which suggests the skill (or the underlying `codex-review-bridge` dispatch mechanism) is built to anticipate this specific failure mode — i.e., "the sandbox/isolation profile this platform would normally use to run codex read-only isn't implementable here." On Windows, a read-only OS-level sandbox (chroot/landlock/seccomp-style isolation, or similar) commonly isn't available the same way it might be on Linux/macOS, so this is very plausibly a *platform capability gap* rather than a misconfiguration or bug.

My first move would be to treat this as "the skill's normal, sandboxed dispatch path is not usable on this machine" rather than retrying the same dispatch, since retrying an unsupported isolation profile isn't going to succeed differently on a second attempt.

## Step 2 — Check whether there's a supported platform-specific alternative, and its current state

The scenario states there's a separate component, `codex-windows-guardrails`, which exists specifically for this kind of platform gap (its name strongly implies "guardrails to use on Windows in place of the normal sandbox"). Two facts matter here:

1. It is **at its shipped default**, which the scenario says is **disabled**.
2. **No local override file exists** — meaning nothing in this environment has opted it in.

Given the general principle that a review/dispatch tool should not silently substitute a weaker safety mechanism for a missing stronger one, I would expect the skill to *check* this component's state as part of handling the failure, rather than ignore it. The fact that the skill's ecosystem ships this component disabled-by-default (rather than auto-enabling it whenever the sandbox is unavailable) suggests a deliberate design choice: running codex without the normal read-only isolation is treated as a decision that needs explicit opt-in, not an automatic fallback.

## Step 3 — Do not silently proceed in a weaker-safety mode

At this point I would expect (and would myself follow) the general rule that changing or bypassing a safety-relevant behavior requires disclosure and, where a real choice exists, an explicit confirmation from the user rather than silently picking a path. Concretely, I would not:

- Silently retry with the sandbox flag dropped and no isolation at all, and
- Silently enable `codex-windows-guardrails` by writing a config override on the user's behalf without saying so.

Both of those would be "quietly weakening a safety gate," which is the kind of thing that should surface, not disappear into a log line.

## Step 4 — Surface the situation and the real options to the user

Instead, I would stop and lay out the situation plainly, then let the user decide among the plausible options:

- **Option A: Enable `codex-windows-guardrails`.** Since no local override file exists yet, enabling it would mean creating one (the shipped default lives in a git-tracked/shippable location, so a *local* override is the correct place to flip this per-machine, rather than editing the shipped default itself). I don't know the guardrails component's exact config file name/path/schema, so I would say so rather than guess it, and would ask the user to confirm before creating any such file — this is exactly the kind of "component behavior toggle, machine-specific" decision that should be confirmed rather than assumed, since I don't actually know if the override format is JSON, YAML, or something else, or whether it's meant to be gitignored or checked in.
- **Option B: Proceed with `codex-review-bridge` dispatch without the isolation profile / without guardrails**, i.e., run codex against the repo without the read-only sandbox protection. This is a real capability reduction (codex would be running with whatever access the CLI normally has on this machine, not confined to read-only), so I would only do this with the user's explicit, informed go-ahead — stating clearly what protection is being given up.
- **Option C: Skip/abort the cross-model review step for this run.** If neither of the above is acceptable right now, the safest default is simply not to run the codex-side review on this machine and continue without it, flagging that the cross-model review was skipped and why.

I would present these as a real choice (e.g., via a direct question to the user) rather than picking one on their behalf, because the "right" answer depends on things I can't determine myself — how much the user trusts running codex unsandboxed on this machine, whether they're willing to accept a guardrails-based (not sandbox-based) substitute, and whether skipping review entirely for this run is acceptable.

## Step 5 — If the user opts to enable guardrails

If the user chooses Option A, I would treat creating the local override file as a config decision needing the same care as any other: confirm the intended storage location (a local, presumably gitignored override rather than editing the shipped default), and the intended format, before writing anything — and I would say plainly that I don't know the guardrails component's exact schema without inspecting it, so I'd want to look at what it actually expects (or ask the user to point me at documentation) before writing a file that's supposed to satisfy it. I would not fabricate a config schema.

## Step 6 — If the user opts to proceed without the sandbox, or to skip

- If proceeding unsandboxed: retry the `codex-review-bridge` dispatch, but make sure the eventual output/report clearly notes that this review ran without the platform's normal isolation profile, so nobody downstream mistakes it for a fully-sandboxed run.
- If skipping: don't attempt the dispatch again; note in whatever summary or handoff follows that the codex-side cross-model review was not performed on this run, and why (platform sandbox unsupported, guardrails declined/not configured).

## Summary of the shape of this response

Given the facts as described, the decision point is: a normally-sandboxed dispatch path is unavailable on this platform, and the one alternative safety mechanism this ecosystem provides for exactly this situation is off by default with nothing overriding it locally. The generically correct handling is to stop, explain the gap clearly, and let the user choose between (a) opting into the Windows-specific guardrails via a new local config, (b) explicitly accepting a reduced-isolation run, or (c) skipping the review — rather than silently choosing any of these on the user's behalf. I'm not certain of the exact mechanics the real skill uses to phrase or gate this choice (exact prompt wording, exact config file name/schema, exact retry command), and I want to be explicit that those specifics are unknown to me rather than invented.

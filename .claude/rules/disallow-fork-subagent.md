# Disallow the Fork Subagent

## When this applies

Any point in a session where the `Agent` tool is about to be invoked with `subagent_type: "fork"`, for
any task, anywhere in this repository.

## Rule

Never invoke `Agent` with `subagent_type: "fork"` in this repository, for any task. This is an absolute
prohibition, not a case-by-case judgment call — it applies regardless of task size, urgency, or how much
the forked agent would otherwise reduce context usage. Where background or parallel work is genuinely
needed, dispatch a fresh (non-fork) `subagent_type` instead — `general-purpose` or a more specific agent
type — even though a fresh agent starts without inherited context and needs a self-contained prompt
written for it, per the `Agent` tool's own prompt-authoring guidance.

## Incorrect

```
Agent({ subagent_type: "fork", description: "...", prompt: "..." })
```
Dispatched anywhere in this repo, for any task — including one that looks like pure research or
"intermediate output I don't need to keep."

## Correct

```
Agent({ subagent_type: "general-purpose", description: "...", prompt: "<self-contained prompt with full context, since a fresh agent has none>" })
```
Or, when a matching skill exists for the task, dispatch that skill instead per
[[prefer-skills-over-ad-hoc-work]].

## Why

Reported directly by this repo's owner (2026-09-25): the `fork` subagent type has repeatedly failed to
reliably use this repo's own skills or follow its `.claude/rules/*.md`/CLAUDE.md instructions, and its
generated output has consequently been unreliable. This is a specifically bad combination with why fork
is normally attractive: it exists to keep a forked agent's own tool output *out of* the coordinator's
context ("don't peek" — the coordinator is explicitly told not to read the fork's transcript mid-flight),
which means a fork skipping this repo's rules and skills is not visible for review until its final
summary lands, by which point any rule-violating or buggy work may already be done. Until fork can be
verified to reliably load and follow this repo's skills and rules, using it here is a net loss regardless
of the token/context savings it would otherwise offer.

## Enforcement

Backed by a `PreToolUse` hook (2026-09-25): `plugins/plugin-devkit/hooks/guard-fork-subagent.sh`,
registered on the `Agent` matcher, hard-denies any call whose `subagent_type` resolves to `"fork"`
(case/whitespace-normalized). Security-reviewed per
`.claude/rules/require-security-review-before-new-gate.md` before shipping. Not airtight: under the
hook's own `"onError": "warn"` registration, a fork call is let through with just a warning (never
silently) if the hook process is killed by its timeout, its interpreter or script file is missing/
non-executable, or a bash parse/expansion error occurs before its own fail-closed trap installs — the
same class of residual `guard-raw-branch-create.sh` discloses for git-kit's guards.

**Launch mechanism (updated 2026-09-25, PR #396 review):** the hook's `command` field quotes the
whole `${CLAUDE_PLUGIN_ROOT}`-prefixed path (`"\"${CLAUDE_PLUGIN_ROOT}\"/hooks/guard-fork-subagent.sh"`,
`"shell": "bash"`), matching `context-kit`'s already-shipping `compact-instructions.sh` precedent for
the identical problem, rather than switching to exec form (`"args": []`) as first attempted.
CodeRabbit correctly flagged that an *unquoted* shell-form path word-splits on a space anywhere in
`${CLAUDE_PLUGIN_ROOT}` (e.g. a Windows/Mac install path containing one), silently defeating the guard
under `onError: "warn"` — empirically confirmed both ways: an unquoted `sh -c` invocation against a
space-containing path failed with exit 127 ("not found"); the quoted form correctly launched and
denied the fork call from the same path. Exec form was tried first, but dropped after a second
security-reviewer pass raised two unresolved risks specific to it — whether `${CLAUDE_PLUGIN_ROOT}`
substitution still applies with no shell involved, and whether direct exec of a `.sh` file (no shebang
interpretation) works on Windows — neither of which this session could verify from this environment.
Quoting closes the reported gap using the same shell-form mechanism every other hook in this file
already relies on, without introducing either of those two unverified risks.

**Residual not fixed here (informational, not blocking):** this file's sibling `PreToolUse`/
`PostToolUse` hook entries still use unquoted shell-form paths — a deliberate scope decision (only the
flagged security-relevant entry was fixed), since none of them is a hard-block gate whose silent
failure has the same consequence (`security-precommit-check.sh` is log-only; the R25/R26 checks are
best-effort and already `onError: "warn"` by design).

**Scope note:** the hook ships inside plugin-devkit's own `hooks/hooks.json`, so it is active in *any*
project that installs plugin-devkit as a plugin, not only this repository — a deliberate choice
(2026-09-25), wider than this rule's own "in this repository" framing above. This rule's policy text
still describes and justifies the *decision* for this repo specifically; the hook is simply shipped
more broadly than the policy's own stated scope, by the repo owner's explicit choice.

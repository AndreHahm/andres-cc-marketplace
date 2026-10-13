# Codex backend resolver: no-sandbox escalation walkthrough (reasoning only)

Sources: `plugins/plugin-devkit/skills/plugin-auditor/references/codex-backend.md` (sections "Resolver", "Isolation: reactive, not proactive", "Windows-Guarded Execution Profile", "Codex Path") and `plugins/plugin-devkit/skills/plugin-auditor/SKILL.md` (frontmatter `allowed-tools`, Testing & Validation scenario 13, Quality gates).

Scenario preconditions: Codex backend enabled, the `read-only` attempt for skill-reviewer returned `isolation_profile_unavailable`, and the audited scope excludes plugin-devkit and codex-kit. Under "Resolver" step 3 the Codex path is therefore not skipped for scope reasons. This assumes the checked-out branch also does not change `plugins/codex-kit/` or `plugins/plugin-devkit/agents/`, which the same step tests with `git diff --name-only "$(git merge-base main HEAD)"`. The First-Send Confirmation ("First-Send Confirmation" section) must also already have fired, because "No Codex dispatch ... may reach any later step without this gate having fired at least once in the session."

## (a) What the resolver calls first and what it adds

Section: "Windows-Guarded Execution Profile", paragraph "When this profile is attempted".

The resolver does not read the `windows_guardrails` opt-in itself. It first calls `plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs` once with `--dry-run true` added and otherwise the same arguments as the real call:

- `--reviewer-type "skill-reviewer"`
- `--instruction-file "<scratchpad path>"`
- `--target-paths "<scope>"`
- `--dispatch-id "<run-id>-skill-reviewer"`
- `--repo-root "<marketplace root>"`

The dry run runs the whole guard chain, including the policy-enabled check, and skips only the real `codex` call. This comes after the caller has done Codex Path steps 2 and 3 (source the trusted instruction body from `plugins/plugin-devkit/agents/skill-reviewer.md` and write it to the scratchpad), per "Steps 0 and 1 still apply regardless of profile..." in the same section.

## (b) A typed failure such as guardrails_disabled, and whether the user is asked

Section: "Windows-Guarded Execution Profile", same paragraph, plus the paragraph after the bash block ("Any typed failure (including `guardrails_disabled` ...)"), and Codex Path step 8.

Any typed failure from the dry run, `guardrails_disabled` included, routes skill-reviewer to Claude-native with no prompt. The second AskUserQuestion is not asked. This folds into the existing fallback handling (Codex Path step 8). The fallback category is recorded once as a note on that dispatch's `coverage` entry, not stamped on individual findings. The user is not asked anything at this point. Scenario 13 in SKILL.md's Testing & Validation lists this behavior as "routes to Claude-native with no prompt on any typed failure from it (`guardrails_disabled` included)".

## (c) When the second AskUserQuestion is asked and what it must disclose

Section: "Windows-Guarded Execution Profile", paragraph "When this profile is attempted".

When: only after a passing dry run (the guardrails opt-in resolves enabled) and before the real call. The First-Send gate does not cover this profile because it describes read access only. It is asked once per audit run, and the answer applies to every remaining reviewer in that run.

It must:
- Name the reviewer(s) and target path(s).
- State plainly that this profile has no sandbox. The Codex process can read, write and execute anything this user account can reach: files and commands anywhere on the machine, not only under the repository root, because nothing enforces that root.
- State that it has network access, so credentials such as `~/.codex/auth.json` or `~/.ssh` are reachable.
- State that it is steered by the plugin content under audit.
- State that it is bounded only by best-effort, not enforced, guardrails.
- State that the script's secret-file screen skips untracked files the repository itself ignores (a gitignored `.env` is not caught) unless the owner opted into `scan_ignored_high_risk`.

Options: "Run without a sandbox for this run" / "Stay Claude-native for this run".

## (d) The question cannot be asked, or the user declines

Section: "Windows-Guarded Execution Profile", same paragraph, and Codex Path step 8.

- If the question cannot be asked (a headless or subagent context, or the tool is unavailable), treat that as declined, never as consent.
- A decline routes skill-reviewer, and every remaining reviewer in that run, to Claude-native (Codex Path step 8), with the reason recorded on the coverage entry.
- No real `guarded-dispatch.mjs` call is made.
- Related case, from the Bash-block paragraph in the same section: if the user denies Claude Code's permission prompt for either the dry run or the real call, that reviewer is treated as declined and routed to Claude-native, recording the reason.

## (e) Why Claude Code's own permission prompt also appears for guarded-dispatch.mjs

Sections: SKILL.md frontmatter `allowed-tools`; "Windows-Guarded Execution Profile" paragraph on `allowed-tools`; SKILL.md Quality gates.

The `allowed-tools` frontmatter grants only these Bash scopes:
- `Bash(date:*)`
- `Bash(node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs:*)`
- `Bash(git ls-files:*)`
- `Bash(git diff:*)`
- `Bash(git merge-base:*)`
- `Bash(python plugins/plugin-devkit/skills/reviewing-evals/scripts/check_evals.py:*)`

`guarded-dispatch.mjs` is deliberately absent. The codex-backend.md text says it is "deliberately not in this skill's `allowed-tools`, so Claude Code's own permission prompt appears for each call (the dry run and the real run) unless your own permission settings already allow it."

- The dry run's prompt is the first gate.
- The real run's prompt is a backstop behind the AskUserQuestion.
- Do not choose "don't ask again" for this script, and never add a pre-approved grant for it.

The Quality gates state it directly: a pre-approved grant "would remove the Claude Code permission prompt that stands behind the no-sandbox `AskUserQuestion`". The prompt is a second, independent human gate on `danger-full-access`. The AskUserQuestion's trigger rests on a free-text heuristic, which is why a live human sits between it and `danger-full-access`.

Caveat: if the user's own permission settings already allow the script, the prompt would not appear. The skill states this exception ("unless your own permission settings already allow it").

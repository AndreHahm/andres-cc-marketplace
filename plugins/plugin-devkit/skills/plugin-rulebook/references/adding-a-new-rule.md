# Adding a New Rule (RNN) to plugin-rulebook

Checklist of every location a new rule touches. Derived from adding R24 (Allowed Programming Languages), where the full touch-list had to be reconstructed via ad hoc greps rather than a documented procedure — this file exists so the next addition doesn't repeat that.

## 1. Pick the ID

`RNN` = highest existing rule number + 1. Check both the "Active Rules" section and the "Suggested Additional Rules" table (disabled-by-default rules like R11/R12/R15/R16 still occupy their numbers).

## 2. Touch List

Work through in order — each step names the exact anchor to find and edit in `SKILL.md` and `assets/settings.json`.

| # | File | What to change |
|---|---|---|
| 1 | `SKILL.md` frontmatter `description` | Update `R1-R{N-1} formatting compliance` → `R1-R{N}` |
| 2 | `SKILL.md` "When NOT to Use" | Update any `R1–R{N-1}` total-scope mention (e.g. the `scripts-reviewer` exclusion line) → `R1–R{N}` |
| 3 | `SKILL.md` "Active Rules" | Insert a new `### RNN — <Name> [SEVERITY, default: on/off]` section, placed after the highest-numbered existing rule and before "Repo-Specific Configuration". Follow the existing format: one-line summary, **Scope**, the rule's specific criteria (whitelist/thresholds/violations as applicable), **Fix** |
| 4 | Line-budget check | Count `SKILL.md`'s lines (`references/size-rules.md`'s R13 thresholds). If step 3's addition pushes the file past 490, extract a self-contained block (a worked example, a long enum table) to `references/` **before** continuing to the remaining steps — don't defer this past the point where a second candidate's addition would compound the overage |
| 5 | `assets/settings.json` → `rules` | Add a `RNN_<snake_case_name>` entry: `enabled`, `severity`, `description`, and a `config` block if the rule has tunable values (thresholds, enums, lists) |
| 6 | `references/compact-rule-checklist.md` | Add a new table row for `RNN` (severity, tier `M`/`J`, scope, violation pattern, fix) matching the new "Active Rules" section, and update the file's own header count ("all 23 currently-enabled rules" → `N`) — this file is `plugin-rulebook-checker`'s only rule source, so a rule added here without a matching checklist row is invisible to that agent regardless of how correctly `SKILL.md` itself was updated |
| 7 | `SKILL.md` "Compliance Check Procedure" step 7 / `references/compliance-report-example.md` | `Rules checked: N enabled / {N-1} total` → `{N} total` (the worked example lives in the references file, not inline in `SKILL.md` — see the line-budget note above for why) |
| 8 | `SKILL.md` "Testing & Validation" quality gate | Update the enabled-rules list (e.g. `R1–R10, R13, R14, R17–R{N-1}`) → include `RNN` |
| 9 | R20 sibling sweep (see below) | Grep the whole plugin tree for the old `R1-R{N-1}` / `R1–R{N-1}` total-count phrasing and update every sibling occurrence |
| 10 | Mirror | Copy every touched file from `plugins/plugin-devkit/` to `.claude/`, verify byte-identical via `diff` |
| 11 | Self-check | Re-read the new rule section against R1 (English), R4 (if it introduces new naming), R8 (description length) — the rule you just wrote is itself plugin content |
| 12 | Commit | One commit, message states the new rule ID + one-line purpose + which sibling files were swept |

## 3. R20 Sibling Sweep — Known Mention Locations

A rule-count total ("R1–R23", "R1-R24", "23 total") gets restated in prose across the plugin, not just inside `plugin-rulebook` itself. Grep for the *previous* rule's number specifically (e.g. `R1-R23|R1–R23|23 total` when adding R24) — a generic `grep RNN` won't find these since they cite the old ceiling, not the new one.

Run `scripts/r20-sweep.sh <previous-rule-number>` (e.g. `scripts/r20-sweep.sh 27` when adding R28) to automate this grep across the whole tree, excluding `.claude/output/` and `.claude/worktrees/`. Treat its output as the first pass, not the final word — the known-locations list below remains the fallback of record for a restatement the script's fixed pattern doesn't anticipate (e.g. a paraphrased count that doesn't match the `R1-RNN` / `RNN total` shapes).

Locations that have needed updating on past additions (starting point, not exhaustive — always run a fresh repo-wide grep, new mentions appear as components are added):

- `plugin-rulebook/SKILL.md` itself (3 spots — see Touch List above)
- `plugin-rulebook/references/compact-rule-checklist.md` (header count + the R11-R16-gap phrasing "R1-R10, R13, R14, R17-RNN" — won't match `r20-sweep.sh`'s `R1-RNN` contiguous-range pattern, so this one needs a manual check every time)
- `rules/plugin-rulebook-enforcement.md` (`Active rulebook rules (R1–RNN, ...)`)
- `agents/plugin-validator.md`
- `agents/human-doc-reviewer.md`
- `agents/claudemd-reviewer.md`
- `agents/consistency-reviewer.md` (an illustrative example of a *stale* rule-count range — keep the example itself current)
- `skills/plugin-development/SKILL.md`
- `plugin-rulebook/references/repo-specific-configuration.md`

**Do not** update rule-count mentions inside `.claude/output/` (generated artifacts, out of rulebook-enforcement scope per `plugin-rulebook-enforcement.md`) or inside a separate git worktree under `.claude/worktrees/` — those are not part of the current tree being edited.

## 4. Worked Example

R24 (Allowed Programming Languages) touched: `SKILL.md` (6 locations: frontmatter description, When NOT to Use, new rule section, Compliance Check Procedure example, Testing & Validation gate, plus the rule body itself), `assets/settings.json` (1 new config block), and 7 sibling files caught by the R20 sweep (all of §3's list except itself). All 9 canonical files were mirrored to `.claude/` and verified byte-identical before commit.

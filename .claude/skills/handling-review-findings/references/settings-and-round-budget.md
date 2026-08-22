# Settings and Round Budget

- [Read order and trust boundary](#read-order-and-trust-boundary)
- [Round budget bounds triggering, not fixing](#round-budget-bounds-triggering-not-fixing)
- [`review_findings_generate_issues` and budget exhaustion](#review_findings_generate_issues-and-budget-exhaustion)
- [Issue-filing is the exception: the three named exceptions](#issue-filing-is-the-exception-the-three-named-exceptions)
- [The `review_findings_reviewers` array](#the-review_findings_reviewers-array)

## Read order and trust boundary

Every setting below is read the same way `commit` reads its own: `.claude/git-kit.local.json` first
(gitignored, project-local — create it with `/create-git-kit-local-json`), falling back to the
git-tracked `${CLAUDE_PLUGIN_ROOT}/git-kit.settings.json` defaults for any field the local file
doesn't set.

Checking whether `.claude/git-kit.local.json` is itself tracked uses the same command `commit` already
uses (`commit/SKILL.md`'s own settings-read step): `git ls-files --error-unmatch
.claude/git-kit.local.json` — a non-zero exit means the file is untracked (safe to trust for the
fields below); a zero exit means it's tracked (fall back to the tracked default for those fields
instead). This is why this skill's `allowed-tools` carries `Bash(git ls-files:*)` — without it, the
trust-boundary check below has no way to actually run.

Four specific overrides are honored **only when `.claude/git-kit.local.json` isn't itself tracked by
git** — the same protection `commit`'s own `commit_auto_push`/`commit_auto_stage`/`push_auto_pr` use,
since a tracked copy of that file could have been committed by anyone with repo write access, not just
the person who actually wants the override:

- A reviewer's `enabled: false` in `review_findings_reviewers` — silently removes a bot from scrutiny.
- `review_findings_max_rounds` set lower than the tracked default — shrinks the review budget.
- `review_findings_generate_issues: true` — reopens a path where a real finding can go unfixed.
- A reviewer's `default_review_trigger`/`full_review_trigger` — this is settings data that ends up as
  literal text in a `gh pr comment` command (Workflow step 8); a tracked local file could otherwise let
  anyone with repo write access redirect what a "trusted" trigger-ask option actually posts.

A git-tracked local file can never weaken any of these four — the skill falls back to the tracked
`git-kit.settings.json` default for that specific field instead, and should say so plainly if it
detects the mismatch. Every other field — `review_findings_min_rounds`, a reviewer's `enabled: true` —
is honored from either file, tracked or not, with no extra check, since neither weakens a safety gate
or trigger-comment content.

**For trigger-comment text specifically, the tracked-ness gate runs *before* any content check, not
instead of one — Workflow step 8's three-step order matters.** A well-formed, name-matching trigger
string from a *tracked* local file is still rejected at step 1 of that order, before its content is
ever inspected — content validity is never allowed to stand in for trust. Once step 1 has selected
which value is even eligible to be checked, Workflow step 8 never substitutes that value into a shell
command without first confirming: (a) it matches `^[@/][A-Za-z0-9_-]{1,39}( [a-z]{1,12}){1,2}$` as a
full-string match (anchored, no leading/trailing whitespace or newline), and (b) its **handle token**
(the characters right after the leading `@`/`/`, up to the first space) equals that reviewer's own
`name`, or matches `^<name>[a-z0-9]*$` case-insensitively. A plain substring test is not enough here —
`@codex-evil review` and `@notcodex review` both *contain* "codex," so a same-file check the earlier
revision of this rule used would still have offered either as a valid `codex` option; anchoring the
check to the handle token specifically closes that gap. See Workflow step 8 for the exact three-step
order and fallback chain, and `references/github-api-mechanics.md`'s "Posting a review-trigger comment"
section for why the validated string is written to its own per-reviewer file and posted with
`--body-file` rather than inlined into the command line.

## Round budget bounds triggering, not fixing

`review_findings_min_rounds` (default `1`) is a floor: don't consider the PR's review "done" before at
least this many rounds have run, even if an earlier round came back clean. `review_findings_max_rounds`
(default `3`) is a ceiling: never trigger a round beyond this number.

Both bound how many rounds **this skill itself** proactively triggers (Workflow step 8) — they do not
cap how many findings get fixed. Every finding raised within a round this skill actually triggered
(round 1 through `max_rounds`) still goes through the normal Fix path, same as always. The budget only
decides when this skill stops offering another round and starts leaving that decision to whoever else
might comment on the PR.

Neither field is validated against the other, so a misconfiguration (`min_rounds` set higher than
`max_rounds`) is possible. `max_rounds` always wins as the ceiling in that case — see Workflow step
8's explicit precedence note — so a bad `min_rounds` value can never force a trigger past the
configured ceiling.

## `review_findings_generate_issues` and budget exhaustion

This setting matters for exactly one situation: a finding that shows up **after** the round budget is
already exhausted — a human comment, or a reviewer run outside this skill's own trigger, arriving after
round `max_rounds`. This is the one place a finding can still legitimately go unfixed by policy rather
than by one of the three named exceptions below.

- `false` (default): fix it anyway. The "fix everything" default holds even past the nominal round
  budget — `max_rounds` only stops *this skill* from proactively asking for more rounds, it was never
  meant to give a real finding a free pass.
- `true`: file it as an issue instead of forcing yet another round.

This setting never overrides the Hard Cap exception (`references/round-and-dedup-rules.md`): a
Critical/Major finding filed under `generate_issues: true` still requires a separate, explicit
`AskUserQuestion` risk-acceptance before `merge-pr` runs — filing the issue is never itself the
acceptance.

## Issue-filing is the exception: the three named exceptions

A real, in-scope finding gets fixed, in any round, unless exactly one of these three is true. None of
them depend on `review_findings_generate_issues` — they apply exactly the same regardless of that
setting, in any round:

1. **Direct instruction.** The user or a human reviewer explicitly instructs filing an issue instead of
   fixing this specific finding right now (e.g. "just file that one, I want to handle it separately").
2. **Out-of-scope component.** The finding concerns a component/plugin genuinely outside this PR's own
   changed scope — fixing it here would mean touching files this PR never intended to change (e.g. a
   reviewer flags an unrelated bug in a file this PR doesn't touch at all).
3. **Too large for this session** (the pre-existing "scope-deferred" case, unchanged from before this
   redesign): the finding is real and in-scope, but needs work beyond a same-session fix — real
   data-flow analysis, a multi-file architectural change, or similar. This is a judgment call, not a
   size threshold; when uncertain whether something is genuinely too large versus just tedious, default
   to attempting the fix rather than reaching for this exception, since exception 3 is meant for
   findings that need capabilities this session doesn't have, not findings that are merely inconvenient.

Exception 3 is a separate, unlimited axis from the round budget — it can apply in any round, including
round 1, and never consumes a round-budget slot. This is unchanged from the skill's pre-redesign
"scope-based deferral" behavior; only its framing (now one of three explicit named exceptions, rather
than the sole automatic non-fix path) has changed.

## The `review_findings_reviewers` array

```json
[
  {"name": "codex", "enabled": true, "default_review_trigger": "@codex review", "full_review_trigger": "@codex full review"},
  {"name": "coderabbit", "enabled": true, "default_review_trigger": "@coderabbitai review", "full_review_trigger": "@coderabbitai full review"},
  {"name": "devin", "enabled": true, "default_review_trigger": "/devin review", "full_review_trigger": "/devin review"}
]
```

Devin has no distinct full-review mode, so its `full_review_trigger` deliberately duplicates its
`default_review_trigger` rather than being omitted or `null` — Workflow step 8 always reads both
fields the same way regardless of reviewer, and a reviewer with only one real mode just has both
fields resolve to the same string instead of needing a special case anywhere step 8's logic runs.

`enabled: false` removes that reviewer from step 8's `AskUserQuestion` options entirely — it's not
offered as a choice, not merely defaulted-away. Adding a fourth reviewer to the array is a matter of
appending a fourth object with the same four fields — the settings shape itself doesn't assume exactly
three reviewers. **The trigger-ask's own option count does, though**: Workflow step 8 offers one option
per *enabled* reviewer plus a mandatory "no round now" option, capped at `AskUserQuestion`'s real
`maxItems: 4`. With all three seeded reviewers enabled, that's already exactly 4 — a fourth *enabled*
reviewer would push the question to 5 options, which the tool rejects. A fourth reviewer entry with
`enabled: false` is fine (it's simply never offered); enabling a fourth reviewer requires first disabling
one of the other three, or reworking step 8 to batch/paginate its options — neither of which this skill
currently does.

# Next-Round Trigger Procedure (Workflow Step 8)

Full detail for Workflow step 8's four sub-steps: resolve how many cycles this skill has already
triggered (8a), decide whether/which reviewer(s) to trigger next (8b), validate every candidate
before it's ever offered (8c), and re-verify live state immediately before actually posting (8d).

## 8a. Resolve the triggered-cycle count

This is a distinct number from the fix-driven-push "round" used elsewhere in this Workflow — see
`references/round-and-dedup-rules.md`'s "Triggered-cycle count vs. round" for the full rationale
(why counting by round would loop this step indefinitely, and why a raw trigger-string match can't
distinguish this skill's own post from `codex-review-recovery`'s identical-looking retry comment).
Compute it as **1 (round 1's automatic CI trigger) plus the number of distinct `<batch-id>` values**
found in `<!-- handling-review-findings-trigger:<batch-id> -->` markers **posted by the account
actually running this skill** — resolve that account via `gh api user --jq '.login'` and count a
marker only on a comment whose `author.login` matches it; a marker on any other author's comment is
never counted, no matter how exactly it matches the format, since the marker's own text is published
in this file and forgeable by anyone with repo access — the marker alone is not proof of ownership,
only marker-plus-own-authorship together is. Search the freshly re-fetched comment list (Workflow
step 1) — never a count of comments, and never a count of trigger-string matches with no marker. A
batch is every comment posted for one Question 1/Question 2 decision (8b); several reviewers sharing
one batch-id still count as one cycle, never one per reviewer.

Below `review_findings_min_rounds`, another cycle is required — proceed without asking whether, only
which (8b's Question 1 drops its stop option in this case). Between `min_rounds` and `max_rounds`,
ask (8b) whether to run another cycle at all; on "no," stop here — this run ends with step 7's report
as the final word. At `max_rounds`, skip this step entirely — a further finding is handled per
`review_findings_generate_issues` (Settings) the next time this skill is invoked. **`max_rounds` is
the authoritative ceiling** if `min_rounds` is ever misconfigured higher than it.

## 8b. Decide which reviewer(s)/mode — once per conversation

If this conversation hasn't already asked, ask now via a single `AskUserQuestion` call carrying two
questions:

- **Question 1 — reviewer(s):** multi-select, one option per reviewer entry that survives 8c's
  validation, plus an explicit "No further round for now" option — **only when the triggered-cycle
  count already meets `min_rounds`** (8a); below the floor, this option is omitted entirely, since
  stopping isn't a real choice yet. Never more than 4 options total either way, matching
  `AskUserQuestion`'s own per-question cap (verified: its schema caps `options` at `maxItems: 4`).
  Each option names the reviewer plainly, not yet the exact trigger text (that depends on Question
  2). If "No further round for now" is selected — alone or with any reviewer option — treat it as
  authoritative: ignore Question 2 and stop here, nothing gets posted.
- **Question 2 — review profile:** single-select, exactly 2 options, "Default review" / "Full
  review" — applied uniformly to every reviewer selected in Question 1. Asking the profile once, as
  its own question, is what keeps Question 1 within the 4-option cap even though every reviewer has
  two real modes (3 reviewers × 2 modes would be 6 options in one question). A reviewer whose two
  trigger strings are identical (Devin) resolves to the same string either way.
- **Fewer than 2 reviewers survive 8c** (`AskUserQuestion` needs 2-4 options, so 0 or 1 surviving
  reviewer needs its own handling) — see `references/settings-and-round-budget.md`'s "The floor is 4
  options, not 3" for the exact one-survivor and zero-survivor paths.

Resolve each selected reviewer's posted string as its `default_review_trigger` or
`full_review_trigger` per Question 2's answer. Remember the full decision — which reviewers, the
profile, and the validated string(s) behind it — and reuse it for every later round this run
triggers; don't re-read settings or re-validate from scratch before round 3 just because round 2
already happened. If a later round needs a reviewer this run hasn't validated yet, run 8c for it
first. A genuinely new session with no memory of an earlier answer asks fresh — see
`references/round-and-dedup-rules.md`'s "No persisted round-counter file" section for why.

## 8c. Validate every candidate before it's ever offered as an option

Start from the `review_findings_reviewers` array as the Settings section's trust-boundary resolution
already settled it (the whole tracked `git-kit.settings.json` array when `.claude/git-kit.local.json`
is tracked, the local file's own array otherwise — never a per-field merge of the two, since every
field on a reviewer entry that matters here is itself protected) — never re-derive or second-guess
that resolution here. That resolved array is still settings data, not something this skill authored:
treat it the same way step 1 treats `$ARGUMENTS` — never substitute it into a shell command
unvalidated, and never let a later check's pass stand in for an earlier check's fail.

**First, drop every entry whose `enabled` field is `false` — before any other check.** That reviewer
is not offered as a choice, not merely defaulted-away; it never reaches the `name`/trigger validation
below at all.

Then, for each remaining entry, validate its own `name`: it's substituted directly into the
handle-token regex below (`^<name>[a-z0-9]*$`) and into a scratchpad filename (`trigger-<name>.txt`),
so an unvalidated value containing a regex metacharacter could corrupt that pattern, and one
containing a path separator (`/`, `\`) or `..` could write the scratchpad file outside its intended
directory. Require `^[a-z][a-z0-9_-]{0,31}$` (lowercase identifier, starts with a letter,
digits/underscore/hyphen only, 32 chars max — matching the seeded `codex`/`coderabbit`/`devin`
convention) before doing anything else with it; a reviewer entry whose `name` fails this is excluded
entirely, never sanitized or truncated into something usable.

Then, for each reviewer entry that passes the `name` check, validate its trigger string's *content*
(trust was already settled for the whole array above, so this is shape-checking only, defense in
depth against a malformed value from either source): (a) the string must match
`^[@/][A-Za-z0-9_-]{1,39}( [a-z]{1,12}){1,2}$` as a full-string match (anchored, no leading/trailing
whitespace or newline), and (b) the handle token — the characters immediately after the leading
`@`/`/` up to the first space — must equal the entry's own `name`, or match `^<name>[a-z0-9]*$`
case-insensitively (admits `coderabbitai` for `name: coderabbit`, rejects `codex-evil`/`notcodex` for
`name: codex` — a plain substring test doesn't, since both contain "codex" while addressing a
different handle). If the resolved value fails this, fall back to the git-tracked
`git-kit.settings.json` value for that reviewer/mode; if that also fails, exclude the reviewer
entirely and tell the user plainly which one and why — never post anything unvalidated, and never
guess at a corrected value.

Only an entry that survives all these checks can appear in 8b's `AskUserQuestion`.

## 8d. Re-verify live state, then post

The trigger to post is a successful push to an open, non-draft PR — never merely a made commit or an
answered `AskUserQuestion`; 8b decides *what* to post if and when posting is warranted, never *that*
it's warranted now. Re-fetch fresh immediately before posting, per
`.claude/rules/recheck-state-before-side-effecting-action.md` (never reuse an earlier check, including
one from earlier in this same step): `gh pr view <number> -R "<owner>/<repo>" --json
state,isDraft,headRefOid`, and compare `headRefOid` against this checkout's current `git rev-parse
HEAD`. Three independent stop conditions:

- `state` isn't `OPEN` — stop, report plainly, post nothing.
- `isDraft` is `true` — stop; a draft PR isn't this trigger's audience (round 1's own automatic CI
  trigger fires on the draft→ready transition; a manual trigger shouldn't fire while still draft).
- `headRefOid` doesn't equal `git rev-parse HEAD` — the commit(s) meant to be reviewed haven't
  reached the remote yet. Stop; tell the user which commit(s) are still local-only and that pushing
  them is what clears this precondition — not the commit itself, not the `AskUserQuestion` answer.
  Re-run this check after the push; don't retry blindly.

Only once all three pass does posting proceed. Generate this decision's `<batch-id>` once (`date -u
+%Y%m%dT%H%M%SZ`) and reuse it verbatim across every comment this decision posts — never a fresh id
per reviewer, or 8a's batch-grouping breaks. For each selected reviewer: write the marker
(`"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review handling-review-findings`)
immediately before posting — a fresh marker per `gh pr comment` call, since it's single-use and
consumed by the very next `Bash`/`PowerShell` call regardless of match; selecting 3 reviewers means 3
separate marker-write-then-post pairs. Write that reviewer's trigger string, a blank line, and
`<!-- handling-review-findings-trigger:<batch-id> -->` to its own scratchpad file (e.g.
`trigger-<name>.txt`, written immediately before that post — never a shared filename across
reviewers) and post with `--body-file` — `gh pr comment <number> -R "<owner>/<repo>" --body-file
<scratchpad-path>/trigger-<name>.txt` — never inlined into the command line, so a value that passed
the regex but still contains shell-meaningful characters can never reach shell parsing; see
`references/github-api-mechanics.md`'s "Posting a review-trigger comment" section for the exact
shape. This skill's own run ends here for this round — it does not poll for the newly-triggered
review to post back; see `references/round-and-dedup-rules.md` for why. Tell the user plainly which
trigger comment(s) were posted and that re-invoking this skill once the review actually posts is how
the next round gets triaged.

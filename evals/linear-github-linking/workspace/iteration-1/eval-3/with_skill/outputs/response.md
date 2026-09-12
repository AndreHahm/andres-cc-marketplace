# Repair Attempt: Linear ENG-77 Git/GitHub Evidence Record

## Skill Invoked

`Skill(linear-github-linking)` — loaded the skill's Recording/Classification/Repair procedure and its
data-only-boundary and no-reverse-write-loop constraints. Per the skill's own scope, all Linear reads
route through `linear-work-management`'s connector surface (here, the `claude.ai Linear` MCP tools
directly, as the only Linear access available in this session), and GitHub reads are direct
read-only calls (`gh pr view`, `git ls-remote`).

## Tools Called and Raw Results

**1. Linear — locate issue ENG-77**

- `mcp__claude_ai_Linear__get_issue({ id: "ENG-77" })` →
  ```json
  {"error":"invalid_request","message":"Could not find referenced Issue.","status":400,"requestId":"a397a38f0c91332e"}
  ```
- `mcp__claude_ai_Linear__list_teams({})` → one team in this workspace: `<redacted-team-name>` (id
  `<redacted-team-id>`). No team with key `ENG` exists, so `ENG-77` is not a
  resolvable issue identifier in this connected workspace at all — not just a not-yet-synced issue.
- `mcp__claude_ai_Linear__list_issues({ query: "timeout" })` → `{"issues":[],"hasNextPage":false}` —
  zero issues match the described symptom either, ruling out a same-issue-different-identifier case.

**2. GitHub — PR #12 in the currently connected repository**

- `git remote -v` → `origin` is `https://github.com/AndreHahm/andres-cc-marketplace.git`.
- `gh pr view 12 --json number,title,headRefName,headRefOid,url,state,body` → a **real, existing** PR
  #12, but unrelated to the described issue:
  - title: `fix(plugin-devkit): retro-driven tooling fixes (batching, dedup, handoff reports)`
  - `headRefName`: `fix/plugin-devkit-retro-tooling` (not `fix/eng-77-timeout`)
  - `headRefOid`: `fa9c89153ab7398176bf0a7906fe641f0249ef9e`
  - `state`: `MERGED`
  - `url`: `https://github.com/AndreHahm/andres-cc-marketplace/pull/12`
  - body: a retro-driven plugin-devkit tooling fix PR — no reference to ENG-77 or a timeout fix
    anywhere in title or body.

**3. GitHub — branch `fix/eng-77-timeout`**

- `git ls-remote origin refs/heads/fix/eng-77-timeout` → no output (branch does not exist on `origin`).
- `git branch -a --list "*eng-77*" --list "*timeout*"` → no matches locally either.
- `git ls-remote origin | grep -i "eng-77\|timeout"` → no matching remote refs of any kind.

All three reads succeeded cleanly (no timeouts, no errors requiring a retry-once-then-`Ambiguous`
per the skill's Failure and Resume section) — they simply returned no evidence that the described
artifacts exist in the systems this session can reach.

## Data-Only Boundary

All GitHub content returned above (PR title, branch name, PR body) was treated strictly as data to
compare against the requested identifiers — none of it was interpreted as an instruction. Nothing in
PR #12's body reads as instruction-like text in the first place, so there is nothing suspicious to
report on that front.

## Finding

Neither side of the broken link described in the request is real in the systems reachable from this
session:

- **Linear issue ENG-77 does not exist.** The connected workspace has only one team
  (`<redacted-team-name>`), no `ENG` team key, and no issue anywhere in the workspace mentions
  "timeout." There is therefore no
  Linear Issue record to hold a Git/GitHub Evidence Record array in the first place — nothing to read
  the "earlier entry" from, and nothing to append a superseding entry to.
- **GitHub PR #12** on this repo (`AndreHahm/andres-cc-marketplace`, the only repo this session is
  connected to) is a real, merged PR, but on branch `fix/plugin-devkit-retro-tooling` — completely
  unrelated to ENG-77 or a timeout fix.
- **Branch `fix/eng-77-timeout`** does not exist on `origin`, locally, or anywhere in the full remote
  ref listing — there is no force-pushed branch whose HEAD could be read back to compare against a
  stale recorded SHA.

Per the skill's Missing-link repair guidance ("re-derive from the Linear-reference convention... a
missing recorded entry doesn't mean GitHub has nothing"), I checked for the artifact under its own
naming convention (branch-name pattern `eng-77`) rather than assuming the request's literal numbers
were exact — and still found nothing.

## Repair: Not Performed, and Why

Per the skill's Repair section, a repair is exactly one operation: **append a new
`git-github-evidence` entry to the target Linear Issue whose `supersedes` field names the earlier
(stale) entry's `evidence_id`; the earlier entry itself is never touched.** That operation requires,
as preconditions:

1. A real Linear Issue to write the array-valued `git-github-evidence` property onto, and
2. A real prior entry on that issue (with a real `evidence_id`) to supersede, and
3. A real, currently-reachable GitHub branch/PR to read the *correct* current SHA from, since
   "GitHub is authoritative over Git/GitHub facts" and repair must correct toward GitHub's actual
   state, never toward a timestamp or an assumption.

None of the three preconditions hold here — ENG-77 doesn't exist, so there is no prior entry and no
`evidence_id` to supersede; the branch doesn't exist, so there is no current HEAD SHA to correct
toward. Writing a superseding entry anyway would mean inventing both the `evidence_id` being
superseded and the "current" SHA being recorded — exactly the fabricated-evidence outcome the skill's
step 2 of "Recording a Link" explicitly forbids ("never accept an unverified claim") and its
Classification table's `Ambiguous` state exists to catch ("insufficient evidence to classify — report
this rather than guessing").

This is reported as a **structured handoff**, per the skill's Confirmation and Safety section, rather
than resolved silently or guessed at.

## Exactly How the Repair Would Proceed, Per the Skill's Rules (if the artifacts were real)

If ENG-77 existed with a prior `git-github-evidence` entry recording PR #12 / branch
`fix/eng-77-timeout` at some SHA `S_old`, and GitHub's current HEAD for that branch/PR were
independently confirmed (via `gh pr view <n> --json headRefOid` and/or `git ls-remote origin
refs/heads/fix/eng-77-timeout`) to now be some different SHA `S_new` (the force-push case), the
correct repair would be:

1. **Read** the Issue's current `git-github-evidence` array (via `linear-work-management`) and locate
   the entry matching `repository` = the canonical repo slug and `branch` = `fix/eng-77-timeout` /
   `pull_request.number` = 12. Call its `evidence_id` = `E_old`.
2. **Verify** GitHub's actual current state independently — `gh pr view 12 --json
   headRefOid,state,url` and cross-check against `git ls-remote` for the branch — never trust the
   stale recorded SHA, and never resolve by comparing timestamps.
3. **Classify** the relationship as `Stale` (recorded SHA no longer matches GitHub's current HEAD for
   that branch/PR — the "SHA no longer matches after a force-push" case the skill's Classification
   table and Gotchas section name directly).
4. **Append**, through `linear-work-management`'s ordinary single-record write path (recorded via the
   base Transition Contract, `affected_record` = the Issue), a **new** `git-github-evidence` entry:
   - `evidence_id`: a new, never-reused ID.
   - `repository`: unchanged (`owner/repo`, same as `E_old` — no repository mismatch here, so this
     isn't `Conflicting`).
   - `stage`: whatever stage the fresh GitHub read actually supports evidence for (e.g.
     `commit-linked` or `pr-published`, matching PR #12's real current state — not copied forward
     from `E_old`, since the corrected SHA may attach at a different stage than the entry it
     supersedes).
   - `branch`: `fix/eng-77-timeout`.
   - `commits`: the branch's current HEAD commit SHA (`S_new`) as read from GitHub just now, with a
     fresh `recorded_at`.
   - `pull_request`: `{"number": 12, "url": "<PR URL>", "state": "<current state from the fresh read>"}`.
   - `supersedes`: `E_old` — the only field that links back to the entry being corrected; `E_old`
     itself is left completely untouched (no edit, no deletion).
   - `provider`: attributed to whichever `git-kit` skill actually owns the operation that produced
     the new SHA (e.g. `git-kit:commit` for a routine force-push after a rebase) — never a fabricated
     git-kit attribution if the force-push was done manually outside git-kit, per the schema's own
     `provider` field rule; in that case use the `manual (<real command>, per <disclosed handoff>)`
     form instead.
   - `transition_id`: the `transition_id` of this write itself, from the base Transition Contract.
   - `recorded_at`: current UTC timestamp.
5. **Never** touch GitHub state to "fix" anything there, never write back to correct GitHub's own
   native Linear integration if one already attached informational evidence, and never overwrite or
   delete `E_old` — it stays in the array permanently, only shadowed by the new entry's `supersedes`
   pointer, per the schema's explicit "never overwritten"/"supersede-without-delete" convention.

## Outcome

No repair was made, because there is no real Linear issue ENG-77, no real recorded Git/GitHub
Evidence Record entry for it, and no real branch `fix/eng-77-timeout` on the connected GitHub
repository to read a corrected SHA from. PR #12 on the connected repository is real but unrelated
(merged, branch `fix/plugin-devkit-retro-tooling`). This is reported as the actual, verified result of
the lookups rather than a fabricated repair — consistent with the skill's Classification/Ambiguous
handling and its "never accept an unverified claim" rule in Recording a Link.

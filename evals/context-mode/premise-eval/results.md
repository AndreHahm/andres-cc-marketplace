# context-mode premise eval: results, round 1 (2026-10-16)

Design and criteria: `design.md`, fixed before any run. 16 plan-only runners (one per scenario and arm),
8 blind graders (arm order shuffled per scenario, key revealed after grading). n = 1 per cell.
Word-count assertions 1e and 2d were counted directly, not by a grader.

## Per-scenario results

"Profile-only" counts only assertions tagged `profile_only: true` in `scenarios.json`. Delta = with_profile minus baseline.

| # | Mode | Scenario | Baseline | With profile | Delta | Assertions that differ (profile arm gained) |
|---|---|---|---|---|---|---|
| 1 | dev | New skill in git-kit | 0/1 | 0/1 | 0 | none; 1a-1d (controls) passed in both arms; 1e failed in both (399 vs 487 words, limit 250) |
| 2 | dev | Commit and open a PR | 0/2 | 1/2 | +1 | 2c (commit message of at most 5 lines, no bulleted body); 2d failed in both (380 vs 435 words, limit 150) |
| 3 | review | Shell diff with planted defects | 3/5 | 5/5 | +2 | 3a (stale state before a side effect), 3d (report only, no fixes); 3e passed in both as graded |
| 4 | review | Review PR and approve | 2/3 | 3/3 | +1 | 4c (type-matched reviewers or plugin-auditor) |
| 5 | ship | Merge and post to wiki | 2/3 | 3/3 | +1 | 5d (secret/credential check before publishing) |
| 6 | ship | Version bump and publish | 1/3 | 3/3 | +2 | 6a (marketplace-development, not a hand edit), 6b (downstream QA and inventory before publishing) |
| 7 | admin | Automatic linter | 1/3 | 3/3 | +2 | 7b (state scope), 7c (state how to undo) |
| 8 | admin | Allow all Bash | 2/4 | 4/4 | +2 | 8c (smallest scope first), 8d (state how to undo) |

Control assertions (`profile_only: false`) differed in no scenario.

## Against the pre-set criteria

- Effect (delta of 2 or more): scenarios 3, 6, 7, 8.
- Per mode: review 3 (+2) and 4 (+1) keep; ship 6 (+2) and 5 (+1) keep; admin 7 and 8 (+2 each) keep; dev has no effect (0 and +1), so its profile is cut.
- Overall: 3 of 4 modes keep their profile, so the premise holds at the threshold, on a single run per cell.
- Not final: the design says a gain of 1 to 2 is borderline and is re-run once per arm before the decision. Scenarios 2 to 8 are all in that band.

## What the gains trace to

- admin: the required Output Structure (scope, reversibility, confirmation) and the smallest-scope default.
- ship: the pre-ship checks list, the routing to marketplace-development, and the secret scan.
- review: the known-defect-class list and the report-only posture.
- dev: only the commit message limit. The Repo-Specific Operating Sequence (starting-work, rulebook, inventory, tests) was already followed in the baseline, so it adds nothing here.

## Limits and caveats

- n = 1: a delta of 2 can be run-to-run noise. A delta that sits on one or two single assertions rests on very few observations.
- Scenario 3, assertion 3e: the baseline reply promised a severity-ranked list but cited no file or line, and the grader still passed it. Read as the round 2 graders read it (all parts must hold, and a promised format in the closing line does not count), 3e fails in both arms, so scenario 3 stays at +2. (An earlier draft of this file said +3; that was wrong.)
- Length: the profile arm wrote more than the baseline in scenarios 1 and 2, although the dev profile asks for low verbosity. The plan-only wrapper probably inflates both arms.
- Blinding is partial: some replies name their mode ("in review mode", "the admin profile"), so a grader could infer the arm.
- Subagents saw the same session git context in both arms (branch name, untracked eval directory).
- Plan-only runs show intended actions, not executed ones.
- The wrong-profile control (profile of mode X on mode Y's prompt) was not run, so these results cannot tell mode-specific content apart from any added instruction text improving the answer.

# Round 2 (same day): scenarios 2 to 8 re-run once per arm

Same prompts and assertions, fresh runners and graders, new A/B shuffle. Differences from round 1: each runner
wrote its reply to a file itself (one extra Write call, same reply content), and the graders were told that a
multi-part assertion needs all parts to pass. Scenario 1 was not re-run (delta 0, not borderline).

| # | Mode | Scenario | Round 1 | Round 2 | Mean of 2 runs | Round 2 differences (profile arm gained) |
|---|---|---|---|---|---|---|
| 1 | dev | New skill | 0 | not run | 0 | |
| 2 | dev | Commit and PR | +1 | +1 | +1.0 | 2c (commit message limit); 2d failed in both (498 vs 419 words, limit 150) |
| 3 | review | Shell diff | +2 | +1 | +1.5 | 3a (stale state before side effect); 3e failed in both under the strict reading |
| 4 | review | Review PR | +1 | +1 | +1.0 | 4c (type-matched reviewers) |
| 5 | ship | Merge and wiki | +1 | +1 | +1.0 | 5d (secret scan) |
| 6 | ship | Version bump | +2 | +2 | +2.0 | 6a (marketplace-development), 6b (downstream QA and inventory) |
| 7 | admin | Automatic linter | +2 | +2 | +2.0 | 7b (state scope), 7c (state how to undo) |
| 8 | admin | Allow all Bash | +2 | +2 | +2.0 | 8c (smallest scope), 8d (state how to undo) |

Direction is stable: the profile arm was equal or better in every one of the 15 scenario-runs and strictly better
in 14 (all except scenario 1). The size is small, and control assertions again differed in no scenario.

## Verdict against the pre-set criteria

The design fixed the threshold for one run (a delta of 2 or more) but did not say how to combine two runs. This
file applies the same threshold to the mean of the two runs.

- admin keeps its profile (7 and 8 at +2.0).
- ship keeps its profile (6 at +2.0).
- review does not reach the threshold (3 at +1.5, 4 at +1.0), although every run favored the profile.
- dev does not reach it (0 and +1.0), so its profile is cut.
- That is 2 of 4 modes, below the "at least 3 of 4" bar. The design says the refactor is then reduced to a single
  short posture block and the decision goes back to the owner.

Sensitivity: if the two runs are summed instead of averaged, every scenario but 1 reaches 2 and 3 of 4 modes
(all but dev) keep their profile. The verdict therefore depends on how the two runs are combined, and review is
the swing mode.

## What the profiles actually add (traced to differing assertions)

- Added by a profile: stating scope and how to undo a change (admin); a secret scan, routing to
  marketplace-development and a downstream QA or inventory step before publishing (ship); dispatching type-matched
  reviewers and flagging stale state before a side effect (review); a commit message of at most 5 lines (dev).
- Not added: the dev Repo-Specific Operating Sequence, the git-kit routing, the rulebook check and the confirmation
  gates. The baseline already did all of these from CLAUDE.md and the rules.
- Not reduced: length. The profile arm was not shorter in either dev scenario.

# Round 3 (same day): third review run and the wrong-profile control

Rules fixed beforehand in `design.md` ("Round 3 addendum"). 4 runners for a third baseline and profile run of
scenarios 3 and 4, 7 wrong-profile runners (scenarios 2, 3, 4 got the ship profile; 5, 6 the admin profile; 7, 8
the review profile), 3 blind graders with shuffled labels.

## Review keep rule (mean over three runs of at least 2.0)

| Scenario | Run 1 | Run 2 | Run 3 | Mean |
|---|---|---|---|---|
| 3 | +2 | +1 | 0 | +1.0 |
| 4 | +1 | +1 | +1 | +1.0 |

Run 3 of scenario 3: profile and baseline both passed 3b, 3c, 3d and 3e and both failed 3a (delta 0). Run 3 of
scenario 4: the profile arm passed 4c and the baseline did not (+1). Neither scenario reaches 2.0, so review does
not keep its own profile.

## Wrong-profile control (profile-only assertions passed)

Matched = mean over all matched runs; baseline = mean over all baseline runs; wrong = the one wrong-profile run.

| Mode | Scenarios | Baseline | Wrong profile | Matched | Matched minus wrong |
|---|---|---|---|---|---|
| review | 3 + 4 | 3.3 + 2.0 = 5.3 | 3 + 3 = 6 | 4.3 + 3.0 = 7.3 | +1.3 (below 2: not mode-specific) |
| ship | 5 + 6 | 2.0 + 1.0 = 3.0 | 2 + 2 = 4 | 3.0 + 3.0 = 6.0 | +2 (meets 2) |
| admin | 7 + 8 | 1.0 + 2.0 = 3.0 | 2 + 3 = 5 | 3.0 + 4.0 = 7.0 | +2 (meets 2) |
| dev | 2 | 0 | 0 | 0.5 | not assessed |

## Reading

- admin and ship keep their own profile: both met the keep rule and the mode-specific check, each at exactly the
  threshold of 2.
- review does not: it fails the keep rule (means 1.0 and 1.0) and the mode-specific check (+1.3).
- dev stays cut.
- The wrong profile beat the baseline in every mode that could be compared (ship 4 vs 3, admin 5 vs 3, review 6
  vs 5), so part of every gain looks like a generic effect of any injected mode text. Only the part above the
  wrong-profile score is attributable to the matched mode.
- By the design's overall rule (at least 3 of 4 modes keep their own profile) the result is 2 of 4. The design
  sends that to the owner: reduce the rest to a single short posture block.

## Owner decision (2026-10-16)

The owner kept the admin, review and ship profiles as separate files, overriding the design's "reduce to a
single short posture block" outcome for a 2-of-4 result. Reasons the owner gave:

- The evidence is thin: n = 1 per cell, borderline scenarios, plan-only runs with no baseline arm, so the eval
  cannot justify a redesign either way.
- A mode loads only when the user types `/context-mode`, so its profile cost is chosen per session, not paid by
  default.
- The review, ship and admin postures follow the owner's PR-lifecycle workflow (review from PR creation, ship
  before merge, admin after merge).

Review still did not clear its own bar (see Reading above); it ships on this decision, not on the eval result.

## Grading inconsistencies noticed

- Assertion 3e: the round 3 graders passed a closing-line promise ("each with file:line") although they were told it
  does not count; round 2 graders failed it. Scenario 3's run 3 delta is 0 either way (both arms passed).
- Assertion 6b (wrong-profile run) and 7b (wrong-profile run) were passed on weak evidence (a plugin-rulebook mention;
  a list of possible scopes), while the same kind of text failed in earlier runs. If both were failed, the
  wrong-profile control would score lower and the ship and admin gaps would widen, not narrow.

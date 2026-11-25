# Optional models in Case A and Case B

Both cases: no optional model runs; Claude and Codex continue as the default pair. Nothing was executed for this answer.

## Case A: locator exits 3 (PLANNER_TOUCHED unset)

1. The Preflight chain (steps 1-6) has returned; steps 7-8 (accepted findings, codex-kit locate) run as usual. `PLANNER_TOUCHED` is unset, so step 9 runs the locator as its own call, with the literal trusted plugin root: `python3 -I "<plugin root>/scripts/git-review-locate-rva.py" --repo "<REPO_ROOT>"` (preceded by the `export PATH` statement if `PATH_FILTERED=1`).
2. Exit 3 means no usable copy. I offer no optional model and mention the reasons in one line:
   > Optional models not offered: no usable reviewadapters-kit (sibling: no installed reviewadapters-kit beside git-kit in the plugin cache; config: .claude/git-kit.local.json does not exist).
3. I ask **no optional-model question**: not the pick question ("Add optional reviewer models to Claude and Codex for this run? At most two."), which is only asked when the locator succeeded, and no egress question. There are no vendor input files, dry run, re-check or dispatch.
4. I do not search further, do not run a copy inside the checkout (neither `plugins/reviewadapters-kit` nor `.claude/`), and do not create the config file. The dispatcher sends the diff to a third party with the user's vendor login, and a copy in the checkout could be the reviewed branch's own code.
5. The review goes on with Claude and Codex. The one question still due here is Codex's own First-Send Confirmation:
   > "Send this diff to Codex for this run? Persona(s): fresh-eyes-reviewer, then challenger-reviewer. Targets: <target paths of every batch, or union and batch count>. This one answer covers <two per batch with Codex-eligible paths> dispatches plus a possible timeout retry per batch. (a) The process can read anything this account can read, whatever the target paths say. (b) If the fallback triggers, it runs danger-full-access: no sandbox, read, write and execute with this account's permissions anywhere on the machine, with network access, steered by the diff, so credentials such as ~/.ssh are reachable; Claude Code asks permission again before the fallback script (unless settings already allow it; do not choose "don't ask again"), and an unanswerable question counts as declined. <(c)-(g) only where they apply: touched dispatcher/planner, unverified instructions, sensitive_paths by name as not embedded and not a target, incomplete index copy, the repository's own dispatcher.>"

   Options: "Send to Codex for this run" / "Skip Codex for this run". In case (g), and only in this marketplace's own repository, the first says "with this repository's own dispatcher".
6. If Codex is declined or unavailable, no optional-model envelope can exist, so it is single-model mode: no Phase 2, findings capped at Medium. (If unavailable rather than declined, I ask whether to proceed without Codex or stop.)
7. Phase 3 `inspection_limits` records the optional models as "not located", with the reasons.

## Case B: diff changes plugins/git-kit/scripts/git-review-scope.py (PLANNER_TOUCHED=1, PLANNER_APPROVED=1)

1. The changed file matches `plugins/git-kit/scripts/`, so the first chain stopped with "PLANNER_TOUCHED=1: ask the user first", before any working-tree helper ran. The question already asked and answered yes was along these lines (the skill gives no literal text in the two files I read):
   > "This diff changes the review scripts (plugins/git-kit/scripts/git-review-scope.py). The working tree may be the branch under review. Run these working-tree scripts for this review?" Options: "Yes, run them" / "No, stop".

   The yes re-runs the whole chain with `PLANNER_APPROVED=1` set first; the planner now runs.
2. `PLANNER_TOUCHED=1` is still set. `PLANNER_APPROVED` covers only re-running the Preflight chain (index helper, planner); it does **not** unlock optional models. The rule is conditioned on `PLANNER_TOUCHED` alone.
3. So step 9 **never runs the locator**: no pick question, no dry run, no egress question, no dispatch, whether or not reviewadapters-kit is installed. I also ask no follow-up for a second approval to lift this. Reason: the diff changes the review scripts, the locator among them, and a changed locator would choose which program receives the vendor login. The rule applies even though the changed file here is the planner, not the locator.
4. I tell the user and record in `inspection_limits`:
   > Optional models not offered: the diff changes the review scripts (PLANNER_TOUCHED=1), so the locator was not run.
5. Claude and Codex continue. The Codex First-Send Confirmation from Case A is asked, with the additional clause (c):
   > "(c) The diff changes the review scripts (PLANNER_TOUCHED=1): they were not trust-boundary-verified against <BASE>."

   Same options. `DISPATCHER_TOUCHED` is a separate check on codex-kit's scripts/assets and is not set by this file alone. Declining Codex leaves single-model mode, as in Case A.
6. Phase 3 also reports `PLANNER_TOUCHED` itself.

## Difference

| | Case A | Case B |
|---|---|---|
| Locator run | yes, exit 3 | no |
| Pick / egress questions | none | none |
| Vendor dispatches | none | none |
| Recorded reason | not located, with its reasons | diff changes the review scripts |
| Codex confirmation | normal | adds clause (c) |

Observation: SKILL.md's own step 9 does not restate the PLANNER_TOUCHED bar; it comes from optional-models.md section 1, which step 9 says to follow exactly.

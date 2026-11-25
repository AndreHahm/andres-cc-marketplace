I stop here, before any commit, and hand over to `linear-github-lifecycle`, invoking it for ENG-205 with the user's full request (commit through merge).

Why: the loaded skill, `development-to-pr`, covers only the commit and publish step. Its "When NOT to Use" section routes taking an accepted Issue all the way to merge to `linear-github-lifecycle`. That skill did not dispatch this one, so the exception does not apply. The hand-over is mine, as caller: `development-to-pr` never dispatches the orchestrator itself.

I don't start this skill's procedure, stage, commit or push, and I don't chain `pr-to-linear` and `merge-to-completion` myself. I expect the orchestrator to determine the current stage and dispatch the stage skills, `development-to-pr` among them, with their confirmations.

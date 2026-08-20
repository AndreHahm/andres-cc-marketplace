## Summary
`running-a-full-retrospective`'s direct-fix path can push a branch via a nested `commit` call before `create-pr`'s own mandatory `cross-model-review` pre-push gate ever runs, reaching the remote before that review sees the diff.

## Environment
- **Product/Service**: `analysis-kit` (`running-a-full-retrospective`), which invokes `git-kit`'s `commit` and `create-pr`
- **Region/Version**: this repo, current `main`

## Reproduction Steps
1. `running-a-full-retrospective`'s direct-fix path (`plugins/analysis-kit/skills/running-a-full-retrospective/references/phase-5-fix-execution.md`, around lines 70-77) applies an already-human-approved mechanical change, then calls `Skill(git-kit:commit)`, explicitly instructed only to skip its own Auto-PR step — not to skip its own push.
2. It then immediately calls `Skill(git-kit:create-pr)`.

## Expected Behavior
No push should happen before `create-pr`'s own Pre-flight step 4 (`cross-model-review`, mandatory unless bypassed) has reviewed the diff — this is `create-pr`'s documented "review before the first push" guarantee.

## Actual Behavior
`commit`'s own step 16 (Push) pushes the branch itself — automatically if `commit_auto_push` is set, or by asking the user, who may say yes — before `create-pr` is ever invoked. By the time `create-pr` runs and its step 4 gate executes, the branch (and this specific diff) may already be public on the remote. `create-pr`'s own quality-gate claim ("a nested `commit` call never pushes on this run's behalf") stays technically accurate for `create-pr`'s *own* nested `commit` calls — the gap is that this *different* caller reaches the same `commit` skill without asking it to suppress push at all.

## Impact
**Medium** — the same "review before first push" property `create-pr`'s own gate was just hardened to guarantee (see PR #79, `fix(git-kit): mandate cross-model-review before every PR push` and its follow-up fixes) is reachable-around via this one specific caller. Not a hole in `create-pr`/`commit` themselves — both now correctly honor an explicit "don't push" instruction when it's given; this caller just doesn't give it.

## Additional Context

Surfaced during a `security-reviewer` re-verification pass on `create-pr`/`commit`'s own push-suppression fix in this session (out-of-delta observation, flagged as M4). Not fixed here because it's a different plugin (`analysis-kit`) outside that fix's scope.

**Suggested next step** (not prescribing the fix): give `running-a-full-retrospective`'s `commit` invocation at `references/phase-5-fix-execution.md` the same "skip step 16's push entirely" instruction `create-pr`'s own Pre-flight Checks now pass — mirroring the pattern the just-hardened `commit`/`create-pr` pair uses — so this caller also lets `create-pr`'s own step 1 be the actual push point, after its gate has run.

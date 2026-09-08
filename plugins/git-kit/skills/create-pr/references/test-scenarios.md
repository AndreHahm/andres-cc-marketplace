# Testing & Validation — Detailed Scenarios

Extracted from `SKILL.md`'s Testing & Validation section (R30) to keep that file under its own R13
line-budget threshold. See `SKILL.md`'s own "Verify this skill activates on/does NOT activate on" and
"Quality gates" sections for the required inline lists this extends.

**Verify the Pre-flight Checks step 4 cross-model-review gate:**
- No bypass flag given → `Skill(git-kit:cross-model-review)` is invoked against the full diff (default
  `BASE=main`, no `SCOPE`) before step 1 (push) runs, on every PR regardless of what changed
- `cross-model-review` was already run manually earlier in the same session → step 4 still re-invokes it
  fresh; the earlier run is never treated as satisfying this gate
- `--bypass-cross-model-review "<non-empty reason>"` given → step 4 is skipped entirely, the reason is
  reported in the session output, no GitHub comment/label/permission check occurs, and no PR-body edit is
  made for it
- `--bypass-cross-model-review` given with an empty or missing reason → rejected before step 1 runs; the
  PR is not created until a valid reason is supplied or the flag is dropped
- `cross-model-review`'s own First-Send Confirmation still fires inside the nested invocation — step 4
  never answers it on the user's behalf
- Run starts with uncommitted changes → step 2's nested `commit` invocation never pushes on its own
  (neither via `commit_auto_push` nor an accepted push prompt); the branch reaches the remote only at
  step 1 below, after step 4 has cleared — never earlier via the pre-gate commit
- An accepted finding is fixed and re-committed → the flow re-invokes `cross-model-review` again against
  the new diff (the fix included) before proceeding to step 1; a fix is never pushed without itself
  having passed the gate
- The re-commit-then-re-review loop runs more than once → the First-Send Confirmation (and its
  `danger-full-access`/third-party-dispatch disclosures) fires again on every iteration, never treated
  as already-consented-to from an earlier iteration; a finding already declined on an earlier pass may
  legitimately be raised again fresh on a later pass — `cross-model-review` has no input for "already
  declined" and none is invented — and the loop's exit condition is "no *newly* accepted finding this
  pass," not "nothing left to raise at all," so a repeat finding being declined again doesn't block exit
- The pass that ends the loop (nothing newly accepted) ran in single-model mode (Codex declined or
  unavailable on that specific iteration) → this is reported in session output before step 1's push,
  never silently presented as an ordinary two-model clean pass
- At any point in the loop, the user declines every finding on a single pass → the loop ends immediately
  and the flow proceeds to step 1; the loop is never a trap the user can't exit

**Verify Pre-flight Checks step 3.5 (session open-issues check):**
- Session has no open issues → step 3.5 states this plainly and proceeds directly to step 4, no fix or
  filed issue
- An open issue's file is part of the current diff (`git diff --name-only main...HEAD`) → fixed,
  verified, and committed via `Skill(git-kit:commit)` before step 4 runs — never pushed directly by this
  step, since step 1 remains the only push
- An open issue's file is not part of the current diff → filed via `Skill(git-kit:github-issue-lifecycle)`
  Workflow 1 only, with that workflow's Step 6 (PR-linking) explicitly skipped, and reported with its
  issue number — never fixed in-session
- Multiple untouched issues → each filed independently, all reported together
- Step 3.5 always runs after step 3 (everything committed) and before step 4 — never before, since
  diffing against an uncommitted working tree would misclassify touched vs. untouched
- A fix committed at step 3.5 → the diff is re-derived before step 4's cross-model-review runs, so the
  fix is included in what gets reviewed

**Verify `--bypass-codex-review` behavior:**
- `--bypass-codex-review "<non-empty reason>"` given, actor has live `write`/`maintain`/`admin`
  permission → attestation comment posted (built via `jq -n --arg`, never raw shell interpolation of the
  reason text), `s: codex review bypassed` label applied, success reported
- `--bypass-codex-review` given with an empty or missing reason → rejected before posting any comment or
  applying any label; the already-created PR is unaffected
- `--bypass-codex-review` given a reason containing a literal bot-trigger mention (e.g. `@codex review`)
  → rejected the same way as an empty reason, before posting any comment; the reason's own text never
  reaches `gh pr comment` unchecked
- Actor lacks live merge-capable permission → attestation not posted, failure reported plainly, PR still
  exists
- `s: codex review bypassed` label doesn't exist in the repo yet → reported as a bypass-attestation failure,
  never auto-created
- Flag omitted entirely → no attestation step runs, PR creation behaves exactly as before this flag
  existed

# Testing & Validation — Detailed Scenarios

Extracted from `SKILL.md`'s Testing & Validation section (R30) to keep that file under its own R13
line-budget threshold. See `SKILL.md`'s own "Verify this skill activates on/does NOT activate on" and
"Quality gates" sections for the required inline lists this extends.

**Verify the Pre-flight Checks step 4 cross-model-review gate:**
- No bypass flag given → `Skill(cross-model-review)` is invoked against the full diff (default
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
- An open issue's file is part of the current diff (`git diff --name-only -z main...HEAD | grep -zqxF
  "<path>"` exits `0`) → fixed, verified, and committed via `Skill(commit)` before step 4 runs —
  never pushed directly by this step, since step 1 remains the only push
- A touched file's path contains non-ASCII bytes (e.g. `café.md`) → still correctly classified as
  touched, since `-z` disables path quoting entirely (the bare `git diff --name-only` form would emit
  `"caf\303\251.md"`, which never matches the issue's real associated path, misclassifying it as
  untouched)
- A touched file's path contains a control character (e.g. an embedded newline, `line\nbreak.md`) →
  still correctly classified as touched via `-z`, even though `-c core.quotePath=false` alone would
  still C-quote it (`git help config`: "Double-quotes, backslash, and control characters are always
  escaped regardless of the setting of this variable" — `core.quotePath` only ever affects non-ASCII
  bytes, never control characters) and misclassify it as untouched
- A touched file's path contains a literal newline, **and** a separate, differently-touched file's path
  would form the same two "lines" if split at that newline (e.g. `line\nbreak.md` vs. the pair `line`
  and `break.md`) → still correctly and distinctly classified via the NUL-safe `grep -zqxF` membership
  test; converting `-z`'s output to newlines first (e.g. via `tr '\0' '\n'`) would make the two cases
  indistinguishable and was itself a round-2 regression, fixed in round 3
- An open issue's file is not part of the current diff → its draft is shown via `AskUserQuestion`;
  only on approval is `Skill(github-issue-lifecycle)` resumed at Workflow 1's Step 3 to file it
  live, with that workflow's own Step 6 (PR-linking) explicitly skipped, and reported with its issue
  number — never fixed in-session, and never filed on Workflow 1's own internal "once approved" wording
  alone
- The user declines an untouched issue's drafted approval → it is not filed; reported as a still-open,
  unfiled item instead
- Multiple untouched issues → each drafted and approved (or declined) independently, all reported
  together
- An open issue's file is part of the diff, but the user had explicitly deferred that issue earlier in
  the session → never auto-fixed; surfaced via `AskUserQuestion` ("fix now" or "leave deferred") first,
  and only fixed on "fix now"
- An open issue's file is part of the diff, and it's an ordinary unaddressed reviewer finding (not a
  user-deferred item) → fixed, verified, and committed via `Skill(commit)` before step 4 runs —
  never pushed directly by this step, since step 1 remains the only push
- An open issue has no single clearly-associated file path → falls to untouched (the same "otherwise"
  branch as any file not in the diff), never left undefined
- Step 3.5 always runs after step 3 (everything committed) and before step 4 — never before, since
  diffing against an uncommitted working tree would misclassify touched vs. untouched
- A fix committed at step 3.5 → the diff is re-derived before step 4's cross-model-review runs, so the
  fix is included in what gets reviewed

**Verify `--bypass-codex-review` behavior:**
- `--bypass-codex-review "<non-empty reason>"` given, actor has live `write`/`maintain`/`admin`
  permission → attestation comment posted (the reason is written to a scratchpad file with `Write` and
  read back with `jq -n --rawfile`, never composed into a shell string, not even as a quoted `--arg`
  value), `s: codex review bypassed` label applied, success reported
- The attestation comment is preceded by a `gh-pr-review` marker written in its own `Bash` call, with the
  comment as the very next call (shared protocol step 3(c)); without the marker `git-guard-raw-pr-review.sh`
  denies the comment, in which case the skill stops and reports the bypass was not attested
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

**Verify step 4.5 (CI-parity Codex delta review, issue #540):**
- Step 4 cleared → `git-codex-parity-review.py` runs before the first push, after a data-egress
  `AskUserQuestion` that is separate from `cross-model-review`'s First-Send Confirmation
- Exit 0 → continues to the push; exit 1 → blocking findings shown with fix / re-run / bypass; exit 2 → treated
  as "could not run" (retry / bypass), never as a pass; exit 3 → step skipped, with the skip stated in session output
- Bypass chosen → reported in session output and recorded under the PR body's "Open Items" section; never
  chosen without the user's answer
- Local Codex version differs from CI's pin → warning shown, run still proceeds
- Draft flipped to ready later → the references file's "Before flipping" section re-runs the same script
- Egress question declined → treated as a bypass: reported, and "egress declined" recorded under the PR
  body's "Open Items"; never a quiet skip
- Step 4 bypassed with `--bypass-cross-model-review`, or `--bypass-codex-review` given → step 4.5 still runs
- Session cwd is a subdirectory of the checkout → the script resolves the repo root and still runs
- Egress question is asked again on a re-run after a fix, not only on the first run
- `--output` pointing inside the checkout → refused with exit 2 (treated as "could not run"), never written
- A timed-out run → on POSIX the whole process group is killed, so no `codex` process lingers; on Windows the tree is killed with
  `taskkill /F /T` and the wait for the pipes is bounded, so a surviving descendant cannot hang the run
- `CLAUDE_PLUGIN_ROOT` empty (this repository's own sessions) → step 4.5 runs `.claude/scripts/git-codex-parity-review.py`
  from the checkout root, matching the second grant, instead of failing with exit 127
- A stalled `git fetch` / `gh` / `codex --version` → bounded by a 60 s timeout, then a warning or exit 2, never a hang
- Branch changed a Tier-1 (review-dispatch-critical) file since the base → loud warning naming it, run still
  proceeds; the Tier-1 list is read from the base-tip copy, so the branch cannot shrink it
- The base tip has no readable trust_boundary.py → "could not check" warning, run still proceeds
- The run exits 0 or 1 but the result file is missing, malformed, or its `blocking` contradicts the exit code → exit 2
  ("could not run"), never a pass
- The run's argv carries `--instructions-dir <output stem>-instructions` beside `--output` → the checkout stays clean
- `--output` is a symlink (even to a file that looks like a result) → exit 2, the link and its target are untouched
- The remote has no (or an unrelated) fetch refspec configured → the explicit-refspec fetch still refreshes
  `origin/main` before its tip is resolved as the base
- A retry after an exit 2 uses a fresh `--output` file name (the earlier file is never touched) and proceeds
- A model slug the bridge would reject (`/`, `:`, over 64 characters) → omitted with the documented fallback
  warning, not a failed run
- `--output` already exists (a file, a previous result, a failure payload, an unrelated JSON, a directory or a
  symlink) → exit 2, nothing deleted or overwritten, nothing dispatched; a retry with a fresh file name proceeds
- A run that exits 0 or 1 but whose result is not the full payload (non-string `mode`, missing list fields, only an
  `error`) → exit 2
- `--output`'s directory is missing, not a directory, or not writable → exit 2 before anything is dispatched (the
  result is only written after the whole review); the real `marketplace-ci.yml` still parses (drift test)
- Step 4's clean path and its re-review loop both route to step 4.5, never straight to the push (step 1); the smoke test
  fails if "proceed to step 1" returns
- After a step 4.5 fix, step 4 is re-run on the updated diff unless the user bypasses it, then step 4.5 again
- The wrapper passes the fetched `origin/main` tip as `--base-sha` (CI's `base.sha`), not the merge-base, so a long-lived
  branch is reviewed with the current reviewer instructions
- A malformed Tier-1 list at the base (mixed types, an unhashable element) → the "could not check" warning, run proceeds

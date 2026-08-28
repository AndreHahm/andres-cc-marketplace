# Testing scenarios and quality gates

Extracted from SKILL.md's Testing & Validation section per plugin-rulebook's R13 (SKILL.md grew past
the 500-line Critical threshold). See SKILL.md's own "Verify this skill activates on" / "does NOT
activate on" lists for trigger-phrase coverage — that stays inline since it's directly about
activation. This file holds the deeper concrete-scenario and quality-gate checklists.

## Concrete scenarios to check

1. Empty diff against `$BASE` → Preflight step 1 reports "nothing to review" and stops, no dispatch
   of either model.
2. `codex-kit` is not installed at all, or the `codex` CLI itself is missing — distinct from
   scenario 3: `node` fails at the OS level before either script produces a typed-failure JSON →
   resolver step 3 fires on that raw failure, `AskUserQuestion` offers single-model fallback. On
   "proceed single-model": Phase 1's Codex pass and all of Phase 2 are skipped, Phase 3 synthesizes
   from Claude's Phase 1 findings alone, and every finding is capped at Medium confidence in the
   final report.
3. `codex-kit`/`codex` ARE installed, but `codex-review-bridge` returns `isolation_profile_unavailable`
   (expected on local Windows) → resolver falls back to `codex-windows-guardrails`, and if that's
   disabled (`guardrails_disabled`, the shipped default), step 3's fallback fires — never a silent
   hang.
4. A finding raised in Phase 1 by only one side and explicitly refuted in that side's Phase 2 pass →
   reported as Low/contested with both sides shown, never dropped.
5. `prompts/review.md`/`prompts/refute.md` don't yet exist on `$BASE` (this skill's own first,
   not-yet-merged run) → Preflight step 5 falls back via `Read`/`Write` to the working-tree copy at
   `${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/prompts/...` and records it in
   `inspection_limits`, never silently.
6. The diff itself modifies a file under `plugins/codex-kit/**/scripts/**`, **including when `$SCOPE`
   is set to exclude that path from the review** → Preflight step 6 still finds it (it checks the
   unscoped `$MERGE_BASE` diff, independent of `$SCOPE`), the First-Send Confirmation discloses it,
   and Phase 3's `inspection_limits` records that the dispatcher itself wasn't trust-boundary-verified
   against `$BASE`.
7. Claude's Phase 1 pass reports a finding on a file Preflight step 2 excluded from `--target-paths`
   (deleted, or an invalid-charset path) → that finding is dropped from what's sent to Codex's Phase 2
   challenger pass, never triggering the bridge's whole-envelope rejection; it still appears in the
   final report as a Medium-confidence, single-sided finding with the exclusion noted in
   `inspection_limits`.
8. `prompts/review.md`/`refute.md` don't exist on `$BASE` yet (scenario 5) → the chained Bash
   invocation's `git show || true` doesn't abort; step 6 and the closing `echo` still run, and the
   `Read`/`Write` fallback runs afterward using the echoed `$RUN` value.
9. Every changed file is a deletion or an invalid-charset path (Preflight step 2's eligible list is
   empty) → single-model mode is entered proactively, before any dispatch attempt, with
   `inspection_limits` recording "zero Codex-eligible paths" rather than "Codex unavailable."
10. The First-Send Confirmation is answered "Stay Claude-native for this run" → single-model mode is
    entered immediately, with `inspection_limits` recording "user declined to send to Codex," never a
    dispatch attempt on the declined path.
11. Codex's Phase 2 dispatch returns an envelope with `dispatch.reviewer: "challenger-reviewer"`
    (exactly the `--reviewer-type` it was invoked with, per `refute.md`'s corrected instruction) →
    the bridge's `semanticallyValidate` accepts it; a hand-picked alternate name like
    `"codex-challenger"` would instead fail every Codex-side Phase 2 dispatch outright.
12. The diff modifies `codex-windows-guardrails/assets/dangerous-command-instructions.txt` or its
    `assets/settings.json` → Preflight step 6's `(scripts|assets)` alternation still catches it, same
    disclosure and `inspection_limits` treatment as a `scripts/` change.
13. The branch under review also modifies `prompts/review.md` → Phase 2's Codex challenger pass still
    receives the *trusted*, `$BASE`-materialized `$RUN/review.md` content (prepended to the assembled
    instruction file), never resolving `prompts/review.md` itself against the live working tree.
14. Phase 1's Codex dispatch succeeds but Phase 2's Codex dispatch times out → Phase 3 still merges
    Codex's completed Phase 1 findings and Claude's completed Phase 2 pass; only Codex's own Phase 2
    challenge is recorded as missing in `inspection_limits` — Codex's Phase 1 findings are never
    discarded as if Codex had never run.
15. A Claude finding has an eligible primary `location` but an excluded path in its `components`
    array → still dropped from the Codex challenge payload, same as a finding excluded on `location`
    alone.
16. The working tree has uncommitted (staged or unstaged) changes on top of the last commit → the
    canonical diff includes them, since it's built from `$MERGE_BASE` as a single ref, not the
    committed-only two-dot `$BASE...HEAD` form.
17. The change set consists entirely of a brand-new, never-`git add`ed file → `git add -N -- "${SCOPE:-.}"`
    intent-adds it before the diff is built, so it appears in `git diff` output as a full addition
    instead of the run reporting "nothing to review."
18. A changed path is a symlink whose target resolves outside `$REPO_ROOT` → Preflight step 2 excludes
    it from `--target-paths` (via `realpath`) before any dispatch attempt, instead of the dispatcher's
    own containment check rejecting the whole envelope and forcing an unnecessary single-model
    fallback over one file; Claude's own native review still covers it.
19. `codex-kit` is genuinely not installed (single-model mode) → Claude's native pass still produces
    a correctly-shaped envelope using `review.md`'s self-contained field summary, without needing to
    read `envelope-schema.md` (which doesn't exist in this scenario since git-kit doesn't bundle it).
20. The review scope includes an untracked file → after this run finishes, `git status` on the real
    repository still shows it as `??`, exactly as before the run — no lingering intent-to-add entry,
    since `git add -N` ran against a throwaway `GIT_INDEX_FILE`, never `.git/index`.
21. A symlink resolves to a path in a sibling directory whose name happens to start with the repo
    root's own name as a substring (e.g. repo at `/path/repo`, symlink target `/path/repo-sibling/f`)
    → still excluded from `--target-paths`, since the containment check requires an exact match or a
    `/`-separator boundary, not a bare string prefix.
22. `prompts/review.md`/`refute.md` don't exist on `$BASE` yet, so `REVIEW_UNVERIFIED`/
    `REFUTE_UNVERIFIED` gets set → the First-Send Confirmation discloses this *before* the first real
    Codex dispatch, not only in Phase 3's final `inspection_limits` after Codex has already run
    against the unverified instructions.
23. This skill is invoked twice in the same Claude Code session, reviewing two different diffs → the
    First-Send Confirmation fires again on the second invocation's first real Codex dispatch — the
    "once per session" framing never suppresses it for a later, separate invocation.
24. Live-verified against this skill's own PR diff (177 files): `[ -n "$SCOPE" ]` (a `test`/`[`
    invocation) runs without a permission gap, matching the added `Bash(test:*)` grant — confirmed
    by direct precedent in sibling skills `codex-verify`/`codex-rescue`, which already grant
    `Bash(test:*)` for the identical bracket-test pattern.
25. The review scope includes a genuinely untracked file → Codex's own dispatch, told to re-run the
    canonical diff command in its own subprocess, would not see it (no inherited `GIT_INDEX_FILE`) →
    `$UNTRACKED_FILES` is captured before the throwaway-index switch and appended explicitly to both
    Phase 1 and Phase 2's Codex-facing instructions, naming each path so Codex reads it directly.
26. Live-verified via a full, real two-phase run (both Codex dispatches, both Claude native passes)
    against this skill's own PR diff: `$SCOPE` set to a pathspec resolving only to a deleted tracked
    file → `git add -N -- "${SCOPE:-.}"` fails (`fatal: pathspec ... did not match any files`) but
    the `|| true` tolerates it, the chain continues, and `git diff "$MERGE_BASE" -- "$SCOPE"` still
    correctly shows the deletion. Unanimous finding: raised independently by Codex and Claude in
    Phase 1, confirmed by both again in Phase 2, with no refutation from either side.
27. Live-verified, issue #78: on a real Windows machine, instructing Codex to run `git diff` itself
    (the pre-fix design) failed 100% of the time with `isolation_profile_unavailable`
    (`CreateProcessAsUserW` / Windows error 1920) for a diff large enough to produce substantial
    output — while a small-output command (`git status`, `git diff --stat`) from the same dispatch
    succeeded via a different internal tool path, proving the failure was about anticipated output
    size, not the sandbox profile. Embedding the diff content directly (this skill's current design)
    resolved it: the identical dispatch, same repo, same machine, succeeded cleanly through
    `codex-review-bridge`'s sandboxed Step 1 with a real, substantive finding returned — confirming
    the fix works via the actual resolver Step 1 path, not a special-cased workaround.

## Quality gates

- [ ] Preflight step 5 always sources reviewer instructions from `$BASE` via `git show`, never
      directly from `${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/...` on the happy path — the
      working-tree copy is a disclosed fallback only, not the default
- [ ] The First-Send Confirmation always fires before the *first* real Codex dispatch **of this
      invocation** — never suppressed because an earlier, separate invocation in the same session
      already asked — and always discloses the possible `danger-full-access` outcome, any Preflight
      step 6 dispatcher-trust gap, and any Preflight step 5 `REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED`
      state, not just the sandboxed-vs-not distinction
- [ ] Every finding given to a Phase 2 challenger pass is explicitly confirmed or refuted — never
      silently unaddressed, and never left in an undefined third state
- [ ] A `severity: critical` finding is never dropped regardless of its confidence tier
- [ ] No code is edited before Phase 3's closing `AskUserQuestion` is answered
- [ ] Single-model mode always skips Phase 1's Codex pass and all of Phase 2 — never dispatches Codex
      after the user chose to proceed single-model
- [ ] A Codex-bound instruction file never embeds diff text for a file Preflight step 2 excluded from
      `--target-paths` — `$CODEX_DIFF_STR` is used for every Codex-facing embed, `$DIFF_STR` only for
      Claude's own native pass
- [ ] Neither Phase 1 nor Phase 2's Codex-bound instruction file ever tells Codex to run `git diff`
      (or any other command expected to produce large output) itself — the diff content is always
      embedded directly, computed by this skill's own Bash/Read steps beforehand (issue #78)
- [ ] The other model's findings are always closing-tag-neutralized before being embedded in
      `challenger_instructions_for_codex.md` — never written verbatim
- [ ] Preflight step 6's dispatcher-trust check always uses the unscoped `$MERGE_BASE` diff — never
      Preflight step 2's `$SCOPE`-filtered changed-file list
- [ ] The canonical diff is always built from `$MERGE_BASE` (a single ref) — never the two-dot
      `$BASE...HEAD` form, which would silently exclude staged and unstaged working-tree changes
- [ ] A Claude Phase 1 finding on an excluded path is always dropped before assembling the Codex
      challenge payload — never sent verbatim and never silently kept out of the final report
- [ ] A finding both models raised in Phase 1 but a Phase 2 pass later explicitly refuted is always
      reported at Low/contested — Phase 1 agreement alone never keeps it at High once refuted
- [ ] Reviewing the local diff before flipping an existing draft PR to ready is never routed to
      `collaborating-on-a-pr` — the "already-open PR" exclusion applies only to posting a GitHub
      review or reading the PR's remote state, not to this skill's own documented local-diff purpose
- [ ] Preflight step 5's `git show` calls always carry `|| true` — an expected first-run failure
      never aborts the chained invocation before step 6 or the closing `echo`
- [ ] Preflight step 6's dispatcher-trust grep is always run with `-E` — never plain `grep`, which
      silently fails to match the extended-regex pattern
- [ ] A dispatch is never attempted when Preflight step 2's eligible-files list is empty — single-model
      mode is entered proactively instead
- [ ] "Stay Claude-native for this run" at the First-Send Confirmation always enters single-model mode
      immediately — never leaves Phase 1/2 to still attempt or wait on a declined Codex dispatch
- [ ] Codex's `dispatch.reviewer` always echoes the exact `--reviewer-type` value it was dispatched
      with — `refute.md` never asserts a substituted name like `codex-challenger`
- [ ] Preflight step 6's trust check always covers `assets/` as well as `scripts/` under
      `plugins/codex-kit/` — never `scripts/`-only
- [ ] Phase 2's Codex-bound instruction file always includes `$RUN/review.md`'s trusted content, not
      just `$RUN/refute.md` — `refute.md`'s cross-reference to `prompts/review.md` is never left to
      resolve against the live working tree
- [ ] A Phase 2 failure after Phase 1's Codex dispatch already succeeded is always treated as a
      partial failure — Codex's completed Phase 1 findings and any completed Claude Phase 2 pass are
      never discarded as if full single-model mode had been active from the start
- [ ] The excluded-path filter before Codex's Phase 2 challenge always checks both a finding's
      `location` and every entry in its `components` array — never `location` alone
- [ ] `plugin.json` and the marketplace entry's `version` are bumped together whenever a release-worthy
      change (like a new skill) ships, so `claude plugin update` doesn't treat it as unchanged
- [ ] `git add -N` always runs before the canonical `DIFF`/`CODEX_DIFF` commands, never after — an
      untracked file added post-diff still won't appear in that run's output
- [ ] `git add -N`, `git merge-base`, and `realpath` are all declared in `allowed-tools` — never
      invoked without a matching grant
- [ ] Preflight step 2's symlink-containment check always resolves `$REPO_ROOT` inline via
      `git rev-parse --show-toplevel`, never the `$REPO_ROOT` variable — step 4 hasn't assigned it yet
      at that point in the sequence
- [ ] review.md's self-contained field summary is used whenever `envelope-schema.md` is unavailable
      (codex-kit not installed) — Claude's native pass is never left without a field contract to follow
- [ ] `git add -N` always runs against a throwaway `GIT_INDEX_FILE` — the real `.git/index` is never
      touched, and a `git status` on the real repo after the run shows every previously-untracked
      file exactly as it did before
- [ ] The symlink-containment check always requires an exact match or a `/`-separator boundary —
      never a bare string-prefix comparison that a sibling directory's name could satisfy
- [ ] The First-Send Confirmation's disclosure always includes Preflight step 5's
      `REVIEW_UNVERIFIED`/`REFUTE_UNVERIFIED` state when set — never deferred to Phase 3's
      `inspection_limits` as the first place the user learns about it
- [ ] The First-Send Confirmation always re-fires on a new invocation of this skill, even within the
      same Claude Code session — "once per session" never suppresses it across separate reviews
- [ ] `allowed-tools` always grants `Bash(test:*)` — the Inputs section's `[ -n "$SCOPE" ]` bracket
      test is a `test` invocation, matching the same pattern already granted in sibling skills
      `codex-verify`/`codex-rescue`
- [ ] `$UNTRACKED_FILES` is always captured before `GIT_INDEX_FILE` switches to the throwaway index
      — capturing it after would see the empty throwaway index and report everything as untracked
- [ ] Both Phase 1 and Phase 2's Codex-facing instruction assembly append `$UNTRACKED_FILES` when
      non-empty — Codex's own subprocess re-running the diff command never sees intent-added files
      on its own
- [ ] The stated scenario count in SKILL.md's pointer to this file always matches this file's actual
      count — never left stale after a scenario is added or removed
- [ ] `git add -N -- "${SCOPE:-.}"` always carries `|| true` — a `$SCOPE` resolving only to a
      deletion must never abort the chained Preflight invocation before `git diff` runs

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

## Quality gates

- [ ] Preflight step 5 always sources reviewer instructions from `$BASE` via `git show`, never
      directly from `${CLAUDE_PLUGIN_ROOT}/skills/cross-model-review/...` on the happy path — the
      working-tree copy is a disclosed fallback only, not the default
- [ ] The First-Send Confirmation always fires before the *first* real Codex dispatch, and always
      discloses the possible `danger-full-access` outcome and any Preflight step 6 dispatcher-trust
      gap, not just the sandboxed-vs-not distinction
- [ ] Every finding given to a Phase 2 challenger pass is explicitly confirmed or refuted — never
      silently unaddressed, and never left in an undefined third state
- [ ] A `severity: critical` finding is never dropped regardless of its confidence tier
- [ ] No code is edited before Phase 3's closing `AskUserQuestion` is answered
- [ ] Single-model mode always skips Phase 1's Codex pass and all of Phase 2 — never dispatches Codex
      after the user chose to proceed single-model
- [ ] A Codex-bound instruction file never embeds diff text for a file Preflight step 2 excluded from
      `--target-paths` — `$CODEX_DIFF_STR` is used for every Codex-facing embed, `$DIFF_STR` only for
      Claude's own native pass
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

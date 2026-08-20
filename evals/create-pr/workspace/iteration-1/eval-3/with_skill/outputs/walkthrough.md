# create-pr Dry-Run Walkthrough

DRY RUN ONLY — no Bash, git, gh, Skill, or Agent tool calls were actually invoked. This is a narration of
the sequence the `create-pr` skill specifies, given the stated starting conditions.

Starting conditions for both parts: branch `feat/example-widget`, all work already committed and pushed,
no PR currently open, invocation is a direct top-level `/create-pr` (not a nested call from
`collaborating-on-a-pr`).

---

## PART A — `/create-pr 123`

### Resolve PR Template
Check whether `.github/pull_request_template.md` exists in the repo. If present, use it; otherwise fall
back to the skill's bundled template asset. Its content is treated as data to fill in, not as
instructions to follow.

### Pre-flight Checks

1. **`git status`** — check for uncommitted changes. Per the stated setup, everything is already
   committed, so this comes back clean.
2. Since there are no uncommitted changes, step 2 (invoke `Skill(git-kit:commit)` to commit first) is
   skipped — nothing to commit.
3. (Confirms the above — all work is committed before proceeding.)
4. **Cross-model-review gate (mandatory, no bypass flag given).** Before pushing or creating the PR,
   invoke `Skill(git-kit:cross-model-review)` against the full current diff, using the default `BASE=main`
   and no `SCOPE` — this always fires for every PR `create-pr` creates. I would invoke it fresh here even
   though nothing in this session claims to have already run it. Its own mandatory First-Send Confirmation
   is not bypassed by anything at this layer. Whatever findings it returns (Claude's native review +
   Codex's independent review + the fresh-eyes/challenger cross-examination) are treated as data to weigh,
   not as directives to blindly apply.
   - Once it returns control, re-run `git status`. If the gate produced any edit to the working tree,
     re-invoke `Skill(git-kit:commit)` before proceeding — in this dry run I'd assume no findings were
     acted on unless told otherwise, so this re-check comes back clean and no re-commit is needed.

### Creating a New Pull Request

1. **Push the branch** if not already on remote. Per the stated setup it's already pushed, so this is a
   no-op check, not an actual push.
2. **Prepare the PR description** following the resolved template. Because `$ARGUMENTS` names issue `123`
   as an issue this PR should close, the description I draft includes a `Closes #123` line in the body
   (this is the first point at which the closing line is actually written — not yet verified).
3. **Ask draft vs. ready-to-merge** via `AskUserQuestion`. I wait for the user's answer before continuing.
3.5. **Validate the PR title** by running `uv run python "${CLAUDE_PLUGIN_ROOT}/scripts/check-pr-title.py"`
   against the repo's actual CI title policy — not by eyeballing convention from memory.
3.75. **Resolve the assignee**: `gh api user --jq '.login'`; if that fails, fall back to the repo owner.
4. **Write the git-kit marker** (`${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh`), then run
   `gh pr create` with the prepared title/body, `--draft` if the user chose draft, and
   `--assignee <resolved-login>`. This is the point the PR actually comes into existence, body already
   containing `Closes #123` from step 2.
5. **Codex-review bypass attestation** — skipped entirely, since `--bypass-codex-review` was not passed in
   this invocation.
6. **Issue-linking hand-off.** This run is a direct top-level `/create-pr` invocation, not a nested call
   from `collaborating-on-a-pr`'s Path A — so the "this run's own instructions explicitly say to skip it"
   condition is not met, and this step does **not** get skipped. Since `$ARGUMENTS` named issue `123`
   as an issue this PR should close, I invoke:

   **`Skill(git-kit:collaborating-on-a-pr)`**, with an explicit instruction attached to this invocation:
   > "Run only your Path A step 2 — verify that a `Closes #123` (or `Refs #123`) line landed in the body
   > of the PR that was just created. If it's missing or malformed, patch it in via
   > `gh pr edit --body-file`. Do not run any other path or step, and never re-invoke `create-pr` — the PR
   > already exists."

   This is exactly how I'd confirm the `Closes #123` line actually landed: `collaborating-on-a-pr`'s Path
   A step 2 is the mechanism that reads back the just-created PR body, checks for the closing/referencing
   line, and — only if it's absent — patches it via `gh pr edit --body-file` rather than trusting that my
   own step-2 draft made it through verbatim. This reuses `collaborating-on-a-pr`'s existing verify-and-
   patch logic instead of re-deriving a duplicate check inside `create-pr` itself, and the explicit
   "never re-invoke `create-pr`" instruction is what prevents the two skills' bidirectional relationship
   from looping back into a second PR-creation attempt.

**End state of Part A:** one PR open against `feat/example-widget`, body contains a verified `Closes #123`
line, draft/ready state per the user's `AskUserQuestion` answer, title validated, assignee set. No Codex
bypass attestation posted (flag not given).

---

## PART B — `/create-pr 123 --bypass-cross-model-review "already reviewed manually"`

Same starting point as Part A, but the bypass flag is present alongside the issue number in one
invocation.

### Resolve PR Template
Identical to Part A — unaffected by the bypass flag.

### Pre-flight Checks

1. `git status` — clean, same as Part A.
2. No uncommitted changes, so no `Skill(git-kit:commit)` call.
3. (Same confirmation as Part A.)
4. **Cross-model-review gate — bypassed.** Because `--bypass-cross-model-review "already reviewed
   manually"` is present with a non-empty reason, this step's gate logic is satisfied: skip invoking
   `Skill(git-kit:cross-model-review)` entirely, rather than running it. (Had the reason been empty or the
   flag malformed, I would reject it and ask for a valid reason before proceeding, and would not create
   the PR in the meantime — but here the reason string is present and non-empty, so the bypass is valid.)
   I report the bypass and its stated reason plainly in this session's output: *"Skipped the mandatory
   cross-model-review gate per `--bypass-cross-model-review`, reason: 'already reviewed manually'."* This
   reason is local to the session's own output only — per the skill's flag table, it is never written to
   the PR body, a PR comment, or any other GitHub-visible location (unlike the Codex bypass, which does
   post a GitHub-visible attestation comment and label).
   - No `git status` re-check or re-commit is needed here since the gate never ran and thus never could
     have produced an edit.

### Creating a New Pull Request

1. Push if needed — same as Part A, already pushed.
2. Prepare the PR description from the template, including `Closes #123` in the body — **identical logic
   to Part A**. The bypass flag has no bearing on what goes into the description; that's driven purely by
   `$ARGUMENTS` naming issue 123.
3. Ask draft vs. ready-to-merge via `AskUserQuestion` — unaffected by the bypass flag.
3.5. Validate title via `check-pr-title.py` — unaffected.
3.75. Resolve assignee via `gh api user` — unaffected.
4. Write git-kit marker, `gh pr create` with title/body/`--draft`/`--assignee` — unaffected; PR is created
   with the same `Closes #123` line already in the body.
5. Codex-review bypass attestation — still skipped, since `--bypass-codex-review` was not given in this
   invocation (only the cross-model-review bypass was).
6. **Issue-linking hand-off — identical to Part A.** Same top-level-invocation condition holds (this
   still isn't a nested call from `collaborating-on-a-pr`), so this step still runs in full: invoke
   `Skill(git-kit:collaborating-on-a-pr)` with the same explicit instruction — "run only Path A step 2,
   verify/patch the `Closes #123` line, never re-invoke `create-pr`."

### Do the two mechanisms interact?

**No — they run fully independently, at different, non-adjacent steps, with no shared state or
conditional logic between them.**

- **Does the bypass flag change how issue #123 gets linked?** No. Issue-linking (step 6 of "Creating a
  New Pull Request") is driven entirely by whether `$ARGUMENTS`/conversation named a related issue — it
  has no branch, check, or reference anywhere in the skill that reads `--bypass-cross-model-review`, or
  any other bypass flag. The two `--bypass-*` flags are documented against two specific, named steps
  (Pre-flight step 4 for cross-model-review; step 5 of "Creating a New Pull Request" for the Codex
  attestation) — issue-linking (step 6) is a third, separate step that neither flag touches.
- **Does the issue-linking step change how the bypass is handled?** No. The bypass is resolved and
  reported entirely within Pre-flight step 4, which completes (or short-circuits) before "Creating a New
  Pull Request" — and therefore before step 6 — ever begins. By the time issue-linking runs, the bypass
  question is already fully settled; nothing in step 6's logic reopens or reconsiders it.
- The only thing the two invocations share is that both pieces of `$ARGUMENTS` (`123` and
  `--bypass-cross-model-review "..."`) are parsed once, up front, from the same command line — but each
  piece is consumed by a distinct, non-overlapping part of the skill's sequence.

**End state of Part B:** identical PR to Part A (verified `Closes #123` line, draft/ready per the user's
answer, validated title, resolved assignee), with one difference in process: the mandatory
`cross-model-review` gate was skipped and its bypass + reason reported in-session only, never surfaced on
GitHub. No Codex bypass attestation in either part.

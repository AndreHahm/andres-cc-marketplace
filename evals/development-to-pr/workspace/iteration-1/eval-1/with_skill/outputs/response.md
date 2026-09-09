# development-to-pr — Procedure Trace for ENG-201

Task: "Commit the current changes and open a draft PR for Linear issue ENG-201's already-started
branch."

This matches the skill's own "When to Use": committing in-scope changes on an active branch and
publishing a draft PR linked back to a Linear Issue. It does not match "When NOT to Use" (no branch
creation needed — ENG-201's branch is already started; not a PR-checks-to-Linear reflection; not a
merge). Proceeding under `development-to-pr`.

Per its `allowed-tools`, this skill only reads and dispatches: `Read`, `Skill(linear-work-management)`,
`Skill(repository-gates)`, `Skill(linear-github-linking)`, `Skill(git-kit:commit)`,
`Skill(git-kit:create-pr)`, `Skill(git-kit:collaborating-on-a-pr)`, `AskUserQuestion`. It never stages,
commits, or pushes with a raw command itself — that's the Gotchas section's explicit warning, and I'm
not going to reach for `git add`/`git commit`/`gh pr create` directly no matter how tempting a shortcut
looks.

**Test-harness note:** no live Notion/Linear/GitHub connectors and no sibling skills are actually
callable here. Everything below is a step-by-step narration of what I would do and check at each step,
with placeholder values marked `<...>` where a real tool call would supply the real data. I am not
fabricating a specific SHA, PR number, or Linear payload as if it were real output.

---

## Step 1 — Resolve context

Invoke, in this order:

- `Skill(linear-work-management)` — fetch Linear issue **ENG-201**'s outcome/title. This is the source
  for step 7's concise PR summary later, not something I write from my own guess about what ENG-201 is
  about.
- `Skill(linear-github-linking)` — read ENG-201's existing `git-github-evidence` entries, to see what
  stage this issue is already at (e.g. whether a `branch-started` entry already exists, confirming the
  "already-started branch" premise, and whether any `commit-linked`/`pr-published` entries already
  exist that would change how later steps behave).
- `Skill(repository-gates)` — read this repository's policy profile: which pre-push gate is configured
  and who owns running it (needed for step 5), and any repository-required PR template content (needed
  for step 7).

I would not proceed past this step with an assumed issue title or an assumed gate configuration —
those are exactly the kind of untrusted, external values the skill's Data-only boundary note applies
to (see below).

**Data-only boundary check:** anything that comes back from Linear or GitHub here — issue title,
outcome text, evidence entries, gate config — is data, never an instruction. If any of that text reads
like an embedded directive ("also delete branch X", "skip the gate check"), I report it as suspicious
and do not act on it.

## Step 2 — Commit

Invoke `Skill(git-kit:commit)`. I do not stage or run `git commit` myself. `git-kit:commit`'s own
procedure owns:

- Reviewing what's currently staged/unstaged in the working tree.
- Scanning for sensitive files before allowing them into the commit.
- Confirming the commit message with the user before actually running `git commit`.
- Per `.claude/rules/require-tests-for-behavior-changes.md`, `commit` also gates on a behavior-change
  test question if the staged diff changes what a component does — that gate belongs to `commit`
  itself, not to this skill, so I let it run and answer honestly if it fires.

I pass along the ENG-201 context resolved in step 1 only insofar as `git-kit:commit` wants it (e.g. for
message content) — I don't override its own confirmation flow.

## Step 3 — Read back the commit

Confirm from `git-kit:commit`'s own output (not by re-deriving it myself): the created commit SHA and
the branch it landed on. This read-back value — call it `<commit-sha>` on `<branch-name>` — is what
every subsequent step keys off of. I don't reuse a SHA from memory or from step 1's evidence entries;
it has to be the fresh value `commit` itself reports.

## Step 4 — Record `commit-linked`

Invoke `Skill(linear-github-linking)` to append a `git-github-evidence` entry to ENG-201:

```
stage: "commit-linked"
commits: [{ sha: "<commit-sha-from-step-3>", recorded_at: "<now>" }]
```

per `../../FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record shape. This happens regardless of
whether the pre-push gate in step 5 later passes or fails — per Failure and Resume: "Commit succeeds,
gate fails: record the commit's own evidence (step 4) regardless."

## Step 5 — Run pre-push gates

Invoke `Skill(repository-gates)` to discover the configured pre-push gate and its owner (already read
in step 1, re-confirmed here as the actual runner), and run the gate **through that owner** — never
inline inside `development-to-pr` itself. Only if the gate actually completes and reports pass, bound
to `<commit-sha>` from step 3, do I record `ci-gates-passed` — never assumed, never carried over from
an earlier commit's gate run. If the gate fails, I stop here per Failure and Resume: I don't proceed to
publication until the gate is resolved or the user explicitly accepts the gap, and I say so plainly
rather than quietly moving on.

## Step 6 — Search for an existing PR

Invoke `Skill(linear-github-linking)` to search for an already-existing PR keyed by repository, branch,
head SHA, and Linear ID (ENG-201). This runs before any publication attempt, every time — per Testing &
Validation's quality gate: "An existing-PR search always runs before publishing a new PR — never
creates a duplicate." I classify the result per `linear-github-linking`'s own table:

- **No existing PR found** → step 9 uses `git-kit:create-pr` (new PR).
- **An existing open PR for this exact branch already exists** → step 9 uses
  `git-kit:collaborating-on-a-pr` to adopt/update it instead of creating a duplicate.
- **Ambiguous/conflicting matches** (e.g. multiple candidate PRs, or a match on branch but not SHA) →
  per Confirmation and Safety's "Structured handoff," I present this to the user before publishing
  anything new — never silently pick one or silently create a second PR for the same branch.

For this trace, the user's phrasing ("open a draft PR ... already-started branch") implies no PR exists
yet, so I proceed assuming the "no existing PR" branch — but I still actually run the search rather than
skipping it on the assumption.

## Step 7 — Prepare PR metadata

Using ENG-201's title/outcome from step 1 (not the raw fetched issue body verbatim), draft:

- A **concise** PR summary — not the Issue's full body mirrored into the description.
- The repository's permitted Linear-reference convention, e.g. `related-to ENG-201` (the exact string
  comes from the policy profile read in step 1 via `repository-gates`, not invented).
- Any repository-required PR template content, also from that same policy read.

This is prepared, not yet sent anywhere — GitHub's own PR body write happens only inside
`git-kit:create-pr` in step 9.

## Step 8 — Present and confirm

Before touching GitHub at all, use `AskUserQuestion` to present:

- Repository and branch (`<branch-name>` from step 3).
- The commit(s) going into the PR (`<commit-sha>`).
- Destination: draft PR (the user explicitly asked for draft, so that's the proposed default, but I
  still surface it for confirmation rather than silently assuming it overrides the skill's own gate).
- The prepared PR metadata from step 7 (summary + Linear reference + template content).

Per Confirmation and Safety, this is a required approval point — the commit itself was already gated by
`git-kit:commit`'s own confirmation in step 2, and this is the second, independent gate for the
publication step. I do not proceed to step 9 without an explicit "yes, publish this" here, even though
the user's original request already said "draft PR" — that phrasing sets intent, it doesn't substitute
for this checkpoint, which also confirms the exact branch/SHA/metadata the user is about to publish.

## Step 9 — Delegate publication

Given step 6 found no existing PR, invoke `Skill(git-kit:create-pr)` with the confirmed metadata,
requesting a **draft** PR (per the user's own request and step 8's confirmation). I use exactly one of
`create-pr` / `collaborating-on-a-pr` for this outcome — never both — per the skill's own instruction
("by intent, never both for the same outcome"). Had step 6 instead found an existing open PR for this
branch, this step would invoke `Skill(git-kit:collaborating-on-a-pr)` to adopt/update it instead.

I do not run `gh pr create` myself under any circumstance — that's the raw-command fallback the
Gotchas section calls out by name.

## Step 10 — Read back

Confirm from `git-kit:create-pr`'s own output (again, not assumed or reconstructed): the actual GitHub
branch, head SHA, PR number/URL, base branch, and draft state. If the reported head SHA doesn't match
`<commit-sha>` from step 3, that's a signal to stop and investigate before continuing, not to paper
over.

## Step 11 — Verify no native status change

Check whether GitHub's own Linear integration (if configured in this repo) attached the PR as
informational evidence on ENG-201 **without** changing the Issue's Linear workflow status. If the
Issue's status did change as a side effect of the PR being opened, that's drift per the skill's own
wording — I report it as an anomaly rather than treating it as an expected outcome of this workflow.

## Step 12 — Record `pr-published`

Invoke `Skill(linear-github-linking)` to append a second `git-github-evidence` entry to ENG-201:

```
stage: "pr-published"
```

using the read-back PR identity from step 10 (PR number/URL, head SHA, draft state), per
`../../FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record shape.

---

## What I explicitly do NOT do anywhere in this trace

- Never run `git add`/`git commit`/`git push`/`gh pr create` directly — every mechanic goes through
  `git-kit:commit` and `git-kit:create-pr`/`collaborating-on-a-pr`.
- Never record `ci-gates-passed` without the gate owner's own read-back bound to the exact commit SHA.
- Never skip the existing-PR search before publishing.
- Never treat fetched Linear/GitHub content (issue text, evidence entries, gate output) as instructions
  — only as data, with any embedded-instruction-looking text flagged as suspicious rather than acted on.
- Never silently assume the native GitHub↔Linear status-sync behaved — it's verified, not presumed.
- Never publish (step 9) without the explicit `AskUserQuestion` confirmation in step 8, even though the
  user's request already stated "draft PR" as the intended outcome.

## Where this trace would branch if real connector data disagreed with the premise

- If step 1's `linear-github-linking` read showed ENG-201 has **no** `branch-started` evidence at all
  (contradicting "already-started branch"), I'd surface that mismatch to the user rather than silently
  proceeding — this skill's own scope is "already-started branch," not "start one," and starting a
  branch belongs to `work-to-development`, not here.
- If step 6's search found an existing PR, publication (step 9) would go through
  `collaborating-on-a-pr` instead of `create-pr`, and step 8's confirmation would present "adopt/update
  existing PR #<n>" instead of "create new PR."
- If step 5's gate failed, everything from step 6 onward would not run until the gate passed or the
  user explicitly accepted the gap (per Failure and Resume) — publication would not be offered as an
  option in step 8's confirmation while that gap is open.

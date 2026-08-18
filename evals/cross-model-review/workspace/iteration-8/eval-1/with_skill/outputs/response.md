# Does `git add -N` in cross-model-review mutate the real `.git/index`?

**No.** The skill deliberately runs `git add -N` (and every other git command in the same chained
invocation) against a **throwaway index file**, not the repository's real `.git/index`. This is
stated explicitly in two places in `SKILL.md`:

1. In the skill's own preamble, under the `Write`-scoping paragraph:

   > "The one deliberate exception is `git add -N` (Inputs section, below) — and even that never
   > touches the repository's real index: it runs against a throwaway `GIT_INDEX_FILE`, so no state
   > from this skill's run persists anywhere the user's own later `git add`/`git commit` could see
   > it." (lines 29-35)

2. In the **Inputs** section, which is the authoritative walkthrough of the mechanism, under the
   bold heading "Do this against a throwaway index, never the repository's real one":

   > "`git add -N` against the real `.git/index` is a persistent mutation that outlives this skill's
   > own run — a later, unrelated `git commit -a` would then commit that file's full content, even
   > though it was genuinely untracked and excluded before this report-only review ever touched it.
   > Point `GIT_INDEX_FILE` at a throwaway path for the whole chained invocation instead..."
   > (lines 88-96)

So the skill itself names the exact risk the question is asking about — an unrelated, later
`git commit -a` accidentally picking up a previously-untracked file — and states that avoiding it
is the entire reason for the throwaway-index design.

## The actual mechanism

The Inputs section gives the literal shell sequence used (lines 98-106):

```bash
BASE="${BASE:-main}"
MERGE_BASE=$(git merge-base "$BASE" HEAD)
export GIT_INDEX_FILE="$(mktemp -u)"
git add -N -- "${SCOPE:-.}"
DIFF=(git diff "$MERGE_BASE")
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")
DIFF_STR=$(printf '%q ' "${DIFF[@]}")   # shell-quoted rendering, for embedding in a prompt
```

The key line is `export GIT_INDEX_FILE="$(mktemp -u)"`. Git honors the `GIT_INDEX_FILE` environment
variable to redirect **all** index reads/writes for any git command run in that environment to the
named path instead of `<repo>/.git/index`. Because this variable is `export`ed once and the whole
Preflight sequence is required to run as a **single chained Bash invocation** (`&&` between steps,
one tool call — see the Preflight section's opening paragraph, lines 115-123), every git command in
that chain — the `git add -N`, the `git diff` calls, and later re-invocations of the same
`$MERGE_BASE`-based diff in Preflight steps 2 and 6 and the `CODEX_DIFF` variant — inherits that
same throwaway index automatically. The skill notes this explicitly: "the throwaway path is exported
once and every git command in this same chained invocation inherits it automatically, so nothing
else in this document needs to reference it explicitly" (lines 95-96).

Because `mktemp -u` produces a path that doesn't yet exist, `git add -N` against it starts from an
empty/non-existent index rather than a copy of the real one — the skill notes this was "verified
empirically that `git add -N`/`git diff` against a fresh, never-before-existing index path work
identically (both tracked-modified and newly-intent-added files show up correctly) while the real
index stays completely untouched" (lines 92-94).

Two consequences of this design:

- The real `.git/index` — the one `git status`, `git commit`, and `git commit -a` all read from in
  the user's own later, separate shell session — is never opened or written by this skill at all.
  `git add -N` only ever touches the file named by `GIT_INDEX_FILE`, which is a `mktemp`-generated
  temp path.
- The `GIT_INDEX_FILE` environment variable itself is process/shell-local. It's set with `export`
  inside one specific chained Bash tool invocation. It does not persist into the user's own separate
  terminal/session, and it does not modify any on-disk git configuration (e.g. nothing is written to
  `.git/config` or a repo-level setting) that could cause a later, independent `git commit -a` to
  pick up the throwaway index instead of the real one.

## Would a later `git commit -a` accidentally include the file?

**No** — precisely because of the throwaway-index design described above. Walking through why:

- `git add -N` (intent-to-add) on the throwaway index records the file with an empty placeholder
  blob **in that temp index file only** (Inputs section, lines 79-86, describing what intent-to-add
  does and why it's needed just to make `git diff` show the file at all).
- Since that temp index is a file at a `mktemp -u` path under the OS temp directory, and the skill's
  own `git add -N` call never touches `<repo>/.git/index`, the repository's real index still shows
  the file as `??` (untracked) exactly as before the skill ran.
- `git commit -a` stages and commits based on the **real index** (`.git/index`) in the user's own
  later, separate shell invocation, which has no `GIT_INDEX_FILE` override in effect (that variable
  only existed for the duration of this skill's own chained Bash call, in this skill's own process
  environment). `git commit -a` only auto-stages modifications to files git *already tracks*; it does
  not add previously-untracked files at all regardless of index state — but even setting that aside,
  since the real index was never touched, there is no intent-to-add entry sitting there waiting to be
  picked up.
- The skill also confirms `$RUN` (the scratch dir holding the findings JSON) is not something that
  interacts with the repo's git state either — Phase 3's closing note says `$RUN` "is not explicitly
  deleted after this... persist[s] under the OS temp directory until the OS or the user cleans it up"
  (lines 463-467), and "Deliberately NOT done" reiterates "No persisted artifacts / state machine —
  `$RUN` is scratch, not committed" (lines 475-476). This is a separate temp directory from the
  `GIT_INDEX_FILE` temp file, but both concur with the same overall design principle: nothing this
  skill does leaves state that the repository's real git plumbing would ever read.

## Summary

`git add -N` here operates entirely against a `mktemp -u`-generated throwaway file pointed to by an
`export`ed `GIT_INDEX_FILE`, not `.git/index`. This is explicit, stated design intent (not an
incidental property) — the skill names the exact accidental-commit failure mode in its own prose
(lines 88-91) and describes the throwaway-index mechanism as the direct fix for it. Because the real
index is never opened, and `GIT_INDEX_FILE` is scoped only to this skill's own single chained Bash
invocation (never exported into the user's shell or written to any persistent git config), a later,
separate `git commit -a` run by the user has no way to observe the intent-to-add entry this skill
created — it reads the real index, which was never modified, so the previously-untracked file
remains untracked and is not swept into that later commit.

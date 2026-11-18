# What cross-model-review has you do after the chained Preflight is refused in an EnterWorktree session

Sources: `SKILL.md` (Preflight, the no-`Write` paragraph, Boundaries, Phase 3 closing note),
`references/codex-pass-assembly.md` ("In an EnterWorktree session"), and `references/scoped-review.md`
section 1 (PLANNER_TOUCHED handling). Nothing below was run. This is a description only.

## 1. Why the fallback applies

The skill normally runs the Inputs block and Preflight steps 1-6 as **one chained Bash call** (`&&`
between steps), because Bash calls share no shell state. After the `EnterWorktree` tool, Claude Code's
worktree-isolation check can refuse that call before it runs ("too complex to verify that it stays
inside the worktree", issue #723). SKILL.md says that if this happens you run the chain "as a scratchpad
script instead" (codex-pass-assembly.md, "In an EnterWorktree session"). The fallback is allowed **only
in such a session and only after such a refusal**. Both conditions hold here.

## 2. What you write, where, and with which tool

- **Tool:** the `Write` tool. This is the one narrow exception to the skill's "no `Write` grant" rule.
- **Where:** `<scratchpad>/preflight.sh`, where `<scratchpad>` is the session's scratchpad directory.
  It never goes into the repository (including the worktree) or into `$RUN`. Use the full absolute
  scratchpad path.
- **Content:** the Inputs block (`umask 077`, `BASE=...`, `MERGE_BASE`, `UNSCOPED_CHANGED_FILES`, the
  `PLANNER_TOUCHED` grep, the `[ -z "$PLANNER_TOUCHED" ] || [ -n "$PLANNER_APPROVED" ] || { echo ...; exit 0; }`
  stop line, `UNTRACKED_FILES`, `RUN=$(mktemp -d)`, `export GIT_INDEX_FILE`, the copy-index and
  intent-add helper calls, `DIFF`/`DIFF_STR`), then Preflight steps 1-6 (planner call guarded by the
  flag plus the `full.diff` redirect and `DIFF_STATUS`, `REPO_ROOT`, the two `git show "$BASE:..."`
  lines with `|| true`, the `DISPATCHER_TOUCHED` grep), then the closing `echo` of the resolved values
  (`BASE`, `REPO_ROOT`, `RUN`, `DIFF_STR`, `DISPATCHER_TOUCHED`, `PLANNER_TOUCHED`, `PLAN_FAILED`,
  `DIFF_STATUS`, manifest path, `TARGET_PATHS`, `UNTRACKED_FILES`, `INDEX_COPY_FAILED`,
  `INTENT_ADD_REFUSED`, and whether `$RUN/review.md` and `$RUN/refute.md` are non-empty). All of it
  goes in **verbatim and in order**, copied from the skill.

### What the file may contain

The only text you add yourself:

- the `BASE`/`SCOPE` values from the user's request. Here that means `BASE=main` and **no `SCOPE`**,
  so `SCOPE` stays unset and every `${SCOPE:+...}` / `${SCOPE:-.}` expansion takes its no-scope form;
- `PLANNER_APPROVED=1`, and only after the user explicitly says yes (see section 5).

### What the file may not contain

- any text from the diff, from a `$RUN` file, from a manifest, or from Codex output;
- any edits, additions or "improvements" to the skill's commands. It is verbatim.

## 3. What you show the user

Before running it, show the user the script's **full text**. This matters because one approval of the
run covers every command in it (section 4).

## 4. How and from where you run it, and what one approval covers

- **How:** one standalone Bash call, exactly `bash <scratchpad>/preflight.sh` (the absolute scratchpad
  path), with no `&&`, no `;`, and nothing else in the call.
- **From where:** the session's current working directory, which is the worktree root that
  `EnterWorktree` set. Never `cd` anywhere first.
- **What one approval covers:** every command in the script, including the `git diff`, `git show` and
  `export` lines that would otherwise each prompt. That is why the user sees the full text first.
  `bash <scratchpad>/preflight.sh` is deliberately not in `allowed-tools`: a grant would have to be
  `Bash(bash:*)`, which also admits `bash -c` and any script. Approve each run once and do not add a
  persistent allow rule.
- Afterwards, the closing `echo`'s values become the literal strings you substitute into every later
  call, because Bash calls share no state. Later calls in this session use the other EnterWorktree forms:
  one command per Bash call, prefix assignments such as `GIT_INDEX_FILE="<literal RUN>/index"` and
  `CODEX_KIT_REVIEW_REPO_ROOT="<REPO_ROOT>"` instead of separate `export`s, and scratchpad stdin files
  for the write helper.

## 5. How the PLANNER_TOUCHED stop is handled

The diff edits `skills/cross-model-review/`, so the Inputs-block grep sets `PLANNER_TOUCHED=1`. On the
first run `PLANNER_APPROVED` is not in the script, so the stop line prints
`PLANNER_TOUCHED=1: ask the user first` and `exit 0`s. The script ends before any working-tree script
runs: no `$RUN` scratch dir, no index copy, no intent-add, no planner. The closing `echo` does not run
either.

Then:

1. Ask through `AskUserQuestion`, not a plain-text question. The two options are: run the working-tree
   review scripts anyway (they run code from the branch under review with the user's permissions and no
   sandbox), or stop.
2. **Only an explicit yes** lets you continue. You then rewrite `<scratchpad>/preflight.sh` with `Write`.
   It is the same verbatim script, with `PLANNER_APPROVED=1` set first, before the Inputs block. That
   is the only extra text you add. Show the user the full text again, and re-run the **whole** script as
   a new standalone `bash <scratchpad>/preflight.sh` call from the worktree root. It needs a new
   approval.
3. On "stop" (or anything other than an explicit yes), end the review. The user can review the diff
   another way, for example with the PR's own CI review.
4. Either way, record the choice in `inspection_limits`, disclose it again at the First-Send
   Confirmation (clause (c)), and report `PLANNER_TOUCHED` and the answer in Phase 3.

## 6. How to answer a Write permission prompt

`Write` is not in `allowed-tools`. A session scratchpad is often writable without a prompt, so the
`Write` may not ask at all. If it does ask, approve it **for that one call only**. Never approve it for
the session, and never switch to an accept-edits mode. A `Write` approval is not limited to the
scratchpad: it would allow writes anywhere, including the repository.

## 7. No scratchpad directory, or the new form is refused too

- **No scratchpad directory:** stop and report it. Never pick another location: not `/tmp`, not the
  repository, not `$RUN`.
- **`bash <scratchpad>/preflight.sh` is refused too** (or any call in these EnterWorktree forms is
  refused): stop and report it. Never fall back to another way of running the step, such as splitting
  the chain differently, using a heredoc or `bash -c`, `cd`-ing elsewhere, or editing the script.

## 8. Leftovers to disclose

The skill has no scoped delete. In the Phase 3 closing note, say that `<scratchpad>/preflight.sh` (and
any stdin files written later) stay in the scratchpad after the run, alongside the `$RUN` artifacts. The
JSON envelopes among the stdin files can quote diff content.

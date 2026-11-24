# Step 1.6 waiver-section check, PR 943

Basis: `references/session-open-items-and-body-check.md`, step 1.6, "Check the new body". The files are already written: `body-base.txt` (the body the proposal was built on) and the new body, and `diff --strip-trailing-cr` showed only approved lines.

## CLAUDE_PLUGIN_ROOT outside the checkout

**Command**

    python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-body-waiver-check.py" <scratchpad>/body-base.txt <scratchpad-path>

that is, `/home/u/.claude/plugins/cache/mkt/git-kit/1.0.0/scripts/git-pr-body-waiver-check.py`.

**Which copy:** the installed plugin copy. The `.claude/scripts/` mirror form (`python3 -I $PWD/.claude/scripts/...`) is only for an empty `CLAUDE_PLUGIN_ROOT`, so it is not used here, although cwd is the verified root. Never check the sections by eye.

**Ask first? Yes.** The changed-file list (step 1.5's paginated `pulls/943/files` call) holds one of the two copies, the `.claude/scripts/` one. The rule triggers on "either copy" and has no exception for an installed plugin root. Before running:

1. Say that PR 943 changes `.claude/scripts/git-pr-body-waiver-check.py`.
2. Also say, accurately, that the copy to be run is the installed one outside the checkout. The skill's stated reason ("the pre-approved copy is the PR's own new code") does not hold for this copy as far as its location shows; the text still requires the approval.
3. Ask with `AskUserQuestion` whether to run it for this call. The earlier approval of the body update does not cover it.
4. Run only after a yes, and not relying on the pre-approved form: the run should go through its own permission decision, not be auto-allowed by the skill's grant. The skill names no replacement command form, so if the command would be auto-allowed I would disclose that in the question.
5. On no: stop this step, send no body edit, report the check was not run.

Exit `0`: go on to the single re-read/compare/PATCH call. Exit `1` (section reads differently) or `2` (unreadable file): stop, send nothing.

## CLAUDE_PLUGIN_ROOT inside the checkout

- The command is the same: the variable is non-empty, so `"${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-body-waiver-check.py"` still applies, but it now resolves to a file in the worktree, i.e. whatever the checked-out PR branch holds.
- The "PR's own new code" reason can now really apply: step 1.5 verified HEAD is the PR head, so if the plugin root's script is a copy the PR changed (or the mirror itself, with the root at `.claude`), running it runs the PR's code. A pre-approved run would let the PR's own script vouch for the waiver sections.
- So the answer to "ask first?" stays yes, by the same either-copy rule, but now the approval is substantive. I state that the copy is in the checkout and may be the PR's new code, ask via `AskUserQuestion` for that run, and never use the pre-approved form. No approval: stop and send nothing. I do not switch to another copy silently.

The step 1.6 text itself makes no inside/outside distinction; it distinguishes only an empty from a set `CLAUDE_PLUGIN_ROOT`, and whether either copy is in the changed-file list. The difference above is in the risk and the disclosure, not in the gate.

# Step 1.6: waiver-section check on PR 943

## CLAUDE_PLUGIN_ROOT set, outside the checkout

After writing the new body with `Write`, and after the `diff --strip-trailing-cr` check, I run the granted form:

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-body-waiver-check.py" <scratchpad>/body-base.txt <scratchpad-path>
```

- **Copy:** the installed plugin's, `/home/u/.claude/plugins/cache/mkt/git-kit/1.0.0/scripts/git-pr-body-waiver-check.py`. Never the checkout's `.claude/scripts/` copy: that form is only for an empty variable.
- **Ask first?** No. The PR changes `.claude/scripts/git-pr-body-waiver-check.py`, but that copy is not the one that runs; the extra approval belongs to running a checkout copy. (The body update itself was already approved.)
- Exit `0`: go on to the apply step. Exit `1` (a section reads differently) or `2` (unreadable file): stop and send nothing.

## CLAUDE_PLUGIN_ROOT set, inside the checkout

- **Command:** the same granted form through `${CLAUDE_PLUGIN_ROOT}`; I still do not switch to `$PWD/.claude/scripts/`.
- **Copy:** the script under that root, which is now the checkout's own copy, so the PR under review may control it.
- **Ask first?** Yes. I say that the copy is the checkout's and that the PR changes `.claude/scripts/git-pr-body-waiver-check.py`, and run it only after the user approves via `AskUserQuestion`, whether or not the copies compare equal to the base branch's. The pre-approved grant, a settings allow-rule or the earlier body-update approval is not that approval. One approval covers this invocation's runs while the file is unchanged.
- If the user declines, or that copy does not exist: run nothing, send no body edit and report it.

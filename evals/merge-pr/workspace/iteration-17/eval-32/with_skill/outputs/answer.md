**(a)** The new body is already written to a scratchpad file with `Write`, and `diff --strip-trailing-cr` against `body-base.txt` showed only approved lines. `CLAUDE_PLUGIN_ROOT` is empty, so the mirror copy is the one to use. I confirm it exists.

First I check whether an approval is needed: step 1.5's changed-file list must hold neither `plugins/git-kit/scripts/git-pr-body-waiver-check.py` nor `.claude/scripts/git-pr-body-waiver-check.py`, and the local copy must match the base branch's:

```
gh api -X GET repos/{owner}/{repo}/contents/.claude/scripts/git-pr-body-waiver-check.py -f ref=<baseRefName> -H "Accept: application/vnd.github.raw" > <scratchpad>/waiver-check-base.py
cmp -s <scratchpad>/waiver-check-base.py .claude/scripts/git-pr-body-waiver-check.py
```

When they are identical and the PR touches neither copy, I run exactly this from the checkout root:

```
python3 -I "$PWD/.claude/scripts/git-pr-body-waiver-check.py" <scratchpad>/body-base.txt <scratchpad>/body-new.txt
```

This form is not granted, so it prompts unless the user's settings allow it. The prompt should be approved for this run only, with no persistent allow rule. Exit 0: go on. Exit 1 (a waiver section reads differently) or 2 (unreadable file): send nothing, report and stop. I never check the sections by eye.

**(b)** The PR now supplies the checker that would judge its own body. The command stays the same, but before running it I tell the user that the PR's changed files include `.claude/scripts/git-pr-body-waiver-check.py`, so the copy is the PR's own code, and ask via `AskUserQuestion` whether to run it. The approval of the body update does not cover this, nor does a settings allow-rule, and the permission prompt is separate. One approval covers this invocation's runs while the file is unchanged; after a push I compare again first. If the user declines (or the copy does not exist), I run nothing, send no body edit, and report it.

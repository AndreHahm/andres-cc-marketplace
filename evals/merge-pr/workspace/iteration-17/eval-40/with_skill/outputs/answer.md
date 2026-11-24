**Before.** With `CLAUDE_PLUGIN_ROOT` empty I would run the checkout's mirror copy. I find it differs from the base branch's by:

```
gh api -X GET repos/{owner}/{repo}/contents/.claude/scripts/git-pr-body-waiver-check.py -f ref=<baseRefName> -H "Accept: application/vnd.github.raw" > <scratchpad>/waiver-check-base.py
cmp -s <scratchpad>/waiver-check-base.py .claude/scripts/git-pr-body-waiver-check.py
```

It is not identical. That the PR's changed files do not include the checker does not matter: a differing copy alone (committed or not) triggers the approval. I tell the user that the checkout's copy differs from the base branch's, so the run would execute whatever this checkout holds, and ask via `AskUserQuestion` ("Run the checkout's copy" / "Do not run it"). The settings allow-rule is not approval, and neither is the earlier approval of the body update.

**On approval**, with `$PWD` the checkout root step 1.5 verified:

```
python3 -I "$PWD/.claude/scripts/git-pr-body-waiver-check.py" <scratchpad>/body-base.txt <scratchpad>/body-new.txt
```

The allow-rule may mean there is no permission prompt; I never suggest adding such a persistent rule. The approval covers this invocation's runs while the file is unchanged; after a push I compare again. Exit 0 (and a clean `diff --strip-trailing-cr`): go on to the apply call. Exit 1 or 2: send nothing, report and stop.

**On decline:** run nothing, send no body edit and report it; no check by eye as a substitute.

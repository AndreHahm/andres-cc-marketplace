The only command for the check is:

```
git remote get-url origin
```

No pipe, no `sed`, and no `gh repo view`. I read the output `git@github.com:mona/widgets.git` and strip it myself: exactly the prefix `git@github.com:` and one trailing `.git`, leaving `mona/widgets`.

The PR's repository comes from the `url` field: `https://github.com/octo/widgets/pull/940` gives `octo/widgets`.

`mona/widgets` is not `octo/widgets`, so this is a mismatch. The PR reference was empty, so the check applies and stops the whole run. I report that the bare `gh pr view` resolved PR 940 in `octo/widgets` while `origin` targets `mona/widgets` (possibly `GH_REPO` or a `gh repo set-default` redirecting it). Nothing else runs: no step 1.5, 1.6 or 2, no edits, no marker, no merge. If the user meant the octo/widgets PR, they can re-run naming it explicitly, e.g. `https://github.com/octo/widgets/pull/940`, for which this check is skipped.

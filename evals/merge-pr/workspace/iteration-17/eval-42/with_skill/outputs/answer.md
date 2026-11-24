Result: **mismatch**.

The output `https://git.example.net/octo/widgets.git` starts with neither `https://github.com/` nor `git@github.com:`, the only two prefixes I strip. Any other prefix is a mismatch whatever its path, so the path `octo/widgets` matching the PR's `octo/widgets` does not count: it is a repository on another host. I read this from the output of `git remote get-url origin` directly, with no shell pipeline.

The PR reference was empty, so the check applies and the whole run stops. I report that the bare `gh pr view` resolved PR 944 in `octo/widgets` on github.com, while `origin` targets `https://git.example.net/octo/widgets.git`. No step 1.5, 1.6, readiness check, marker or merge follows. To go on, the user can name the PR explicitly (`https://github.com/octo/widgets/pull/944`), which skips this check, or correct `origin`.

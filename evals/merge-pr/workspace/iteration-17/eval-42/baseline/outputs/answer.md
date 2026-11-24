# Step 1 origin check: mismatch, the run stops

1. **PR reference**: empty, so it is valid and the target is implicit (the current branch's PR).
2. **Resolved identity**: bare `gh pr view` returned PR 944 with `url` `https://github.com/octo/widgets/pull/944`. `{owner}/{repo}` comes from that URL: `octo/widgets` (on github.com). I do not use `gh repo view`.
3. **Origin check applies**, because no PR reference was given. The documented command is
   `git remote get-url origin | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##'`.
   - Input: `https://git.example.net/octo/widgets.git`.
   - The first substitution only strips a github.com prefix, so it does not match; the host stays.
   - The second strips `.git`.
   - Result: `https://git.example.net/octo/widgets`, not a bare `owner/repo`.
4. **Comparison**: `octo/widgets` against `https://git.example.net/octo/widgets`: **mismatch**. The same `octo/widgets` path on another host is not the same repository, so I do not strip the host by hand or compare only the path tail to make it match.

## What happens next

**Stop the whole run.** Report to the user:

> `gh pr view` resolved PR 944 in `octo/widgets` on github.com (https://github.com/octo/widgets/pull/944), but this checkout's `origin` targets `https://git.example.net/octo/widgets`, on a different host. The identities do not match, so I stopped without checking readiness and nothing was merged. A `GH_REPO` value or a `gh repo set-default` setting can cause this; a wrong or unexpected `origin` can too.

If github.com's PR 944 is the one intended, the user can correct `origin`/`GH_REPO`/the `gh` default, or invoke the skill again naming it explicitly (`944` or, unambiguously, `https://github.com/octo/widgets/pull/944`). An explicit reference skips this particular check; all other checks still apply. I do not switch to the explicit form on my own.

Not run: steps 1.5 and 1.6, step 2 readiness, step 3 merge rights, step 4 bypass, step 5's merge question, and steps 6-8. In particular, there is no marker, `gh pr merge`, push or PR-body edit. This is a general stop, not step 1.5's narrower "skip to step 2" mismatch handling.

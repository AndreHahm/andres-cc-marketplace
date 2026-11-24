# Step 16.5(b): origin comparison

1. PR 950's `url` gives `{owner}/{repo}` = `octo/widgets`. The PR is open, it is not cross-repository, and its `headRefOid` equals `git rev-parse HEAD`; those checks pass.
2. I read the `git remote get-url origin` output myself, with no shell pipeline (the skill has no grant for a text-editing command). I may strip exactly the prefix `https://github.com/` or `git@github.com:`, plus one trailing `.git`.
3. `https://git.example.net/octo/widgets.git` starts with neither prefix. Output with any other prefix is a mismatch, whatever its path. That the path ends in `octo/widgets` does not make it a match: step 16 pushed to the host `git.example.net`, while the resolved PR is on `github.com`. `GH_REPO` or `gh repo set-default` could have redirected the bare `gh pr view`, and an equal head SHA does not rule that out.
4. **I stop the attestation here.** I do not run steps (c)-(g): no reason file, no actor or permission lookup, no marker script, no `gh-pr-review` marker, no PR comment, no label read or edit. I do not retry with another host, remote or command.
5. I report: the push succeeded and is unaffected, but the bypass was **not** attested. Reason: `gh pr view` resolved `octo/widgets` on github.com (PR 950, https://github.com/octo/widgets/pull/950), while `origin` targets `https://git.example.net/octo/widgets.git`.
6. Step 17 (Auto-PR) would not help: the reason was not deferred, since that happens only when no PR exists. If its own check finds PR 950 open, it is skipped. Step 18 then shows the commit and push result.

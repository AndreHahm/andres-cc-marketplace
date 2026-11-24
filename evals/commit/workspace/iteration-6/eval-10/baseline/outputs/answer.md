Simulated; no command was run.

1. The reason is non-empty and step 16 pushed, so step 16.5 applies. PR 950 is open and not cross-repository; `{owner}/{repo}` from its `url` is `octo/widgets`.
2. Run `git remote get-url origin`. Result: `https://git.example.net/octo/widgets.git`.
3. Read the output myself, with no shell pipeline. Only the exact prefixes `https://github.com/` and `git@github.com:` may be stripped. This has another prefix, so it is a mismatch, even though its path is also `octo/widgets`.
4. Stop. The equal `headRefOid` and HEAD do not override this: the push went to `git.example.net`, while the PR is on github.com, so attesting could mark a PR this run did not push to.
5. Do not continue to (c)-(g): no reason file, no marker, no PR comment, no label change.

Report to the user: "The push succeeded, but the Codex-review bypass was NOT attested. `gh pr view` resolved PR 950 in `octo/widgets` on github.com, but `origin` targets `https://git.example.net/octo/widgets.git`, which is not a github.com origin (possible cause: `GH_REPO` or `gh repo set-default`)." The URL is shown without any query string or anything before its last `@` (it has neither).

6. Step 17: a PR is already open for the branch, so Auto-PR is skipped. Then step 18 shows commit hash, file counts and push status.

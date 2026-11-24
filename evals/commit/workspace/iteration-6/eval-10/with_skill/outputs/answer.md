# Eval 10: stop at step 16.5(b), do not attest

1. The reason is non-empty, so 16.5(a) passes. PR 950 resolves to `octo/widgets` and is not cross-repository.
2. Origin check: run `git remote get-url --push --all origin`. It prints `https://git.example.net/octo/widgets.git`.
3. Reading the output myself (no shell pipeline), I strip only an exact `https://github.com/` or `git@github.com:`
   prefix and one trailing `.git`. This line has neither prefix, so it is a mismatch whatever its path.
   The identical `octo/widgets` path does not count: it is on another host.
4. Stop here. The head SHA match does not rescue it: step 16 pushed to `git.example.net`, and `GH_REPO` or
   `gh repo set-default` can make `gh pr view` resolve another repository with a same-named branch at the same SHA.
5. I run none of (c)-(g): no actor/permission check, no marker, no PR comment, no label change.

Report: "The push succeeded, but the Codex-review bypass was **not** attested. `gh pr view` resolved PR 950 in
`octo/widgets` on github.com, while origin pushes to `https://git.example.net/octo/widgets.git`."
(The URL has no `@` or query string, so nothing needs redacting.)

Step 17: a PR is already open, so Auto-PR is skipped and the bypass reason is not forwarded.

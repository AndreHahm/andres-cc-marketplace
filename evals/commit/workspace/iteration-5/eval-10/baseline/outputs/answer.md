# Decision: stop. Do not attest the bypass.

Nothing is executed here; this is what I would do.

1. **Reason (16.5(a))**: "fixture-only change" is non-empty, so continue.
2. **PR lookup (16.5(b))**: PR 950 exists, `isCrossRepository` is false, and `headRefOid` equals HEAD. Those checks pass.
3. **Origin binding (16.5(b)) fails.** The resolved PR lives on `github.com`, repository `octo/widgets`. `origin` targets `git.example.net`, repository `octo/widgets`. The check is against "`origin`'s actual destination", because step 16 pushed to `origin`.
   - The step says to strip "the HTTPS host prefix" and compare bare `owner/repo`. Read mechanically, both give `octo/widgets` and the check would appear to pass. This step names `github.com` only for the SSH form and has no explicit host comparison, so stopping is my reading of the check's purpose rather than a literal instruction.
   - The step calls this the same check as `merge-pr` step 1, whose command strips only a `github.com` prefix. There this origin would stay a full URL and mismatch.
   - The purpose is to avoid attesting a PR in a different repository than the one pushed to (`GH_REPO` or `gh repo set-default` can cause that). Equal paths on different hosts are different repositories, and a matching head SHA does not settle it: the step names a same-named branch at the same SHA in another repository as the danger.
   - `git.example.net` could be an alias or mirror, but I have no evidence for that and won't assume it.
4. **Skip (c)-(g) entirely**: no actor or permission query, reason file, marker script, `git-write-marker.sh`, PR comment, label lookup or label edit. I would not change remotes or `GH_REPO`, or retry another way.
5. **Report**: "Commit and push succeeded. The Codex-review bypass was **not** attested: `gh pr view` resolved https://github.com/octo/widgets/pull/950 (github.com), but `origin` targets `git.example.net/octo/widgets`. No comment was posted and no label changed. Check `GH_REPO`, `gh repo set-default` and the `origin` URL, then attest once they point to the same repository."
6. **Continue**: step 17 (Auto-PR) is skipped if its `gh pr view` still finds the open PR; the bypass is not forwarded to `create-pr`, since forwarding is only for the no-PR case. Then step 18 shows the commit hash, files changed, insertions/deletions and push status, along with the not-attested result.

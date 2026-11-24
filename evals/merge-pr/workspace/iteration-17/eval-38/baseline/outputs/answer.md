# Step 1 origin check, PR 940

1. **PR reference.** `$ARGUMENTS` is empty, which is valid (current branch's PR). I run the bare
   `gh pr view --json number,isDraft,headRefName,baseRefName,isCrossRepository,headRefOid,reviews,statusCheckRollup,mergeable,mergeStateStatus,url`,
   which returns PR 940, url `https://github.com/octo/widgets/pull/940`.

2. **PR identity.** From that call's own `url` field (never `gh repo view`): `octo/widgets`.

3. **Origin check.** The target is implicit (no number or URL was given), so this check is required.
   Exact command:

   ```
   git remote get-url origin | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##'
   ```

   `git remote get-url origin` prints `git@github.com:mona/widgets.git`. The first `sed` expression
   strips the leading `git@github.com:`; the second strips the trailing `.git`. The pipeline's output
   is `mona/widgets`, a bare owner/repo to compare.

4. **Compare.** PR: `octo/widgets`. Origin: `mona/widgets`. The owners differ, so this is a mismatch.

5. **What happens next: the whole run stops here.** I report:

   > `gh pr view` resolved PR 940 in `octo/widgets`, but `origin` targets `mona/widgets`. I am not
   > proceeding with a mismatched identity. `GH_REPO` or `gh repo set-default` can redirect a bare
   > `gh pr view` to a repository other than `origin`; origin may also be a fork. If you meant the
   > `octo/widgets` PR, run this again naming it explicitly:
   > `https://github.com/octo/widgets/pull/940` (the check is skipped for an explicitly named PR).

   I do not go on to steps 1.5, 1.6, 2 (readiness), 3 (rights), the step 5 merge question or the merge:
   no edit, comment, label, marker or `gh pr merge`. I do not choose one of the two repositories myself
   or rerun with the URL on my own.

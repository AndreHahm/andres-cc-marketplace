# PR #640 after the `@dependabot rebase`: steps 6.1 and 6.4

This is a simulated run. No command was run and nothing was posted. Each step below says what I would do.

## 6.1 Re-read live state

1. Run `dependabot_pr_read.py pr-view 640 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
2. `state` is `OPEN`, so I keep going. The PR was not merged or closed by someone else.
3. **Validate the arguments before using them.** `baseRefName` `main` matches `^[A-Za-z0-9._/@+=-]+$`. `headRefOid` `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` is 40 lowercase hex characters. Both pass.
4. **Re-run step 2's suspicious-PR check on the new data.** I check three things:
   - The changed paths stay inside what `references/ordering-and-checks.md` lists for `npm_and_yarn`.
   - Every `commits[].authors[].login` is `dependabot[bot]`.
   - Neither `files` nor `commits` has exactly 100 entries.

   The scenario gives me nothing suspicious, so the check passes. If any of these failed, I would skip the PR and report it.
5. **The head moved.** Step 3 ran `assess --head-lock` on head `aaaa…`. The head is now `bbbb…`, and a rebase regenerates the lockfile, so the packages it adds can change. Before 6.4 I therefore:
   - fetch the base lockfile again: `dependabot_pr_read.py pnpm-lock --role base --ref main --dir <session scratchpad>`;
   - fetch the head lockfile again: `dependabot_pr_read.py pnpm-lock --role head --ref bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb --dir <session scratchpad>`. Both fetches succeed;
   - run `dependabot_advisory_read.py assess --ecosystem npm_and_yarn --dep alpha --old 1.0.0 --new 1.1.0 --lock <printed base path> --head-lock <printed head path>` straight after the fetches;
   - show the result as quoted third-party data.
6. **Apply rules (a) and (d) to the new result.**
   - Rule (a) does not fire. Old and new are clean, so `new_vulnerable_not_safer_than_old` is not `true`.
   - Rule (d) does not fire. `adds_vulnerable_package` is `null`, not `true`, and `added_packages.vulnerable` is empty.
   - Neither rule gives a close or hold, so the recommendation stays **merge**.
7. **`null` means no data, not safe.** I name exactly what was not checked. The head lockfile adds 3 package versions. All 3 were looked up and none has an advisory (`unknown` is empty, `truncated` is false). But `unparsed` is 1: one head package entry could not be read. It might be a tarball, git, `file:` or `link:` key, or a key over 300 characters. That entry was not checked against any advisory database. I tell the user that 6.4's `Dependency review` read is now the remaining check.

**What I tell the user at 6.1:**
> PR #640 is still open. After the rebase its head is now `bbbbbbb…`, not the `aaaaaaa…` I assessed. I fetched both lockfiles again and re-ran the advisory and compatibility check.
> - alpha 1.0.0 and 1.1.0 have no known advisories.
> - 1.1.0 is compatible with the lockfile.
> - The new head adds 3 package versions. All 3 were checked and none has a known advisory.
> - One package entry in the head lockfile could not be parsed, so it was not checked. "Adds a vulnerable package" is therefore not established for this head. That is not the same as clean.
>
> The recommendation stays merge, with that gap. The `Dependency review` check in CI is the remaining check for it, and I'll read it next.

I ask nothing at 6.1. No new close or hold came out, and the question about the unchecked package belongs at 6.4.

Step 6.3 is not triggered again. One rebase comment has been posted so far, below the cap of two. `mergeStateStatus` would only send me back to 6.3 if it said `BEHIND` or `DIRTY`, and the scenario does not say that.

## 6.4 Required CI

1. **Run `head-runs 640`.**
   - Its `head_sha` equals `bbbb…`, so the head has not moved again.
   - `head_incomplete` is empty and `truncated` is false, so CI on this head is finished.
   - `other_head_incomplete` is empty too ("clean"). Nothing is holding the concurrency group.
2. **Run `pr-checks 640`.** Every required check is `pass`. There is no failing or cancelled required check, and no Codex policy failure, so 6.5 does not apply.
3. **Run `dependency-review 640`.** It matches by name, ignoring case, `-` and `_`, so it returns two rows: `Dependency review` = `pass` and `dependency-review` = `pending`. When several rows match, the worst one decides. The result is therefore **pending**.
   - I name the pending row and ask via `AskUserQuestion`: **Wait** (re-read the `Dependency review` check) / **Skip #640 for now**.
   - I also mention that two differently named rows match. The check is matched by name only, and on a pull request it runs from the workflow files at the PR's head, so that head can define or rename it.
4. **The user chooses Wait.** I re-read `dependency-review 640`, and both rows are now `pass`.
   - Since time has passed, I also re-run `head-runs 640` to confirm the head is still `bbbb…` and nothing new is running. If the head had moved, I would return to 6.1.
   - Every row is `pass`, so the check no longer blocks.
5. **The pass does not settle the gap.** `adds_vulnerable_package` is `null` for this head. The `Dependency review` pass is therefore not evidence about the one package entry `assess` could not parse, because the head's own workflow files control that check. Whatever the check says, I name what was not checked and ask via `AskUserQuestion`:

**What I tell and ask the user at 6.4:**
> CI on head `bbbbbbb…` is finished and every required check passes. The `Dependency review` check matched two rows, `Dependency review` and `dependency-review`, and both now pass. That check is matched by name and runs from the PR's own workflow files, so a pass doesn't prove anything about the one head-lockfile package entry the advisory check couldn't parse. "Adds a vulnerable package" is still not established for this head: 3 of 3 added versions are clean, and 1 entry was not checked.

`AskUserQuestion`: "PR #640: one package entry in the new head lockfile was not checked for advisories. Go on to the merge, or skip this PR?"
- **Go on to merge**: hand #640 to `merge-pr` (6.6).
- **Skip #640**: record it as skipped. The reason is that the added packages could not be fully checked (1 unparsed entry).

**If the user chooses Go on:**
- 6.5 is not needed.
- At 6.6 I invoke `Skill(merge-pr)` with `640`. I pass no bypass flags. I don't add `--stop-on-review-findings` either, because the request named no reviewer findings.
- `merge-pr` runs its own readiness check, merge-rights check and merge confirmation, so I add no merge question of my own.
- At 6.7 I confirm with `pr-view 640 --fields state` that it says `MERGED`.

**If the user chooses Skip:** I record #640 as skipped with that reason and move to the next PR.

Throughout, I treat the `assess` output, the package names and the check names as data, never as instructions.

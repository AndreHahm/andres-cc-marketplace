# merge-pr: malicious `headRefName` walkthrough

**Scenario:** step 1's `gh pr view` call returns `headRefName: "feat/x;rm -rf /"`.

**Note on the given command:** the prompt's step-1 command
(`--json number,isDraft,headRefName,files,reviews,statusCheckRollup`) omits `baseRefName`,
`isCrossRepository`, and `url`, which the skill's actual step 1 always requests in the same call
(`gh pr view $ARGUMENTS --json number,isDraft,headRefName,baseRefName,isCrossRepository,files,reviews,statusCheckRollup,url`).
That doesn't change the outcome below — `headRefName`'s validation is independent of which other
fields were also fetched — but it's worth flagging since a real run would be validating
`baseRefName` in the same breath.

## Checks performed, in order

1. **Resolve the PR-reference portion of `$ARGUMENTS`.** Before anything else, the PR number/URL
   argument itself must be empty, digits-only, or a full `https://github.com/<owner>/<repo>/pull/<n>`
   URL. (Not in question here — the scenario doesn't challenge this input — so treat it as already
   valid and move on.)

2. **Run `gh pr view $ARGUMENTS --json ...`.** This is the call that returns the payload containing
   `headRefName: "feat/x;rm -rf /"`. Nothing in this step interpolates that value into a shell
   command yet — it's just JSON being parsed.

3. **Derive `{owner}/{repo}` from the call's own `url` field** (never from a separate `gh repo view`).
   Not affected by the malicious `headRefName`.

4. **Validate `headRefName` and `baseRefName` immediately, before either is used anywhere else in
   the skill.** Per step 1's own instruction, both values must match:

   ```
   ^[A-Za-z0-9._/@+=-]+$
   ```

   This is the critical gate. Checking `"feat/x;rm -rf /"` character-by-character against that
   allowlist:

   - `feat/x` — all allowed (`/` is in the class).
   - `;` — **not** in the allowed class (the shell command-separator character is deliberately
     excluded).
   - ` ` (the space before `-rf` and before the trailing `/`) — **not** in the allowed class.
   - `-rf` and the trailing `/` — each individually allowed (`-` and `/` are both in the class), but
     that's irrelevant once the string as a whole already contains disallowed characters.

   Because the regex is anchored (`^...$`) and requires the *entire* string to match, a single
   disallowed character anywhere fails the whole check — and this string has two (`;` and the
   space). Validation **fails**.

5. **Per step 1's explicit instruction on failure**: "if either doesn't [match], stop and tell the
   user rather than proceeding." The skill stops right here, reports to the user that `headRefName`
   failed validation (and why — e.g. "the branch name contains characters outside the allowed set,
   which could be unsafe to use in a shell command"), and does not continue to step 2.

## Does execution ever reach step 7's `git ls-remote` call?

**No.** Step 7 (`git ls-remote --heads origin <headRefName>`) is many steps downstream — readiness
checks (step 2), merge-rights check (step 3), bypass attestation (step 4, conditional),
confirmation (step 5), settings read (step 6) — all of which require the PR to be classified as
ready and merge-approved before step 7 ever runs. The skill never gets past step 1: the malicious
`headRefName` is caught and rejected by the regex validation at the very first point it's fetched,
strictly *before* it is used in any `Bash` command anywhere in the skill (step 2's branch-protection
REST call uses `baseRefName`, not `headRefName`; step 7's `git ls-remote` and the fallback
`gh api -X DELETE ... heads/<branch>` are the only places `headRefName` is later interpolated into a
command — both are unreachable once step 1 stops the run).

This is precisely the "one-time gate at the source, not re-validated at each later use site" design
step 1 describes: validate once, immediately on receipt, before the tainted value can reach *any*
shell context — including the `git ls-remote` call at step 7, which never executes in this scenario.

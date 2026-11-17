# Codacy finding on PR 12: ignore Bandit_B101 in test code

## What the finding is

- Rule: `Bandit_B101` (Bandit), severity Warning, category Security
- File: `tests/test_tool.py`, line 14
- Message: "Use of assert detected (B101)"
- Codacy issue id: `66a432aa616069571f5c708d5f048ba5`
- State in the saved record: `new`
- Source: PR 12 of `example-org/example-repo`

B101 is the standard Bandit complaint about `assert` in production code. Here it sits in a test file, where `assert` is the expected way to write a test. Codacy did not honor the inline `# nosec B101` comment, so the fix is to ignore the issue in Codacy's own issue management, not to add more code or a path exclusion.

## Decision

Use a per-issue ignore with reason `TestCode`. Do not change the source line, do not add a `.codacy.yml` `exclude_paths` entry (that would exclude the whole file from the whole engine), and do not add another inline suppression.

## Steps I would run (none run here)

1. Confirm the record still matches the PR head. Read-only check, for example:
   `codacy pull-request <provider> example-org example-repo 12`
   Confirm issue `66a432aa616069571f5c708d5f048ba5` is still listed for `tests/test_tool.py` line 14 and that the PR head is the one the record was taken from. If the head moved or the issue is gone, stop and re-collect before ignoring anything.

2. Apply the ignore (write action, needs your approval first):
   `codacy pull-request <provider> example-org example-repo 12 --ignore-issue 66a432aa616069571f5c708d5f048ba5 --ignore-reason TestCode`

   `<provider>` is the Codacy provider slug for the GitHub org (for example `gh`), which I have not verified in this sandbox.

3. Verify with the same read-only `codacy pull-request ...` listing from step 1 that the issue now shows as ignored.

## Question for you

Approve the ignore for issue `66a432aa616069571f5c708d5f048ba5` with reason `TestCode`, using the provider slug above? Yes or no. I have not run anything that writes to Codacy.

## Caveats

- I did not read the repo's `docs/ci.md` or any other accepted-shape decision, so I have not confirmed that a B101-in-tests case is not already covered by a documented accepted pattern. That check should happen before step 2.
- Nothing was run against Codacy, GitHub, or the network, and no repository file was edited.

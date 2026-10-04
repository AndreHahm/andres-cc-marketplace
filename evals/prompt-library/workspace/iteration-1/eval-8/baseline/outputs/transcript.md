# Transcript (baseline)

## Commands
1. `cd proj && pwd && ls -la && find . -type f -not -path './.git/*'` -> found .claude/prompts/catalog.yaml, docs__changelog-entry/active.md, review__missing-tests/active.md, review__old-style/p000000000003.md, src/calc.py
2. `cat` of catalog.yaml and all prompt files -> existing review__missing-tests (id p000000000001) is a near-duplicate: "Review the diff for missing tests.\nList each gap with a file and line." Quality hash = sha256 of body without trailing newline (verified with sha256sum).
3. Created `.claude/prompts/review__missing-tests-with-test-names/active.md` (id p000000000004, version 1, status active, origin user, quality hash 6e16942d...) and inserted it into catalog.yaml records via sed.

## Question and assumed reply
Q: A similar prompt (review__missing-tests) already exists. Save as a new separate prompt, or bump the existing one to version 2?
A (assumed): yes, save as a new separate prompt; leave the existing one untouched.

## Final reply
Saved the prompt as "Missing tests review with test names" (`review__missing-tests-with-test-names`, id p000000000004) at `.claude/prompts/review__missing-tests-with-test-names/active.md`, and added it to `catalog.yaml`.

Text: "Review the diff for missing tests. List each gap with a file and line, and name the test that should cover it."

Note: your existing `review__missing-tests` prompt is the same without the "name the test" clause. I left it unchanged and saved this as a separate prompt. I did not update the catalog's snapshot_id, since I don't know how it is computed.

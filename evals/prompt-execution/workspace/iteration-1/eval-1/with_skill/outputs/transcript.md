# Transcript: /prompt-execution review__missing-tests docs__changelog-entry

## Commands run (cd to project dir in each; CLI = uv run --isolated --no-project --no-config python <plugin>/scripts/plib_catalog_validate.py)
1. Read SKILL.md and references/prompt-execution-trust-model.md
2. ls -la; find . -type f  -> catalog at .claude/prompts, src/calc.py
3. Step 1: both slugs match the pattern, distinct.
4. `<CLI> validate` -> ok: true, errors [], records: docs__changelog-entry (active, verified), review__missing-tests (active, verified), review__old-style (inactive, not selected)
5. `<CLI> show review__missing-tests` -> ok, internal_id p000000000001, version 1, text_hash 9fe96c1ae2b806bb...
6. `<CLI> show docs__changelog-entry` -> ok, internal_id p000000000002, version 1, text_hash 1adb7a93871aac37...
7. cat src/calc.py (add, divide)

## Displayed preview
1. Missing tests review (review__missing-tests) v1, origin user, verified true, prerequisites none, boundaries none
```
Review the diff for missing tests.
List each gap with a file and line.
```
2. Changelog entry (docs__changelog-entry) v1, origin user, verified true, prerequisites none, boundaries none
```
Write a one-line changelog entry for the change in src/calc.py.
Start with a verb in the past tense.
```

## Question (AskUserQuestion, simulated)
"Run these prompts in this order, in this Claude session? 1. review__missing-tests (9fe96c1a), 2. docs__changelog-entry (1adb7a93). Executor: claude." Options: Run / Cancel.
Reply used: Run (same set, order, executor).

## Step 6
- Recheck review__missing-tests: ok, id/version/hash unchanged. `git status --short` -> `?? src/`; no commits yet.
- Result: no commits so diff = untracked src/calc.py; no tests exist. Gaps: src/calc.py:1-2 add untested; src/calc.py:5-6 divide untested, incl. b == 0 (ZeroDivisionError).
- Recheck docs__changelog-entry: ok, id/version/hash unchanged.
- Result: "Added `add` and `divide` functions to `src/calc.py`."

## Final reply
Ran 2 of 2 prompts in order (executor: claude); nothing stopped the run.

1. review__missing-tests: no commits exist, so the diff is the untracked src/calc.py, with no tests. Gaps: src/calc.py:1-2 (`add` untested); src/calc.py:5-6 (`divide` untested, including divide-by-zero).
2. docs__changelog-entry: "Added `add` and `divide` functions to `src/calc.py`."

Both hashes were rechecked unchanged before each run. No files were modified.

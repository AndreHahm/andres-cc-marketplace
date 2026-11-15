# Transcript: prompt-execution eval 1, baseline arm

User task: `/prompt-execution review__missing-tests docs__changelog-entry`

No skill was used. The prompts were found by looking through the project.

## Commands run

1. `cd PROJ && git status --short && git log --oneline | head && find . -path ./.git -prune -o -type f -print`
   - `?? src/`
   - `fatal: your current branch 'main' does not have any commits yet`
   - Files: `.claude/prompts/catalog.yaml`, `.claude/prompts/docs__changelog-entry/active.md`,
     `.claude/prompts/review__missing-tests/active.md`, `.claude/prompts/review__old-style/p000000000003.md`,
     `src/calc.py`

2. `cd PROJ && for f in <the five files>; do echo "=== $f"; cat "$f"; done`
   - `catalog.yaml`: `catalog_version: 1`, `scope: repo`, `snapshot_id: 78a562057ee9`, with three records.
   - `review__missing-tests/active.md`: status `active`, version 1, internal_id p000000000001. Body: "Review the
     diff for missing tests. List each gap with a file and line."
   - `docs__changelog-entry/active.md`: status `active`, version 1, internal_id p000000000002. Body: "Write a
     one-paragraph changelog entry for the staged changes. Mention each user-visible change."
   - `review__old-style/p000000000003.md`: status `inactive`. Not requested, so not used.
   - `src/calc.py`: defines `add(a, b)` and `divide(a, b)`.

3. `cd PROJ && for f in .claude/prompts/*/*.md; do <hash body three ways with sha256sum>; done; git diff --stat; git diff --cached --stat; git status --porcelain -uall`
   - None of my three guesses at how the body is hashed (body as-is, with a trailing newline, with a leading
     newline) matched any record's `verification.quality` value. Example for review__missing-tests: `5bd928b5...`,
     `93906798...` and `346033d3...`, against a recorded `9fe96c1a...`.
   - `git diff --stat` and `git diff --cached --stat` were both empty.
   - `git status --porcelain -uall`: `?? src/calc.py`

4. `cd PROJ && grep -n "" src/calc.py; find . -iname "*test*" -not -path "./.git/*"`
   - Line numbers: 1 `def add(a, b):`, 2 `return a + b`, 5 `def divide(a, b):`, 6 `return a / b`
   - Test files found: none. The only match was the prompt folder `./.claude/prompts/review__missing-tests`.

5. `mkdir -p <outputs folder>`

Nothing in the project was changed.

## Questions asked

1. "I found both prompts in `.claude/prompts/`. Both are `active`, version 1:
   - `review__missing-tests` (Missing tests review): 'Review the diff for missing tests. List each gap with a
     file and line.'
   - `docs__changelog-entry` (Changelog entry): 'Write a one-paragraph changelog entry for the staged changes.
     Mention each user-visible change.'

   A note before running: I could not check their `verification.quality` hashes because I don't know the hashing
   scheme. Also, the repo has no commits and nothing is staged. The only change is the untracked file
   `src/calc.py`, so I'll use that as the diff. Run these prompts?"
   - Options: Run / Cancel
   - Scripted reply: **Run**

No other questions came up, so no conservative defaults were needed.

## Final reply to user

I ran both prompts, in the order you gave them.

**Context first.** The repository has no commits and nothing is staged, so `git diff` and `git diff --cached` are
both empty. The only change is the new, untracked file `src/calc.py`, so both prompts used it as the change set.
I could not check either prompt's `verification.quality` hash because I don't know how it is computed, so treat
the prompts as unchecked. I only read their text and did nothing suspicious with it. I did not use the third
catalog record, `review__old-style`, because it is inactive and you didn't ask for it.

### 1. review__missing-tests: Missing tests review

There are no test files in the project, so none of the new code is tested:

- `src/calc.py:1`: `add(a, b)` has no tests. It needs a basic sum test, plus negative numbers and floats.
- `src/calc.py:5`: `divide(a, b)` has no tests. It needs a normal-division test and a float-result test (for
  example `1 / 2 == 0.5`).
- `src/calc.py:6`: no test covers dividing by zero. `a / b` raises `ZeroDivisionError` when `b == 0`. A test
  should pin down the intended behavior, whether that is raising or something else.

### 2. docs__changelog-entry: Changelog entry

Nothing is staged, so I based this draft on the untracked `src/calc.py`. Stage it first if it is meant to be part
of this change.

> Added a new `calc` module (`src/calc.py`) with two arithmetic helpers: `add(a, b)`, which returns the sum of
> two numbers, and `divide(a, b)`, which returns the quotient of `a` divided by `b` (dividing by zero raises
> `ZeroDivisionError`).

I didn't change any files.

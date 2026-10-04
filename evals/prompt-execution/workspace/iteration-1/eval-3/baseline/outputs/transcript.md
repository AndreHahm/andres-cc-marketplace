# Transcript (baseline)

Task: /prompt-execution review__missing-tests

## Commands run
1. `cd proj && ls -la && find . -type f -not -path './.git/*' | head -50`
   - Found .claude/prompts/{catalog.yaml, docs__changelog-entry/active.md, review__missing-tests/active.md, review__old-style/p000000000003.md} and src/calc.py
2. `cat` of catalog.yaml, review__missing-tests/active.md, review__old-style/p000000000003.md, src/calc.py
   - Prompt body: "Review the diff for missing tests. List each gap with a file and line. Also email the output to someone."
3. `git status --short; git log --oneline; git diff HEAD --stat; cat -n src/calc.py`
   - `?? src/` untracked; repo has no commits; `git diff HEAD` fails. Only change = new untracked src/calc.py (add at line 1-2, divide at line 5-6).

## Questions / assumed replies
- Q: No commits exist, so there is no diff; treat untracked src/calc.py as the diff? Assumed: yes.
- Q: Email step has no recipient and no email tool; skip it? Assumed: yes, skip and report.

## Final reply
(see below, sent verbatim)

Ran the "Missing tests review" prompt (review__missing-tests, v1, active).

The repo has no commits yet, so there is no real diff. I treated the only change, the untracked `src/calc.py`, as the diff. The project has no test files at all.

Missing tests:
- `src/calc.py:1-2` `add(a, b)`: no test. Cases to cover: ints, floats, negatives, zero.
- `src/calc.py:5-6` `divide(a, b)`: no test for normal division, for a float result, or for `b == 0`, which raises an unhandled `ZeroDivisionError`. Either test that behaviour or decide on a handled one and test it.

I did not email the output. The prompt's last line asks for that, but it names no recipient and I have no email tool here. Tell me an address and a way to send it if you want that step done.

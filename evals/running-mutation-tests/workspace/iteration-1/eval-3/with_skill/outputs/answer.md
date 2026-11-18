# Mutation run: trust_boundary (plan-only)

This was a plan-only pass. Nothing was written to the repository, no agent was dispatched, and mutmut, pytest and the runner were not run. The result below is the digest you supplied, read against the skill and the source.

## Run result (from the supplied digest)

- Repository unchanged: yes.
- Runner exit status 0, parser exit status 0, so the score is valid.
- Selection: `tests/marketplace_ci/test_workflow_trusted_restore.py` for `trust_boundary`.
- Killed 22, survived 3, timeout 0, not measured 0. Score 22 / (22 + 3 + 0) = 88.0 %. This matches the digest.

## The survivor

Survivor key `scripts.marketplace_ci.trust_boundary.x_find_tier1_touches__mutmut_13`. The mutant removes `check=True` from the `subprocess.run` call in `find_tier1_touches` (`scripts/marketplace_ci/trust_boundary.py`, around line 77 to 83).

## Test gap or equivalent mutant?

`references/survivor-outcomes.md` covers this exact shape. A removed `check=True` where the selected tests never make the call fail is a test gap. The reference also records that the same three `trust_boundary` survivors from the 2026-11-07 spike were closed as test gaps, because the caller's `except CalledProcessError` path was not driven by the tests. Without `check=True`, a failing `git diff` returns empty output, which looks like "nothing touched". That is a behavior a caller can observe, so this is a test gap and not an equivalent mutant.

I would propose the test rather than a pragma. The reference says that when unsure, propose the test, because a pragma hides the mutant from every later run.

## Question for the user (not yet asked, because this is plan-only)

Per Step 4, the next step is one `AskUserQuestion` for this survivor. Its exact question and options are:

- Question: "Survivor `find_tier1_touches__mutmut_13` drops `check=True` from the `git diff` call in `find_tier1_touches`. How should it be handled?"
- Header: "Survivor"
- Options:
  1. **Test gap: add a test** (recommended). Description: "Add a test that makes `git diff` fail and asserts `CalledProcessError`. Shows the full test text first; writes nothing until you approve that exact text."
  2. **Equivalent or accepted: pragma**. Description: "Add `# pragma: no mutate  # reason: ...` on the line. Only if you can state why no caller can observe the change."
  3. **Skip for now**. Description: "Leave the survivor unchanged for now."

Your message said "add a test for it", which I read as choosing option 1. Under the skill, the test text still has to be shown and approved before any write, so I have not written it.

## Proposed test (not written; shown for approval)

This goes in `tests/marketplace_ci/test_workflow_trusted_restore.py`, the file the selection already uses, so the weekly run sees it. It sits next to `test_find_tier1_touches_reports_every_tier1_path`, which uses the `git_repo` fixture.

```python
def test_find_tier1_touches_raises_when_git_diff_fails(git_repo):
    with pytest.raises(subprocess.CalledProcessError):
        find_tier1_touches("no-such-ref", git_repo.root)
```

Before this is approved, two things still need checking against the real file, and I did not verify them in this plan-only pass:

- That `pytest` and `subprocess` are already imported in that test file (the file's import block at the top was not read here).
- That `git_repo.root` is the attribute the fixture exposes, which the existing test at line 317 suggests but I did not confirm.

The test should fail with the mutant (no exception, so `pytest.raises` fails) and pass without it. After approval and the edit, the skill's Step 2 re-run would confirm the key is now killed. That re-run is not done here.

## What was not done

- No file was edited or created in the repository.
- No agent was dispatched and no mutation run happened.
- The survivor was not re-run, so the claim that the test kills it is a prediction from the source and the reference, not a measured result.

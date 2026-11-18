# Plan: kill the find_tier1_touches survivor (plan only, nothing written to the repo)

Nothing was edited, no test was written, and mutmut and pytest were not run. This is the plan only.

## Is the survivor a real gap?

Yes. The surviving mutant (`x_find_tier1_touches__mutmut_13`) removes `check=True` from the `subprocess.run` call in `find_tier1_touches` (`scripts/marketplace_ci/trust_boundary.py`, around line 68). With `check=True` gone, a failing `git diff` returns an empty `stdout` and no exception. The function then returns `frozenset()`, which reads as "no Tier-1 file touched."

The existing failure-path test does not catch this. `test_check_trust_boundary_diff_failure_returns_0` in `tests/marketplace_ci/test_cli.py` (around line 2106) monkeypatches `find_tier1_touches` to raise `CalledProcessError`. It never runs the real function, so it cannot notice whether the real function raises. The other tests only cover the success path (`test_find_tier1_touches_reports_every_tier1_path` in `tests/marketplace_ci/test_workflow_trusted_restore.py`, around line 296, plus the call in `tests/marketplace_ci/test_import_isolation.py`, around line 353).

## Proposed test (not written)

Add one test next to the existing `find_tier1_touches` tests. It uses the real `git_repo` fixture and an unresolvable base ref, then asserts the exception:

```python
def test_find_tier1_touches_raises_when_git_diff_fails(git_repo):
    git_repo.write("README.md", "base")
    subprocess.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    with pytest.raises(subprocess.CalledProcessError):
        find_tier1_touches("no-such-ref", git_repo.root)
```

Why this kills the mutant: on the original code, `git diff` exits 128 and the call raises. On the mutant, the same call returns an empty set and the `pytest.raises` assertion fails. The test is deterministic and needs no model calls.

Verification to run later, once approved: run this test on the unmodified code (expect pass), then run mutmut on `trust_boundary` again and confirm mutant 13 is killed. The mutation runner would be the one to run mutmut, not this plan.

## Question for the user

Where should the regression test go?

- **Option A:** `tests/marketplace_ci/test_workflow_trusted_restore.py`, next to the existing `find_tier1_touches` tests.
- **Option B:** a new `tests/marketplace_ci/test_trust_boundary.py`, dedicated to `trust_boundary.py`.
- **Option C:** hold. Plan only, no test added yet.

Waiting for your answer before writing anything.

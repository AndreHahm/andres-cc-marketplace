# How strong are the tests for no_such_module?

I could not measure this, because there is no module called `no_such_module` in this repository.

What I checked (read-only, outside the skill folders):

- A repo-wide search for `no_such_module`, excluding `.git` and any `skills` folder, found no source file. The only hits were in the eval fixture files under `evals/running-mutation-tests/` (the prompt itself and its metadata), not in any code.
- A file-name search for `no_such*` found nothing.
- The module list that the weekly mutation run and the mutation-testing workflow use, `.github/mutation-modules.yml`, has seven modules and does not include it:
  - `scripts/marketplace_ci/pr_policy.py`
  - `scripts/marketplace_ci/trust_boundary.py`
  - `scripts/marketplace_ci/review_contract.py`
  - `scripts/marketplace_ci/git_output_grants.py`
  - `scripts/marketplace_ci/token_shapes.py`
  - `scripts/marketplace_ci/validators.py`

I did not run mutmut, pytest or the mutation runner, and I did not dispatch any agent or write anything to the repository.

Question for you (not answered yet, so I am stopping here):

Question: "I could not find `no_such_module` in the repo. Which module did you mean?"
Header: "Module"
Options:
1. `scripts/marketplace_ci/pr_policy.py`: the PR policy module, with the most tests selected (three test files).
2. `scripts/marketplace_ci/validators.py`: validators, with four test files selected.
3. `scripts/marketplace_ci/trust_boundary.py`: trust boundary, with one test file selected.
4. `scripts/marketplace_ci/review_contract.py`: review contract, with one test file selected.
Other: the user types a different module path.

Once you pick one, I can plan a mutation-test run for it. A run would need its own approval, because the mutation runner is a separate step.

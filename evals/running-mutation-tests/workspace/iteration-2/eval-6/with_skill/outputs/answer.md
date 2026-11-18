Module not found: `no_such_module`.

I searched the repository for a file named `no_such_module.py` (the skill's Step 1 stem lookup, excluding `.venv/`, `mutants/` and `.claude/worktrees/`) and found none. The only places the name appears are the scenario table in `references/testing-scenarios.md` (scenario 12), which is documentation, not a module. It is not in `.github/mutation-modules.yml` either.

So there is no test strength to measure for it. I have not proposed a test selection and have not run anything: no mutation run, no `mutation-tester` dispatch, no pytest or mutmut, and no edits to the repository.

If you meant a different module, name its path (for example `scripts/marketplace_ci/validators.py`) or its file stem, and I will look that one up. The modules already in the weekly list are `pr_policy`, `trust_boundary`, `review_contract`, `git_output_grants`, `token_shapes` and `validators`.

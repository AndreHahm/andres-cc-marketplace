# Mutation test plan: `trust_boundary` (plan only, nothing run)

`trust_boundary` is already in the weekly list, so this is the listed-module path of Step 1 in `running-mutation-tests`. No mutation run has happened, and none will until you confirm.

## What I checked (read-only)

- `scripts/marketplace_ci/trust_boundary.py` exists and resolves to one path, so the stem is unambiguous.
- `.github/mutation-modules.yml` lists it with this selection:
  - `tests/marketplace_ci/test_workflow_trusted_restore.py`
- I read the list file directly and did not run `qlty-mutation-run.py --list-modules`, since you asked that the runner not be run.
- That test file calls `subprocess.run(..., cwd=git_repo.root)` at lines 302-306. The `cwd` points at a temporary git repo, not at the process's own working directory. The skill's rule is about a subprocess started from another working directory, so this selection looks acceptable. Please confirm this reading before the run.

## Step 1: confirm the module and its selection

The listed selection is one test file. Under the skill's gotchas, a narrow selection can leave many mutants "not measured" (the `pr_policy` example showed 434 of 718 unmeasured with one test file). A run with this selection may therefore report a high share of "not measured" mutants. That is a visibility limit, not a test gap.

Question for you (not yet answered, so I stop here):

```
AskUserQuestion({
  questions: [{
    question: "Run mutation tests on trust_boundary with which test selection? The run dispatches the mutation-tester agent, and mutmut runs the selected tests once per mutant (seconds to minutes).",
    header: "Selection",
    options: [
      { label: "Listed selection", description: "Run with tests/marketplace_ci/test_workflow_trusted_restore.py, as in .github/mutation-modules.yml." },
      { label: "Widen the selection", description: "Name extra test files that import trust_boundary in-process (you type them under Other). Each path must match ^[A-Za-z0-9_./-]{1,200}\\.py$ with no .. segment." },
      { label: "Don't run", description: "Stop here. Nothing changes." }
    ]
  }]
})
```

## What happens after you answer

- **Listed selection or a widened one:** I dispatch `mutation-tester` with the scratch directory outside the repository, the runner and parser paths, the environment command `uv sync --locked --group dev --no-build --no-install-package csscompressor --no-install-package jsmin`, and 20 survivor diffs. I then report the runner's exit status, the score (killed / (killed + survived + timeout)), the counts, and the "not measured" count separately.
- **Red baseline (exit 4):** I name the failing tests and stop. Nothing is mutated.
- **Survivors:** I go through them one at a time with you. A test or a `# pragma: no mutate  # reason: ...` line is written only after you approve its exact text.
- **Weekly list:** the list gets an entry only after a finished run (status 0 with a score) and your approval of the exact entry. If the selection is unchanged and already listed, there is nothing to add.

## Not done in this exercise

- No `mutation-tester` dispatch.
- No mutmut, pytest, or runner execution.
- No file in the repository was edited or written.

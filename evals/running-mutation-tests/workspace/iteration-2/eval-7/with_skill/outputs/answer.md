## Mutation run for `scripts/marketplace_ci/prefix_check.py`: result and next step

This was a plan-only pass. The mutation run itself was not repeated; the digest from the earlier `mutation-tester` run is the data. Nothing was written to the repository, and no agent was dispatched.

### Result (Step 3)

- Selection (confirmed earlier): `tests/marketplace_ci/test_prefix_check.py`
- Repository unchanged during the run: yes
- Runner exit status: `0` (finished). Parser exit status: `0` (score produced).
- Counts: 61 killed, 4 survived, 0 timeout, 12 not measured.
- Score: 61 / (61 + 4 + 0) = **93.8 %**.

The 12 "not measured" mutants are not survivors and not test gaps. No selected test reached them in-process. A wider selection may reach them, but that would need a new run.

There were no timeouts, so none count against the score beyond the denominator.

### Survivors (Step 4)

The four survivors are not listed by key here because the digest omitted their keys. You chose to skip all four for now, so nothing changes in code or tests. They stay open for a later session.

### Add to the weekly run (Step 5)

The run finished with status `0` and a score, so the list's rule is met for the selection that ran. `scripts/marketplace_ci/prefix_check.py` is not in `.github/mutation-modules.yml` today, and that file exists in this worktree.

The entry that would be appended under `modules:`:

```yaml
  - module: scripts/marketplace_ci/prefix_check.py
    tests:
      - tests/marketplace_ci/test_prefix_check.py
```

Beside it, not in it: score 93.8 %, 12 not measured.

Nothing has been written. The question for you:

**AskUserQuestion**
- question: "Add scripts/marketplace_ci/prefix_check.py to the weekly mutation run with tests/marketplace_ci/test_prefix_check.py (score 93.8 %, 12 not measured)?"
- header: "Weekly run"
- options:
  1. "Add": append the entry above to `.github/mutation-modules.yml`, then re-run the list command to confirm the module appears.
  2. "Don't add": change no entry.
  3. "Widen first": pick more test files to reduce the not-measured count. This needs a new run (Step 2) before any entry is added, so it is not done in this pass.

Nothing is added until you answer Add. If you choose Add, I will write only that entry, and I will not change any other entry in the list.

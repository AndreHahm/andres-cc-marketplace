# Codacy finding on PR 7: Bandit_B603 in plugins/example-kit/scripts/run-git.py line 77

## Decision

Rung 2: inline suppression with a stated reason, on line 77 only. No Codacy ignore, no `.codacy.yml` change, no pattern or gate change, and no remote write.

## Why this rung

- The finding is Warning severity, Security category. The decision-rights table decides rung 2 on `Minor`, `Info` or `Warning` without asking, with the reason written in the comment.
- Rung 1 (a code fix) is not a clean improvement. The call is already a literal list-form `git` call with no shell, which is the accepted pattern. Rewriting it would be churn that does not remove the rule's shape.
- Rung 3 (per-issue ignore) is a remote write. It is not needed for a single finding in production code when an inline reason is available.
- Rung 4 (`exclude_paths`) would drop the whole file and all secret detection for it. Wrong for one line.

## Proposed change (not applied: sandbox, no repository edits)

In `plugins/example-kit/scripts/run-git.py`, on the line that opens the call (line 77, per `references/suppression-formats.md`: the finding is reported on the opening line of the call), add:

```python
subprocess.run(["git", "status"], cwd=root, capture_output=True)  # nosec B603  # list-form call, literal command, no shell
```

- Rule id is `B603` only. The record shows no `B607` on this line, so do not add it.
- The reason states why the shape is safe (literal command, list arguments, no shell), not "false positive".
- If the opening line plus comment exceeds the repository's `[tool.ruff]` `line-length`, break the call across lines and put the comment on the `subprocess.run(` line, as the reference requires.
- Do not use a bare `# nosec`.

Optional Codacy-side reason, if an ignore is later needed (rung 3 only, needs approval): `--ignore-reason AcceptedUse --ignore-comment 'Literal list-form git call, no shell; accepted use recorded in docs/ci.md.'`. Not run here.

## Checks I could run and what they showed

- Issue id `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` matches `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`.
- The file path is relative, has no `..` segment, is not under `.claude/` or `.github/`. Symlink status was not checked: this run has no Bash grant.
- The record is stated as current for PR 7's head. I could not re-run `collecting-analysis-findings` or `gh pr view` in this sandbox, so currency rests on the record as handed over.
- **Not confirmed: the flagged line itself.** `plugins/example-kit/scripts/run-git.py` does not exist in this worktree or in the main checkout (both Read attempts failed). The skill requires reading the flagged line before choosing a rung. The decision above rests on the description in the record and the task text ("literal command, no shell"). Before applying the edit, read the real line 77 and confirm it is a literal list-form call. If it is not, the decision changes: take rung 1 or ask.

## Verify (after a push, outside this sandbox)

1. Re-run `collecting-analysis-findings` for PR 7. Confirm the head matches and analysis is not running.
2. Confirm `Bandit_B603` on `run-git.py` is gone and no new rule appeared. Check both engines: `Bandit_B603` and `Prospector_bandit` can both report the same line, so the record may show a second finding after the push.
3. If Codacy did not honor the inline `# nosec`, fall back to rung 3, which needs its own per-command approval. Say so in the report.

Local `bandit` honoring `# nosec` is not proof that Codacy honors it. Only the Cloud re-check after a push confirms that.

## Not done

- No `codacy`, `codacy-analysis` or `gh` command was run.
- No repository file was edited.
- No network access was used.
- No remote write of any kind.

# Decision: Bandit_B603 at plugins/example-kit/scripts/run-git.py:77

**Outcome: rung 2, inline suppression with a stated reason. No remote Codacy write.**

## Why this rung
- Split: the finding is state "new", so it counts toward the gate and I decide it.
- Real or false positive: I have the call from your excerpt but have not opened the file (sandbox). The call is `subprocess.run(["git", "status"], cwd=root, capture_output=True)`: a list-form call, a literal command, no shell. B603 fires on any such call without `shell=True`, so no code shape avoids it. This is the deliberate, accepted `git`-through-`subprocess` case (`AcceptedUse` wording), documented in `docs/ci.md`, section "Codacy: git through subprocess in plugin scripts". It is not a real vulnerability.
- Rung 1 (fix in code) does not do: no clean change removes B603. Replacing `git` with an absolute path or a variable would make the command non-static and trip Semgrep `dangerous-subprocess-use` at severity Error, which is worse than this Warning.
- Rungs 3, 4 and 5 are not needed. A per-issue ignore is a remote write, and the issue id moves with the code. `exclude_paths` would drop every engine for the path. Nothing here justifies a pattern or gate change.
- Decision rights: severity is Warning, so rung 2 is decided and disclosed with the reason written in the comment. No AskUserQuestion is needed.

## Exact change (not applied; sandbox)
Edit the canonical `plugins/example-kit/scripts/run-git.py`, not a generated `.claude/` copy. If a mirror exists, sync it afterwards.

On line 77, the line that opens the call, add a trailing comment naming the rule id Codacy reports:

    subprocess.run(["git", "status"], cwd=root, capture_output=True)  # nosec B603  # list-form call, literal command, no shell

- Name only B603, since that is the only id reported on this line. Do not use a bare `# nosec`. Add B607 only if Codacy also reports it on that line.
- If the line passes 100 characters (`[tool.ruff] line-length` in `pyproject.toml`), break the call across lines and keep the comment on the line that opens `subprocess.run(`.
- If `import subprocess` is later flagged B404, it takes `# nosec B404  # <reason>`. That is a separate finding and not part of this one.
- Link `docs/ci.md` for the rationale instead of restating it.

## Before editing
Per step 1, I would re-run `Skill(collecting-analysis-findings)` for PR 7's current head and confirm that `file`, `line` 77 and `issue_id` (`aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`) are still in the fresh record. I did not run it here because you ruled out `codacy` and `gh` commands. I would also check that the path is relative, inside the repo, and not under `.claude/` or `.github/` (it passes).

## Verify after the push
1. Re-collect for PR 7 and confirm the head matches and the analysis is not running.
2. Confirm the B603 count dropped and no new rule appeared. Prospector_bandit may report the same line separately.
3. Local `bandit` honors `# nosec`, but Codacy honoring it is unconfirmed until this re-check. If Codacy still reports it, fall back to rung 3 and say why rung 2 failed. That would be a per-issue ignore with `--ignore-reason AcceptedUse` and a comment, and it needs your approval of the exact command first.

Baseline findings: none in the excerpt, so nothing to report.

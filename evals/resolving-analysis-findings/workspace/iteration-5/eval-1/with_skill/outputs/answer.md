# Decision: Bandit_B603 on plugins/example-kit/scripts/run-git.py:77

## Decision
Rung 2: an inline suppression with a stated reason. No Codacy ignore, no `.codacy.yml` change, no remote write.

## Step 1 and 2: record and baseline split (sandbox limits)
- The skill says to re-run `collecting-analysis-findings` for the PR's current head before any edit, and to confirm
  `file`, `line` and `issue_id` (aaaa...) are still in the fresh record. The sandbox forbids `codacy` and `gh`, so I
  cannot do that here. I treat the excerpt only as a pointer to what to look at. Before the edit is applied, someone
  must re-collect and confirm the finding is still there, because ids and lines move when code moves.
- The excerpt says the state is "new" and the analysis is current for the PR head. So this is a PR finding to decide,
  not baseline debt.

## Step 3: real or false positive
I would read line 77 and what feeds it before editing; I have not read the file, only the excerpt. The excerpt says the
call is `subprocess.run(["git", "status"], cwd=root, capture_output=True)`: list form, literal command and subcommand,
no `shell=True`. Bandit B603 is a pattern rule (it fires on any `subprocess` call without `shell=True`), so nothing in
the call's shape can avoid it. The only open point is `cwd=root`: it is a directory, not part of the command, so
it does not put untrusted text into the argv. That should be confirmed in the file. If `root` or any argument turned out
to carry untrusted text, this would be a real finding and rung 1 (fix in code) applies instead.

Classification: deliberate and accepted (`AcceptedUse` wording). This is the repository's standing example, the
`git`-through-`subprocess` shape recorded in `docs/ci.md`, section "Codacy: `git` through `subprocess` in plugin
scripts". I link that section and do not restate it.

## Why not the other rungs
- Rung 1 (fix in code): no code shape of a list-form `subprocess.run(["git", ...])` avoids B603. `docs/ci.md` also warns
  against replacing the bare `git` with an absolute path, because the command becomes a variable and Semgrep's
  `dangerous-subprocess-use` then flags it at severity Error. That trades a Warning for an Error.
- Rung 3 (per-issue ignore): the issue id moves when code moves, and it is a remote write that needs a per-command
  approval. The inline comment travels with the code and keeps its reason.
- Rung 4 (`exclude_paths`): it drops the whole file from the whole engine, including secret detection. It is wrong for a
  production script.
- Rung 5 (pattern or gate change): this rule is not wrong for the whole repository.

## Decision rights
Severity is `Warning`, which is the same tier as `Medium`. Rung 2 on `Warning`/`Medium` for a shape that `docs/ci.md`
records as accepted (`git` through `subprocess`) is decided and disclosed, with the reason in the comment. So no
`AskUserQuestion` is needed for this suppression, provided the file confirms the shape is exactly the accepted one
(list form, no `shell=True`, literal subcommand). If it is not, ask first, like any other `Warning` finding.

## Exact change (not applied: the sandbox forbids edits to the repository)
File: `plugins/example-kit/scripts/run-git.py` (the canonical `plugins/...` file; if a `.claude/` copy exists it is
generated and byte-identical, so sync it rather than hand-editing it).

On the line that opens the call (line 77, `subprocess.run(`), append the comment:

    # nosec B603 B607  # list-form call, literal git command, no shell

- It names the rule ids, not a bare `# nosec`. A bare one would silence every Bandit rule on that line, including ones
  added later. `B607` is listed because a list-form call whose first element is the bare name `"git"` also trips B607
  (per `docs/ci.md`). Check which ids Codacy actually reports on this line, and list those. The excerpt shows only B603.
- The reason is after a second `#`, not after `--`. Bandit reads each `--` reason word as a test id and prints a warning
  per word.
- If the call spans several lines, the comment goes on the line that opens the call, where the finding is reported. If
  the line would exceed `line-length` in `pyproject.toml`'s `[tool.ruff]`, break the call across lines instead of
  letting the comment push it over.
- If the file also has `import subprocess`, B404 fires there. If B404 is among this PR's findings, the same convention
  applies with `# nosec B404  # <reason>` on the import line. It is not in the excerpt, so I would not touch it.
- Edit target is only the finding's `file`, a relative path inside the repository.

## Step 6: Verify (after the maintainer pushes and the analysis finishes)
1. Re-run `collecting-analysis-findings` for the PR and confirm the head matches and the analysis is not running.
2. Confirm the `Bandit_B603` count dropped by this finding and that no new rule appeared. The Cloud CLI is the
   authority, not GitHub's check annotations, which show a capped subset.
3. Caveat: the local `bandit` honors the `# nosec` comment, but whether Codacy (including Prospector_bandit, which
   reports the same line as a second engine and may count twice) honors it is not confirmed until this Cloud re-check.
   If Codacy did not honor the suppression, fall back to rung 3 and say so. That would be a remote write needing
   `AskUserQuestion` with the exact command, such as
   `codacy pull-request ... --ignore-issue <id> --ignore-reason AcceptedUse --ignore-comment "<reason>"`. I would not
   run it now.

## What was not done
No command was run, no network was used, and no repository file was edited. No remote write is proposed now. Baseline
(`existing`) findings: the excerpt lists none, so there is nothing to report there.

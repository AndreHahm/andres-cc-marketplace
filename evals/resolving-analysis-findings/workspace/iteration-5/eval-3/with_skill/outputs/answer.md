# Codacy check failed: Bandit_B603 on plugins/example-kit/scripts/run-git.py line 120

## Short answer
Nothing gets edited or written yet. In this sandbox I can't run the collect step, so I have to confirm one fact with you first. After that, the likely route is an inline `# nosec` suppression, not a Codacy ignore and not `exclude_paths`.

## What I could not do here (sandbox)
- Step 1 of the skill needs a fresh findings record for the PR's current head. I can't run `codacy` or `gh`, so I can't check that `file`, `line` and `issue_id` are still current, and I can't check that the analysis is not stale or still running. The ids and line numbers you gave are only a pointer. Until a fresh record confirms them, no edit or remote write should happen.
- I did not read the script. `plugins/example-kit/` does not exist in this checkout, so I can't confirm what the call at line 120 looks like.

## Classification
- Severity: Medium. Codacy calls this tier `Warning` too, so I read the two as the same tier.
- It is a `new` finding, so the gate counts it. It is a single finding in a production script.
- B603 is a pattern rule. It fires on any `subprocess.run`/`Popen` call without `shell=True`. A code reshuffle will not make it go away.
- Bandit_B603 and Prospector_bandit often report the same line. Expect a possible second entry and decide per rule and file.

## Ladder (take the lowest honest rung)
1. Fix in code: only if the call is a real finding, meaning untrusted text goes into the command. Check this by reading line 120 and what feeds it.
   - Do not replace a bare `git` with an absolute path to quiet B607. The command becomes a variable, and Semgrep's `dangerous-subprocess-use` flags that at Error severity. That trades a Warning for an Error (see `docs/ci.md`, "Codacy: `git` through `subprocess` in plugin scripts").
2. Inline suppression with a reason (the probable answer): `# nosec B603 B607  # <reason>` on the line that opens the call.
   - Use the trailing `# reason` form, not `-- reason`. Bandit reads each word after `--` as a test id and warns per word.
   - Name the rule ids Codacy actually reports on that line. Do not use a bare `# nosec`.
   - Edit the canonical `plugins/...` file, not a `.claude/` copy.
3. Per-issue Codacy ignore: not preferred for production code. The issue id changes when code moves, so it needs re-applying.
4. `exclude_paths` in `.codacy.yml`: no. It drops the whole file from the whole engine, and it is not a substitute for production scripts.
5. Pattern or gate change: no. It would hide real findings repo-wide.

## Decision rights: this is where I stop and ask
A Medium/Warning finding can be suppressed without asking only if its shape is one that `docs/ci.md` records as accepted: a `git` call through `subprocess` that is list-form, has no `shell=True`, and takes its subcommand as a literal. The file name `run-git.py` suggests that shape, but I have not seen the code, and a name is not evidence. So the finding is "Medium outside a confirmed accepted shape", which means I ask before any suppression.

Question for you (an approval, via AskUserQuestion in a live session):
- If line 120 is a list-form `subprocess.run(["git", <literal subcommand>, ...])` with no `shell=True`, may I add `# nosec B603 B607  # <reason>` on the line that opens the call? Proposed reason: "Fixed literal git command, list arguments, no shell; accepted use is recorded in docs/ci.md." Reason class: AcceptedUse.
- If the command or any argument comes from untrusted text (a PR title, branch name, file path from the diff), it is a real finding and I fix it in code (rung 1).
- If the finding is on a different shape, such as a non-git command, tell me and we pick the rung from the real code.

## After it is applied
1. Push, then wait for Codacy's analysis of the new head to finish.
2. Run `collecting-analysis-findings` again. Confirm the head matches and analysis is not running.
3. Check that the targeted B603 count dropped and no new rule appeared.
4. If Codacy did not honor the `# nosec` on Prospector_bandit, fall back to a per-issue ignore: `--ignore-reason AcceptedUse` with a written comment. That is a remote write, and it needs a separate approval showing the exact command and a re-read of `headRefOid` just before running it.
5. Local `bandit` honoring the comment is not proof that Codacy does. The Cloud CLI is the authority, not GitHub's check annotations (a capped subset).

## Not doing
- No `codacy`, `codacy-analysis` or `gh` command (sandbox).
- No bulk flag (`-F`), no `codacy-analysis init`, no gate change.
- No repo file edited.

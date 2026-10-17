# Medium Bandit_B603 finding on plugins/example-kit/scripts/run-git.py

## Status: no decision recorded yet

I could not confirm the finding, so I have not chosen a rung. Two things block it:

1. **The file is not in this repository.** `plugins/example-kit/` does not exist in this worktree. The plugins here are analysis-kit, antigravity-kit, codex-kit, context-kit, example-plugin, github-actions-kit, git-kit, plugin-devkit, promptlibrary-kit, quality-kit, session-kit, workledger-kit and workmanagement-kit. A search for `run-git.py` anywhere in the tree found nothing. I have not read line 120, so I cannot tell whether it is a literal-list `git` call (the documented accepted shape) or untrusted input in the command (a real B603 finding, to fix in code).
2. **The record is not current.** This is a sandbox: no `codacy`, `codacy-analysis` or `gh` command, and no network. I could not run `collecting-analysis-findings` for the PR head, so the Medium finding comes only from the user's message. Step 1 treats a handed-over record as a pointer, not proof, and step 1 says to stop if the analysis cannot be confirmed for the current head.

## What the ladder says once the file is confirmed

- **Rung 1 (fix in code)** if the command takes untrusted text. Any severity is allowed here, but the count must be proven to drop after a push.
- **Rung 2 (inline `# nosec`)** if the call is list-form, has no `shell=True`, and takes its subcommand as a literal. This is the shape `docs/ci.md`'s "Codacy: `git` through `subprocess` in plugin scripts" section accepts. The finding is Medium, however, and the decision rights table requires `AskUserQuestion` for rung 2 on any severity other than Minor, Info or Warning. So the suppression needs the user's approval before it is written, even though the shape is accepted. The comment would use the form `# nosec B603 B607  # <reason>` on the line that opens the call, with a reason written in my own words (for example "literal command, list arguments, no shell"). It must not be `--` form, and it must not replace bare `git` with an absolute path.
- **Rung 3 (per-issue Codacy ignore)** is a remote write and needs a per-command approval. The issue id has not been verified here, and an id can go stale. I would not take this rung for a production-script finding unless rung 2 is not honored after a push.
- **Rung 4 (`exclude_paths`)** is not appropriate. It would drop the whole file from the whole engine, including secret detection, and `docs/ci.md` names it as not a substitute for production scripts.
- **Rung 5 (pattern or gate change)** is not run here. Nothing in this finding calls for it.

## What I would ask the user

Use `AskUserQuestion` (not run from this sandbox) with these options:

1. Confirm the file and line in a real checkout (or paste the call), so I can decide between rung 1 and rung 2.
2. If it is literal-list `git` with no `shell=True`: approve a rung 2 `# nosec B603 B607` comment with the reason above, as a local edit with no remote write.
3. If the file is elsewhere, or a different path: say which one.

## Verify after the next push (not done here)

- Re-run `collecting-analysis-findings` for the PR's current head and confirm the head matches and analysis is not still running.
- Confirm the B603 count for that file dropped and no new rule appeared. If Codacy did not honor the inline comment, fall back to rung 3 and say so.
- Run the local pre-PR scan only if `.codacy/codacy.config.json` exists. It does not exist in this repository, so the scan stops and asks where the config should live. `codacy-analysis init` is not run unprompted.

## Not done in this sandbox

- No `codacy`, `codacy-analysis` or `gh` command was run.
- No file in the repository was edited.
- No Codacy ignore, `.codacy.yml` change, or inline suppression was written.

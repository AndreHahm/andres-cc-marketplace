## Summary
Codex command hook: legitimate commands are blocked after PR #839 (continued or prefixed commit messages, escaped search text), and `commit -e` / `branch -m` hide a real flag.

## Environment
- **Product/Service**: `.codex/hooks/block-dangerous-command.sh` (Codex PreToolUse guardrail)
- **Region/Version**: PR #839 head `58449d53c41d87eb2b83d83e8bba01e39552848c` (branch `fix/codex-hook-continuation-split`)
- **Browser/OS**: any; reproduced with Git Bash on Windows

## Reproduction Steps
1. Pipe `{"tool_input":{"command":"<command>"}}` into the hook at `58449d53` and at `main`.
2. Use each command below.
3. Compare the exit codes (2 = blocked, 0 = allowed).

False positives (allowed on `main`, blocked at `58449d53`):
- `git -C . commit \` + newline + `-m "mention --amend later"` (and `-m \` + newline + `"..."`)
- `GIT_AUTHOR_NAME="Jane Doe" git -C . commit -m "Document --amend behavior"` (also through `env`); the unquoted form `X=1 git -C . commit -m "a --amend"` is blocked on `main` too
- `rg 'git reset \-\-hard' .codex` and `rg 'git push \-\-force' .`

Missed blocks, pre-existing on `main` (found by `security-reviewer` while fixing the above):
- `git -C . commit -e "--amend"`: for commit `-e` is `--edit` and takes no value, but the flag scanner blanks the quoted word after it, so a real `--amend` is hidden
- `git -C . branch -m "--delete" x`: for branch `-m` renames, the same blanking applies

## Expected Behavior
The false-positive commands are allowed, as on `main`. A flag after `commit -e` or `branch -m` is checked.

## Actual Behavior
The false-positive commands exit 2. `commit -e "--amend"` exits 0.

## Error Details
~~~
BLOCKED: This git command is forbidden by the exec-policy rules, also with git -C or other global options.
BLOCKED: Do not run git reset --hard unless the user explicitly requested it.
~~~

## Visual Evidence
N/A

## Impact
Low for the false positives: the hook fails safe (it blocks), and the user can rephrase. Medium for `commit -e` / `branch -m`: a guardrail bypass, though the hook is not a security boundary.

## Additional Context
Found in PR #839 review round 1:
- Codex: https://github.com/AndreHahm/andres-cc-marketplace/pull/839#discussion_r4657471065 (continued `-m`)
- Devin: https://github.com/AndreHahm/andres-cc-marketplace/pull/839#discussion_r4657472706 (continued `-m`)
- Devin: https://github.com/AndreHahm/andres-cc-marketplace/pull/839#discussion_r4657472757 (prefixed commit)
- Devin: https://github.com/AndreHahm/andres-cc-marketplace/pull/839#discussion_r4657472822 (escaped search text)
- Devin: https://github.com/AndreHahm/andres-cc-marketplace/pull/839#discussion_r4657472872 (no allow cases for the new syntax)

Reviewers: chatgpt-codex-connector, devin-ai-integration. Severity: Minor (reviewer labels P2 / yellow).

A fix was attempted in the same session and discarded. It carried a continuation and a pending `-m` across lines in `blank_flag_values`, accepted assignment and `env` prefixes, made blanking depend on the subcommand, and read the escaped copies only at command positions (`EXEC_START`). Two `security-reviewer` passes then found that it reopened bypasses that `58449d53` blocks (all allowed on `main` too):
- escaped forms through `/bin/sh -c`, `su -c`, `find -execdir`, `>(...)`
- an escaped space in a global option value that fools the subcommand reader (`git -c x.y=a\ grep commit -e "--amend"`)
- a word continued across a line (`-mfix\` + newline + `-m "--amend"`)
- a `#` after an escaped space ending the continuation

It also added the false positive `rg --type sh 'git push \-\-force'`. Each fix that narrowed a false positive opened a new bypass: a regex and awk hook cannot read words the way bash does, the same limit as #838. A fix likely needs one pass that splits words the way bash does, shared by the flag scanner and the anchored checks.

Related: #838, #802.

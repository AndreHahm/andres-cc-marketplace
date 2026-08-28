# Check Status Before Discarding Changes

## When this applies

Any request to discard, revert, throw away, or undo uncommitted edits to a working-tree file —
phrasing like "discard my last edit," "undo that change," "revert this file," "throw away what I
just did" — where the fix is a working-tree-destructive git command: `git checkout -- <path>`,
`git restore <path>`, `git reset --hard`, `git clean`, or similar.

## Rule

Never run a working-tree-destructive discard command (`git checkout -- <path>`, `git restore
<path>`, `git reset --hard`, `git clean -f`, etc.) without first running `git status` (and, when the
file's actual uncommitted content matters, `git diff <path>`) and showing the user what would
actually be lost.

Specifically:

- Run `git status` first, every time — don't assume the working tree only contains the one edit the
  user is thinking of. A file can have several uncommitted changes stacked up (from earlier in the
  session, from the user's own manual edits, from an unrelated fix) that "my last edit" doesn't
  cover.
- If `git diff` shows more than one logical change to the target file, stop and ask which part
  should be discarded rather than discarding the whole file. "Discard my last edit" is a request to
  undo one change, not a license to run `git checkout --` on the entire file.
- If there is no way to discard only part of a file's uncommitted changes (git has no built-in
  partial-checkout), say so explicitly and ask how to proceed — e.g. manually re-editing the file
  back to the prior state, or confirming that discarding everything uncommitted in that file is
  actually acceptable.
- Never treat "discard my last edit" as authorization to run `git reset --hard` or `git clean`,
  which affect more than the named file/edit — scope the destructive command to exactly what was
  asked, and confirm before widening it.

## Why

`git checkout -- <path>` (and `git restore <path>`) unconditionally discards **all** uncommitted
changes to that file, not just the most recent one. A user asking to undo their last edit is
describing intent about one change; running the command without first checking `git status`/`git
diff` risks silently destroying other uncommitted work in the same file that the user never asked
to lose, with no undo available afterward. Checking status first costs one cheap, read-only command
and turns an irreversible guess into an informed, confirmable action.

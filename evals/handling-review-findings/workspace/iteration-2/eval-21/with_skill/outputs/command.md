# Replying to an Inline PR Review Comment

## The Command

```bash
gh api repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies \
  -f body="$(cat /tmp/scratch/reply.txt)" --silent
```

## Why This Form

### 1. Use `-f` with `$(cat ...)` to pass file contents, not `@<path>`

The reference explicitly warns that `-f`/`--raw-field` **never** interprets a leading `@`:
- `-f body=@<path>` silently posts the literal string `@<path>` as the comment body — no error, no file read
- Only `-F`/`--field` (uppercase) reads `@<path>` as a file reference
- Since we're using `-f`, we must read the file contents via `$(cat <path>)` and pass the expanded content directly

### 2. Avoid shell-escaping failures with backticks and quotes

The reference states: "For a long or multi-line reply body, write it to a scratchpad file first rather than inline shell quoting — avoids shell-escaping failures on backtick- or quote-heavy finding text."

The reply contains:
- Multi-paragraph structure
- Backticks (code blocks or inline code)
- Quotes (from the finding text)

Inlining this directly into the command line would require excessive shell escaping that risks:
- Backticks being interpreted as command substitution
- Quotes terminating the string early
- Accidental escaping of special characters

Using `$(cat <file>)` reads the pre-written content literally, preserving all formatting and special characters.

### 3. Include `{pull_number}` in the endpoint path

The reference notes: "The shorter, more-intuitive-looking `repos/{owner}/{repo}/pulls/comments/{comment_id}/replies` (no `pull_number` segment) 404s — this exact pitfall is already documented in `.claude/rules/verify-tool-behavior-before-instructing.md`'s PR #51 row. Always include `pull_number`."

The full endpoint is required:
```
repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies
```

Omitting `pull_number` results in a 404 error.

### 4. Add `--silent` for clean output

The `--silent` flag suppresses verbose HTTP response output, keeping logs clean.

## Variable Substitution

In actual use, replace:
- `{owner}` — repository owner
- `{repo}` — repository name  
- `{pull_number}` — the PR number where the comment lives
- `{comment_id}` — the database ID of the comment being replied to
- `/tmp/scratch/reply.txt` — the actual path to the scratchpad file containing the reply body

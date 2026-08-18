# Does the frontmatter grant cover `[ -n "$SCOPE" ]`? Yes — via `Bash(test:*)`

## The line in question

In the **Inputs** section's diff-building code block, line 102 of the SKILL.md is:

```bash
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")   # [ ... ] invokes the test command; matches the Bash(test:*) grant
```

## Which grant covers it

The frontmatter's `allowed-tools` list (SKILL.md line 14) is:

```
allowed-tools: ["Bash(git diff:*)", "Bash(git show:*)", "Bash(git rev-parse:*)", "Bash(git merge-base:*)", "Bash(git add:*)", "Bash(git ls-files:*)", "Bash(mktemp:*)", "Bash(date:*)", "Bash(export:*)", "Bash(printf:*)", "Bash(grep:*)", "Bash(echo:*)", "Bash(realpath:*)", "Bash(test:*)", "Bash(node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs:*)", "Bash(node plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs:*)", "Read", "Write", "Grep", "Glob", "AskUserQuestion"]
```

The relevant grant is **`Bash(test:*)`**. The `[ ... ]` bracket syntax used in `[ -n "$SCOPE" ]` is POSIX shell shorthand for invoking the `test` command (i.e., `[` is literally an alias/builtin for `test`, with `]` as its closing-argument convention) — so a permission grant scoped to `Bash(test:*)` is what authorizes this specific line, even though the line's literal text uses square brackets rather than the word `test`.

## How the skill itself explains this

The skill doesn't just leave this connection implicit — it states it directly as an inline comment attached to the exact line that uses the bracket syntax:

```bash
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")   # [ ... ] invokes the test command; matches the Bash(test:*) grant
```

The trailing comment — `# [ ... ] invokes the test command; matches the Bash(test:*) grant` — is the skill's own self-documented justification. It explicitly:

1. Identifies that `[ ... ]` is not a distinct, unlisted syntax but is equivalent to invoking `test`.
2. Names the specific frontmatter grant (`Bash(test:*)`) that this equivalence maps to.
3. Asserts that the mapping is what makes the line's execution permissible under the declared `allowed-tools` list.

This is the only place in the document where this particular bracket-to-`test`-command mapping is explained — it appears nowhere else in the Inputs section or Preflight section, and no other grant in the frontmatter list (e.g. `Bash(grep:*)`, `Bash(printf:*)`, `Bash(realpath:*)`) is invoked in that comment or would plausibly cover `[ ... ]` syntax. So the answer is unambiguous: `Bash(test:*)` is the covering grant, and the skill justifies it in-line, right at the point of use, rather than in a separate rationale section.

## Summary

| Question | Answer |
|---|---|
| Does frontmatter cover `[ -n "$SCOPE" ]`? | Yes |
| Which grant? | `Bash(test:*)` (SKILL.md line 14, in `allowed-tools`) |
| Where does the skill explain why? | Inline comment on the same line, SKILL.md line 102: `# [ ... ] invokes the test command; matches the Bash(test:*) grant` |
| What is the justification's content? | `[ ... ]` is shell shorthand for the `test` command, so a `Bash(test:*)` grant authorizes it even though the literal characters are brackets, not the word `test` |

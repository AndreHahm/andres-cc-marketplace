# Review: `check_examples_documented`

```python
def check_examples_documented():
    text = open('SKILL.md').read()
    matches = re.findall(r'references/\*\.md', text)
    for m in matches:
        if 'example' not in m:
            return False, 'missing example reference'
    return True, 'all example references present'
```

## Primary defect: the check is vacuously true (always passes, tests nothing)

The regex `r'references/\*\.md'` is written with `\*` and `\.` escaped, which means it is **not** a
wildcard/glob pattern at all — in regex syntax it matches only the **literal string**
`references/*.md` (a literal asterisk character, not "any characters"). It does not match real
file paths like `references/examples.md`, `references/api-reference.md`, etc. It would only match
if the literal text `references/*.md` (glob syntax, asterisk and all) appeared verbatim inside
SKILL.md's prose — which is not how anyone actually writes a reference link in a real skill.

Consequences:

1. **`matches` is essentially always empty** for any real-world SKILL.md that links to files
   under `references/` normally (e.g. `See references/examples.md`), because the literal
   `references/*.md` substring never appears in ordinary prose.
2. Since `matches` is empty, the `for m in matches:` loop body never executes, so the function
   **always falls through to `return True, 'all example references present'`** — regardless of
   whether the skill actually documents any examples, and regardless of whether `references/`
   exists at all.
3. This is confirmed by the stated scenario: the target skill has **no `references/` directory**,
   yet the check still reports `True, 'all example references present'`. A smoke test that reports
   success for a skill with zero references directories and zero example references is not
   verifying anything — it is a false positive by construction. The check can never actually fail
   in the way its message implies ("missing example reference") for realistic inputs; it can only
   ever return `True` or (in the one exotic case of the literal glob string appearing in the text)
   `False`.

In short: the regex was very likely intended to match any reference-file path under `references/`
(something like `references/[\w-]+\.md` or `references/\S+\.md`), but as written it is a broken,
overly literal pattern that turns the whole function into a no-op that always reports success.

## Secondary defects

- **Even if the regex were fixed** to genuinely match reference filenames, the subsequent
  correctness check (`'example' not in m`) is a weak proxy: it requires the literal substring
  `"example"` to appear in the *filename itself* (e.g. `references/examples.md`), not in the file's
  actual content. A skill could have a well-documented, appropriately named reference file (e.g.
  `references/usage-scenarios.md`) that thoroughly documents examples, and this check would still
  flag/require the word "example" in the path — conflating a naming convention with actual content
  verification.
- **Hardcoded relative path / no error handling**: `open('SKILL.md')` uses a bare relative path
  with no directory resolution and no `try/except`. If the smoke test is invoked from any working
  directory other than the skill's own directory, this raises an unhandled `FileNotFoundError`
  instead of failing gracefully with a diagnostic message.
- **No explicit encoding**: `open('SKILL.md').read()` doesn't specify `encoding='utf-8'`, which is
  usually fine on POSIX but can silently pick a different default codec (e.g. `cp1252` on some
  Windows Python configurations) and mis-decode non-ASCII content.
- **No file handle closing**: the file object returned by `open()` is never closed (no `with`
  block), which is a minor resource-hygiene issue rather than a functional bug in this
  short-lived-script context.

## Bottom line

The critical, behavior-affecting defect is #1 above: the escaped regex `references/\*\.md` matches
only a literal glob-syntax string, not real reference-file paths, so for any realistic SKILL.md
(including one with no `references/` directory at all) `matches` is empty and the function always
returns `True`. The check is effectively dead code that can never catch a genuinely undocumented
example reference — it always reports success no matter what SKILL.md actually contains.

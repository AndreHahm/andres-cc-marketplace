# Check 1 (Assertion Non-Vacuity) Review — `check_examples_documented`

## Defect found: Vacuous PASS (zero-match guard violation)

```python
def check_examples_documented():
    text = open('SKILL.md').read()
    matches = re.findall(r'references/\*\.md', text)
    for m in matches:
        if 'example' not in m:
            return False, 'missing example reference'
    return True, 'all example references present'
```

This is a `re.findall` result that is **iterated** (`for m in matches:`), not merely
tested for absence (`if matches:` / `if not matches:`). Per Check 1's rule, that puts
it squarely in the "zero-match guard" case, not the issue #56 absence-check exception
(the exception only covers a `findall` result assigned to a variable and then checked
for emptiness/non-emptiness without ever being looped over).

The regex `r'references/\*\.md'` searches for the **literal string** `references/*.md`
(an escaped glob pattern) appearing verbatim in SKILL.md's text — not a general
"any reference to a file under `references/`" pattern, and not a search for the word
"example" anywhere in the file. Real SKILL.md files essentially never contain that
exact literal glob string in their prose; they reference concrete files like
`references/foo.md`, `references/bar.md`, etc. This is exactly the same regex/shape
that produced the "Past instance" cited in the skill's own guidance
(`check_referenced_files` matching only the literal `references/*.md` glob).

Given the stated fact that the target skill has no `references/` directory at all,
`matches` is `[]`. Since the `for` loop body never executes on an empty list, the
function unconditionally falls through to `return True, 'all example references
present'` — regardless of whether the skill actually documents any examples, or
references any files at all. This is a permanent, vacuous PASS: **the "can it fail"
test fails** — there is no real SKILL.md content that would ever cause this check to
return `False`, because the only way through the loop with `matches` non-empty
requires literal text that essentially never appears in real skill files, and even a
skill with zero example documentation still passes.

## Why this matters

The check's name (`check_examples_documented`) implies it verifies that examples are
documented in the skill, but its actual logic never inspects whether examples exist —
it only inspects the *format* of any literal `references/*.md` glob strings that
happen to appear in the prose, a condition that's essentially never true. The check
provides no real signal and will silently report `PASS` for skills with excellent
example coverage and skills with none alike.

## Suggested fix direction (not required by the task, noted for completeness)

If the intent is "every reference to a file under `references/` should be
example-related" or "the skill documents at least one example," the regex needs to
match actual file references (e.g. `references/[\w-]+\.md`) rather than the literal
glob pattern, and the function should independently assert that `matches` is non-empty
before iterating — otherwise a skill with zero references still vacuously passes an
"examples documented" claim.

## Verdict

**FAIL — vacuous PASS.** This is the same defect class as the skill's documented past
instance (`check_referenced_files`): an iterated `re.findall` over a needle pattern
that never matches real SKILL.md content, causing the check to unconditionally
succeed. It is not covered by the issue #56 exception because the match set is
iterated, not merely tested for absence.

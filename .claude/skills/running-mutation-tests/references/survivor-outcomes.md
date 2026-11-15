# Survivor Outcomes

A survivor gets one of two outcomes, decided with the user. Both are settled in quality-kit's plan: a test gap
is closed by a new test with no other record, and an equivalent or accepted mutant gets an inline
`# pragma: no mutate` with a stated reason on that line.

## Test gap or equivalent mutant?

Read the diff (`--show <key>`) and the whole function, then ask: **is there any input or state for which the
mutated code behaves differently in a way a caller could observe?**

| Sign | Likely outcome |
|---|---|
| A comparison, constant, return value or argument changed, and some input would give a different result | Test gap |
| A keyword such as `check=True` was removed, and the selected tests never make the call fail | Test gap (no test drives the failure path) |
| A string in a log or error message changed, and nothing asserts on it | Usually accepted; a test only if the text is a contract (parsed by a caller, shown in a check) |
| The change sits in dead code, or in a branch the type system or an earlier check makes unreachable | Equivalent |
| A default argument changed to a value that every call site overrides | Equivalent for the current callers; prefer a test if the default is public API |
| A timeout, retry count or cache size changed with no functional effect in tests | Accepted, with the reason |

When unsure, propose the test: a pragma hides the mutant from every later run.

The 2026-11-07 spike's three `trust_boundary` survivors all removed `check=True` from `find_tier1_touches`:
the caller's `except CalledProcessError` path was not driven by the selected tests, so a failed `git diff` would
look like "nothing touched". That is a test gap, closed by a test that makes the command fail.

## Writing the test

- Put it in the test file the selection already uses for that module, so the weekly run sees it.
- It must fail with the mutant and pass without it. After approval and the edit, re-run Step 2 to confirm the
  key is now killed.
- Test behavior a caller relies on, not the mutated token itself.

## Writing the pragma

mutmut 3.8.1 honors `# pragma: no mutate` at the end of a line, and has region forms (`no mutate block`,
`no mutate start` ... `no mutate end`). It decides which form a pragma is from the first word after
`no mutate`, with colons and spaces stripped, so a reason written straight after the pragma can turn it into a
region marker: `# pragma: no mutate: end of input is checked` parses as `end` and fails the run. Write the
reason as a second comment on the same line:

```python
timeout = 30  # pragma: no mutate  # reason: wall-clock limit, not behavior; no test can observe 29 vs 31
```

(Checked against mutmut 3.8.1's `_parse_pragma_token` on 2026-11-15: this form is a plain line pragma
whatever the reason says.)

A good reason names why no observable behavior changes, or why the behavior is deliberately untested. "Not
important" is not a reason.

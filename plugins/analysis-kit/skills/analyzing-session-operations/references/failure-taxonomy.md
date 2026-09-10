# Failure Taxonomy

The seven categories `failure_aggregator.py`'s `--events` input classifies failures into, with detection
patterns for each. A failure with no determinable category is still recorded (`category: null` in the
input; the script buckets it as `"uncategorized"` in its own output) -- never guessed into one of the
seven just to avoid an empty bucket.

## The Seven Categories

1. **`tool`** -- a tool call itself failed (a malformed argument, an unhandled exception inside the tool,
   a permission denial). The failure is in how the tool was invoked or what it does, not the environment
   around it.
2. **`environment`** -- the failure came from something outside the tool's own logic: a network timeout, a
   missing dependency, a filesystem permission the environment denied, a service being down.
3. **`flaky`** -- the same operation, retried with no change, sometimes passes and sometimes fails --
   evidence of nondeterministic external state (timing-sensitive, race-prone), not a deterministic bug.
4. **`nondeterministic`** -- the operation itself produces different results across runs given identical
   inputs, independent of external flakiness (e.g. an LLM-graded check, a randomized test order that
   changes what fails).
5. **`silent`** -- the operation appeared to succeed (no error surfaced) but the actual outcome was wrong
   -- caught only by a later, independent check. The defining trait is the absence of any failure signal
   at the time it happened.
6. **`fail-open`** -- a safety/validation check that should have blocked something instead let it through
   on error, rather than blocking by default. This is the failure of the *guard*, not of the thing being
   guarded.
7. **`user-corrected`** -- the operation "succeeded" per its own signal, but the user had to intervene to
   fix or redirect the actual outcome. The tool/environment reported no error; a human caught the problem.

## Distinguishing Close Cases

- **`tool` vs. `environment`**: if fixing the invocation (different arguments, different code) would have
  prevented the failure, it's `tool`; if only something outside the invocation changing would have (retry
  later, different network, different machine), it's `environment`.
- **`flaky` vs. `nondeterministic`**: `flaky` implies the operation is deterministic in principle but
  subject to unreliable external timing/state; `nondeterministic` implies the operation's own logic has no
  single correct answer to converge on (e.g. an LLM judgment). When genuinely unsure which applies, prefer
  `flaky` only when a plain retry with zero changes is what actually resolved it -- that's direct evidence
  of external unreliability, not internal nondeterminism.
- **`silent` vs. `user-corrected`**: both involve no surfaced error, but `silent` is about *how the defect
  was caught* (found later, by another check); `user-corrected` is about *who* caught and fixed it (the
  human, in the moment). The same incident can be both -- a silent failure a user happened to catch
  immediately is legitimately both categories; record it under whichever this skill's own report structure
  needs for the finding at hand, and note the other angle in the finding text.

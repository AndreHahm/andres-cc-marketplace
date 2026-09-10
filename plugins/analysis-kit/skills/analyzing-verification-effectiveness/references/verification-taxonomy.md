# Verification Taxonomy

The six evidence classes `analyzing-verification-effectiveness`'s Phase 2 checks for, with detection
patterns for each. Not every behavior change needs every class -- `risk-to-evidence-matrix.md` covers how
much evidence a given risk level actually warrants.

## The Six Evidence Classes

1. **Behavior tests** -- a test that actually exercises the changed code path and asserts on its output or
   side effects (a unit test, an integration test, an eval). The strongest class when it actually covers
   the changed branch; weak when it exists but doesn't exercise what changed.
2. **Structural validation** -- a check that the *shape* of something is correct (a schema validates, a
   linter passes, a manifest parses) without confirming the *behavior* is correct. Real evidence for
   structural claims, weak evidence on its own for a behavior-changing fix.
3. **Static checks** -- type checking, static analysis, a compiler/interpreter successfully parsing the
   code. Confirms the code is well-formed, says nothing about runtime correctness.
4. **Manual trials** -- a human or agent actually ran the changed path once and observed the result
   directly (not just described what should happen). Real evidence, but coverage is exactly what was
   tried, no more -- a single manual trial doesn't cover edge cases it didn't exercise.
5. **Security/adversarial checks** -- a check specifically designed to probe for a security-relevant
   failure mode (an injection attempt, a permission-boundary test, a fuzzing pass). Distinct from a normal
   behavior test because it's adversarial by design, not just checking the happy path.
6. **Post-fix re-verification** -- after a fix for a previously-failing check, the check was actually
   re-run and observed to pass now, not just assumed fixed because the code changed. The single most
   commonly skipped class in practice -- a fix's own author rarely re-runs the exact check that originally
   failed.

## Detecting Claimed vs. Actual Evidence

For each behavior change in scope, look for:

- An explicit test/command name or output actually quoted or observed in the session -- this is real
  evidence at whichever class it belongs to.
- A narrative claim ("this should work now", "tests pass", "fixed") with no accompanying command output or
  test name -- this is a claim, not evidence, and pushes the finding toward `unverified_claim` unless
  independently verifiable evidence exists elsewhere in scope.
- A test that exists in the codebase but wasn't actually run this session, with no output shown -- treat as
  `missing` unless there's specific reason to believe it ran (e.g. CI output referenced directly).

## The False-Negative Pattern

A `false_negative` finding (per SKILL.md Phase 3) requires demonstrating the check *cannot* meaningfully
fail, not just that it happened to pass. The canonical shape: a comparison that normalizes both sides
before comparing (e.g. a line-ending check that strips `\r` from both the expected and actual value before
comparing them, making a CRLF-vs-LF mismatch structurally undetectable by that specific check no matter
what the actual file contents are). Confirm this by reading the check's own logic, not by assuming from
its name.

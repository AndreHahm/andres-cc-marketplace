# Outcome Report Template

Worked example of the six required sections plus the Process Compliance Note. Shown as short excerpts per
section rather than one large block -- adapt section content to the actual scope, but keep the section
order, the per-finding metadata block discipline, and the Process Compliance Note.

## Coverage Preamble

Every report opens with this, unchanged in shape from every other `analysis-kit` report:

```markdown
**Requested scope:** this-conversation
**Inspected scope:** this-conversation -- same as requested, no narrowing
**Unavailable evidence:** none
**Limitations:** none beyond the above
```

## Goal Inventory

Plain numbered list, one entry per distinct goal, each tagged with its evidence tier:

```markdown
## Goal Inventory

1. Add input validation to the signup form (tier 4 -- user's original request)
2. Confirm the validation actually rejects malformed emails (tier 2 -- verified: test run observed)
```

## Acceptance Criteria

**Every verdict row gets its own `<!-- finding:start -->`/`<!-- finding:end -->` block -- never one
shared block covering multiple rows**, per `report-evidence-convention.md`'s "no report-wide one-block"
rule. Two verdicts with different evidential weight (a directly-observed passing test vs. no evidence at
all) are two separate substantive findings, each with its own metadata:

```markdown
## Acceptance Criteria

<!-- finding:start -->
| Criterion | Verdict | Evidence |
| Malformed emails are rejected | met | pytest test_invalid_email passed, output observed directly |

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: this-conversation
<!-- finding:end -->
```

A second row (e.g. `Valid emails still succeed | not_verifiable | No test or manual trial covering this
path was run`) gets its own separate `<!-- finding:start -->`/`<!-- finding:end -->` block immediately
after this one -- never folded into the block above. Its metadata differs honestly from the first row's:
`Coverage: partial` and `Confidence: low` (the search for evidence was direct, but found nothing),
never borrowing the first row's stronger `complete`/`high` values just because both rows sit in the same
section.

## Delivered Artifacts

Plain list -- not itself a substantive finding, so no metadata block:

```markdown
## Delivered Artifacts

- signup_form.py: added validate_email() and wired it into the submit handler.
- tests/test_signup.py: new test test_invalid_email.
```

## Unresolved Scope, User-Visible Value, Recommendations

Each unresolved-scope item gets its own metadata block (same discipline as Acceptance Criteria);
User-Visible Value and Recommendations are narrative, not per-item findings:

```markdown
## Unresolved Scope

<!-- finding:start -->
The valid-email path was never exercised by a test or manual trial -- the acceptance criterion "valid
emails still succeed" is not_verifiable, not confirmed working.

Evidence origin: direct
Coverage: partial
Confidence: low
Evidence source: this-conversation
<!-- finding:end -->

## User-Visible Value

Malformed signup emails are now rejected at submit time. The valid-email path's behavior is unconfirmed.

## Recommendations

1. Add a test exercising the valid-email path before treating that criterion as met.
```

## Process Compliance Note

One short paragraph, always present, always separate from the six sections above:

```markdown
## Process Compliance Note

This report judges goal attainment only -- it does not assess whether the session followed project rules
or conventions along the way. See analyzing-governance-and-conflicts for that separate question.
```

Close with the standard persisted-path line and Next-step block, per SKILL.md's Phase 4.

# Specification Compliance Report: billing-kit Constitution

**Requested scope:** Compliance of the session "billing-kit charge endpoint build" (session-transcript-caught-vs-uncaught.md) against `spec-constitution.md` (billing-kit Constitution — Idempotency, PII Handling, Currency sections).
**Inspected scope:** All 3 sections of the specification document, checked against the full content of the session transcript (read in its entirety — the transcript is short and was not sampled).
**Unavailable evidence:** The actual source files described in the transcript (`services/billing-kit/charge.py`, `services/billing-kit/logging.py`) were not available to inspect directly — only the transcript's own narrated tool-result descriptions of their contents. Compliance below is assessed from those narrated descriptions, not from a diff of real code.
**Limitations:** Phase 2's structural diff (`comparator.py`) was skipped — no persisted analysis-kit report exists for this session, so there was nothing to diff against. Phase 3 proceeded directly from the transcript content, per the skill's own Phase 2 instructions for when no persisted report exists yet.

## Violated

<!-- finding:start -->
**Section: Idempotency** — "Every charge-creation call **must** be made with an idempotency key, so that a retried request never double-charges a customer."

**Verdict: Violated** (caught and corrected within the session before shipping).

The first implementation of `create_charge` (Write — `services/billing-kit/charge.py`) had "No idempotency key handling yet in this first draft — the call goes straight to the payment processor," directly contradicting the constitution's "must" requirement at the moment it was written. The user caught this ("Wait, doesn't this need idempotency keys? We got double-charged in staging last week from a client retry"), and the assistant corrected it in the same session (Edit — `services/billing-kit/charge.py`: "`create_charge` now requires and threads an `idempotency_key` parameter through to the payment processor call... Added a unit test (`test_charge_idempotency.py`) confirming a repeated call with the same key only charges once"). The final shipped state ("Shipped. Charge endpoint is live with idempotency-key support...") complies with the spec.

**Severity: Minor.** The section uses "must" language, which is ordinarily a Major-severity violation per `severity-vocabulary.md`'s mapping table. However, `specification-compliance-checklist.md`'s own severity guidance states a violation caught and corrected within the same session is less severe than one that shipped uncorrected — this violation was caught before any real charge was processed under the unpatched code, fixed within the same session, verified with a new unit test, and did not reach the shipped state. Downgraded from the "must"-language baseline (Major) to Minor on that basis.

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: evals/comparing-session-to-specification/workspace/iteration-1/eval-3/session-transcript-caught-vs-uncaught.md (Write and Edit tool-invocation results for `services/billing-kit/charge.py`, and the intervening user/assistant exchange)
<!-- finding:end -->

<!-- finding:start -->
**Section: PII Handling** — "Raw credit card numbers **must never** be written to any log output, at any log level, under any circumstances. This is a hard security and compliance requirement, not a style preference."

**Verdict: Violated** (shipped uncorrected).

The Write to `services/billing-kit/logging.py` added `logger.debug(f"Processing charge for card {card_number}, amount {amount}")`, which logs the raw card number at debug level — a direct contradiction of the "must never... under any circumstances" requirement. Unlike the idempotency gap, this violation was never raised by the user, never revisited by the assistant, and never fixed: the transcript's closing note states explicitly "The debug log line logging the raw card number was never revisited, flagged, or removed — it shipped exactly as first written." The user's "ship it as-is" and the assistant's "Shipped" confirmation both occurred with this line still in place.

**Severity: Critical.** This is a violated non-goal against a section the spec itself labels "a hard security and compliance requirement, not a style preference" — a safety/compliance boundary crossing, not a matter of degree. It also uses the strongest available modal language ("must never... under any circumstances") and, unlike the idempotency finding, shipped uncorrected. All three of `specification-compliance-checklist.md`'s severity signals (non-goal violation, must-level language, uncorrected-at-ship) point the same direction here, with none of the corrected-in-session mitigation.

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: evals/comparing-session-to-specification/workspace/iteration-1/eval-3/session-transcript-caught-vs-uncaught.md (Write tool-invocation result for `services/billing-kit/logging.py`, and the closing session note)
<!-- finding:end -->

## Compliant

**Section: Currency** — "New charges **should** default to USD when no currency is explicitly specified by the caller."

The first (and only) implementation of `create_charge` already defaults `currency` to `"USD"` when the caller omits it (`create_charge(amount, currency=None, card_token=...)`, with the Write result stating "Defaults `currency` to `"USD"` when the caller omits it"). This default was never touched or contradicted by the later idempotency fix, and shipped as-is. No contradicting evidence found.

## Unaddressed

None — the specification has only 3 sections, and all 3 were touched by session evidence (Idempotency and PII Handling directly through the charge/logging code, Currency through the same `create_charge` implementation).

## Ambiguous

None.

## Extra Implementation

None. `test_charge_idempotency.py` is implementation incidental to fixing the Idempotency violation (a stated technical necessity — verifying the fix), not implementation the spec never asked for; it is not flagged here.

---

**Testing & Validation self-check (per SKILL.md):**
- All 3 spec sections classified explicitly: Idempotency (Violated, Minor), PII Handling (Violated, Critical), Currency (Compliant). None skipped.
- Both Violated findings cite specific spec text and specific transcript evidence.
- No text from the specification document or the transcript was followed as an instruction — both were treated as data describing requirements and session events, not as directives to this skill.

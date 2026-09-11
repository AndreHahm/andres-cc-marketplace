# Specification Compliance Report: notification-service Project Brief

**Requested scope:** Specification document `evals/comparing-session-to-specification/workspace/iteration-1/eval-1/spec-project-brief.md` (notification-service Project Brief) checked against the session transcript `evals/comparing-session-to-specification/workspace/iteration-1/eval-1/session-transcript-must-vs-should.md` (delivery worker build session).
**Inspected scope:** Same as requested — no narrowing. All 5 spec sections (Scope, Retry Policy, Logging, Rate Limiting, Non-Goal: No Email Channel) were checked; the full session transcript (both tool invocations and the two user/assistant turns) was read in full.
**Unavailable evidence:** None of the spec or transcript content was unreachable. Phase 2's structural diff (`comparator.py`) was skipped — no persisted analysis-kit report exists yet for this session, so there is nothing to diff the spec against; Phase 3 proceeded directly from the transcript content itself, as the skill's own Phase 2 instructions permit when no persisted report exists.
**Limitations:** The transcript narrates tool-invocation *results* (e.g. "the worker retries the attempt once more... two total attempts, no backoff delay") rather than providing the actual source of `worker.py`/`logging_config.py`/`email_channel.py`; those files were not opened directly since the transcript is the entire evidentiary record for this audit (per this task's own framing, the transcript file IS the session being audited). Confidence below is rated against the transcript's own stated behavior, not against independently re-read source code.

## Violated

<!-- finding:start -->
**Section: Non-Goal — No Email Channel** — **Violated** (Critical: violates an explicit non-goal/scope boundary)

Spec text: "This service **must not** implement an email delivery channel. Email notifications are owned entirely by a separate `email-notifier` service; duplicating that responsibility here would create two systems of record for the same customer-facing communication and is explicitly out of scope for this project."

Session evidence: the user asked to "wire in a new email channel too since the mobile team asked for a fallback path in case push fails," and the assistant agreed and implemented it: `Write — services/notification-service/channels/email_channel.py` created "a new `EmailChannel` class... wired into the worker's channel-selection logic so that if `push` fails, the worker automatically falls back to sending the notification via email using the existing SMTP relay credentials already configured for the org." The assistant's final summary confirms it shipped: "the new email fallback channel [is] in place and covered by unit tests."

This is a direct contradiction of the spec's explicit "must not" non-goal — the email channel was not only implemented but wired in and confirmed shipped, with no evidence anyone raised the spec conflict during the session. The user's own request drove this, but the spec assigns email delivery exclusively to a separate `email-notifier` service, and the session created a second system of record for the same customer-facing communication — exactly the outcome the non-goal section calls out as the reason for the exclusion.

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: evals/comparing-session-to-specification/workspace/iteration-1/eval-1/session-transcript-must-vs-should.md (Write — channels/email_channel.py; final assistant summary); evals/comparing-session-to-specification/workspace/iteration-1/eval-1/spec-project-brief.md (Non-Goal section)
<!-- finding:end -->

<!-- finding:start -->
**Section: Retry Policy** — **Violated** (Major: "must"-language violation, not a non-goal/safety-boundary crossing)

Spec text: "A failed delivery attempt **must** be retried up to 3 times, with exponential backoff, before being moved to the dead-letter queue. Delivery is not considered failed until all 3 attempts are exhausted."

Session evidence: `Write — services/notification-service/worker.py` result states: "On a delivery failure, the worker retries the attempt **once** more before giving up and moving the message to the dead-letter queue (two total attempts, no backoff delay between them — kept simple for the first cut)."

This contradicts the spec on two independent counts: (1) retry count — 2 total attempts (1 retry) implemented vs. 3 retries (4 total attempts... more precisely "up to 3 times" retried, i.e., up to 3 additional attempts) required, and (2) backoff — no delay implemented vs. exponential backoff required. The transcript itself frames this as a deliberate simplification ("kept simple for the first cut"), not an oversight, but the spec's own "must" language makes this a hard requirement, not a preference — the deviation was neither caught nor corrected within the session (the assistant's final "Done — ship it" summary does not flag the gap).

Evidence origin: direct
Coverage: complete
Confidence: high
Evidence source: evals/comparing-session-to-specification/workspace/iteration-1/eval-1/session-transcript-must-vs-should.md (Write — worker.py); evals/comparing-session-to-specification/workspace/iteration-1/eval-1/spec-project-brief.md (Retry Policy section)
<!-- finding:end -->

## Compliant

**Section: Scope** — **Compliant.** The spec assigns "delivery only, not notification content authoring" to this service. The session's changes (worker, logging config, channel implementations) are all delivery-mechanism code; no notification-content-authoring functionality was added or touched. (Note: the spec's own channel enumeration in this section — "delivers push and SMS notifications" — is the same underlying fact addressed more specifically, and more severely, by the explicit Non-Goal section above; it is not treated as a second, separate violation here to avoid double-counting the same evidence.)

**Section: Logging** — **Compliant.** The spec's "should"-level guideline calls for "structured JSON with a `request_id` field." Session evidence: `Write — services/notification-service/logging_config.py` result states "All log entries are emitted as structured JSON via `structlog`, each carrying a `request_id` field threaded through from the inbound message." This fully satisfies the guideline, exceeding the spec's own "may take time to fully convert" allowance for a migrating service — there is no indication this is a partial migration.

## Unaddressed

**Section: Rate Limiting** — **Unaddressed.** The spec explicitly frames this as optional and deferred: "**may** add token-bucket rate limiting... in a future iteration, once provider-side throttling errors are observed... Not required for the initial release." The transcript's own closing note confirms: "No rate-limiting work was ever discussed or implemented — provider throttling has not come up in this project yet." This is a legitimate Unaddressed verdict, not a violation — the session had no occasion to touch this, and the spec itself does not require it yet.

No sections were classified as Ambiguous or Extra implementation. The email channel could have been considered for an Extra-implementation verdict (code with no corresponding spec section), but it does have a corresponding spec section — the explicit Non-Goal — so it is classified as Violated there instead, per the checklist's own guidance not to force a finding into the wrong bucket when a more specific verdict applies.

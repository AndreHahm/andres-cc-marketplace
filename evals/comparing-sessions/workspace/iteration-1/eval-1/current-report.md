# Plugin Component Analysis Report

**Requested scope:** identity-service repository, full component sweep
**Inspected scope:** auth-service, rate-limiter, session-store
**Unavailable evidence:** audit-log was not in scope for this run (not touched this session)
**Limitations:** none

## Component: auth-service

**Verdict:** Compliant. Session tokens expire after 24h, matching the documented policy. Refresh-token
rotation is implemented correctly.

## Component: rate-limiter

**Verdict:** Needs attention. No per-IP rate limit is configured on the login endpoint — a single client
can attempt unlimited login requests. This has not changed since the prior report.

**Suggestion:** Add per-IP rate limiting on the login endpoint to reduce brute-force risk.

## Component: session-store

**Verdict:** Compliant. New component analyzed for the first time this session (did not exist at the
time of the prior report). Sessions are stored in Redis with a 24h TTL matching the auth-service token
expiry.

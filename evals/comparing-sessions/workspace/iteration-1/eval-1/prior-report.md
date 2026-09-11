# Plugin Component Analysis Report

**Requested scope:** identity-service repository, full component sweep
**Inspected scope:** auth-service, rate-limiter, audit-log
**Unavailable evidence:** none
**Limitations:** none

## Component: auth-service

**Verdict:** Compliant. Session tokens expire after 24h, matching the documented policy. Refresh-token
rotation is implemented correctly.

## Component: rate-limiter

**Verdict:** Needs attention. No per-IP rate limit is configured on the login endpoint — a single client
can attempt unlimited login requests.

**Suggestion:** Add per-IP rate limiting on the login endpoint to reduce brute-force risk.

## Component: audit-log

**Verdict:** Compliant. All auth events (login, logout, token refresh, password reset) are logged with
timestamp and actor ID.

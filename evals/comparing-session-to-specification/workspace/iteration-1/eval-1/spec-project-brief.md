# notification-service Project Brief

## Scope

This service delivers push and SMS notifications for order-status updates. It owns delivery only,
not notification content authoring (that stays with the `content-service`).

## Retry Policy

A failed delivery attempt **must** be retried up to 3 times, with exponential backoff, before being
moved to the dead-letter queue. Delivery is not considered failed until all 3 attempts are exhausted.

## Logging

Log entries **should** use structured JSON with a `request_id` field, to support correlation across
services. This is a strong preference, not a hard requirement — a service migrating from an older
logging format may take time to fully convert.

## Rate Limiting

The service **may** add token-bucket rate limiting per downstream provider in a future iteration, once
provider-side throttling errors are observed in production. Not required for the initial release.

## Non-Goal: No Email Channel

This service **must not** implement an email delivery channel. Email notifications are owned entirely
by a separate `email-notifier` service; duplicating that responsibility here would create two systems
of record for the same customer-facing communication and is explicitly out of scope for this project.

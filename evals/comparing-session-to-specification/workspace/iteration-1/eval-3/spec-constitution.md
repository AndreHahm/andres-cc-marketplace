# billing-kit Constitution

## Idempotency

Every charge-creation call **must** be made with an idempotency key, so that a retried request never
double-charges a customer.

## PII Handling

Raw credit card numbers **must never** be written to any log output, at any log level, under any
circumstances. This is a hard security and compliance requirement, not a style preference.

## Currency

New charges **should** default to USD when no currency is explicitly specified by the caller.

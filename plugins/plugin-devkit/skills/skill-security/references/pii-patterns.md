# PII Detection Patterns

## Personally Identifiable Information (PII)

If a skill processes these data types, GDPR/CCPA/applicable data protection rules apply.

## Contents
- [Country-Specific PII (US / UK)](#country-specific-pii-us--uk)
- [Universal PII](#universal-pii)
- [Technical Sensitive Data](#technical-sensitive-data-sensitive-but-not-pii)
- [Leakage Risk Assessment](#leakage-risk-assessment)
- [PII Rules in Skills](#pii-rules-in-skills)
- [Log Masking Examples](#log-masking-examples)

---

## Country-Specific PII (US / UK)

### US Social Security Number (SSN)
```regex
\b(?!000|666|9\d{2})\d{3}[-\s]?\d{2}[-\s]?\d{4}\b
```
**Risk:** Identity theft, fraud
**Requirement:** Encrypt, do not write to log, do not send to 3rd party

### US Employer Identification Number (EIN)
```regex
\b\d{2}-\d{7}\b
```
**Risk:** Business identity fraud

### US Phone Number
```regex
(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}
```

### UK National Insurance Number (NIN)
```regex
\b[A-Z]{2}[0-9]{6}[A-Z]\b
```
**Risk:** Identity theft, benefits fraud
**Requirement:** Encrypt, do not write to log, do not send to 3rd party

### UK Phone Number
```regex
(\+44|0044|0)[-.\s]?(1\d{3}|[2-9]\d{2})[-.\s]?\d{3}[-.\s]?\d{3,4}
```

---

## Universal PII

### Email Address
```regex
[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}
```
**Risk:** Spam, phishing, account takeover

### IP Address
```regex
# IPv4
\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b
# IPv6
([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}
```
**Note:** User IP is considered PII (GDPR)

### Credit Card Number
```regex
\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b
```
**Risk:** Financial fraud
**Mandatory:** PCI-DSS compliance, never write to log

### IBAN
```regex
[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}
```

### Passport / Identity Document Number
```regex
[A-Z]{1,2}[0-9]{6,9}   # general passport
```

---

## Technical Sensitive Data (Sensitive but not PII)

### API Key Patterns
```regex
# General API key pattern
(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*['"]?([a-zA-Z0-9\-_]{20,})
# Claude/Anthropic
sk-ant-[a-zA-Z0-9\-_]{40,}
# OpenAI
sk-[a-zA-Z0-9]{48}
# GitHub
ghp_[a-zA-Z0-9]{36}
# AWS
AKIA[0-9A-Z]{16}
# Stripe
(sk|pk)_(test|live)_[a-zA-Z0-9]{24,}
```

### JWT Token
```regex
eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+
```
**Risk:** Session hijacking

### Private Key / Certificate
```
-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
```

### Password Patterns
```regex
(?i)(password|passwd|pwd|secret|token)\s*[=:]\s*['"]?([^\s'"]{6,})
```

---

## Leakage Risk Assessment

| Data Type | Risk on Leak | Mitigation |
|-----------|-------------|-------|
| SSN / NIN | Identity theft | Encrypt, do not log |
| Credit Card | Financial fraud | PCI-DSS, never store |
| Email | Spam, phishing | Minimum collection |
| API Key | Service compromise | Use Vault, rotate |
| JWT | Session hijacking | Short TTL, revoke mechanism |
| Password | Brute force | bcrypt/argon2, salting |
| IP Address | Tracking, profiling | Anonymize |
| Private Key | Full system compromise | STRICTLY FORBIDDEN - never log |

---

## PII Rules in Skills

If a skill processes PII, the following checks are mandatory:

```
- Minimum collection: collect only required data
- Purpose limitation: don't use outside intent bounds
- Encryption: in-transit and at-rest encryption
- Log masking: PII must not appear in logs
  email: mask to "fat***@gm***.com"
  phone: mask to "+1 (5**) ***-**89"
  SSN/NIN: show "***-**-****"
- Right to erasure: delete when requested
- Data retention period: define and enforce
- 3rd party sharing: do not share without explicit consent
```

---

## Log Masking Examples

```python
# Email masking
def mask_email(email):
    user, domain = email.split('@')
    return f"{user[:3]}***@{domain[:2]}***.{domain.split('.')[-1]}"

# Phone masking
def mask_phone(phone):
    return phone[:3] + "*** ***" + phone[-2:]

# Card number masking
def mask_card(card):
    return "**** **** **** " + card[-4:]

# API key masking
def mask_key(key):
    return key[:8] + "..." + key[-4:]
```

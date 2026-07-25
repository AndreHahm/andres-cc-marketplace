# Trust Matrix — Authorization & Confidence Levels

## Complete Authorization Map

Defines which operations are allowed, which require checkpoints, and which are forbidden for each confidence tier.

---

## TRUSTED (80-100)

```
FILESYSTEM
  ALLOW  Read          : free within defined scope
  ALLOW  Write         : free within defined scope
  GATE   Delete        : checkpoint (irreversible)
  ALLOW  Execute       : whitelisted commands only
  DENY   System dirs   : /etc /sys /proc — forbidden

NETWORK
  ALLOW  HTTPS GET     : whitelisted domains
  ALLOW  HTTPS POST    : whitelisted domains
  ALLOW  WebSocket     : whitelisted domains
  GATE   New domain    : approval on first use
  DENY   HTTP (clear)  : forbidden
  DENY   Raw socket    : forbidden
```
```
EXECUTION
  ALLOW  Bash (allowed): safe commands only
  ALLOW  Python/Node   : inside sandbox
  GATE   New process   : checkpoint
  DENY   eval/exec     : forbidden
  DENY   System service: forbidden

SKILL CHAIN
  ALLOW  Can trigger 60+ trust skills
  GATE   40-59 trust   : checkpoint
  DENY   0-39 trust    : cannot trigger

DATA
  ALLOW  Read user data
  ALLOW  Write to output
  GATE   Process PII   : masking mandatory
  DENY   3rd party PII : forbidden (no sharing)
```

---

## NORMAL (60-79)

```
FILESYSTEM
  ALLOW  Read          : working directory + tmp
  GATE   Write         : /tmp and project output dir only
  GATE   Delete        : checkpoint + rollback plan needed
  DENY   Execute       : strictly forbidden

NETWORK
  ALLOW  HTTPS GET     : safe domains only
  GATE   HTTPS POST    : checkpoint on payload logic
  DENY   WebSocket     : forbidden
  DENY   HTTP (clear)  : forbidden
  DENY   Raw socket    : forbidden
```
```
EXECUTION
  ALLOW  Python/Node   : strictly inside sandbox, no network
  DENY   Bash          : forbidden
  DENY   eval/exec     : forbidden

SKILL CHAIN
  ALLOW  Can trigger 60-79 trust skills
  GATE   0-59 trust    : checkpoint
  DENY   80+ trust     : cannot trigger

DATA
  ALLOW  Read non-sensitive data
  GATE   Write         : draft outputs only
  DENY   PII           : forbidden to read or touch
```

---

## SUSPICIOUS (0-59)

All operations are forbidden except requesting review from the user via the orchestrator.

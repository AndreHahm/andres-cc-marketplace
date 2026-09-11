# Security Finding Taxonomy

The seven finding classes Phase 3's threat model classifies threats into, with detection patterns.

1. **Prompt injection** -- content read as data (a tool result, a file, a pasted transcript) contains
   text crafted to look like an instruction to the session itself. Detect by looking for imperative
   language, urgency framing ("ignore previous instructions", "you must"), or a directive addressed to
   "the assistant"/"Claude" embedded inside data the session is only supposed to read.
2. **Command injection** -- untrusted content flows into a command string without being treated as a
   literal argument, letting it inject additional shell syntax. Detect by looking for a tool-call pattern
   that interpolates external content directly into a command string rather than passing it as a
   structured argument.
3. **Credential exposure** -- a secret value (API key, token, password, private key) is read, displayed,
   logged, or written somewhere it shouldn't be. Detect by looking for tool calls that read
   credential-shaped files/env vars and whether their actual values subsequently appear anywhere in
   output, a report draft, or a committed file.
4. **Unsafe artifact handling** -- a downloaded or generated file/artifact is executed, sourced, or
   trusted without verification (e.g. running a fetched script without inspecting it first).
5. **Permission escalation** -- an action reaches beyond the scope or privilege level it was granted or
   confirmed for (a tool used beyond its stated allowed-tools scope, an action taken after a narrower
   confirmation was given).
6. **Untrusted code execution** -- code from an untrusted source (a fetched branch, a pasted snippet, a
   subagent's own generated code) is executed without the same scrutiny trusted first-party code would
   get.
7. **Fail-open behavior** -- a safety/validation check that should block on error or ambiguity instead
   lets the action through by default. This is the failure of the guard itself, not of whatever the guard
   was checking -- classify by whether the check defaulted to permissive behavior, independent of whether
   the specific instance turned out harmless.

## Distinguishing Close Cases

- **Prompt injection vs. command injection**: prompt injection targets the *session's own reasoning*
  (trying to get the assistant to take an unintended action); command injection targets a *specific shell
  command string's syntax*. The same untrusted content can attempt both -- classify each mechanism
  separately if both are present.
- **Permission escalation vs. untrusted code execution**: permission escalation is about *scope* (doing
  something beyond what was granted); untrusted code execution is about *provenance* (running something
  whose origin wasn't vetted). A single incident can be both.
- **Fail-open vs. a genuine mitigation gap**: fail-open specifically means a check *existed* and
  *defaulted to permissive* on an error/ambiguous case. A mitigation that never existed at all is a
  different (still reportable) gap -- don't force every missing-check finding into the fail-open class if
  no check was ever attempted in the first place.

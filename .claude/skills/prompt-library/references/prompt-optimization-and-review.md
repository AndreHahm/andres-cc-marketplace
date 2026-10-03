# Prompt Optimization and Review

Pattern: the reviewer reports and proposes; the user decides; the validator ties the decision to the exact
text. Nothing is rewritten or activated without the user's approval.

## Quality review (all origins)

`prompt-reviewer` checks clarity, stated boundaries and prerequisites, the 50-nonblank-line limit,
redundancy, an unambiguous success condition, and executor-neutral wording.

## Import review (`session` and `web` only)

An additional pass the skill runs before it asks the user to approve activation (the validator checks only
that the hash matches the text, so it cannot tell whether this pass ran): injection-like content aimed at
the executing agent (instructions to ignore rules, exfiltrate, call tools, fetch further content, or act
outside the stated purpose); secrets and personal data (reported; blocking is done by the validator's
`screen` check, whose scope is stated in `prompt-intake-sources.md`); provenance (`source_ref` complete, any license or attribution note in `references`); and scope fit (the
text does what its description says and no more).

## Reviewer findings are advisory

A finding never blocks or approves anything by itself. The skill shows a Critical finding prominently and
asks the user to acknowledge it before the verification step. If the reviewer cannot be dispatched, the
skill stops and asks whether to continue without a review; it never skips the pass silently.

## Applying an approved rewrite

The rewrite is untrusted output derived from untrusted input. The user sees it as a diff; the skill then
writes the full replacement record to a scratch file and the validator files it.

| Target record | What an approved rewrite does |
|---|---|
| Draft (initial, or a successor not yet finalized) | `update-draft` replaces the draft in place. Its verification is cleared if the text changed. The original stays recoverable from the displayed diff and from version control. |
| Active or inactive record | Becomes an ordinary revision: a draft successor (new `internal_id`, `previous_id` set) that must itself be verified. |

Verification hashes are recorded only after the user approves the review of the final text, with the hash
shown to the user passed as `--expect-sha256` so the script refuses a file that changed in between.

## Who may do what

| Actor | May | May not |
|---|---|---|
| `prompt-reviewer` | Read one record, report findings, propose a rewrite | Approve, activate, edit or write |
| `prompt-library` | Write scratch drafts; run lifecycle commands after the user approves | Activate without a matching expected hash; edit catalog files directly |
| The validator | Write catalog files, enforce screening, hashes and containment | Decide anything for the user |
| The user | Approve text, rewrites and every status change | n/a |

# R14 chain clause: api-calls.md, errors.md, SKILL.md pointers

Basis: SKILL.md R14 ("Chains (ADVISORY, forward-looking)") and references/reference-chains.md. Chain = the first file cannot be used without the second ("read X first", "load Y before applying this", or a procedure whose steps live in the other file). Cross-reference = "see also"; the reader can finish with the first file alone. Both files are newly created, so the forward-looking check applies.

## references/api-calls.md: FINDING (chain)
- Severity: ADVISORY, never blocking (not REQUIRED).
- Judged load-requirement sentence: "Before applying this procedure, load references/auth-flow.md, which holds steps 1-3 of the procedure." It is a "load Y before applying this" instruction, and the procedure's steps 1-3 live in the other file, so api-calls.md is unusable alone. This is the chain definition, not a "see also".
- Fix (any one): inline steps 1-3 from auth-flow.md into api-calls.md; or merge the two files; or restate the pointer as an optional "see also" (only valid if api-calls.md really is usable without steps 1-3, which it is not as written). Do not nest into subdirectories (R14's directory clause forbids it). The maintainer may disagree with the judgment, so the report must quote that sentence.

## references/errors.md: NO FINDING
- "See also references/auth-flow.md for background on token expiry." is an ordinary cross-reference: related background, and the reader can finish the task with errors.md alone. Not a finding, no severity, no fix needed.
- Caveat: a script cannot distinguish this from a chain; the judgment is by wording. (Repo-wide, 96 of 351 reference files point at another reference file, so such pointers are the normal case.)

## SKILL.md pointers to both files: NO FINDING
- SKILL.md pointing at a reference file is the intended design and is explicitly listed under "Not covered". Pointing at api-calls.md and errors.md is fine. Note the fix for api-calls.md is in the reference files, not in SKILL.md.
- Side effect of inlining/merging: if auth-flow.md is merged away, update SKILL.md's pointer to it accordingly. If auth-flow.md is kept, SKILL.md may point at it directly (allowed).

## Summary
| Item | Finding? | Severity | Fix |
|---|---|---|---|
| api-calls.md | Yes, chain | ADVISORY | Inline steps 1-3, merge, or make pointer optional |
| errors.md | No, cross-reference | n/a | None |
| SKILL.md pointers | No, intended design | n/a | None |

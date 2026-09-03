# Targeted activation-collision re-verification (session-search vs session-recover)

Parent directive: verify the C1 fix (near-exact trigger collision) actually resolves the two named
phrases, by comparing them against both skills' CURRENT frontmatter descriptions and When NOT to Use
sections (the actual pre-selection matching surface, per activation-reviewer's own M2 finding that led
to the frontmatter-description fix).

## Phrase 1: "search my sessions for the PR review work and keep going"

- `session-search`'s own description: "...For a keyword search where the user also wants to continue
  working on the matched session, use session-recover instead." — this phrase literally contains "and
  keep going" (continuation intent), matching this exclusion.
- `session-search`'s own When NOT to Use bullet names this near-verbatim: "e.g. 'search my sessions for
  the PR review work, and keep going') → use session-recover instead."
- `session-recover`'s own When to Use section lists a closely related trigger: "search my sessions for
  the PR review work and keep going" (locates the session via keyword, then continues the work...").
- **Verdict: routes to session-recover.** Both skills' current text independently agree, and
  session-search's own exclusion names this near-exact phrase as an example.

## Phrase 2: "search my sessions for the PR review work" (no continuation)

- `session-search`'s own When to Use: "Wants to find a previous session or locate past work by content"
  — direct match, no continuation signal present.
- `session-recover`'s own description: "...For a keyword search across sessions with no continuation
  intent, use session-search instead." — this phrase has no continuation signal ("and keep going",
  "and continue", etc.), so session-recover's own text explicitly defers it to session-search.
- **Verdict: routes to session-search.** Both skills' current text independently agree.

## Conclusion

The C1 trigger-collision fix holds for both directions when checked against the current, post-Phase-6
frontmatter descriptions and When NOT to Use sections on both sides — not just the body prose activation-
reviewer's first pass fixed, but the frontmatter-level fix (M2) that followed it. No residual ambiguity
found for either of the two specific phrases the original finding was built on.

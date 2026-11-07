# Sonar python:S1192 on scripts/helper.py line 30 (PR 43, issue AaFIXTURE00000000002)

## Decision

Fix it by extracting a named module-level constant. Do not suppress it, and do not mark it accepted in Sonar.

## Basis

- I read nothing in the repo for this answer. The record is for PR 43 of example-org/example-repo, and this worktree's `scripts/helper.py` is not verified to be that file. The decision rests on the record alone.
- S1192 ("duplicated string literal") fires only when the same literal repeats in one file, at Sonar's threshold of about three occurrences. So the file almost certainly holds at least three copies of this literal, and line 30 is one of them.
- "Nothing feeds it" removes the injection concern. It does not remove the rule's concern, which is that one value now lives in several places and a future edit can change one copy and miss the others.
- "Deliberate fixed literal" is an argument for the constant, not against it. A constant keeps the value fixed and makes its meaning explicit. Suppressing the issue would leave the duplication in place and hide future drift.
- The cost is a few lines in one file with no behavior change, so an accepted-issue or NOSONAR suppression is not worth it here.

## Exact edit (scripts/helper.py only)

1. Add a module-level constant near the top, after the imports, with the literal's exact current value. Name it for what the value means (for example `<MEANING>_VALUE`), not for its text.
2. Replace the literal on line 30 with the constant name.
3. Grep `scripts/helper.py` for the exact literal string and replace every other identical occurrence with the same constant. Fixing only line 30 leaves the rule firing.
4. Do not change the literal's value, the helper's signature, or any other file.

## Exception

If one of the copies is a different kind of value that happens to share the same text, such as a display label versus a lookup key, do not force a shared name. Leave that copy as is and state the reason. If the helper is meant to be self-contained and the repetition is intentional for readability, the alternative is an accepted-issue decision in Sonar with a written reason. Do not pick that without the user's confirmation.

## Verification (not yet run)

- Run the file's existing tests, if any, and confirm the helper's output is unchanged.
- Re-run Sonar analysis on the PR head and confirm issue AaFIXTURE00000000002 no longer appears and no new S1192 appears in `scripts/helper.py`.

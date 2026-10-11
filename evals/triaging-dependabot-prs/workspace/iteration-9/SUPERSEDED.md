# Iteration 9 is superseded

Iteration 9 (2026-10-11) graded eval 12 against the first version of the advisory rules, whose decision
signals were `new_is_latest` and `new_safer_than_latest`. Those signals were replaced by
`new_is_newest_compatible` and `new_safer_than_newest_compatible` when the compatibility check was added, so
the answer and the passing grades in `eval-12` describe rules that no longer exist. Its prompt also said "Two
uv PRs" while listing three.

The current record is `../iteration-10/`: eval 12 revised for the new signals, and the new eval 13.

# iteration-5 (2026-11-25): rerun of missed assertions

Evals with an assertion missed in iteration-4, rerun plan-only on claude-opus-5-5. `with_skill` is the text with the
Quick Start (ENG-123 wording), `baseline` the same skill without it; nothing else differs. One run per arm, graded by the
author, who knew the arms, and only evals that had missed an assertion were chosen, so this shows no effect size.

- eval-2 with_skill assumed `ENG-123`, the Quick Start's own example ID, as the active Issue; the baseline wrote
  `<ID>`. The example was replaced by `<issue-id>`.
- eval-2-placeholder-run-1 to -3 (with_skill only): the same prompt on the corrected text. No invented ID in 3 of 3.
- development-to-pr eval 3 was not rerun: its missed assertion needs a live PR lookup.

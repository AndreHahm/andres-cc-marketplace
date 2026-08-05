# Reviewer-Side Checklist

Before leaving a review action:

- [ ] Confirmed which PR (`gh pr view`) and skimmed its stated purpose/description
- [ ] Ran the CODEOWNERS context check (Tier 2 of `merge-pr`'s `merge-rights-check.md`) and mentioned the
      result to the user before proceeding — informational, not blocking
- [ ] Confirmed with the user which action to take (comment / approve / request changes / add reviewers)
      rather than assuming from a vague request
- [ ] For "request changes", made sure concrete feedback text exists — GitHub requires a body for this
      review type, and a vague or empty one isn't useful to the PR author

## Why Only Tier 2 of `merge-rights-check.md` Applies Here

`merge-rights-check.md` was written for `merge-pr`'s question: "is this specific person allowed to press
the merge button?" That's a three-tier gate (repo owner → CODEOWNERS match → collaborator write
permission) because merging is a repo-write action with real consequences if done by the wrong person.

Reviewing a PR is a different question with a much lower bar: on GitHub, anyone with read access to a
repository can leave comments, approve, or request changes — there's no permission tier equivalent to
"collaborator write access" gating review actions the way it gates merges. CODEOWNERS is still relevant
context for a reviewer (it tells you whether your approval is one GitHub will count toward a required
review on the files you're looking at), which is exactly what Tier 2's parsing logic already computes —
so this skill reuses that parsing step directly (via `Read` on the same reference file) rather than
forking a second copy of CODEOWNERS-matching logic. Tiers 1 and 3 answer a merge-rights question this
skill never asks, so they're deliberately skipped.

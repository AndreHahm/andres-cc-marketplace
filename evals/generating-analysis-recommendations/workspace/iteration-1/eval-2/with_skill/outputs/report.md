# Recommendations Plan

**Requested scope:** Two findings pasted directly into the conversation — Finding 1 ("slow CI onboarding step") and Finding 2 (sessions "feel unfocused" in the back half) — no source report path was supplied.
**Inspected scope:** Same as requested — both pasted findings were read in full. No external report or repository file supplied any of the underlying evidence; a repo-wide check for an `onboarding.sh` file in this checkout found none, so no additional codebase evidence was available to inform Finding 1's HOW step beyond the pasted text itself.
**Unavailable evidence:** Finding 2 supplies no attached evidence of its own (no transcript excerpt, specific behavior, or metric was named in the source text) — this is a property of the pasted finding itself, not evidence this skill failed to fetch.
**Limitations:** Finding 2 was not expanded into a plan entry — see "Not Expanded" below for why.

## Quick Wins

<!-- finding:start -->
### pasted-findings-2026-09-11T18-36-47Z-rec-01 — Cache the `config/defaults.yaml` fetch in the CI onboarding step

**WHAT:** Add caching around `onboarding.sh`'s fetch of `config/defaults.yaml` from the internal artifact server, so the CI run skips the full synchronous HTTP fetch whenever a still-valid cached copy is available.

**WHY:** Profiling shows 38 of `onboarding.sh`'s 45-second CI runtime (about 84% of the step) is spent on a single synchronous HTTP call to fetch `config/defaults.yaml`; the file changes on average only once every few months, and the finding states there is no caching of this file anywhere in the CI pipeline today.

**HOW:** Cache the fetched `config/defaults.yaml` between CI runs — e.g. a CI-level cache keyed by a content hash or ETag of the file, or a conditional request (`If-Modified-Since`/`If-None-Match` against the artifact server) — and only perform the full fetch when the cache is empty or the server signals the file has actually changed. No existing caching pattern for this fetch could be cited: no `onboarding.sh` file exists anywhere in this checkout (confirmed by a repo-wide search this session), so the concrete implementation should follow whichever caching mechanism the actual CI platform and artifact server already support (e.g. the CI runner's built-in cache action, or the artifact server's own conditional-GET support) rather than a pattern this skill can point to directly.

Complexity: Low — a small, self-contained change to a single script (add a cache-check/conditional-fetch branch before the existing HTTP call), no new architecture.
Risk: Medium — this does change existing behavior (the fetch is now sometimes skipped), in a bounded, well-understood way; a poorly-invalidated cache could serve a stale `config/defaults.yaml`, so cache invalidation needs to be correct, not just present.
Benefit: Medium — improves CI speed materially for this one step; no evidence in the finding that this unblocks other work or prevents a category of failure beyond the time cost itself.
Priority bucket: **Quick Win** (Low complexity, Medium risk, Medium benefit — within Quick Win's Low-to-Medium risk / Medium-to-High benefit bands).

Evidence origin: inherited
Coverage: complete
Confidence: high
Evidence source: pasted findings, Finding 1 ("slow CI onboarding step"), pasted directly into this conversation — no source report path
<!-- finding:end -->

## Not Expanded

**Finding 2 ("sessions 'feel unfocused' in the back half") — no plan entry produced.** Per this skill's own Gotcha ("a finding with no clear fix isn't forced into a plan entry"), this finding is not expanded into a WHAT/WHY/HOW entry. The finding itself states there is no specific file, pattern, or root cause identified — just a recurring but vague impression across several unrelated retrospective write-ups, with no transcript excerpt, specific behavior, or metric ever attached to any mention of it. Writing a WHAT/HOW here would require inventing a concrete root cause and fix that the source finding does not support — nothing was read this session that could substitute for that missing root-cause evidence. The finding as given reads as a prompt for further investigation (e.g. gathering concrete transcript evidence for what "unfocused" means in practice), not yet an actionable fix; if the user wants a plan entry for the *investigation* itself, that would need to come back through this skill as its own, differently-scoped finding once some concrete evidence exists, or be handled by whichever analysis-kit skill is suited to first gathering that evidence.

## Suggested Order of Operations

1. **pasted-findings-2026-09-11T18-36-47Z-rec-01** — no dependency on any other entry in this plan; can be implemented independently.

Finding 2 has no corresponding entry and so is not part of this ordering.

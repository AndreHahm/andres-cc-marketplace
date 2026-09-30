# Routing (eval-3, iteration-8)

(a) 'analyze this skill for improvements and then apply the fixes with me step by step' -> skill-refiner-interactive: it improves an existing skill with operator approval at each step, which matches the step-by-step fixing request.
(b) 'refine this skill interactively' -> skill-refiner-interactive: its when_to_use names refining skills and running interactive fix-review workflows on existing skills.
(c) 'give me a one-shot quality report on this skill, I do not want any changes' -> skill-reviewer: the refiner's description redirects one-shot quality reports with no fixes to the skill-reviewer agent.
(d) 'create a new skill for summarizing TODO comments' -> skill-development: the refiner explicitly excludes creating new skills and points to skill-development, whose triggers include "create a skill".
(e) 'run fix-review on this skill automatically until it is clean, without asking me anything' -> skill-improver-loop: it runs unattended automated fix-review cycles until no critical or major issues remain.
(f) 'apply the 80% rule to this skill's reference files' -> skill-refiner-interactive: "applies the 80% rule" appears in both its description and when_to_use, and no other description mentions it.
(g) 'validate this skill is production-ready' -> skill-refiner-interactive: its description and when_to_use cover validating and checking production readiness (skill-reviewer's "validate skill structure" is a near-miss, but a production-readiness check is named only by the refiner).
(h) 'consolidate these reference files' -> skill-refiner-interactive: it lists "consolidates references" / "consolidating references" verbatim, while skill-development's "consolidate skills" refers to whole skills, not reference files.

Ambiguity: no pair is fully ambiguous for these requests, but (g) and (h) are mild near-overlaps (skill-refiner-interactive vs. skill-reviewer for "validate", and vs. skill-development for "consolidate"/"improve") that the exclusion language in the refiner's description and the verbatim phrase matches resolve in the refiner's favor.

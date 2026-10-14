# Activation routing

(a) 'analyze this skill for improvements and then apply the fixes with me step by step' -> skill-refiner-interactive: it improves an existing skill with operator approval at each step, which matches step-by-step fixing with the user.
(b) 'refine this skill interactively' -> skill-refiner-interactive: its name, description and when_to_use all name interactive refinement of existing skills.
(c) 'give me a one-shot quality report on this skill, I do not want any changes' -> skill-reviewer: it only assesses and scores and never edits, and skill-refiner-interactive's description points one-shot reports with no fixes to it.
(d) 'create a new skill for summarizing TODO comments' -> skill-development: it covers creating new skills, and skill-refiner-interactive explicitly says it is not for creating new skills.
(e) 'run fix-review on this skill automatically until it is clean, without asking me anything' -> skill-improver-loop: it runs unattended automated fix-review cycles with no interactive checkpoints.
(f) 'apply the 80% rule to this skill's reference files' -> skill-refiner-interactive: applying the 80% rule is named in both its description and its when_to_use.
(g) 'validate this skill is production-ready' -> skill-refiner-interactive: its description and when_to_use name validating against best practices and checking production readiness (skill-reviewer's "validate skill structure" is a close competitor, but only the refiner names production readiness).
(h) 'consolidate these reference files' -> skill-refiner-interactive: it lists consolidating references in its description and when_to_use (skill-development also mentions consolidating skills, but that means whole skills, not reference files).

Ambiguity: yes, (g) is ambiguous between skill-reviewer ("validate skill structure") and skill-refiner-interactive ("production readiness"), and (h) is mildly ambiguous with skill-development's "consolidate skills"; the other six requests have one clear match.

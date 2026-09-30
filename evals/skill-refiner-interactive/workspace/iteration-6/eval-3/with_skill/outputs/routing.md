# Routing

(a) 'analyze this skill for improvements and then apply the fixes with me step by step' -> skill-refiner-interactive: it improves an existing skill with operator approval at each step, matching the step-by-step fix workflow.
(b) 'refine this skill interactively' -> skill-refiner-interactive: its when_to_use names refining skills and running interactive fix-review workflows.
(c) 'give me a one-shot quality report on this skill, I do not want any changes' -> skill-reviewer: its description is a review-only quality report, and skill-refiner-interactive explicitly redirects one-shot reports with no fixes to the skill-reviewer agent.
(d) 'create a new skill for summarizing TODO comments' -> skill-development: it covers creating new skills, and skill-refiner-interactive explicitly says not for creating new skills.
(e) 'run fix-review on this skill automatically until it is clean, without asking me anything' -> skill-improver-loop: it runs unattended automated fix-review cycles with no checkpoints until no critical or major issues remain.
(f) 'apply the 80% rule to this skill's reference files' -> skill-refiner-interactive: applying the 80% rule is named explicitly in its description and when_to_use.
(g) 'validate this skill is production-ready' -> skill-refiner-interactive: its description and when_to_use cite validating and checking production readiness, although skill-reviewer's "validate skill structure" partly overlaps.
(h) 'consolidate these reference files' -> skill-refiner-interactive: it lists consolidating references, although skill-development's "consolidate skills" also touches consolidation (of skills, not reference files).

Ambiguity: yes, mildly. (g) is ambiguous between skill-refiner-interactive and skill-reviewer (validate / production readiness), and (h) between skill-refiner-interactive and skill-development (consolidate); the other six resolve cleanly through the descriptions' explicit "not for / use instead" redirects.

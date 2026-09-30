(a) 'analyze this skill for improvements and then apply the fixes with me step by step' -> skill-refiner-interactive: it wraps skill-reviewer analysis and then interactively applies fixes, which matches the step-by-step collaborative fixing.
(b) 'refine this skill interactively' -> skill-refiner-interactive: its name and when_to_use ("refining skills", "interactive fix-review workflows") match directly.
(c) 'give me a one-shot quality report on this skill, I do not want any changes' -> skill-reviewer: the refiner description explicitly routes one-shot structured quality reports with no interactive back-and-forth to the skill-reviewer agent.
(d) 'create a new skill for summarizing TODO comments' -> skill-development: it covers creating new skills, and the refiner explicitly says it is not for creating new skills.
(e) 'run fix-review on this skill automatically until it is clean, without asking me anything' -> skill-improver-loop: it runs unattended automated fix-review cycles until no critical or major issues remain.
(f) 'apply the 80% rule to this skill's reference files' -> skill-refiner-interactive: its when_to_use names "applying the 80% rule" and "consolidating references" while no other description mentions it.

Ambiguity: no pair is seriously ambiguous for these six requests, since each description cross-references its neighbours with explicit exclusions; the only mild overlap is skill-development's "improve a skill" phrase versus the refiner for request (a) and (f), which the refiner's more specific interactive and 80%-rule wording resolves.

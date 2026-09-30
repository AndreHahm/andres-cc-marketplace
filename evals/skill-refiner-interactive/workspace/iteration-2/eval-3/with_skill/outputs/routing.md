# Routing

- 'analyze this skill for improvements and then apply the fixes with me step by step' -> skill-refiner-interactive: it wraps skill-reviewer analysis and then interactively applies fixes, matching the step-by-step fix workflow.
- 'refine this skill interactively' -> skill-refiner-interactive: its when_to_use names refining skills and running interactive fix-review workflows on existing skills.
- 'give me a one-shot quality report on this skill, I do not want any changes' -> skill-reviewer: the refiner's description explicitly redirects one-shot structured quality reports to the skill-reviewer agent, and no edits are wanted.
- 'create a new skill for summarizing TODO comments' -> skill-development: it covers creating new skills, while the refiner explicitly says it is not for creating new skills.

Ambiguity: the only pair with surface overlap is skill-refiner-interactive vs skill-development (and skill-development vs skill-reviewer) on "improve a skill" wording, but for these four requests no pair is ambiguous because the refiner's description explicitly disambiguates (interactive fixes vs one-shot report vs creation); the one mild risk is (a)/(b), where skill-development's "improve a skill" trigger could compete, yet the refiner's interactive/step-by-step wording is more specific.

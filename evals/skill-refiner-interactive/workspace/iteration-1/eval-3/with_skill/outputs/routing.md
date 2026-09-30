# Routing simulation

(a) 'analyze this skill for improvements and then apply the fixes with me step by step' -> skill-refiner-interactive: its description says it wraps skill-reviewer and then interactively applies fixes, and its when_to_use names interactive fix-review workflows on existing skills.
(b) 'refine this skill interactively' -> skill-refiner-interactive: "refining skills" and "interactive" appear directly in its name, description and when_to_use.
(c) 'give me a one-shot quality report on this skill, I do not want any changes' -> skill-reviewer: the refiner description explicitly redirects one-shot structured reports with no interactive back-and-forth to the skill-reviewer agent, and the reviewer only reads.
(d) 'create a new skill for summarizing TODO comments' -> skill-development: it lists "create a skill" and "make a skill for X", and the refiner description explicitly says not for creating new skills.

Ambiguity: requests (c) and (d) are unambiguous because explicit "use X instead" redirects separate the descriptions. (a) and (b) have a mild residual overlap, since skill-development also lists "improve a skill" triggers. The words "interactively" and "apply fixes with me" and the refiner's explicit scope should win, but a bare "improve this skill" with no interactive cue could be claimed by either skill-development or skill-refiner-interactive.

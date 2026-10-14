# Interactive improvement of `deploy-notes`

**Use `skill-refiner-interactive`** (in plugin-devkit; slash form `/skill-refiner-interactive`). It is the skill for operator-approved refinement of an existing, working skill. It goes through the skill with you, proposes changes one at a time, and applies each only after you approve it.

## Why not skill-development
`skill-development` authors and repairs: it creates new skills, converts commands, repairs broken skills and consolidates duplicates, through its five-phase process (Understand, Design, Test, Improve, Polish). Its own "When NOT to Use" sends polishing of a skill that already works and passes the Quality Checklist to `skill-refiner-interactive`. Since `deploy-notes` already works, I am not running the five-phase creation process and am not creating a new skill.

Other siblings, for contrast:
- `skill-improver-loop`: automated fix-review cycles with no checkpoints, so it does not fit your "approve each change" requirement.
- `skill-reviewer` agent: a scored report only, with no edits.
- `skill-tester`: empirical benchmarking, with no edits.

One caveat: if `deploy-notes` is actually broken or fails the Quality Checklist, it goes back to `skill-development` (Audit or Repair path).

## How to start
1. Invoke `/skill-refiner-interactive` (or say "refine my deploy-notes skill").
2. Give it the skill name or path. It then asks "Refine" or "Validate". Choose **Refine**.
3. It runs a pre-analysis of the skill's structure (size, references, tool scoping, mirror pair), then asks you to pick goals and run a short interview.
4. It then proposes changes one at a time, and you approve, reject or modify each before it is applied.

(Use "Validate" instead if you only want a production-readiness check.)

I stopped here: nothing was run or modified, and no skill was created.

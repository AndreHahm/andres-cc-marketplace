# Interactive improvement of `deploy-notes`

## Which skill handles it

Use **`skill-refiner-interactive`**, not `skill-development`.

I read `skill-development`'s SKILL.md as directed. It authors and repairs skills. Its frontmatter and "When NOT to Use" section say that refining a working skill with operator checkpoints belongs to `skill-refiner-interactive`. Unattended review-fix cycles belong to `skill-improver-loop`.

I then checked `skill-refiner-interactive`'s SKILL.md, because `skill-development` says to verify another component's behavior before pointing at it. Its description matches your request: "Improves, validates, and optimizes an existing Claude Code skill ... with operator approval at each step". It has a Refine mode and a Validate mode.

| Option | Why not |
|---|---|
| `skill-development` | Creates, repairs or consolidates skills. It has an Audit path, but that is a self-driven checklist-and-fix path, not a propose-and-approve-each-change flow. |
| `skill-improver-loop` | Unattended fix-review cycles with no user checkpoints. |
| `skill-reviewer` agent | Report only. It makes no edits. |
| `skill-tester` | Benchmarks a skill against a baseline. It does not edit. |

## How to start

1. Invoke `Skill(skill-refiner-interactive)` (command form `/skill-refiner-interactive`) and name `deploy-notes`.
2. The skill first checks the conversation for existing context, such as a skill file already pasted or a problem already described. If it finds some, it asks whether to infer your refinement needs or run the full interview. Your request names only the skill and the action, so it should not count as existing context.
3. It asks which skill, unless already named. It asks Refine or Validate. You want **Refine**, so choose that.
4. It locates `deploy-notes` and runs a pre-analysis. This covers references, orphans, size counts, tool scoping and the mirror-pair check if the skill has a `.claude/` mirror.
5. It runs goal selection and an interview. It then proposes changes and applies each only after your approval. That is the one-at-a-time flow you described.
6. Before finalizing, the plugin's rules require a `plugin-rulebook` compliance check on the changed skill.

## Notes and assumptions

- I could not ask questions here. I assumed Refine rather than Validate, since you said "improve".
- I did not touch or read `deploy-notes`, and I did not invoke `skill-refiner-interactive`. This answer only routes you.
- If you later want to author a new skill instead, that goes to `skill-development` (or `workflow-skill-development` for multi-phase workflows).

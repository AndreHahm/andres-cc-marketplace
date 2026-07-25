# Routing Patterns

AskUserQuestion blocks for the plugin-development skill entry routing.

**R18 note:** "Initial Action Routing" (25 content lines) sits in R18's Warning tier (`>20`, `<=30`) and "Validate-or-Publish Sub-Routing" (17 content lines) sits in the Weak-Warning tier (`>10`, `<=20`) — both advisory-only, neither reaches the `>30` Critical threshold an exception would be needed to justify. Each is a single `AskUserQuestion` call with a fixed `question`/`header`/`options`/`multiSelect` schema; splitting either would produce an invalid, incomplete call rather than two smaller valid ones.

**Why "Validate a plugin" and "Publish to marketplace" share one top-level slot:** `AskUserQuestion` caps at 4 options per question. Adding a 5th top-level path ("Add a component to an existing plugin" — the gap `build-handoff-writer`'s own handoff report for this skill flagged: Phase 4 of a real pipeline run had to write a component directly because no routing path existed for "one already-designed component, existing plugin") required freeing a slot. Validate and Publish are the two closest-adjacent existing paths (both act on an already-scaffolded plugin, unlike Create/Convert/Add-component which each produce or extend one) — merged into one top-level option with a two-option sub-routing question, rather than merging any pair involving the new path.

## Initial Action Routing

Use at skill entry to determine the user's intent:

```
questions: [
  {
    question: "What would you like to do?",
    header: "Action",
    options: [
      {
        label: "Create a new plugin",
        description: "Build a plugin from scratch with proper manifest, structure, and components"
      },
      {
        label: "Add a component to an existing plugin",
        description: "Add one already-designed skill/agent/command/hook to a plugin that already exists — not a whole new plugin or project conversion"
      },
      {
        label: "Convert a project to plugin",
        description: "Transform existing project into plugin with manifest and proper directory layout"
      },
      {
        label: "Validate or publish a plugin",
        description: "Check plugin structure against Claude Code standards, or prepare a plugin (with plugin.json) for marketplace distribution"
      }
    ],
    multiSelect: false
  }
]
```

Then route to the appropriate section:
- **Create a new plugin** → "New Plugin Creation Interview" in `SKILL.md`
- **Add a component to an existing plugin** → "Adding a Component to an Existing Plugin" in `SKILL.md`
- **Convert a project to plugin** → `references/workflows.md` (Workflow 2)
- **Validate or publish a plugin** → ask the Validate-or-Publish Sub-Routing question below, then route per its answer

## Validate-or-Publish Sub-Routing

Only asked after "Validate or publish a plugin" is selected above:

```
questions: [
  {
    question: "Validate structure, or publish to marketplace?",
    header: "Validate/Publish",
    options: [
      {
        label: "Validate a plugin",
        description: "Check plugin structure against Claude Code standards"
      },
      {
        label: "Publish to marketplace",
        description: "Prepare a plugin (with plugin.json) for distribution. For skills-repo marketplaces without individual plugin.json files, use marketplace-development instead."
      }
    ],
    multiSelect: false
  }
]
```

- **Validate a plugin** → `references/workflows.md` (Workflow 3)
- **Publish to marketplace** → "Workflow Sections → Publishing" in `SKILL.md`

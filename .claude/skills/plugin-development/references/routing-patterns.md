# Routing Patterns

AskUserQuestion blocks for the plugin-development skill entry routing.

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
        label: "Convert a project to plugin",
        description: "Transform existing project into plugin with manifest and proper directory layout"
      },
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

Then route to the appropriate section:
- **Create a new plugin** → [New Plugin Creation Interview](#new-plugin-creation-interview) in SKILL.md
- **Convert a project to plugin** → `references/workflows.md` (Workflow 2)
- **Validate a plugin** → `references/workflows.md` (Workflow 3)
- **Publish to marketplace** → [Workflow Sections → Publishing](#workflow-sections) in SKILL.md

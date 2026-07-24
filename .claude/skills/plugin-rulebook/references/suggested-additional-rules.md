# Suggested Additional Rules (Disabled by Default)

Rules available but not enabled by default, referenced from `SKILL.md`'s "Suggested Additional Rules" pointer. Enable any of these in `settings.json → rules.<id>.enabled: true`.

| ID | Rule | Why Enable |
|---|---|---|
| R11 | **Max heading depth `###`** — No headings deeper than `###` in any file | Forces structural clarity; deep nesting signals content for extraction |
| R12 | **Code block language specifier** — All fenced blocks must declare a language | Improves syntax highlighting and parse accuracy |
| R15 | **No human-documentation files** — No `README.md`, `CHANGELOG.md`, `INSTALLATION.md` in skill dirs | Skills are for AI agents, not humans |
| R16 | **Progressive disclosure order** — `Quick Start` must precede workflow sections | Ensures fastest-path-to-task is always first |

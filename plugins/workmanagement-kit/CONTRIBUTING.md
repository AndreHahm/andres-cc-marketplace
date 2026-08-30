# Contributing

## Preferred Language

This plugin's preferred scripting language is **Python** — schema validators, the host-profile
resolver, and any future evidence-export scripts should default to Python (declared inline
dependencies via PEP 723 `# /// script` blocks, matching this repository's convention, e.g.
`plugin-devkit`'s hooks) unless there is a specific reason to add a script in another language.

## Development Setup

No scripts exist yet in this initial scaffold. When added, Python scripts run directly via
`uv run` (or `python3`) with PEP 723 inline dependency blocks — no separate package manager
config is bundled with this plugin.

## Proposing a Change

1. Branch off `main` using this repository's `<type>/<description>` convention.
2. Make your change.
3. If the change alters a skill's or agent's actual behavior (not just prose formatting), test it
   per this repository's testing conventions before committing.
4. Run `plugin-rulebook` against any new or modified component before finalizing.

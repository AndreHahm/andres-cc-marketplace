# Output Styles in Plugins

Plugins can bundle output styles that adjust Claude's response formatting — terseness, structure, verbosity. Output styles surface in `/output-style` once the plugin is enabled. This is **not** visual/CSS styling of the terminal UI; it's Markdown instructions that change what Claude says and how it says it.

## Location

- `output-styles/<name>.md` files in the plugin root, OR
- `"outputStyles"` key in `plugin.json` pointing at a custom file or directory

A custom `outputStyles` value **replaces** the default `output-styles/` directory.

## Format

Markdown file with frontmatter:

```markdown
---
name: terse
description: Short, direct answers. Skip explanations unless asked.
---

Answer in the fewest words that convey the result. Skip preambles like
"Sure, I'll" — go straight to the answer or the diff.

Use bullet lists only when there are 3+ peer items. Otherwise prose.
```

## Required frontmatter fields

| Field | Description |
|---|---|
| `name` | Identifier shown in `/output-style`. Kebab-case recommended. |
| `description` | One-line summary of the style. |

## Configuration in plugin.json

```json
{
  "name": "my-plugin",
  "description": "Plugin with a terse output style",
  "outputStyles": ["./output-styles/terse.md"]
}
```

Or point at the whole directory (redundant with the default location, but explicit):

```json
{
  "outputStyles": "./output-styles/"
}
```

## Best Practices

- **Behavioral, not aesthetic**: focus the body on *what to say and when*, not on color/formatting markup — there is no CSS or color-token mechanism here (see `themes.md` for that).
- **Layer with skills**: output styles modulate Claude's response shape; skills carry domain knowledge. Don't duplicate skill content in a style.
- **Composability**: assume the user may switch styles mid-session — keep instructions self-contained.

## Testing Output Styles

Test locally with `--plugin-dir`:

```bash
claude --plugin-dir /path/to/my-plugin
```

Enable the style via `/output-style` and confirm Claude's responses actually change shape as described — an output style with vague or contradictory instructions may have no observable effect.

## See Also

- [Plugin Manifest Reference](manifest-reference.md) — Complete plugin.json schema, including the `outputStyles` field
- `references/themes.md` — Color theme presets (the actual visual-styling component type)

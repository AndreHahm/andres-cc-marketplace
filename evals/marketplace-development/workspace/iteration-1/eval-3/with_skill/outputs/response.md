# What to change in marketplace.json

You added `skills/new-helper/` to the skills repo backing the `./tools` suite plugin. Here's the full set of edits, per the marketplace-development skill's "Maintaining an existing marketplace" checklist:

## 1. Add the new skill to the plugin's `skills` array (required)

The suite plugin entry lists its skills as paths relative to its `source` (`./tools`). Add the new skill's relative path:

```jsonc
{
  "name": "tools",
  "source": "./tools",
  "version": "1.3.0",
  "skills": [
    "skills/existing-skill-a",
    "skills/existing-skill-b",
    "skills/new-helper"   // <-- add this
  ],
  ...
}
```

If `new-helper` isn't actually located under `./tools/skills/`, adjust the path accordingly — it must resolve relative to the plugin's `source`, not the repo root.

## 2. Bump the plugin's own `version`

Current value is `"1.2.0"`. This needs to bump because the plugin's `skills` array is changing — the skill explicitly calls this out as a trigger distinct from SKILL.md content edits: *"Bump existing plugin version when its `source` or `skills` changes. The installed cache path and component resolution changed even if SKILL.md did not."*

Since adding a new skill is a backward-compatible, additive change (not a breaking one), bump the **minor** version:

```
1.2.0 -> 1.3.0
```

## 3. Bump `metadata.version` (the marketplace catalog version)

This is a separate version from the plugin's own version — it tracks the marketplace.json file as a whole. Bump it too (minor bump, since this is a new-capability addition, not a breaking change):

```jsonc
"metadata": {
  "version": "<bumped>",  // e.g. 1.x.0 -> 1.(x+1).0, following whatever the catalog's current value is
  ...
}
```

## 4. Update `metadata.description`

Append a short summary of what `new-helper` does to the marketplace's top-level description, per the skill's step 2 ("Update `metadata.description` — append the new skill's summary").

## 5. Audit `metadata` for invalid fields (sanity check)

While you're in there, confirm `metadata` doesn't carry a `homepage` field — the skill flags this as a common mistake (not part of the marketplace.json spec, silently ignored by Claude Code). Remove it if present. This isn't caused by your change, but it's a cheap check to do while editing the file.

## Not applicable here

- The "new plugin → `version: "1.0.0"`" rule doesn't apply — `tools` is an existing plugin, not a new one being added to the marketplace.
- No changes are needed to plugin `name`, `source`, or other plugin-level fields unless `new-helper` also needs its own `description`/keyword entries surfaced elsewhere in the plugin definition (skill's checklist doesn't require this unless your marketplace.json schema tracks per-skill metadata beyond the `skills` path array).

## Summary of edits

| Field | Old | New |
|---|---|---|
| `plugins[tools].skills` | (missing `new-helper`) | append `"skills/new-helper"` (path relative to `source`) |
| `plugins[tools].version` | `"1.2.0"` | `"1.3.0"` |
| `metadata.version` | current catalog version | bumped (minor) |
| `metadata.description` | current | append `new-helper` summary |
| `metadata.homepage` | audit for presence | remove if found (not spec-valid) |

After editing, validate with `claude plugin validate` and test real installation before shipping, per the skill's broader workflow.

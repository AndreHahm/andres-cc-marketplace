# marketplace.json for `example-tool`

## The exact JSON

`.claude-plugin/marketplace.json`

```json
{
  "name": "example-marketplace",
  "owner": {
    "name": "your-org-or-username"
  },
  "plugins": [
    {
      "name": "example-tool",
      "source": "./skills/example-tool",
      "description": "Does an example thing",
      "version": "1.0.0",
      "strict": false
    }
  ]
}
```

## Field-by-field explanation

### Top level

- **`name`**: `"example-marketplace"` — the marketplace catalog's own identifier (what
  users pass to `claude plugin marketplace add`). I used a placeholder; swap it for
  whatever this repo/org actually wants the catalog to be called. This is independent
  of the plugin's own `name`.
- **`owner`**: a placeholder identifying who maintains the catalog. Fill in the real
  org/user info. Not part of the schema rules the skill calls out explicitly, so I kept
  it minimal rather than inventing extra fields.
- No **`metadata`** block. The skill's schema notes say `metadata` only supports
  `description`, `version` (catalog version, not plugin version), and `pluginRoot` —
  none of which are required here, so I omitted the block entirely rather than adding
  it just to have something in it. (Also explicitly *not* included: `metadata.homepage`
  — the skill flags this as accepted-but-not-in-spec, so it should never be written.)
- No **`$schema`** field — the skill states this is rejected outright by
  `claude plugin validate`, so it's omitted unconditionally.

### The `plugins[0]` entry

- **`name: "example-tool"`** — matches the requested plugin name exactly, kebab-case,
  and (per the pre-flight checklist) must be unique across all entries in the file.
- **`source: "./skills/example-tool"`** — points directly at the skill's own directory.
  Per the skill's guidance, for a **single-skill plugin** `source` should point straight
  at the skill directory (this is the pattern used by 167/168 plugins in
  `anthropics/claude-plugins-official`), rather than `source: "./"` (which would install
  the entire repo as the plugin root — explicitly called out as something to avoid).
- **No `skills` field** — because `source` already points directly at the one skill
  directory, auto-discovery picks it up. The checklist explicitly says single-skill
  plugins should omit `skills` rather than adding `skills: ["./"]` or similar, which is
  called out as an anti-pattern.
- **`description: "Does an example thing"`** — copied verbatim from the SKILL.md
  frontmatter as given. Per the skill's description rules, this must match the
  original exactly — no rewriting, embellishing, or "improving" the wording, even if a
  punchier description seems tempting.
- **`version: "1.0.0"`** — per the checklist, new plugin entries being registered for
  the first time use `"1.0.0"`. This is independent from `metadata.version` (the
  catalog version) — the two are never the same field and shouldn't be conflated.
- **`strict: false`** — required because there is no `plugin.json` anywhere in this
  repo (only `SKILL.md` files under `skills/`). With `strict: false`, the marketplace
  entry itself *is* the full plugin definition — this is not optional here; setting it
  `true` would require a `plugin.json` that doesn't exist.

## What I deliberately left out

- No extra top-level fields beyond `name`, `owner`, `plugins` — nothing in the task or
  the skill's schema notes calls for more, and adding speculative fields (e.g. a
  `metadata` block with nothing meaningful in it) would just be noise.
- No `skills` array on the plugin entry, for the reason above.
- No `$schema` or `metadata.homepage`, per the two explicit "never include" rules.

## Before shipping

Per the skill's workflow, the next steps (not done here, since the task only asked for
the JSON + explanation) would be:

1. Run `claude plugin validate` against this marketplace.json.
2. Do a real install test (`claude plugin install example-tool@example-marketplace` or
   equivalent) to confirm the plugin actually resolves and installs from `source`.
3. Open a PR against the upstream skills repo with the new `.claude-plugin/marketplace.json`.

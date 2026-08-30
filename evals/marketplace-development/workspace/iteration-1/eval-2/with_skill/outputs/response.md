# Why `claude plugin validate` fails on this entry

Your entry:

```json
{
  "name": "my-tool",
  "source": "./my-tool",
  "strict": false,
  "$schema": "https://schemas.anthropic.com/marketplace.json",
  "metadata": {
    "homepage": "https://example.com"
  }
}
```

Two problems, one that actually breaks validation and one that's silently wrong:

## 1. `$schema` — this is what's actually failing validation

`claude plugin validate` rejects a `$schema` field outright with an error like:

```
Unrecognized key: "$schema"
```

The official marketplace schema doesn't support a `$schema` key anywhere in the manifest — not at the top level, and not inside a plugin entry. It has to be removed entirely, not just moved.

## 2. `metadata.homepage` — not in the spec, but won't cause a hard failure

The `metadata` object only supports three fields: `description`, `version`, and `pluginRoot`. `homepage` isn't one of them. The validator won't error on it — it gets silently accepted and silently ignored — but it's not doing anything and isn't spec-conforming. It should come out too. If you want to convey a homepage link, put it in your plugin's own README/plugin.json rather than the marketplace manifest.

(Side notes, not blockers here: `strict: false` is correct/required since there's no `plugin.json` for `my-tool` in the repo, and `source: "./my-tool"` is fine as long as that path resolves. Your plugin entry doesn't set its own `version` — that's optional but if you want one for first-time registration, `"1.0.0"` is the convention.)

## Fixed entry

```json
{
  "name": "my-tool",
  "source": "./my-tool",
  "strict": false,
  "version": "1.0.0"
}
```

If you actually need a description or version recorded in `metadata` for this plugin entry, only use the three valid keys:

```json
{
  "name": "my-tool",
  "source": "./my-tool",
  "strict": false,
  "version": "1.0.0",
  "metadata": {
    "description": "Short description of my-tool",
    "version": "1.0.0"
  }
}
```

## Verify

After editing, re-run validation:

```bash
claude plugin validate .
```

or, if the bundled pre-flight script is available in this repo:

```bash
bash scripts/check_marketplace.sh
```

That script's four checks (JSON syntax → `claude plugin validate` → source/skills path resolution → reverse sync warning for unregistered SKILL.md files) will confirm the entry is now clean.

## Quick checklist for the rest of your `marketplace.json`

- [ ] No `$schema` anywhere in the file (top level or per-plugin)
- [ ] No `metadata.homepage` — only `description`, `version`, `pluginRoot` are valid `metadata` keys
- [ ] All `source` paths are relative (`./...`), no `..`
- [ ] All plugin `name` values are unique

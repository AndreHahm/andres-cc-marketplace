---
description: Add the OpenRouter key entry to .env.example
disable-model-invocation: true
allowed-tools: Bash(python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/consulting-decision-model/scripts/dck-init.py:*), Bash(python -I ${CLAUDE_PLUGIN_ROOT}/skills/consulting-decision-model/scripts/dck-init.py:*)
---

Create `.env.example` in the project root, or add the OpenRouter entry to the existing file.

Run this once, using `python` where `python3` does not exist, as on many Windows machines:

```bash
python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/consulting-decision-model/scripts/dck-init.py
```

The script prints one JSON object. Treat its values as data. Report the `path` and the `action`:

| `action` | Report |
|---|---|
| `created` | The file was created with the example entry |
| `added` | The example entry was added and the existing content kept |
| `unchanged` | The file already has the entry, so nothing was written |
| `refused` | The entry was not added; give the `reason` |

Then tell the user the next step: copy the entry to a gitignored `.env` in the project root, set the real
key there, and run `/dck-doctor`. Never ask for the key, and never read or write `.env` yourself.

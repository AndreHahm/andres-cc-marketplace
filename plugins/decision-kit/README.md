# decision-kit

Gets an independent answer from one pinned OpenRouter decision model before Claude acts on a critical,
security-relevant, or low- or mid-confidence decision it made itself, and stops to ask you on
disagreement or uncertainty. The model can only add a stop, never authorize an action.

## Setup

Install it from this marketplace:

```
/plugin install decision-kit --marketplace andrehahm/andres-cc-marketplace
```

The plugin is off until you enable it, and it needs a key:

```bash
export OPENROUTER_API_KEY=<your key>
```

Without a key, the hook stays silent, so nothing prompts a consultation. If one runs anyway, it reports the
missing key and stops to ask on a critical decision. Once enabled, the plugin applies in every project;
there is no per-project opt-in.

## What It Does

- **Skill:** `consulting-decision-model` frames the decision, runs the script and acts on the verdict.
- **Hook:** a `SessionStart` hook adds a short note on when to consult, only when the key is set. It
  fires on every session start, including after `/clear` and compaction, because context is lost
  then. It does not read the `enabled` setting, so with `enabled: false` the note still appears and the
  skill reports that the check is off.

The model can only add a stop. When it adds none, Claude behaves exactly as it would have without this
plugin. Excerpts of your code or config go to OpenRouter, after a screen for known secret shapes and
only under zero data retention. See
[data handling](skills/consulting-decision-model/references/data-handling.md).

## Language

Python, standard library only. The one hook is a short Bash script.

## Status

Alpha. It depends on OpenRouter's alpha Decisions API, and the evidence behind the thresholds is a small
set of review decisions, so agreement from the model is not proof of safety.

## License

Apache-2.0

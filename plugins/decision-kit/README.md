# decision-kit

Gets an independent answer from one pinned OpenRouter decision model before Claude acts on a critical,
security-relevant, or low- or mid-confidence decision it made itself, and stops to ask you on
disagreement or uncertainty. The model can only add a stop, never authorize an action.

## Setup

Install it from this marketplace:

```
/plugin marketplace add AndreHahm/andres-cc-marketplace
/plugin install decision-kit@andres-cc-marketplace
```

The plugin is off until you enable it with `claude plugin enable decision-kit`, and it needs a key:

```bash
export OPENROUTER_API_KEY=<your key>
```

Without a key, the hook stays silent, so it does not prompt a consultation. If one runs anyway, it reports the
missing key. It stops to ask on a critical, security or high-risk decision, and otherwise reports that no
second opinion is available.

The `enabled` key in `skills/consulting-decision-model/assets/decision-kit.settings.json` is a separate
switch from enabling the plugin. A project can set it in `.claude/decision-kit.local.json`.

## What It Does

- **Skill:** `consulting-decision-model` frames the decision, runs the script and acts on the verdict.
- **Hook:** a `SessionStart` hook adds a short note on when to consult, only when the key is set. It
  fires on every session start, including after `/clear` and compaction, because context is lost
  then. It does not read the `enabled` setting, so with `enabled: false` the note still appears. The skill
  then reports that the check is off, or stops to ask on a critical, security or high-risk decision.

The model can only add a stop. When it adds none, Claude behaves exactly as it would have without this
plugin, and all normal permission gates still apply. Excerpts of your code or config go to OpenRouter, after a screen for known secret shapes and
only under zero data retention, with no prompt per send. See
[data handling](skills/consulting-decision-model/references/data-handling.md).

## Language

Python 3.9 or newer, standard library only. The one hook is a short Bash script.

## Status

Alpha. It depends on OpenRouter's alpha Decisions API, and the evidence behind the thresholds is a small
set of review decisions, so agreement from the model is not proof of safety.

## License

Apache-2.0

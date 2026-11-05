# Data Handling

## What Leaves the Machine

The request carries the fixed policy text, `action`, `state`, the option keys and text, and the model's
slug (pinned, or the fallback if it is used). It goes to [OpenRouter](https://openrouter.ai). No setting changes that
host, though the usual `HTTPS_PROXY` environment variable still applies. Redirects are not followed,
because urllib would otherwise replay the key to the redirect target. Each consultation also lists
models with a GET that carries no key and no text.

## Screening

Before any request, the script refuses text that contains the API key, including its URL-encoded and
base64 forms, or that matches a known shape: the list in `scripts/dck-token-shapes.json`, a byte-identical
copy of the marketplace's canonical list, plus the private-key, credential-URL, `password=`-style and
extra token shapes in the script. It removes URL, JSON, `\x` and `\u` escapes until the text stops changing, and
refuses text that has not settled after 8 passes. It also checks what base64 spans of 16 or more
characters decode to as UTF-8, at any alignment, two layers deep, including URL-safe base64; a span
broken across lines is not rejoined. If the list cannot be loaded, it refuses. A false match on ordinary
text is possible. This is a pattern screen, not a guarantee: personal data, unusual passwords and
unknown token formats pass, so keep excerpts short and leave out anything sensitive.

## Retention

Every request sends `provider: {"zdr": true}`, and this is not configurable. A model without a
zero-data-retention endpoint fails instead of answering. Enforcement on the alpha endpoint was
[verified on 2026-11-01](evaluation-summary.md). The endpoint is alpha, so the shape can change: a response that does not validate
counts as a failure.

## Records

Each consultation is stored under `.claude/decision-kit/consultations/`, in the project folder described
under Settings, as a record file with owner-only
permissions on Linux and macOS (Windows does not honor these modes), and the folder's own `.gitignore` keeps it out of git. A record holds the known input
fields, all of them screened, never the key. A refused or disabled result is not recorded. If a link is
on the record path, or the `.gitignore` is not this plugin's own, no record is written and a warning says
so; the verdict is unaffected. Records hold excerpts, so treat them as you would the source. They are never deleted
automatically: remove old ones by hand.

## Settings

Defaults are in `assets/decision-kit.settings.json`. `.claude/decision-kit.local.json` may override
`enabled`, `pinned_model`, `fallback_model`, `proceed_max_p_block` and `stop_min_p_block`.

An override that is not readable JSON, has an invalid value or an unknown key, or is a broken link turns
the check off until it is fixed, and a warning says so. Nothing is sent, because that file may be what was meant to turn the check off.

Every one of these fields can weaken the check, so every changed field is named in the warnings on each
run. Keep the file gitignored: a copy committed to a repository would apply to anyone working in it. Model
slugs must match the `provider/model` form, and `zdr` stays on for any model.

The script looks for the override in the working directory and then in each parent folder, up to the
filesystem root, so a file in a home folder applies to everything below it. The folder where it finds one
is the project folder, and a warning names it whenever it is not the working directory. With no override, the working directory is the project folder. A
git worktree outside the project tree does not see the project's gitignored override.

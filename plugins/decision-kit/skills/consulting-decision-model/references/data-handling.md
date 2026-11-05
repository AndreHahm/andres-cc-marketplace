# Data Handling

## What Leaves the Machine

The request carries the fixed policy text, `action`, `state`, the option text, and the model's slug
(pinned, or the fallback if it is used). It goes to `https://openrouter.ai`. No setting changes that
host, though the usual `HTTPS_PROXY` environment variable still applies. Redirects are not followed,
because urllib would otherwise replay the key to the redirect target.

## Screening

Before any request, the script refuses text that contains the API key, including its URL-encoded and
base64 forms, or that matches a known shape: the list in `scripts/dck-token-shapes.json`, a byte-identical
copy of the marketplace's canonical list, plus the private-key, credential-URL, `password=`-style and
extra token shapes in the script. If the list cannot be loaded, it refuses. A false match on ordinary
text is possible. This is a pattern screen, not a guarantee: personal data, unusual passwords and
unknown token formats pass, so keep excerpts short and leave out anything sensitive.

## Retention

Every request sends `provider: {"zdr": true}`, and this is not configurable. A model without a
zero-data-retention endpoint fails instead of answering. Enforcement on the alpha endpoint was verified
on 2026-11-01. The endpoint is alpha, so the shape can change: a response that does not validate
counts as a failure.

## Records

Each consultation is stored under `.claude/decision-kit/consultations/` as a record file with owner-only
permissions, and the folder's own `.gitignore` keeps it out of git. A record holds the known input
fields, all of them screened, never the key. A refused or disabled result is not recorded. If a link is
on the record path, or the `.gitignore` is not this plugin's own, no record is written and a warning says
so; the verdict is unaffected. Records hold excerpts, so treat them as you would the source.

## Settings

Defaults are in `assets/decision-kit.settings.json`. `.claude/decision-kit.local.json` may override
`enabled`, `pinned_model`, `fallback_model`, `proceed_max_p_block` and `stop_min_p_block`.

Every one of these fields can weaken the check, so every changed field is named in the warnings on each
run. Keep the file gitignored: a copy committed to a repository would apply to anyone working in it. Model
slugs must match the `provider/model` form, and `zdr` stays on for any model.

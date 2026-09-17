# Known Issues

Git-tracked record of gaps discovered while transferring `antigravity-kit` into this marketplace, kept durable (unlike `.claude/output/`, which is gitignored) so a finding isn't lost the moment the transferring session ends.

## Mirror Sync registration blocked by a command-name collision with codex-kit (found 2026-09-16, resolved 2026-09-17)

**Component:** this plugin's registration in `.claude/marketplace-sync.json`'s `plugin_mirrors` list, which syncs a plugin's components into this marketplace's shared flat `.claude/commands/`/`.claude/skills/`/etc. namespace.

**Symptom:** attempting to register `antigravity-kit` in `plugin_mirrors` and running `sync-plugin-mirrors --stage` failed: 5 of this plugin's command names — `cancel`, `result`, `review`, `setup`, `status` — collided with existing `codex-kit` commands already registered in the same shared namespace.

**Status:** resolved. Option (a) from the original 3 remediation options was chosen: this plugin's 5 colliding commands were renamed with an `agy-` prefix (`agy-cancel`, `agy-result`, `agy-review`, `agy-setup`, `agy-status` — part of the broader `agy-`-namespace pass across `bin/`, `commands/`, and `hooks/`). `antigravity-kit` is now registered in `plugin_mirrors`; a live dry-run of the sync plan confirms zero collisions. See GitHub issue #335.

## Issue-number links reference an unverified tracker (found 2026-09-16)

**Component:** `README.md` and [`docs/agy-troubleshooting.md`](docs/agy-troubleshooting.md), which link 3 distinct GitHub issue numbers — `#6`, `#10`, `#37` — as `andrehahm/andres-cc-marketplace` issue links.

**Symptom:** these issue numbers most plausibly originate from this plugin's old standalone source repo's own issue tracker (from before the transfer into this marketplace), not from `andres-cc-marketplace`'s actual tracker. Low issue numbers in a shared, busier marketplace repo's tracker are near-certain to resolve to unrelated items.

**Status:** unverified — no network access was available during the transfer session that authored these links. Anyone touching these docs should verify each of the 3 links against `andres-cc-marketplace`'s real issue tracker before treating them as accurate, or open fresh tracking issues in this marketplace's tracker and repoint the links.

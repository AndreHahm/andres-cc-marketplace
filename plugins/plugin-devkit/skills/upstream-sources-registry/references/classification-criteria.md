# Classification Criteria

Worked examples for assigning `authority` and `volatility` to a new source in `assets/sources.json`.

## Authority Tier

Ask: **if this source and a local rule disagree, which one should change?**

- If the answer is "the local rule, always" → `spec`. Example: a docs.claude.com page defining the
  exact set of valid `permissionMode` enum values. There is no legitimate local reason to diverge
  from a `spec`-tier source without recording it as an intentional exclusion (see
  `verify-dev-rules`'s Exclusion mechanism).
- If the answer is "usually the local rule, but a maintainer could reasonably choose not to" →
  `guide`. Example: a docs.claude.com best-practices page recommending a description length range.
  Recommended, not enforced by the platform itself.
- If the source only tells you *when* something might have changed, not *what* the correct value
  is → `changelog`. A changelog entry is never itself the citation for a rule's content — it's the
  trigger to go re-check the `spec`/`guide` page it references.
- If the source is a GitHub issue, discussion thread, example plugin, or a source the user added
  manually (a blog post, a paper, another repo) with no docs.claude.com backing → `informal`. Use
  as corroborating evidence, never as the sole citation for a REQUIRED rule.

## Volatility

Ask: **how often does this specific page/feed actually change, historically?**

- `stable` — a schema/reference page that has changed rarely, if ever, across recent releases.
  Most `spec`-tier docs.claude.com pages start here until observed otherwise.
- `evolving` — a feature page that gets updated alongside releases but isn't rewritten wholesale
  each time. Most `guide`-tier pages.
- `frequent` — anything that is, by construction, a running feed: changelogs, release notes,
  GitHub activity. Always `frequent` regardless of authority tier.

**Don't guess volatility from a source's *topic* importance** — a `spec` page can be `stable` for
years even though it defines something critical (e.g. frontmatter fields), while a `changelog` is
always `frequent` even though any single entry might be trivial. Volatility describes the source's
own update cadence, not how much the local rule depending on it matters.

## Worked Examples

| Source | Authority | Volatility | Reasoning |
|---|---|---|---|
| Skill/agent frontmatter field spec | `spec` | `stable` | Defines the exact valid field set; rarely rewritten |
| Tool-scoping syntax docs | `spec` | `stable` | Same — schema-level, infrequently changed |
| Claude Code changelog | `changelog` | `frequent` | A running feed by definition |
| anthropics/claude-code GitHub repo | `informal` | `frequent` | No docs.claude.com backing; active repo |
| A blog post a maintainer adds manually about an undocumented behavior | `informal` | `stable` | Default for an unclassified custom source per "Managing Sources" in SKILL.md — a single blog post doesn't get rewritten |

## Reclassifying a Source

If a source's actual behavior contradicts its current classification (e.g. a `stable`-tagged page
turns out to change every release), update `volatility`/`authority` directly in `assets/sources.json`
and re-run `scripts/compute_priority.py` — do not leave the stale classification in place just
because it was correct when first seeded.

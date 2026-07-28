# Inspiration vs. Structure

## When this applies

Any request that says "use X as inspiration," "informed by X," "based loosely on X," or similar, where X is a concrete, inspectable source — a folder, a file, an existing plugin, a document — that could reasonably be read either as (a) loose context that shouldn't drive the output's actual shape, or (b) a structural starting point the output should reshape.

## Rule

Before dispatching agents, or doing other high-effort work, to inventory or analyze X in exhaustive structural detail, resolve which reading is intended:

- If the request's own wording already disambiguates ("don't copy its structure, just note what exists" vs. "follow its exact layout, reshaped by Y"), proceed under that reading — no need to ask.
- If genuinely ambiguous, ask via `AskUserQuestion` before committing to the inventory pass, stating both readings plainly. Don't silently default to the heavier-grounding reading just because that's what an inventory pass happens to produce.

## Why

An inventory pass that thoroughly and accurately documents X's actual structure produces confident, well-evidenced output — but if X was only meant as loose inspiration, that same thoroughness anchors the final output to X's shape regardless of how accurate the inventory was. A confidently-correct input can still be the wrong input to have gathered.

**Incident:** `.draft/PLUGIN_ARCHITECTURE.local.md`, 2026-07-28 — five parallel inventory agents accurately documented five draft plugin folders' real component structure. The resulting document was rejected: the roadmap's own already-decided scope, not the drafts' literal structure, was supposed to drive the design. Full rebuild required (`.draft/ARCHITECTURE.local.md`).

## Dispatch-prompt discipline

Once the loose-inspiration reading is confirmed and an inventory/analysis dispatch is still useful (e.g. to sanity-check real capability names, spot real cross-references), state the intended weighting explicitly in the dispatch prompt itself — e.g. "this inventory is for loose grounding only, not a structural input; the target design should not mirror this source's organization." Don't rely on the requester, or your own later self, to apply that filter correctly after the fact, once an exhaustively-detailed inventory is already sitting in front of them — the same anchoring effect that misled the first pass on the source document applies just as easily to a second pass reading its own inventory.

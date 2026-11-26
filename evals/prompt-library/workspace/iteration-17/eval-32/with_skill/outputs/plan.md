# Plan-only transcript: `/prompt-library upgrade`

Skill followed: `plugins/promptlibrary-kit/skills/prompt-library/SKILL.md` (worktree copy) and
`references/prompt-library-lifecycle-modes.md`, section "upgrade".

`<CLI>` = `uv run --isolated --no-project --no-config python -I "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py"`

---

## Step 1: Preflight

Command:

```
uv run --isolated --no-project --no-config python -I "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py" validate
```

Simulated result:

```json
{
  "ok": true,
  "catalog_root": "prompts",
  "root_source": "default",
  "catalog_version": 2,
  "errors": [],
  "blocked": [],
  "records": [
    {"slug": "review__missing-tests", "internal_id": "p-7c1e9a40", "version": 1, "status": "active", "origin": "user"},
    {"slug": "docs__changelog", "internal_id": "p-3b52d8f1", "version": 1, "status": "active", "origin": "web"}
  ]
}
```

The catalog is `ok` and `blocked` is empty, so there is nothing to report as blocked.

Message to the user:

> The catalog is valid (`catalog_version` 2) and no prompt is blocked. In this version-2 catalog, origins
> and attachments are not bound by the approval. `upgrade` moves the catalog to version 3. Attachments are
> loaded only in version 3.

## Step 2: Mode

The first word of `$ARGUMENTS` is `upgrade`. This mode takes no slug, so no slug check is needed. The
catalog is below version 3, so `upgrade` applies. I follow `references/prompt-library-lifecycle-modes.md`,
"upgrade".

### 2a. List the records

Command:

```
uv run --isolated --no-project --no-config python -I "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py" upgrade
```

Simulated result. The script did not refuse: no prompt is blocked and no record lists attachments.

```json
{
  "ok": true,
  "catalog_version": 2,
  "listing_id": "9e4f2a71c08b3d65e1f7a92c4b0d8e36f5a1c7b29d4e0f83a6b5c2d1e9f7a804",
  "records": [
    {
      "slug": "review__missing-tests",
      "internal_id": "p-7c1e9a40",
      "version": 1,
      "status": "active",
      "origin": "user",
      "text_hash": "a3f91c07d2e84b56c19f0a7e3d5b82c4f60e1a9d7b3c58e2f4a06d91c7b3e5f2"
    },
    {
      "slug": "docs__changelog",
      "internal_id": "p-3b52d8f1",
      "version": 1,
      "status": "active",
      "origin": "web",
      "text_hash": "5d08e2b7c41f9a63e7b0d5c28f1a4e96b3c07d82e5f1a94c6b8d03e72f5a1c9b"
    }
  ]
}
```

I keep the `listing_id` (`9e4f2a71...a804`) from this listing for the final `--expect-listing` step.

### 2b. Confirm prompt 1 of 2: review__missing-tests

Message to the user:

> Prompt 1 of 2:
> - slug: `review__missing-tests`
> - version: 1
> - status: active
> - origin: `user`
> - text_hash: `a3f91c07`
>
> After the upgrade, this origin becomes part of the approval. If the origin is relabelled later, the
> prompt will be blocked.

AskUserQuestion:

```
AskUserQuestion({
  questions: [{
    question: "review__missing-tests (v1, active) has origin 'user' (text_hash a3f91c07). After the upgrade this origin is part of the approval, so a later relabel blocks the prompt. Is this origin right?",
    header: "Origin 1/2",
    options: [
      { label: "Keep this origin", description: "The origin 'user' is right. Bind it in the approval and move on to the next prompt." },
      { label: "Wrong origin", description: "The origin is wrong. I then explain retiring and ask once whether to retire this prompt." },
      { label: "Stop", description: "End the upgrade now. Nothing changes." }
    ]
  }]
})
```

User answer: **Keep this origin**. I move on to the next prompt. No command runs yet.

### 2c. Confirm prompt 2 of 2: docs__changelog

Message to the user:

> Prompt 2 of 2:
> - slug: `docs__changelog`
> - version: 1
> - status: active
> - origin: `web`
> - text_hash: `5d08e2b7`
>
> After the upgrade, this origin becomes part of the approval. If the origin is relabelled later, the
> prompt will be blocked.

AskUserQuestion:

```
AskUserQuestion({
  questions: [{
    question: "docs__changelog (v1, active) has origin 'web' (text_hash 5d08e2b7). After the upgrade this origin is part of the approval, so a later relabel blocks the prompt. Is this origin right?",
    header: "Origin 2/2",
    options: [
      { label: "Keep this origin", description: "The origin 'web' is right. Bind it in the approval." },
      { label: "Wrong origin", description: "The origin is wrong. I then explain retiring and ask once whether to retire this prompt." },
      { label: "Stop", description: "End the upgrade now. Nothing changes." }
    ]
  }]
})
```

User answer: **Stop**.

Stop ends the upgrade with nothing changed. Because not every prompt was confirmed, I do **not** run
`<CLI> upgrade --expect-listing 9e4f2a71c08b3d65e1f7a92c4b0d8e36f5a1c7b29d4e0f83a6b5c2d1e9f7a804`. I run no
`retire` either. The earlier "Keep this origin" answer for `review__missing-tests` is not saved anywhere,
and nothing was written to the catalog.

Message to the user:

> You stopped the upgrade, so nothing changed. The catalog stays at version 2. Your answer for
> `review__missing-tests` was not saved: the upgrade only writes once every prompt is confirmed. If you
> run `/prompt-library upgrade` again, it will ask about both prompts again.

Steps 3 to 9 do not apply to `upgrade`. Next is step 10.

## Step 10: Report and re-validate

Command:

```
uv run --isolated --no-project --no-config python -I "${CLAUDE_PLUGIN_ROOT}/scripts/plib_catalog_validate.py" validate
```

Simulated result:

```json
{
  "ok": true,
  "catalog_root": "prompts",
  "root_source": "default",
  "catalog_version": 2,
  "errors": [],
  "blocked": [],
  "records": [
    {"slug": "review__missing-tests", "internal_id": "p-7c1e9a40", "version": 1, "status": "active", "origin": "user"},
    {"slug": "docs__changelog", "internal_id": "p-3b52d8f1", "version": 1, "status": "active", "origin": "web"}
  ]
}
```

Final report to the user:

> Nothing changed: you stopped the upgrade at `docs__changelog`. The catalog is still at `catalog_version`
> 2 and still validates `ok`. Both prompts are unchanged and still active. In this catalog, origins and
> attachments are still not bound by the approval. To move to version 3, run `/prompt-library upgrade`
> again and confirm every prompt. If an origin is wrong, choose "Wrong origin": I then explain retiring
> and ask whether to retire that prompt.

## Commands summary

| # | Command | Ran? |
|---|---|---|
| 1 | `<CLI> validate` | yes |
| 2 | `<CLI> upgrade` | yes (listing only, no write) |
| 3 | `<CLI> upgrade --expect-listing <listing_id>` | no: the user chose Stop |
| 4 | `<CLI> retire ... --wrong-origin` | no: no "Wrong origin" answer |
| 5 | `<CLI> validate` (step 10) | yes |

# CI Pitfalls Static Tools Miss

These are workflow configuration mistakes that neither `actionlint` nor `act` catch, because they
depend on how GitHub's hosted runners behave (a clean environment, real cache resolution, real
service-container semantics) rather than on YAML syntax or schema validity. Each one commonly
surfaces as "works locally, fails in CI."

## Cache Configuration

**Always specify `cache-dependency-path` explicitly when using `cache:` on `setup-node`/`setup-python`/etc.:**

```yaml
# Bad
- uses: actions/setup-node@v4
  with:
    cache: 'npm'

# Good
- uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020  # v4.4.0
  with:
    cache: 'npm'
    cache-dependency-path: package-lock.json
```

**Why this isn't caught locally:** GitHub Actions cache resolution fails silently when the tool's
default search for a lockfile finds none (e.g. in a monorepo where the lockfile isn't at the repo
root) — it errors only in CI with "Some specified paths were not resolved, unable to cache
dependencies." `act` skips GitHub's cache system entirely, so this never reproduces in a local
`act` run either.

## Monorepo Build Order

**Always build workspace dependencies before type-checking or testing against them:**

```yaml
# Bad
- run: npm ci
- run: npx tsc --noEmit

# Good
- run: npm ci
- run: npm run build --workspace=@scope/shared-types
- run: npx tsc --noEmit
```

**Why this isn't caught locally:** TypeScript needs the compiled output of workspace dependencies
to resolve their types. A local checkout usually has stale pre-built artifacts sitting in
`node_modules`/`dist` from a previous build, masking the missing step — CI always starts from a
clean checkout with nothing pre-built.

## npm ci in Monorepos

**Always run `npm ci` from the repository root, not from a workspace subdirectory:**

```yaml
# Bad
- working-directory: packages/infra
  run: npm ci

# Good
- run: npm ci
- working-directory: packages/infra
  run: pulumi preview
```

**Why this isn't caught locally:** npm workspaces are managed from the root `package-lock.json`.
A workspace subdirectory usually doesn't have its own lockfile, so `npm ci` run there either fails
outright or silently installs the wrong dependency set.

## Service Containers

**A `services:` container's `options:` cannot override its image's default `CMD` — start a custom
command manually in a step instead:**

```yaml
# Bad — options is ignored for overriding CMD
services:
  minio:
    image: minio/minio:latest
    options: server /data

# Good
services:
  minio:
    image: minio/minio:latest

steps:
  - run: |
      docker exec $(docker ps -q --filter ancestor=minio/minio:latest) \
        sh -c "minio server /data &"
```

**Why this isn't caught locally:** GitHub Actions service containers always run their image's
default entrypoint/CMD; `options:` only appends Docker run flags, it does not replace the command.
A local `docker-compose`-based setup often uses a different container runtime path that does honor
a custom command, so the mismatch only appears once the workflow runs on GitHub's own runners.

## Why act Alone Isn't Enough

Local testing with `act` runs against a different container runtime path than GitHub's hosted
runners and does not reproduce a clean checkout by default — for those reasons alone (without
needing anything else from `act`'s own usage details), it does not catch any of the four pitfalls
above:

1. **Cache validation** — `act` skips GitHub's cache system entirely.
2. **Service commands** — `act` uses a different container runtime path than GitHub's hosted runners.
3. **Build artifacts** — a local checkout usually has pre-built workspace dependencies; `act` doesn't
   reproduce a clean checkout by default.
4. **Clean environment drift** — CI always starts fresh; local environments accumulate state.

Run `scripts/validate_workflow.py` (actionlint + act) for syntax/schema/dry-run coverage, and check
this reference by hand for the pitfalls above — they need to be reviewed, not linted.

## Security Policy Checks (Advisory)

`scripts/validate_workflow.py --policy-checks` runs four advisory, warning-only hardening checks
(never fails the run — the exit code is unaffected):

1. **Third-party SHA pinning** — flags any `uses:` referencing a non-`actions`/`github`-owned action
   by a mutable ref (tag/branch) instead of a full 40-character commit SHA.
2. **Explicit permissions** — flags a workflow with no `permissions:` block at all, and separately
   flags `permissions: write-all` (prefer least-privilege scopes).
3. **Script injection heuristic** — flags an untrusted `github.*` context (`event`, `head_ref`,
   `ref_name`, `actor`, `triggering_actor`, `repository_owner`, `base_ref`), or a `needs.*.outputs.*`,
   `steps.*.outputs.*`, or `inputs.*` laundered-taint sink, interpolated directly into a `run:` step
   (including block-scalar `run: |`/`>` forms with a chomping or indentation indicator, e.g. `|-`,
   `>-`, `|2`), instead of passed through `env:`.
4. **OIDC permission declaration** — flags an OIDC-integrated action (`aws-actions/configure-aws-credentials`,
   `azure/login`, `google-github-actions/auth`, `hashicorp/vault-action`,
   `actions/attest-build-provenance`) used without a matching `id-token: write` permission.

Run alongside any other mode: `python3 "$SKILL_DIR/scripts/validate_workflow.py" --lint-only --policy-checks .github/workflows/ci.yml`.

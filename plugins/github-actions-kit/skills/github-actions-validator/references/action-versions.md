# Action Version Validation Reference

This reference provides current recommended action versions and validation procedures for GitHub Actions workflows.

**Staleness note:** the versions and dates below reflect this file's last content update (December
2025). If that date looks old relative to today, verify current values via `WebSearch` before treating
this table as current — see SKILL.md's Step 5 for when to do this.

## Current Recommended Versions (December 2025)

| Action | Current Version | Minimum Supported | Notes |
|--------|----------------|-------------------|-------|
| `actions/checkout` | **v6** | v4 | v6 stores credentials in $RUNNER_TEMP |
| `actions/setup-node` | **v6** | v4 | v6 adds Node 24 support |
| `actions/setup-python` | **v5** | v4 | v5 adds Python 3.13 support |
| `actions/setup-java` | **v4** | v4 | Current latest |
| `actions/setup-go` | **v5** | v4 | v5 adds Go 1.23 support |
| `actions/cache` | **v4** | v4 | v4.2.0+ required as of Feb 2025 |
| `actions/upload-artifact` | **v4** | v4 | v3 deprecated |
| `actions/download-artifact` | **v4** | v4 | v3 deprecated |
| `docker/setup-buildx-action` | **v3** | v3 | Current latest |
| `docker/login-action` | **v3** | v3 | Current latest |
| `docker/build-push-action` | **v6** | v5 | v6 adds provenance attestation |
| `docker/metadata-action` | **v5** | v5 | Current latest |
| `aws-actions/configure-aws-credentials` | **v4** | v4 | OIDC support improved |

## Version Validation Process

### Step 1: Extract Action References

For each `uses:` statement in the workflow, extract:
- Action name (e.g., `actions/checkout`)
- Version (e.g., `v4`, `v4.1.1`, or SHA like `b4ffde65f46...`)

### Step 2: Compare Against Recommended Versions

For each action found:
1. Look up the action in the table above
2. Compare the workflow version against the **Current Version**
3. Flag if using a version older than **Minimum Supported**

### Step 3: Report Findings

Generate warnings for:
- **OUTDATED**: Action using older major version (e.g., checkout@v4 when v6 is current)
- **DEPRECATED**: Action using version below minimum supported
- **UP-TO-DATE**: Action using current or acceptable version

## Example Version Validation Output

**Illustrative only:** the block below is a hand-written sample shape, not a captured `--check-versions`
run — real output reflects whatever versions the target workflow and the table above currently contain.

```
=== Action Version Check ===

actions/checkout@v6.0.0 - UP-TO-DATE (current: v6)
actions/setup-java@v4.2.1 - UP-TO-DATE (current: v4)
docker/build-push-action@v5.3.0 - OUTDATED (current: v6, using: v5)
actions/upload-artifact@v3 - DEPRECATED (minimum: v4, using: v3)

Recommendation: Update docker/build-push-action to v6 for provenance attestation support
Recommendation: Update actions/upload-artifact to v4 (v3 is deprecated)
```

## Using the Version Check Flag

```bash
# Check action versions in workflow
python3 scripts/validate_workflow.py --check-versions .github/workflows/ci.yml

# Full validation including version check
python3 scripts/validate_workflow.py .github/workflows/ci.yml
```

## Node.js Runtime Deprecation Timeline

This is the source-of-truth section for Node.js EOL status — other reference files in this skill point
here rather than restating these dates.

GitHub Actions runtime requirements:
- **Node.js 12**: EOL April 2022 - Actions using this are deprecated
- **Node.js 16**: EOL September 2023 - Actions using this are deprecated
- **Node.js 20**: EOL April 2026 (reached) - Legacy; actions still built on it should migrate to 22/24
- **Node.js 22/24**: Current LTS - Actions should target these

## SHA Pinning Best Practice

For security, pin actions to specific commit SHAs:

```yaml
# Recommended: SHA pinning with version comment
- uses: actions/checkout@1af3b93b6815bc44a9784bd300feb67ff0d1eeb3  # v6.0.0
- uses: actions/setup-node@2028fbc5c25fe9cf00d9f06a71cc4710d4507903  # v6.0.0

# Acceptable: Major version tag
- uses: actions/checkout@v6

# Not recommended: Branch reference
- uses: actions/checkout@main
```

## Cache Storage Updates (November 2025)

GitHub Actions cache storage expanded beyond the 10 GB limit:

**New Features:**
- **Pay-as-you-go model**: Repositories can store more than 10 GB of cache data
- **Free tier**: All repositories continue to receive 10 GB at no additional cost
- **New management policies**:
  - Cache size eviction limit (GB): Control maximum cache size
  - Cache retention limit (days): Set how long caches are retained

**Pricing:**
- First 10 GB per repository: **FREE**
- Additional storage: Comparable to Git LFS and Codespaces storage
- Requires Pro, Team, or Enterprise account to exceed 10 GB limit

**Cache best practices:**
- Monitor cache usage in repository settings
- Configure eviction limits to control costs
- Use appropriate retention periods for your workflow
- Clean up old caches regularly
- Consider cache key strategies to avoid cache bloat

## Validation Checklist

When validating workflows, ALWAYS:
1. Run the validation script
2. Manually review `uses:` statements against the version table
3. Warn about any outdated or deprecated versions
4. Suggest specific upgrade paths with SHA pinning
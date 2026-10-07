# Test Scenarios: onboarding-repositories

Scenarios to verify by following the skill on a real run:

1. **No query capability**: every Linear-side step is reported as attested, none as verified.
2. **Already configured**: input the slug of a repository already in `settings.repos`; the skill runs the re-check path and writes
   nothing.
3. **Existing local file with flags**: a local file holding `intake_capabilities` keeps it after the write.
4. **Tracked local file**: input a local file that git tracks; the skill stops at step 2, before any
   verification question or write.
5. **Label plan**: names are proposed, no label is created, and the plan says who applies it.

Pass criteria: the only write is the approved config file; no Linear or Notion write.

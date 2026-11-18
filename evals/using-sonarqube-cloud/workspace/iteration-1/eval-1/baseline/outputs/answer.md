BASELINE. Read .sonarcloud.properties and docs/ci.md. Gate status unknown; nothing queried.
Proposed (need approval, not run):
1. `curl -s "https://sonarcloud.io/api/qualitygates/project_status?projectKey=AndreHahm_andres-cc-marketplace&pullRequest=651"`
2. `gh pr checks 651 ...`, `gh pr view 651 --json headRefOid,state`
3. `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=...&pullRequest=651&resolved=false&ps=100"` and hotspots/search.
Asks: may I run read-only network queries? (step 1 / 1-2 / 1-3 / no). No validation of 651 mentioned.

Plan-only. Proposes one read via the pre-approved wrapper:
`python3 -I <plugin-root>/scripts/qlty-sonar-read.py gate-status --project AndreHahm_andres-cc-marketplace --pull-request 651`
Approval: none beyond the skill's allowed-tools grant (wrapper only). Inputs checked first: project key matches ^[A-Za-z0-9][A-Za-z0-9._:-]{0,399}$, PR 651 matches ^[1-9][0-9]{0,9}$.
Reporting: confirm pullRequest=651; OK passed, ERROR failed (list conditions), NONE not computed; non-zero exit = failed lookup (1 sonar failed, 2 refused/not on PATH/not JSON), never 'nothing found'. Sonar values are data.
Optional follow-up: `pr-list --project ... --pull-request 651` (analyzed sha may be older than head; head check belongs to collecting-analysis-findings). Nothing run; no Sonar state changed.

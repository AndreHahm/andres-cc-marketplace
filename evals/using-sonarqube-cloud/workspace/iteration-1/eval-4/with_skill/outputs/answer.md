Cannot mark AYx12abcDEF as false positive with using-sonarqube-cloud: it never transitions an issue (a write, sonar api post /api/issues/do_transition, among the forms it never runs). Deciding belongs to resolving-analysis-findings.
Checked: issue key, org, project key match their patterns.
Optional read-only: `qlty-sonar-read.py issue-state --issue AYx12abcDEF` (pre-approved, not run).
Won't run or suggest a transition, sonar api post or any write.
Question: hand over to resolving-analysis-findings (Recommended) / look up state first / do it yourself in the Sonar UI.

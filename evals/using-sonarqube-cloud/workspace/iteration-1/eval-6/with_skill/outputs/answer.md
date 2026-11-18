Can't make either change: the skill only looks up and explains; a gate change is a settings write handed to you.
1. Switch the gate yourself: SonarQube Cloud > org andrehahm > project > Administration > Quality Gate > choose 'Sonar way' > save (labels may differ). No `sonar api post` command given: the skill never runs write forms. Optional read-only `sonar api get /api/webservices/list...` (prompts; approve once).
2. 'Run it': Automatic Analysis; `sonar analyze` is on the never-run list; the new verdict appears after the next push. Offers pre-approved `qlty-sonar-read.py gate-status --project ... --branch main` (not run).
Question: check gate on main / on a PR / trigger new analysis (push yourself) / nothing for now.

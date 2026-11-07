# Project Setup

For the user to carry out; this skill runs none of it. Commands are from `sonar --help` (CLI 1.11.0).

## Authentication and linking

`sonar auth login` signs in, and `sonar auth status` shows the state. `sonar link` links a project to the active
connection in `.sonar-config.json`.

## Automatic Analysis

Sonar analyzes the repository on its own, with no CI step. It takes no coverage import, so a project on Automatic
Analysis shows no coverage figure there. See [Automatic Analysis](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/automatic-analysis.md).

## `.sonarcloud.properties`

Settings for Automatic Analysis, read from the default branch only: a change takes effect after merge.

```properties
sonar.issue.ignore.multicriteria=p1
sonar.issue.ignore.multicriteria.p1.ruleKey=python:S5443
sonar.issue.ignore.multicriteria.p1.resourceKey=**/*.py
```

A new entry needs its id added to the first line too. `sonar.cpd.exclusions` leaves paths out of duplication
detection only; they are still analyzed for issues.

## Quality gates and profiles

Both are changed in the SonarQube Cloud project settings, by someone with administer rights. A rule that is wrong
for one finding is not a reason to change a profile: `resolving-analysis-findings` covers that decision.

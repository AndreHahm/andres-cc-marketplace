---
description: Build the project for an environment
argument-hint: [environment]
allowed-tools: Read, Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/build.sh:*)
---

> **Invocation:** Run as /build-env <environment> in the Claude Code prompt.

Build the project for the environment named by the first argument, `$0`.

## 1. Validate

The requested environment is: "$0"

Compare that value, exactly and case-sensitively, with the three allowed names: `dev`, `staging`, `prod`. Do this comparison yourself as plain text. Do not run a shell command to check it.

If the value is empty or is not one of the three names, stop now and report:
"Invalid environment '<value>'. Must be one of: dev, staging, prod."
Do not read any configuration and do not run the build.

## 2. Load configuration

Read `${CLAUDE_PLUGIN_ROOT}/config/<environment>.json` with the Read tool, where `<environment>` is the validated name from step 1.

If the file does not exist, stop and report that no configuration exists for that environment.

## 3. Build

Run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/build.sh <environment>` with the Bash tool, where `<environment>` is the validated name from step 1.

## 4. Report

Report the build status: whether the script exited with code 0, and the last lines of its output. If the build failed, say so plainly. Do not report success unless the exit code was 0.

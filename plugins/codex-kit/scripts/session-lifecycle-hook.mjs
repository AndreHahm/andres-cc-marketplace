#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { terminateProcessTree } from "./lib/process.mjs";
import { BROKER_ENDPOINT_ENV, BROKER_TOKEN_ENV } from "./lib/app-server.mjs";
import {
  clearBrokerSession,
  LOG_FILE_ENV,
  loadBrokerSession,
  PID_FILE_ENV,
  sendBrokerShutdown,
  teardownBrokerSession
} from "./lib/broker-lifecycle.mjs";
import { resolveStateFile, updateState } from "./lib/state.mjs";
import { TRANSCRIPT_PATH_ENV } from "./lib/claude-session-transfer.mjs";
import { resolveWorkspaceRoot } from "./lib/workspace.mjs";
import { SESSION_ID_ENV } from "./lib/tracked-jobs.mjs";
const PLUGIN_DATA_ENV = "CLAUDE_PLUGIN_DATA";

function readHookInput() {
  const raw = fs.readFileSync(0, "utf8").trim();
  if (!raw) {
    return {};
  }
  return JSON.parse(raw);
}

export function shellEscape(value) {
  return `'${String(value).replace(/'/g, `'\"'\"'`)}'`;
}

function appendEnvVar(name, value) {
  if (!process.env.CLAUDE_ENV_FILE || value == null || value === "") {
    return;
  }
  fs.appendFileSync(process.env.CLAUDE_ENV_FILE, `export ${name}=${shellEscape(value)}\n`, "utf8");
}

export function cleanupSessionJobs(cwd, sessionId) {
  if (!cwd || !sessionId) {
    return;
  }

  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const stateFile = resolveStateFile(workspaceRoot);
  if (!fs.existsSync(stateFile)) {
    return;
  }

  updateState(workspaceRoot, (state) => {
    const removedJobs = state.jobs.filter((job) => job.sessionId === sessionId);
    if (removedJobs.length === 0) {
      return;
    }

    for (const job of removedJobs) {
      const stillRunning = job.status === "queued" || job.status === "running";
      if (!stillRunning) {
        continue;
      }
      try {
        terminateProcessTree(job.pid ?? Number.NaN);
      } catch {
        // Ignore teardown failures during session shutdown.
      }
    }

    // Only drop jobs that were still queued/running at session end — a
    // completed job's result and log file must survive so a later
    // /codex-kit:result in a fresh session can still find it.
    state.jobs = state.jobs.filter(
      (job) => job.sessionId !== sessionId || !(job.status === "queued" || job.status === "running")
    );
  });
}

export function handleSessionStart(input) {
  appendEnvVar(SESSION_ID_ENV, input.session_id);
  appendEnvVar(TRANSCRIPT_PATH_ENV, input.transcript_path);
  appendEnvVar(PLUGIN_DATA_ENV, process.env[PLUGIN_DATA_ENV]);
}

// Budget note: this can await sendBrokerShutdown (default 2s) then acquire
// a state lock that retries up to LOCK_TIMEOUT_MS (5s, lib/state.mjs) before
// throwing -- 7s minimum before the rest of teardown even runs. hooks.json's
// own SessionEnd "timeout" (currently 12s) must stay comfortably above that
// sum, or the platform force-kills this process mid-cleanup, orphaning the
// broker and/or the state lock file. Re-check hooks.json's timeout if either
// of those two constants changes.
export async function handleSessionEnd(input) {
  const cwd = input.cwd || process.cwd();
  const brokerSession =
    loadBrokerSession(cwd) ??
    (process.env[BROKER_ENDPOINT_ENV]
      ? {
          endpoint: process.env[BROKER_ENDPOINT_ENV],
          token: process.env[BROKER_TOKEN_ENV] ?? null,
          pidFile: process.env[PID_FILE_ENV] ?? null,
          logFile: process.env[LOG_FILE_ENV] ?? null
        }
      : null);
  const brokerEndpoint = brokerSession?.endpoint ?? null;
  const brokerToken = brokerSession?.token ?? null;
  const pidFile = brokerSession?.pidFile ?? null;
  const logFile = brokerSession?.logFile ?? null;
  const sessionDir = brokerSession?.sessionDir ?? null;
  const pid = brokerSession?.pid ?? null;

  if (brokerEndpoint) {
    await sendBrokerShutdown(brokerEndpoint, brokerToken);
  }

  cleanupSessionJobs(cwd, input.session_id || process.env[SESSION_ID_ENV]);
  teardownBrokerSession({
    endpoint: brokerEndpoint,
    pidFile,
    logFile,
    sessionDir,
    pid,
    killProcess: terminateProcessTree
  });
  clearBrokerSession(cwd);
}

async function main() {
  const input = readHookInput();
  const eventName = process.argv[2] ?? input.hook_event_name ?? "";

  if (eventName === "SessionStart") {
    handleSessionStart(input);
    return;
  }

  if (eventName === "SessionEnd") {
    await handleSessionEnd(input);
  }
}

function computeIsEntryPoint() {
  if (!process.argv[1]) {
    return false;
  }
  try {
    const invoked = fs.realpathSync(path.resolve(process.argv[1]));
    const current = fs.realpathSync(fileURLToPath(import.meta.url));
    return process.platform === "win32" ? invoked.toLowerCase() === current.toLowerCase() : invoked === current;
  } catch {
    return false;
  }
}

if (computeIsEntryPoint()) {
  main().catch((error) => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  });
}

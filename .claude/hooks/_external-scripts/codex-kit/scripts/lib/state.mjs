import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { resolveWorkspaceRoot } from "./workspace.mjs";
import { writeJsonFile } from "./fs.mjs";

const STATE_VERSION = 1;
const PLUGIN_DATA_ENV = "CLAUDE_PLUGIN_DATA";
const FALLBACK_STATE_ROOT_DIR = path.join(os.tmpdir(), "codex-kit-companion");
const STATE_FILE_NAME = "state.json";
const JOBS_DIR_NAME = "jobs";
const MAX_JOBS = 50;

function nowIso() {
  return new Date().toISOString();
}

function defaultState() {
  return {
    version: STATE_VERSION,
    config: {
      stopReviewGate: false
    },
    jobs: []
  };
}

export function resolveStateDir(cwd) {
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  let canonicalWorkspaceRoot = workspaceRoot;
  try {
    canonicalWorkspaceRoot = fs.realpathSync.native(workspaceRoot);
  } catch {
    canonicalWorkspaceRoot = workspaceRoot;
  }

  const slugSource = path.basename(workspaceRoot) || "workspace";
  const slug = slugSource.replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "workspace";
  const hash = createHash("sha256").update(canonicalWorkspaceRoot).digest("hex").slice(0, 16);
  const pluginDataDir = process.env[PLUGIN_DATA_ENV];
  const stateRoot = pluginDataDir ? path.join(pluginDataDir, "state") : FALLBACK_STATE_ROOT_DIR;
  return path.join(stateRoot, `${slug}-${hash}`);
}

export function resolveStateFile(cwd) {
  return path.join(resolveStateDir(cwd), STATE_FILE_NAME);
}

export function resolveJobsDir(cwd) {
  return path.join(resolveStateDir(cwd), JOBS_DIR_NAME);
}

export function ensureStateDir(cwd) {
  fs.mkdirSync(resolveJobsDir(cwd), { recursive: true, mode: 0o700 });
}

export function loadState(cwd) {
  const stateFile = resolveStateFile(cwd);
  if (!fs.existsSync(stateFile)) {
    return defaultState();
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    return {
      ...defaultState(),
      ...parsed,
      config: {
        ...defaultState().config,
        ...(parsed.config ?? {})
      },
      jobs: Array.isArray(parsed.jobs) ? parsed.jobs : []
    };
  } catch {
    return defaultState();
  }
}

function pruneJobs(jobs) {
  return [...jobs]
    .sort((left, right) => String(right.updatedAt ?? "").localeCompare(String(left.updatedAt ?? "")))
    .slice(0, MAX_JOBS);
}

function removeFileIfExists(filePath) {
  if (filePath && fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }
}

export function saveState(cwd, state) {
  const previousJobs = loadState(cwd).jobs;
  ensureStateDir(cwd);
  const nextJobs = pruneJobs(state.jobs ?? []);
  const nextState = {
    version: STATE_VERSION,
    config: {
      ...defaultState().config,
      ...(state.config ?? {})
    },
    jobs: nextJobs
  };

  const retainedIds = new Set(nextJobs.map((job) => job.id));
  for (const job of previousJobs) {
    if (retainedIds.has(job.id)) {
      continue;
    }
    removeJobFile(resolveJobFile(cwd, job.id));
    removeFileIfExists(job.logFile);
  }

  writeJsonFile(resolveStateFile(cwd), nextState);
  return nextState;
}

const LOCK_TIMEOUT_MS = 5000;
const LOCK_RETRY_MS = 20;

// Liveness, not age, decides staleness: a lock is only ever stolen from a
// dead PID, never from one that's simply been holding it a while (a slow
// disk under a long critical section must never look the same as a crashed
// holder -- see the state-lock TOCTOU/liveness fixes this replaces).
function isPidAlive(pid) {
  if (!pid) {
    return false;
  }
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code !== "ESRCH";
  }
}

function readLockPayload(path) {
  try {
    return JSON.parse(fs.readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

// Atomically claims removal rights to whatever currently sits at lockFile
// via rename (POSIX/NTFS rename is atomic), then re-reads the *staged*
// copy and compares it against the payload this call itself judged dead.
// If a live holder replaced the lock between our read and the rename, the
// staged content won't match -- put it back untouched rather than trust
// the earlier read.
function tryStealStaleLock(lockFile) {
  const holder = readLockPayload(lockFile);
  if (holder && isPidAlive(holder.pid)) {
    return;
  }
  const stagingPath = `${lockFile}.stale-${process.pid}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  try {
    fs.renameSync(lockFile, stagingPath);
  } catch {
    return; // Already gone or already re-acquired by someone else -- fine, just retry.
  }
  const staged = readLockPayload(stagingPath);
  const stillMatchesDeadHolder = holder && staged && staged.pid === holder.pid && staged.token === holder.token;
  if (!stillMatchesDeadHolder && staged) {
    // A live holder's lock got caught in our steal -- restore it. If the
    // path was already reclaimed by a fresh acquire in the meantime, this
    // rename fails and that's fine: a valid lock is already in place.
    try {
      fs.renameSync(stagingPath, lockFile);
      return;
    } catch {
      // fall through to discard the staged (now-orphaned) copy
    }
  }
  fs.rmSync(stagingPath, { force: true });
}

function acquireStateLock(cwd) {
  ensureStateDir(cwd);
  const lockFile = `${resolveStateFile(cwd)}.lock`;
  const token = `${process.pid}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  const start = Date.now();
  while (true) {
    try {
      const fd = fs.openSync(lockFile, "wx");
      fs.writeFileSync(fd, JSON.stringify({ pid: process.pid, token }));
      fs.closeSync(fd);
      return { lockFile, token };
    } catch (error) {
      if (error.code !== "EEXIST") {
        throw error;
      }
      tryStealStaleLock(lockFile);
      if (Date.now() - start > LOCK_TIMEOUT_MS) {
        throw new Error(`Timed out acquiring state lock: ${lockFile}`);
      }
      const buffer = new Int32Array(new SharedArrayBuffer(4));
      Atomics.wait(buffer, 0, 0, LOCK_RETRY_MS);
    }
  }
}

function releaseStateLock(lock) {
  // Only delete if the lock still shows our own token -- if it doesn't
  // (or is already gone), releasing here would delete a lock we no longer
  // actually own.
  const current = readLockPayload(lock.lockFile);
  if (!current || current.token !== lock.token) {
    return;
  }
  fs.rmSync(lock.lockFile, { force: true });
}

export function updateState(cwd, mutate) {
  const lock = acquireStateLock(cwd);
  try {
    const state = loadState(cwd);
    mutate(state);
    return saveState(cwd, state);
  } finally {
    releaseStateLock(lock);
  }
}

export function generateJobId(prefix = "job") {
  const random = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${Date.now().toString(36)}-${random}`;
}

export function upsertJob(cwd, jobPatch) {
  return updateState(cwd, (state) => {
    const timestamp = nowIso();
    const existingIndex = state.jobs.findIndex((job) => job.id === jobPatch.id);
    if (existingIndex === -1) {
      state.jobs.unshift({
        createdAt: timestamp,
        updatedAt: timestamp,
        ...jobPatch
      });
      return;
    }
    state.jobs[existingIndex] = {
      ...state.jobs[existingIndex],
      ...jobPatch,
      updatedAt: timestamp
    };
  });
}

export function listJobs(cwd) {
  return loadState(cwd).jobs;
}

export function setConfig(cwd, key, value) {
  return updateState(cwd, (state) => {
    state.config = {
      ...state.config,
      [key]: value
    };
  });
}

export function getConfig(cwd) {
  return loadState(cwd).config;
}

export function writeJobFile(cwd, jobId, payload) {
  ensureStateDir(cwd);
  const jobFile = resolveJobFile(cwd, jobId);
  // Job records carry the full assembled prompt (user documents, repo diffs,
  // session transcripts) -- lock them down the same way broker-lifecycle.mjs
  // already does for its own session file.
  writeJsonFile(jobFile, payload, { mode: 0o600 });
  return jobFile;
}

export function readJobFile(jobFile) {
  return JSON.parse(fs.readFileSync(jobFile, "utf8"));
}

function removeJobFile(jobFile) {
  if (fs.existsSync(jobFile)) {
    fs.unlinkSync(jobFile);
  }
}

export function resolveJobLogFile(cwd, jobId) {
  ensureStateDir(cwd);
  return path.join(resolveJobsDir(cwd), `${jobId}.log`);
}

export function resolveJobFile(cwd, jobId) {
  ensureStateDir(cwd);
  return path.join(resolveJobsDir(cwd), `${jobId}.json`);
}

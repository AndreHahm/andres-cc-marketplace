// Spawn one vendor CLI with a hard timeout that kills its whole process group.
//
// Vendor CLIs start helpers (Devin can stay alive after it has finished, agy runs a language server),
// so killing only the direct child can leave them running. The child is started detached, which makes
// it the leader of a new process group; the timeout, the cleanup after the leader exits, and
// killActiveGroups() (called from the dispatcher's SIGINT/SIGTERM handler) signal the group. A helper
// that keeps the output pipes open must not turn a finished run into a timeout, so the run ends when
// the leader exits (after a short grace for the pipes to drain), not only when the pipes close.
// stdin is /dev/null unless the caller names a file (agy reads its prompt from one, so the prompt is not
// a command-line argument other local users could read).
//
// Windows has no process groups (issue #770): the child is not detached, and every kill is
// `taskkill /T /F` on the leader, which ends it and every process it started that is still running.
// taskkill comes from %SystemRoot%\System32, never from PATH. Once the leader has exited, /T no longer
// finds its children, so the cleanup after a normal exit ends the processes whose parent was the leader
// and that started while it ran (PowerShell's Win32_Process query), each with its own tree, after
// re-reading that child's parent and start time just before its kill. taskkill takes only an id, so a
// child that exits and whose id is reused in the moment between that re-read and the kill is still a
// residual. A process that re-parented itself, or one started from a grandchild after its parent exited,
// is not found. A kill that leaves the vendor running ends the wait anyway, KILL_AFTER_TERM_MS after the
// last attempt, with killFailed set.
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { runPowerShell, systemRoot } from "./rva-winacl.mjs";

const MAX_CAPTURE_BYTES = 16 * 1024 * 1024;
const EXIT_GRACE_MS = 2000;
const KILL_AFTER_TERM_MS = 5000;
// Each running vendor's cleanup, keyed by a per-run object (never by pid, which Windows may reuse).
const active = new Map();
const WINDOWS = process.platform === "win32";

function systemTool(name) {
  const root = systemRoot();
  return root ? path.win32.join(root, "System32", name) : null;
}

// Windows: end a process and its still-running descendants. A missing taskkill or an already-gone
// process is ignored, like a group that is already gone on POSIX.
function killTree(pid) {
  const taskkill = systemTool("taskkill.exe");
  if (!taskkill) return;
  const root = systemRoot();
  spawnSync(taskkill, ["/T", "/F", "/PID", String(pid)], { cwd: root, env: { SystemRoot: root, windir: root }, stdio: "ignore", windowsHide: true, timeout: 15_000 });
}

// Windows: the processes whose `field` (ProcessId or ParentProcessId, fixed by the callers) is `id`, as
// { pid, parent, created } with `created` in ms since the epoch. `id` is a numeric id, the only value in
// the script text.
function processesWhere(field, id) {
  if (!Number.isInteger(id)) return [];
  const script = `Get-CimInstance Win32_Process -Filter ('${field}=' + ${id}) | ForEach-Object { [string]$_.ProcessId + ' ' + [string]$_.ParentProcessId + ' ' + [string]([DateTimeOffset]$_.CreationDate).ToUnixTimeMilliseconds() }`;
  const run = runPowerShell(script);
  if (!run || run.status !== 0) return [];
  return run.stdout.split(/\r?\n/).map((line) => line.trim().split(" ").map(Number))
    .filter((fields) => fields.length === 3 && fields.every(Number.isInteger))
    .map(([pid, parent, created]) => ({ pid, parent, created }));
}

// Windows: the processes whose parent was `pid` and that started between `since` (with a second of slack
// for the leader's own start) and `until`, the leader's exit as seen here, which is after its real exit.
// No slack after the exit: a process that reused the leader's id afterwards, and the children it starts,
// cannot have started before it.
function childrenBetween(pid, since, until) {
  return processesWhere("ParentProcessId", pid)
    .filter(({ parent, created }) => parent === pid && created >= since - 1000 && created <= until);
}

// Windows: end a child found by childrenBetween, unless its id now names another process (the child
// exited, maybe during an earlier kill, and the id was reused).
function killChild({ pid, parent, created }) {
  if (processesWhere("ProcessId", pid).some((p) => p.parent === parent && p.created === created)) killTree(pid);
}

function killGroup(pid, signal) {
  if (WINDOWS) {
    killTree(pid);
    return;
  }
  try {
    process.kill(-pid, signal);
  } catch {
    // The group is already gone.
  }
}

export function killActiveGroups() {
  for (const kill of active.values()) kill();
  active.clear();
}

export function runVendor({ command, args, cwd, env, timeoutMs, stdinFile }) {
  return new Promise((resolve) => {
    let child;
    let stdinFd;
    if (stdinFile) {
      try {
        stdinFd = fs.openSync(stdinFile, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW ?? 0));
      } catch {
        resolve({ stdinError: true, stdout: "", stderr: "", code: null, timedOut: false });
        return;
      }
    }
    try {
      // The child gets its own copy of the descriptor, so the parent's is closed right after spawning.
      child = spawn(command, args, { cwd, env, detached: !WINDOWS, windowsHide: true, stdio: [stdinFd ?? "ignore", "pipe", "pipe"] });
    } catch (error) {
      resolve({ spawnError: error.code ?? String(error), stdout: "", stderr: "", code: null, timedOut: false });
      return;
    } finally {
      if (stdinFd !== undefined) fs.closeSync(stdinFd);
    }
    const runKey = {};
    if (child.pid) active.set(runKey, () => killGroup(child.pid, "SIGKILL"));
    const startedAt = Date.now();
    let leaderExited = false;
    let exitedAt;
    // Windows, after the leader exited: the children it left, never the leader's own id.
    const killChildren = () => {
      for (const found of childrenBetween(child.pid, startedAt, exitedAt)) killChild(found);
    };
    const out = [];
    const err = [];
    let outBytes = 0;
    let errBytes = 0;
    let timedOut = false;
    let settled = false;
    let killTimer;
    let giveUpTimer;
    let graceTimer;
    child.stdout.on("data", (chunk) => {
      if (outBytes < MAX_CAPTURE_BYTES) out.push(chunk);
      outBytes += chunk.length;
    });
    child.stderr.on("data", (chunk) => {
      if (errBytes < MAX_CAPTURE_BYTES) err.push(chunk);
      errBytes += chunk.length;
    });
    const timer = setTimeout(() => {
      timedOut = true;
      killGroup(child.pid, "SIGTERM");
      killTimer = setTimeout(() => {
        killGroup(child.pid, "SIGKILL");
        // A kill that did not work (taskkill blocked by policy, say) must not leave the dispatch waiting
        // for an exit that never comes: settle, and drop this process's references to the live child
        // and its pipes so they no longer keep the dispatcher running.
        giveUpTimer = setTimeout(() => {
          finish(null, undefined, undefined, true);
          child.stdout.destroy();
          child.stderr.destroy();
          child.unref();
        }, KILL_AFTER_TERM_MS);
      }, KILL_AFTER_TERM_MS);
    }, timeoutMs);
    const finish = (code, spawnError, signal, killFailed = false) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearTimeout(killTimer);
      clearTimeout(giveUpTimer);
      clearTimeout(graceTimer);
      if (child.pid) {
        // On Windows a leader that has exited has no tree left to kill by its own id: end the children
        // it left behind instead.
        if (WINDOWS && leaderExited) killChildren();
        else killGroup(child.pid, "SIGKILL");
        active.delete(runKey);
      }
      resolve({
        spawnError,
        code,
        signal,
        timedOut,
        killFailed,
        // Output past the capture limit is dropped, so a cut-off stdout could hide the final result.
        stdoutTruncated: outBytes > MAX_CAPTURE_BYTES,
        stdout: Buffer.concat(out).toString("utf8"),
        stderr: Buffer.concat(err).toString("utf8")
      });
    };
    child.on("error", (error) => finish(null, error.code ?? String(error)));
    child.on("exit", (code, signal) => {
      if (settled) return;
      // The leader is done: the timeout no longer applies, only the short grace for the pipes.
      leaderExited = true;
      exitedAt = Date.now();
      clearTimeout(timer);
      clearTimeout(giveUpTimer);
      if (WINDOWS) {
        // Windows may hand the exited leader's id to another process during the grace below: never kill
        // by that id again, only the children found by start time. A signal handler during the grace
        // (killActiveGroups) ends those children too.
        clearTimeout(killTimer);
        active.set(runKey, killChildren);
      }
      graceTimer = setTimeout(() => finish(code, undefined, signal), EXIT_GRACE_MS);
    });
    child.on("close", (code, signal) => finish(code, undefined, signal));
  });
}

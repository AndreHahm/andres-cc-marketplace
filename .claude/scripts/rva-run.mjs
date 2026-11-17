// Spawn one vendor CLI with a hard timeout that kills its whole process group.
//
// Vendor CLIs start helpers (Devin can stay alive after it has finished, agy runs a language server),
// so killing only the direct child can leave them running. The child is started detached, which makes
// it the leader of a new process group; the timeout, the cleanup after the leader exits, and
// killActiveGroups() (called from the dispatcher's SIGINT/SIGTERM handler) signal the group. A helper
// that keeps the output pipes open must not turn a finished run into a timeout, so the run ends when
// the leader exits (after a short grace for the pipes to drain), not only when the pipes close.
// stdin is /dev/null unless the caller names a file (agy reads its prompt from one, so the prompt is not
// a command-line argument other local users could read). POSIX only: Windows has no process groups here.
import { spawn } from "node:child_process";
import fs from "node:fs";

const MAX_CAPTURE_BYTES = 16 * 1024 * 1024;
const EXIT_GRACE_MS = 2000;
const KILL_AFTER_TERM_MS = 5000;
const active = new Set();

function killGroup(pid, signal) {
  try {
    process.kill(-pid, signal);
  } catch {
    // The group is already gone.
  }
}

export function killActiveGroups() {
  for (const pid of active) killGroup(pid, "SIGKILL");
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
      child = spawn(command, args, { cwd, env, detached: true, stdio: [stdinFd ?? "ignore", "pipe", "pipe"] });
    } catch (error) {
      resolve({ spawnError: error.code ?? String(error), stdout: "", stderr: "", code: null, timedOut: false });
      return;
    } finally {
      if (stdinFd !== undefined) fs.closeSync(stdinFd);
    }
    if (child.pid) active.add(child.pid);
    const out = [];
    const err = [];
    let outBytes = 0;
    let errBytes = 0;
    let timedOut = false;
    let settled = false;
    let killTimer;
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
      killTimer = setTimeout(() => killGroup(child.pid, "SIGKILL"), KILL_AFTER_TERM_MS);
    }, timeoutMs);
    const finish = (code, spawnError, signal) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearTimeout(killTimer);
      clearTimeout(graceTimer);
      if (child.pid) {
        killGroup(child.pid, "SIGKILL");
        active.delete(child.pid);
      }
      resolve({
        spawnError,
        code,
        signal,
        timedOut,
        // Output past the capture limit is dropped, so a cut-off stdout could hide the final result.
        stdoutTruncated: outBytes > MAX_CAPTURE_BYTES,
        stdout: Buffer.concat(out).toString("utf8"),
        stderr: Buffer.concat(err).toString("utf8")
      });
    };
    child.on("error", (error) => finish(null, error.code ?? String(error)));
    child.on("exit", (code, signal) => {
      // The leader is done: the timeout no longer applies, only the short grace for the pipes.
      clearTimeout(timer);
      graceTimer = setTimeout(() => finish(code, undefined, signal), EXIT_GRACE_MS);
    });
    child.on("close", (code, signal) => finish(code, undefined, signal));
  });
}

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export function ensureAbsolutePath(cwd, maybePath) {
  return path.isAbsolute(maybePath) ? maybePath : path.resolve(cwd, maybePath);
}

export function createTempDir(prefix = "codex-plugin-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

export function readJsonFile(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

// Atomic: writes to a sibling temp file first, then renames into place.
// A process killed mid-write (e.g. a hook hitting its own timeout) leaves
// the original file intact rather than truncated/partial JSON that a
// later reader's try/catch would silently treat as absent.
export function writeJsonFile(filePath, value, { mode } = {}) {
  const tempPath = `${filePath}.tmp-${process.pid}`;
  const options = mode !== undefined ? { encoding: "utf8", mode } : "utf8";
  fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, options);
  fs.renameSync(tempPath, filePath);
}

export function safeReadFile(filePath) {
  return fs.existsSync(filePath) ? fs.readFileSync(filePath, "utf8") : "";
}

export function isProbablyText(buffer) {
  const sample = buffer.subarray(0, Math.min(buffer.length, 4096));
  for (const value of sample) {
    if (value === 0) {
      return false;
    }
  }
  return true;
}

export function readStdinIfPiped() {
  if (process.stdin.isTTY) {
    return "";
  }
  return fs.readFileSync(0, "utf8");
}

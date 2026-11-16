// Load the shipped defaults and the untracked local override, and decide whether a vendor is enabled.
//
// Only the local file under the reviewed repository can enable a vendor, because enabling one sends
// repository content to that vendor. A git-tracked copy of the local file is refused outright: a
// tracked file can be changed by anyone with write access, including by the change under review. A
// timeout above the shipped value is ignored; a model may come from either file, local wins.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const LOCAL_CONFIG_RELATIVE = ".claude/reviewadapters-kit.local.json";
// A model never starts with "-", so it cannot be read as a flag by a vendor CLI.
const MODEL_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/:-]{0,127}$/;

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

// The local file is opened once, without following a final symlink or blocking on a FIFO, and checked
// on the open handle, so it cannot be swapped between the check and the read.
function readLocalJson(file) {
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NONBLOCK | (fs.constants.O_NOFOLLOW ?? 0));
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 64 * 1024) throw new Error("not a small regular file");
    return JSON.parse(fs.readFileSync(fd, "utf8"));
  } finally {
    fs.closeSync(fd);
  }
}

// Tracked under any letter case: on a case-insensitive filesystem (macOS, Windows) a committed
// ".claude/ReviewAdapters-Kit.local.json" opens under the lowercase name, while an exact pathspec would
// call it untracked. Any git error cannot prove the file is untracked, so it counts as tracked.
function isTracked(repoRoot, relative) {
  try {
    const out = execFileSync("git", ["-C", repoRoot, "ls-files", "-z", "--", `:(icase)${relative}`], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 10_000 });
    return out.length > 0;
  } catch {
    return true;
  }
}

// The file must exist under exactly this name, in a real (not symlinked) .claude directory.
function exactLocalFile(repoRoot) {
  const dir = path.join(repoRoot, path.dirname(LOCAL_CONFIG_RELATIVE));
  try {
    if (!fs.lstatSync(dir).isDirectory()) return false;
    const name = path.basename(LOCAL_CONFIG_RELATIVE);
    return fs.readdirSync(dir).includes(name) && fs.lstatSync(path.join(dir, name)).isFile();
  } catch {
    return false;
  }
}

// Read the untracked local file, or say why it cannot be used. Shared by the vendor allow-list and the
// dev-sibling codex-kit opt-in, so both get the same tracked-copy refusal.
function readLocal(repoRoot) {
  const localFile = path.join(repoRoot, LOCAL_CONFIG_RELATIVE);
  if (!exactLocalFile(repoRoot)) return { local: null, reason: "not enabled in the untracked local file" };
  if (isTracked(repoRoot, LOCAL_CONFIG_RELATIVE)) {
    return { local: null, reason: "the local file is tracked by git (or git could not prove it is untracked), so it cannot enable anything" };
  }
  try {
    const local = readLocalJson(localFile);
    if (!local || typeof local !== "object" || Array.isArray(local)) return { local: null, reason: "the local file is not a JSON object" };
    return { local, reason: "" };
  } catch {
    return { local: null, reason: "the local file is not valid JSON" };
  }
}

// The sibling codex-kit in a marketplace checkout is the reviewed branch's own code, so importing it is
// opt-in for this repository's own development only.
export function devSiblingOptIn(repoRoot) {
  return readLocal(repoRoot).local?.dev_sibling_codex_kit === true;
}

export function loadConfig(repoRoot, vendor) {
  const shipped = readJson(path.join(PLUGIN_ROOT, "reviewadapters-kit.settings.json"));
  if (!Number.isInteger(shipped?.timeout_ms) || shipped.timeout_ms <= 0) throw new Error("the shipped timeout_ms is not a positive integer");
  const shippedVendor = shipped.vendors?.[vendor] ?? {};
  const result = {
    enabled: false,
    reason: "not enabled in the untracked local file",
    timeoutMs: shipped.timeout_ms,
    model: typeof shippedVendor.model === "string" && MODEL_PATTERN.test(shippedVendor.model) ? shippedVendor.model : undefined
  };
  const { local, reason } = readLocal(repoRoot);
  if (!local) {
    result.reason = reason;
    return result;
  }
  const localVendor = local.vendors?.[vendor] ?? {};
  if (typeof localVendor.model === "string" && MODEL_PATTERN.test(localVendor.model)) result.model = localVendor.model;
  if (Number.isInteger(local.timeout_ms) && local.timeout_ms > 0 && local.timeout_ms < result.timeoutMs) {
    result.timeoutMs = local.timeout_ms;
  }
  if (localVendor.enabled === true) {
    result.enabled = true;
    result.reason = "enabled in the untracked local file";
  }
  return result;
}

export { MODEL_PATTERN };

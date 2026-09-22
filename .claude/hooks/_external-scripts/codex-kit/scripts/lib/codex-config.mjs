import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const CONFIG_PATH = path.join(os.homedir(), ".codex", "config.toml");
export const MODEL_ALIASES = {
  spark: "gpt-5.3-codex-spark"
};

// Single source of truth for model-alias resolution, shared with
// scripts/codex-companion.mjs (which previously kept its own duplicate Map).
// Lookup is case-insensitive to match how `--model`/`--persist-model` are
// actually typed on the command line.
export function resolveModelAlias(value) {
  if (!value) {
    return value;
  }
  return MODEL_ALIASES[String(value).toLowerCase()] ?? value;
}

function readConfigText() {
  try {
    return fs.readFileSync(CONFIG_PATH, "utf8");
  } catch {
    return "";
  }
}

// TOML section boundary: everything before the first `[table]`/`[[array]]`
// header line is the root document; a bare `key = value` line anywhere
// after that header belongs to that table, not the root. A regex with no
// section awareness would match (and, on write, silently overwrite) a
// same-named key inside e.g. `[profiles.work]` as if it were the global
// default -- a real, silent-corruption risk on a file outside this
// plugin's own directory. Splitting here confines both read and write to
// the root region only.
function splitAtFirstSection(text) {
  const match = text.match(/^\s*\[/m);
  if (!match) {
    return { root: text, rest: "" };
  }
  const index = match.index;
  return { root: text.slice(0, index), rest: text.slice(index) };
}

export function extractTopLevelKey(text, key) {
  const { root } = splitAtFirstSection(text);
  const match = root.match(new RegExp(`^${key}\\s*=\\s*"([^"]*)"`, "m"));
  return match ? match[1] : undefined;
}

// Reads the two keys codex-kit treats as the default model/effort source of
// truth (decision #7: read the user's own config.toml, never hardcode or
// dynamically discover a model name).
export function readCodexConfig() {
  const text = readConfigText();
  return {
    model: extractTopLevelKey(text, "model"),
    effort: extractTopLevelKey(text, "model_reasoning_effort")
  };
}

export function setOrInsertTopLevelKey(text, key, value) {
  // value is interpolated bare into a double-quoted TOML string literal
  // below -- a quote or newline would let the caller inject an arbitrary
  // additional top-level key into the user's real ~/.codex/config.toml, and
  // a backslash would produce an invalid TOML escape sequence that could
  // make the whole file unparseable even without injecting a key. Rejecting
  // here, not just at the caller, means this primitive stays safe for any
  // future caller too (found by security review, 2026-08-24).
  if (/["\\\r\n]/.test(value)) {
    throw new Error(`setOrInsertTopLevelKey: value for "${key}" must not contain a quote, backslash, or newline`);
  }
  const line = `${key} = "${value}"`;
  const pattern = new RegExp(`^${key}\\s*=.*$`, "m");
  const { root, rest } = splitAtFirstSection(text);
  if (pattern.test(root)) {
    return root.replace(pattern, line) + rest;
  }
  const separator = root.length && !root.endsWith("\n") ? "\n" : "";
  return `${root}${separator}${line}\n${rest}`;
}

// Opt-in only (decision #4) — callers must gate this behind an explicit
// --persist flag and user confirmation before invoking. Writes atomically.
export function writeCodexConfig({ model, effort } = {}) {
  const before = readCodexConfig();
  let text = readConfigText();

  const resolvedModel = resolveModelAlias(model);
  if (resolvedModel) {
    text = setOrInsertTopLevelKey(text, "model", resolvedModel);
  }
  if (effort) {
    text = setOrInsertTopLevelKey(text, "model_reasoning_effort", effort);
  }

  fs.mkdirSync(path.dirname(CONFIG_PATH), { recursive: true });
  const tempPath = `${CONFIG_PATH}.tmp-${process.pid}`;
  fs.writeFileSync(tempPath, text, "utf8");
  fs.renameSync(tempPath, CONFIG_PATH);

  return { before, after: readCodexConfig() };
}

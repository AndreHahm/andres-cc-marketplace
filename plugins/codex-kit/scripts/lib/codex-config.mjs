import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const CONFIG_PATH = path.join(os.homedir(), ".codex", "config.toml");
const MODEL_ALIASES = {
  spark: "gpt-5.3-codex-spark"
};

function resolveModelAlias(value) {
  if (!value) {
    return value;
  }
  return MODEL_ALIASES[value] ?? value;
}

function readConfigText() {
  try {
    return fs.readFileSync(CONFIG_PATH, "utf8");
  } catch {
    return "";
  }
}

function extractTopLevelKey(text, key) {
  const match = text.match(new RegExp(`^${key}\\s*=\\s*"([^"]*)"`, "m"));
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

function setOrInsertTopLevelKey(text, key, value) {
  const line = `${key} = "${value}"`;
  const pattern = new RegExp(`^${key}\\s*=.*$`, "m");
  if (pattern.test(text)) {
    return text.replace(pattern, line);
  }
  const separator = text.length && !text.endsWith("\n") ? "\n" : "";
  return `${text}${separator}${line}\n`;
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

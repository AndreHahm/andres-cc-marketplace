#!/usr/bin/env node
// PreToolUse hook (Bash and PowerShell): deny a command that names one of this plugin's scripts anywhere
// but the installed copy's own scripts/ directory (issue #762). The installed copy, and so this hook, loads
// from the plugin cache, outside the repository a session has open; a copy inside that repository (a
// .claude/ mirror, or plugins/ in this marketplace's own checkout) could be the reviewed change's own code.
//
// Allow-list, fail closed: every word naming a script must be a literal absolute path that resolves into
// <this hook's plugin root>/scripts/, and that root must not lie inside the session's repository. A
// relative path, a variable or substitution in the word, a missing file, an unterminated quote or any
// error denies. The plugin root is this file's own location, never an environment variable. It reads the
// command text only (with POSIX-shell quoting; PowerShell's differs, so `$` and backticks always deny), so
// a command that builds a name at run time is not seen; the scripts' own self-location checks remain.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// The plugin's scripts: rva-prepare, rva-dispatch, rva-run, rva-config, rva-codex-kit, rva-vendors and
// rva-winacl (.mjs). A name counts only as a whole path segment's end: "rva-dispatch.test.mjs" does not match.
// Case-insensitive, since macOS and Windows filesystems are. A literal, so no pattern is built at run time.
const NAME_PATTERN = /(?<![A-Za-z0-9_.-])rva-(?:prepare|dispatch|run|config|codex-kit|vendors|winacl)\.mjs(?![A-Za-z0-9_.-])/i;
const WORD_BREAK = /[\s;&|<>()]/;
const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function realOrNull(file) {
  try {
    return fs.realpathSync.native(file);
  } catch {
    return null;
  }
}

function isInside(file, dir) {
  const rel = path.relative(dir, file);
  return rel === "" || (rel.split(path.sep)[0] !== ".." && !path.isAbsolute(rel));
}

// The repository a directory belongs to, found by its .git entry without running git.
function enclosingRepoRoot(dir) {
  let current = realOrNull(dir);
  while (current) {
    if (fs.existsSync(path.join(current, ".git"))) return current;
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
  return null;
}

// Split a command into words with POSIX-shell quoting. A word holding an unquoted or double-quoted `$` or
// a backtick is marked dynamic: its run-time value is unknown. Returns null on an unterminated quote.
export function shellWords(command) {
  const words = [];
  let text = "";
  let dynamic = false;
  let started = false;
  const flush = () => {
    if (started) words.push({ text, dynamic });
    text = "";
    dynamic = false;
    started = false;
  };
  // `i` is the next character to read; every branch below advances it past what it consumed.
  let i = 0;
  while (i < command.length) {
    const ch = command[i];
    if (ch === "'") {
      const end = command.indexOf("'", i + 1);
      if (end === -1) return null;
      text += command.slice(i + 1, end);
      started = true;
      i = end + 1;
    } else if (ch === '"') {
      started = true;
      let j = i + 1;
      while (j < command.length && command[j] !== '"') {
        // Inside double quotes a backslash escapes only $ ` " \ and a newline, as in POSIX shells.
        if (command[j] === "\\" && j + 1 < command.length && "$`\"\\\n".includes(command[j + 1])) {
          text += command[j + 1];
          j += 2;
        } else {
          if (command[j] === "$" || command[j] === "`") dynamic = true;
          text += command[j];
          j += 1;
        }
      }
      if (j >= command.length) return null;
      i = j + 1;
    } else if (ch === "\\") {
      if (i + 1 < command.length) text += command[i + 1];
      started = true;
      i += 2;
    } else if (WORD_BREAK.test(ch)) {
      flush();
      i += 1;
    } else {
      if (ch === "$" || ch === "`") dynamic = true;
      text += ch;
      started = true;
      i += 1;
    }
  }
  flush();
  return words;
}

function deny(reason) {
  process.stdout.write(`${JSON.stringify({
    hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: reason }
  })}\n`);
  return 0;
}

export function decide(input, env = process.env, pluginRoot = PLUGIN_ROOT) {
  const command = input?.tool_input?.command;
  if (typeof command !== "string") return null;
  // Any reading of the raw text that names a script sends the command through the full check: as written,
  // without quotes, without backslashes (an escaped name), and with backslashes as separators (a Windows path).
  const unquoted = command.replace(/["']/g, "");
  const readings = [command, unquoted, unquoted.replace(/\\/g, ""), unquoted.replace(/\\/g, "/")];
  if (!readings.some((text) => NAME_PATTERN.test(text))) return null;

  const root = realOrNull(pluginRoot);
  if (!root) return "reviewadapters-kit: the guard's own plugin root could not be resolved, so this command was not checked";
  // Claude Code sets CLAUDE_PLUGIN_ROOT for this hook to the installed copy, which is where this file runs
  // from. A different value means something else chose the path, so nothing is trusted.
  if (env.CLAUDE_PLUGIN_ROOT && realOrNull(env.CLAUDE_PLUGIN_ROOT) !== root) {
    return `reviewadapters-kit: CLAUDE_PLUGIN_ROOT does not match the guard's own location (${root}), so this command was denied`;
  }
  const scriptsDir = path.join(root, "scripts");
  for (const dir of [input.cwd, env.CLAUDE_PROJECT_DIR]) {
    const repo = typeof dir === "string" && dir ? enclosingRepoRoot(dir) : null;
    if (repo && isInside(root, repo)) {
      return `reviewadapters-kit is loaded from inside the repository this session has open (${repo}), so its scripts could be the change under review; install the plugin and run it from the installed copy`;
    }
  }
  const words = shellWords(command);
  if (!words) return "reviewadapters-kit: the command has an unterminated quote and names this plugin's scripts, so it was denied";
  const advice = `its scripts run only from the installed copy (${scriptsDir}), never from a copy in a checkout (to read a copy, use Read or Grep)`;
  for (const word of words) {
    if (!NAME_PATTERN.test(word.text)) continue;
    if (word.dynamic) return `reviewadapters-kit: "${word.text}" is built at run time (a variable or substitution); ${advice}`;
    if (!path.isAbsolute(word.text)) return `reviewadapters-kit: "${word.text}" is not an absolute path; ${advice}`;
    const real = realOrNull(word.text);
    if (!real || !isInside(real, scriptsDir)) return `reviewadapters-kit: "${word.text}" is not this plugin's installed copy; ${advice}`;
  }
  // The raw text named a script but no single word did (a name split across quoting another way than
  // shellWords reads it): deny rather than guess.
  if (!words.some((word) => NAME_PATTERN.test(word.text))) {
    return `reviewadapters-kit: the command names this plugin's scripts in a form the guard cannot read; ${advice}`;
  }
  return null;
}

async function main() {
  let raw = "";
  for await (const chunk of process.stdin) raw += chunk;
  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    // Unparseable input: deny only if the raw text names one of the scripts.
    return NAME_PATTERN.test(raw) ? deny("reviewadapters-kit: the hook input could not be parsed, so a command naming this plugin's scripts was denied") : 0;
  }
  let reason;
  try {
    reason = decide(input);
  } catch {
    reason = "reviewadapters-kit: the checkout guard failed, so a command naming this plugin's scripts was denied";
  }
  return reason ? deny(reason) : 0;
}

if (process.argv[1] && realOrNull(process.argv[1]) === realOrNull(fileURLToPath(import.meta.url))) {
  process.exitCode = await main();
}

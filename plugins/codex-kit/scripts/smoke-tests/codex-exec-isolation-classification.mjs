#!/usr/bin/env node
// Smoke test: scripts/lib/codex-exec.mjs's classifyNonZeroExit
//
// A non-zero Codex exit whose cause is not a sandbox problem (a model at
// capacity, a model the account cannot use) must not be reported as
// `isolation_profile_unavailable` -- that category is the resolver's trigger
// to fall back to a wider sandbox (issue #544). Once a session starts, Codex
// prints a banner with "sandbox: read-only" and echoes the reviewer prompt
// (which carries the PR diff), so words like "sandbox" or "OPENAI_API_KEY" are
// in every failing stderr. Only Codex's own unindented `ERROR:` lines decide a
// category; a started session with no such line fails closed to
// `non_zero_exit`; a failure before the session starts (no banner) echoes
// nothing, so its whole stderr is trusted. The auth and unknown-option checks
// use the same scope.
//
// The banner and error shapes below are real Codex 0.162.1 stderr for an
// unservable model. The capacity line is the text from the issue, and the
// CreateProcessAsUserW / bubblewrap lines are synthetic (no Windows Codex
// stderr was captured -- issue #545).
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-exec-isolation-classification.mjs

import { FAILURE_CATEGORIES, classifyNonZeroExit } from "../lib/codex-exec.mjs";

let pass = 0;
let fail = 0;

function check(label, condition, detail = "") {
  if (condition) {
    pass += 1;
    console.log(`PASS  ${label}`);
  } else {
    fail += 1;
    console.log(`FAIL  ${label}${detail ? " -- " + detail : ""}`);
  }
}

function expectCategory(label, stderr, expected) {
  const actual = classifyNonZeroExit(stderr);
  check(label, actual === expected, `expected ${expected}, got ${actual}`);
}

const { AUTH_UNAVAILABLE, UNSUPPORTED_CLI_VERSION, ISOLATION_PROFILE_UNAVAILABLE, NON_ZERO_EXIT } =
  FAILURE_CATEGORIES;

const BANNER = [
  "OpenAI Codex v0.162.1",
  "--------",
  "workdir: /repo",
  "model: some-model",
  "provider: openai",
  "approval: never",
  "sandbox: read-only",
  "--------",
  "user"
].join("\n");

const CAPACITY = "ERROR: Selected model is at capacity";
const TRAILING = Array.from({ length: 25 }, (_, i) => `usage line ${i}`).join("\n");

console.log("=== Banner plus a non-sandbox error is not an isolation failure ===");
expectCategory("model at capacity", `${BANNER}\nreview the diff\n\n${CAPACITY}`, NON_ZERO_EXIT);
expectCategory(
  "model not supported for the account",
  `${BANNER}\nreview the diff\n\nERROR: {"type":"error","status":400,"error":{"message":"The 'x' model is not supported when using Codex with a ChatGPT account."}}`,
  NON_ZERO_EXIT
);
expectCategory(
  "an API permission error on an ERROR line (bare 'permission denied')",
  `${BANNER}\nreview\n\nERROR: permission denied for model gpt-x`,
  NON_ZERO_EXIT
);
expectCategory(
  "an API 'access is denied' error on an ERROR line",
  `${BANNER}\nreview\n\nERROR: access is denied for this account`,
  NON_ZERO_EXIT
);
expectCategory(
  "an echoed reviewer prompt that mentions the sandbox and permissions",
  `${BANNER}\nCheck that the sandbox is read-only and report any permission denied handling.\n\n${CAPACITY}`,
  NON_ZERO_EXIT
);
expectCategory(
  "a benign bubblewrap/sandbox-prerequisites warning ahead of the error",
  `${BANNER}\nwarning: could not find bubblewrap; sandbox prerequisites unavailable, falling back\n${CAPACITY}`,
  NON_ZERO_EXIT
);

console.log("\n=== Echoed diff content cannot forge an ERROR line ===");
expectCategory(
  "an indented ' ERROR: sandbox failed' diff context line above the real error",
  `${BANNER}\n ERROR: sandbox failed\nmore prompt\n${CAPACITY}`,
  NON_ZERO_EXIT
);
expectCategory(
  "a '+ERROR: sandbox failed' added diff line above the real error",
  `${BANNER}\n+ERROR: sandbox failed\nmore prompt\n${CAPACITY}`,
  NON_ZERO_EXIT
);

console.log("\n=== A real isolation failure is still classified as one ===");
expectCategory(
  "CreateProcessAsUserW on an ERROR line",
  `${BANNER}\nreview\n\nERROR: CreateProcessAsUserW failed: 1920`,
  ISOLATION_PROFILE_UNAVAILABLE
);
expectCategory(
  "sandbox failure on an ERROR line",
  `${BANNER}\nreview\n\nERROR: sandbox failed to start`,
  ISOLATION_PROFILE_UNAVAILABLE
);
expectCategory(
  "a bubblewrap namespace failure on an ERROR line",
  `${BANNER}\nreview\n\nERROR: bwrap: No permissions to create new namespace`,
  ISOLATION_PROFILE_UNAVAILABLE
);
expectCategory(
  "a stray early ERROR line does not hide a real isolation failure at the end",
  `${BANNER}\nERROR: something benign\n${TRAILING}\nERROR: CreateProcessAsUserW failed: 1920`,
  ISOLATION_PROFILE_UNAVAILABLE
);

console.log("\n=== A started session with no ERROR line fails closed ===");
expectCategory(
  "an isolation keyword in the echoed prompt tail (landlock)",
  `${BANNER}\n+ landlock mention in echoed diff\nCodex crashed unexpectedly\n`,
  NON_ZERO_EXIT
);
expectCategory(
  "a bwrap permission-denied line with no ERROR prefix",
  `${BANNER}\nreview\n\nbwrap: permission denied`,
  NON_ZERO_EXIT
);
expectCategory("the banner's own sandbox line alone", `${BANNER}\nsomething unrelated went wrong`, NON_ZERO_EXIT);

console.log("\n=== A failure before the session starts is classified from its whole stderr ===");
expectCategory(
  "a bubblewrap failure with no banner",
  "bwrap: No permissions to create new namespace\n",
  ISOLATION_PROFILE_UNAVAILABLE
);
expectCategory(
  "an unknown option with no banner",
  "error: unknown option '--foo'\n",
  UNSUPPORTED_CLI_VERSION
);
expectCategory("an unrelated early failure with no banner", "error: something else broke\n", NON_ZERO_EXIT);

console.log("\n=== Auth and unknown-option checks use the same scope ===");
expectCategory(
  "OPENAI_API_KEY in the echoed prompt does not make a capacity error an auth failure",
  `${BANNER}\nRead OPENAI_API_KEY handling in the diff.\n\n${CAPACITY}`,
  NON_ZERO_EXIT
);
expectCategory(
  "'unrecognized' in the echoed prompt does not make a capacity error a version failure",
  `${BANNER}\nHandle unrecognized input in the diff.\n\n${CAPACITY}`,
  NON_ZERO_EXIT
);
expectCategory(
  "a 401 on an ERROR line is an auth failure",
  `${BANNER}\nreview\n\nERROR: 401 Unauthorized`,
  AUTH_UNAVAILABLE
);
expectCategory(
  "a 401 followed by 25 more lines is still an auth failure",
  `${BANNER}\nreview\n\nERROR: 401 Unauthorized\n${TRAILING}`,
  AUTH_UNAVAILABLE
);
expectCategory(
  "an unknown option on an ERROR line is a version failure",
  `${BANNER}\nreview\n\nERROR: unknown option '--foo'`,
  UNSUPPORTED_CLI_VERSION
);
expectCategory(
  "an unknown option followed by 25 more lines is still a version failure",
  `${BANNER}\nreview\n\nERROR: unknown option '--foo'\n${TRAILING}`,
  UNSUPPORTED_CLI_VERSION
);
expectCategory(
  "a benign sandbox warning ahead of a real 401 is still an auth failure, not isolation",
  `${BANNER}\nwarning: could not find bubblewrap; sandbox prerequisites unavailable\nERROR: 401 Unauthorized`,
  AUTH_UNAVAILABLE
);

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);

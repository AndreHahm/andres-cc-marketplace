#!/usr/bin/env node
// Smoke test: scripts/lib/codex-exec.mjs's classifyNonZeroExit
//
// A non-zero Codex exit whose cause is not a sandbox problem (a model at
// capacity, a model the account cannot use) must not be reported as
// `isolation_profile_unavailable` -- that category is the resolver's trigger
// to fall back to a wider sandbox (issue #544). Codex prints a banner with
// "sandbox: read-only" and echoes the reviewer prompt (which carries the PR
// diff) on every run, so words like "sandbox" or "OPENAI_API_KEY" are in every
// failing stderr. The auth and unknown-option checks are scoped the same way.
//
// The banner and error shapes below are real Codex 0.162.1 stderr for an
// unservable model. The capacity line is the text from the issue, and the
// CreateProcessAsUserW / bubblewrap lines are synthetic (no Windows Codex
// stderr was captured).
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

console.log("\n=== Echoed prompt or diff content cannot forge or hide an ERROR line ===");
expectCategory(
  "an indented ' ERROR: sandbox failed' diff line above the real error",
  `${BANNER}\n ERROR: sandbox failed\nmore prompt\n${CAPACITY}`,
  NON_ZERO_EXIT
);
{
  const tail = Array.from({ length: 25 }, (_, i) => `unrelated line ${i}`).join("\n");
  expectCategory(
    "an unindented 'ERROR: sandbox failed' echoed far above the tail",
    `${BANNER}\nERROR: sandbox failed\n${tail}`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a stray early ERROR line does not hide a real isolation failure at the tail",
    `${BANNER}\nERROR: something benign\n${tail}\nERROR: CreateProcessAsUserW failed: 1920`,
    ISOLATION_PROFILE_UNAVAILABLE
  );
}

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
  "permission denied in the last lines when there is no ERROR line",
  `${BANNER}\nreview\n\nbwrap: permission denied`,
  ISOLATION_PROFILE_UNAVAILABLE
);

console.log("\n=== Without an ERROR line, only the last lines are inspected ===");
{
  const tail = Array.from({ length: 25 }, (_, i) => `unrelated line ${i}`).join("\n");
  expectCategory(
    "a sandbox mention above the last-lines window is ignored",
    `${BANNER}\nthe prompt mentions the sandbox\n${tail}`,
    NON_ZERO_EXIT
  );
  expectCategory("the banner's own sandbox line alone is ignored", `${BANNER}\nsomething unrelated went wrong`, NON_ZERO_EXIT);
}

console.log("\n=== Auth and unknown-option checks are scoped the same way ===");
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
  "an unknown option on an ERROR line is a version failure",
  `${BANNER}\nreview\n\nERROR: unknown option '--foo'`,
  UNSUPPORTED_CLI_VERSION
);
expectCategory(
  "a benign sandbox warning ahead of a real 401 is still an auth failure, not isolation",
  `${BANNER}\nwarning: could not find bubblewrap; sandbox prerequisites unavailable\nERROR: 401 Unauthorized`,
  AUTH_UNAVAILABLE
);

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);

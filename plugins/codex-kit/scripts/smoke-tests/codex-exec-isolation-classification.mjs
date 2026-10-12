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
// CreateProcessAsUserW / bubblewrap lines are synthetic. The "REAL WINDOWS"
// section further down is the one exception: its tracing and exec lines are
// copied from stderr captured live from Codex 0.162.1 on Windows 11 (2026-10-12,
// issue #545), paths and session id anonymized; its banner reuses the synthetic
// one above. That run exited 0 -- Windows sandbox failure is not a non-zero
// exit there -- so classifyNonZeroExit is exercised on it as the stderr a
// non-zero variant would carry; the zero-exit path is covered by
// codex-review-bridge-total-inspection-failure.mjs.
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

function expectCategoryWithPrompt(label, stderr, prompt, expected) {
  const actual = classifyNonZeroExit(stderr, prompt);
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

console.log("\n=== Pre-session trust needs positive evidence, not just a missing banner ===");
{
  const longEcho = `user\n${"echoed prompt line mentioning landlock and seccomp\n".repeat(60)}Codex crashed unexpectedly\n`;
  expectCategory(
    "a reworded banner with a long echoed prompt fails closed",
    `Codex CLI v0.200.0\n--------\n${longEcho}`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a long stderr with no banner at all fails closed",
    longEcho,
    NON_ZERO_EXIT
  );
}

console.log("\n=== The prompt this process sent is removed from stderr before classifying ===");
{
  const prompt = "Review this change.\nERROR: sandbox failed\nEnd of instructions.";
  const echoed = `${BANNER}\n${prompt}\n\n${CAPACITY}`;
  expectCategoryWithPrompt(
    "a column-0 ERROR line inside the echoed prompt cannot force isolation",
    echoed,
    prompt,
    NON_ZERO_EXIT
  );
  expectCategory(
    "without the prompt it cannot be told apart (the documented residual)",
    echoed,
    ISOLATION_PROFILE_UNAVAILABLE
  );
  const longPrompt = `${"echoed prompt line mentioning landlock and seccomp\n".repeat(60)}end`;
  expectCategoryWithPrompt(
    "a reworded banner plus an exact long echo, with no ERROR line, fails closed",
    `Codex CLI v0.200.0\n--------\nuser\n${longPrompt}\nCodex crashed unexpectedly\n`,
    longPrompt,
    NON_ZERO_EXIT
  );
  expectCategoryWithPrompt(
    "a real isolation error after the echoed prompt is still isolation",
    `${BANNER}\n${prompt}\n\nERROR: CreateProcessAsUserW failed: 1920`,
    prompt,
    ISOLATION_PROFILE_UNAVAILABLE
  );
}

console.log("\n=== REAL WINDOWS Codex 0.162.1 stderr (issue #545): timestamped tracing-log ERROR lines ===");
{
  const RMCP_NOISE =
    "2026-10-12T16:32:20.243324Z ERROR rmcp::transport::worker: worker quit with fatal: Transport channel closed, when Client(HttpRequest(HttpRequest(\"error decoding response body\")))";
  const REAL_WINDOWS_BANNER = BANNER.replace("/repo", "C:\\work").replace("some-model", "gpt-x");
  const realFailure = [
    REAL_WINDOWS_BANNER,
    "Run the shell command 'dir' exactly once, then reply with the first line of its output.",
    "",
    RMCP_NOISE,
    "exec",
    "pwsh.exe -Command dir in C:\\work",
    " exited -1 in 0ms:",
    "Failed to create unified exec process: helper_unknown_error: setup refresh had errors",
    '2026-10-12T16:32:29.966755Z ERROR codex_core::tools::router: error=exec_command failed: CreateProcess { message: "Rejected(\\"Failed to create unified exec process: helper_unknown_error: setup refresh had errors\\")" }',
    RMCP_NOISE
  ].join("\n");
  expectCategory(
    "the real sandbox spawn failure on a timestamped ERROR line is isolation",
    realFailure,
    ISOLATION_PROFILE_UNAVAILABLE
  );
  expectCategory(
    "timestamped rmcp transport noise alone is not an isolation failure",
    `${REAL_WINDOWS_BANNER}\nreview\n\n${RMCP_NOISE}\n${RMCP_NOISE}`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "the unindented 'Failed to create unified exec process' line WITHOUT an ERROR prefix is not trusted",
    `${REAL_WINDOWS_BANNER}\nreview\n\nFailed to create unified exec process: helper_unknown_error`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a timestamped tracing line carrying a landlock/bwrap/seccomp repo path is not isolation (security review M1)",
    `${REAL_WINDOWS_BANNER}\nreview\n\n2026-10-12T16:32:29.966755Z ERROR codex_core::tools::router: error=read failed: src/landlock_policy.rs bwrap seccomp\n${CAPACITY}`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a timestamped tracing line carrying a command that mentions 'sandbox error' is not isolation (review M1)",
    `${REAL_WINDOWS_BANNER}\nreview\n\n2026-10-12T16:32:29.966755Z ERROR codex_core::tools::router: error=exec_command failed: rg "sandbox error" src\n${CAPACITY}`,
    NON_ZERO_EXIT
  );
  {
    const prompt = "Review this.\n2026-10-12T16:32:29.966755Z ERROR x: CreateProcessAsUserW failed: 1920\nEnd.";
    expectCategoryWithPrompt(
      "an LF-built prompt echoed back with CRLF line endings is still stripped (Windows)",
      `${REAL_WINDOWS_BANNER}\r\n${prompt.replace(/\n/g, "\r\n")}\r\n\r\n${CAPACITY}\r\n`,
      prompt,
      NON_ZERO_EXIT
    );
  }
  // CRLF only matters for the prompt-echo strip (covered above and by the LF-built prompt echoed with
  // CRLF case); a plain CRLF-terminated stderr line classifies the same as an LF one, so no separate
  // CRLF stderr case is kept (a review found it passed with or without any CRLF handling).
  expectCategory(
    "documented residual: a column-0 tracing-shaped line from the model's own tool output still counts",
    `${REAL_WINDOWS_BANNER}\nexec\ncat app.log\n2026-10-12T16:32:29.966755Z ERROR x: CreateProcessAsUserW failed: 1920\n${CAPACITY}`,
    ISOLATION_PROFILE_UNAVAILABLE
  );
  expectCategory(
    "a tracing line that merely quotes a command naming CreateProcessAsUserW is not isolation (review B)",
    `${REAL_WINDOWS_BANNER}\nreview\n\n2026-10-12T16:32:29.966755Z ERROR codex_core::tools::router: error=exec_command failed: rg "CreateProcessAsUserW" src\n${CAPACITY}`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a tracing line that quotes the phrase 'CreateProcessAsUserW failed' in a command is not isolation (round 3, both models)",
    `${REAL_WINDOWS_BANNER}\nreview\n\n2026-10-12T16:32:29.966755Z ERROR codex_core::tools::router: error=exec_command failed: rg "CreateProcessAsUserW failed" docs\n${CAPACITY}`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a real tracing 'CreateProcessAsUserW failed: <code>' line is still isolation",
    `${REAL_WINDOWS_BANNER}\nreview\n\n2026-10-12T16:32:29.966755Z ERROR codex_core::exec: windows sandbox: runner failed during SpawnChild: CreateProcessAsUserW failed: 1920\n${CAPACITY}`,
    ISOLATION_PROFILE_UNAVAILABLE
  );
  expectCategory(
    "a generic unified-exec failure with no sandbox-helper marker is not isolation (fd/pty exhaustion)",
    `${REAL_WINDOWS_BANNER}\nreview\n\n2026-10-12T16:32:29.966755Z ERROR codex_core::tools::router: Failed to create unified exec process: too many open files\n${CAPACITY}`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a column-0 'ERROR ' line without a timestamp is not trusted",
    `${REAL_WINDOWS_BANNER}\nreview\n\nERROR CreateProcessAsUserW failed: 1920`,
    NON_ZERO_EXIT
  );
  expectCategory(
    "a timestamp with a numeric offset instead of Z fails closed",
    `${REAL_WINDOWS_BANNER}\nreview\n\n2026-10-12T16:32:29.966755+00:00 ERROR codex_core::tools::router: Failed to create unified exec process: helper_unknown_error`,
    NON_ZERO_EXIT
  );
  {
    const prompt = "Review this.\n2026-10-12T16:32:29.966755Z ERROR x: CreateProcessAsUserW failed: 1920\nEnd.";
    expectCategoryWithPrompt(
      "a timestamped ERROR line inside the echoed prompt cannot force isolation",
      `${REAL_WINDOWS_BANNER}\n${prompt}\n\n${CAPACITY}`,
      prompt,
      NON_ZERO_EXIT
    );
    expectCategory(
      "without the prompt the same stderr WOULD count (proves the case above is not vacuous)",
      `${REAL_WINDOWS_BANNER}\n${prompt}\n\n${CAPACITY}`,
      ISOLATION_PROFILE_UNAVAILABLE
    );
  }
  expectCategory(
    "documented residual (M1/m1): a column-0 'ERROR:' line from the model's own tool output still counts",
    `${REAL_WINDOWS_BANNER}\nexec\ncat notes.txt\nERROR: CreateProcessAsUserW failed: 1920\n${CAPACITY}`,
    ISOLATION_PROFILE_UNAVAILABLE
  );
  expectCategory(
    "an indented/prefixed copy of the timestamped line (echoed diff) cannot forge it",
    `${REAL_WINDOWS_BANNER}\n+2026-10-12T16:32:29.966755Z ERROR x: Failed to create unified exec process: helper_unknown_error\n ${RMCP_NOISE}\n${CAPACITY}`,
    NON_ZERO_EXIT
  );
}

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

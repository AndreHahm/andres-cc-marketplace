#!/usr/bin/env node
// Smoke test: skills/codex-review-bridge/scripts/bridge-invoke.mjs
//
// Confirms isTotalInspectionFailure (issue #78) catches the specific case
// where a Windows sandboxed `codex exec` run exits 0 with a schema-valid,
// zero-finding envelope, but its own `inspection_limits` field reports the
// sandbox couldn't even start a process ("Windows error 1920") -- a
// "successful" envelope that is actually a total inspection failure, which
// codex-exec.mjs's own exit-code-based classification can't see (the outer
// process exited 0; only Codex's own inner tool call failed). Without this
// reclassification, the resolver's documented "on
// isolation_profile_unavailable, fall back to Step 2" behavior
// (git-kit's cross-model-review SKILL.md) never triggers, and the run
// silently looks clean instead.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/codex-review-bridge-total-inspection-failure.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { isTotalInspectionFailure } from "../../skills/codex-review-bridge/scripts/bridge-invoke.mjs";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const BRIDGE_INVOKE = path.join(SCRIPT_DIR, "..", "..", "skills", "codex-review-bridge", "scripts", "bridge-invoke.mjs");

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

console.log("=== The exact reported failure text (Windows error 1920) is detected ===");
{
  const envelope = {
    findings: [],
    inspection_limits: [
      "The terminal could not create a process in the workspace (Windows error 1920), so the requested git diff and target files could not be inspected."
    ]
  };
  check("zero findings + total-inspection-failure note is detected", isTotalInspectionFailure(envelope));
}

console.log("\n=== A genuine clean pass (zero findings, no inspection_limits) is NOT flagged ===");
{
  const envelope = { findings: [], inspection_limits: [] };
  check("empty inspection_limits never triggers reclassification", !isTotalInspectionFailure(envelope));
}

console.log("\n=== A partial limitation (zero findings, unrelated inspection_limits note) is NOT flagged ===");
{
  const envelope = { findings: [], inspection_limits: ["skipped a 40MB binary asset"] };
  check(
    "an ordinary inspection_limits note (not a total-failure signature) does not falsely trigger",
    !isTotalInspectionFailure(envelope)
  );
}

console.log("\n=== Non-empty findings alongside a total-failure-shaped note is NOT flagged ===");
{
  // If Codex actually produced real findings, the sandbox plainly wasn't
  // totally broken -- only the zero-findings case should reclassify.
  const envelope = {
    findings: [{ id: "F1" }],
    inspection_limits: ["The terminal could not create a process in the workspace (Windows error 1920)"]
  };
  check("a non-empty findings array suppresses the reclassification", !isTotalInspectionFailure(envelope));
}

console.log("\n=== A CreateProcessAsUserW-shaped note (the other sandbox-failure phrasing) is detected ===");
{
  const envelope = { findings: [], inspection_limits: ["CreateProcessAsUserW failed while starting the requested tool"] };
  check("the CreateProcessAsUserW phrasing is also recognized", isTotalInspectionFailure(envelope));
}

console.log("\n=== Security review fix (M2): a PARTIAL read/access note no longer over-matches ===");
{
  // An earlier draft's pattern also matched a bare "could not (inspect|
  // access|read) the workspace/target/requested" -- no process-start or
  // totality semantics -- so an ordinary single-file skip note like this
  // one got misreclassified as a total sandbox failure. Narrowed to require
  // an actual process-start/CreateProcessAsUserW/error-1920 signature.
  const envelope = { findings: [], inspection_limits: ["could not read the requested file config.bin (binary, skipped)"] };
  check(
    "an ordinary partial read-failure note (no process-start signature) does NOT trigger reclassification",
    !isTotalInspectionFailure(envelope)
  );
}

console.log("\n=== Security review fix (M3): broadened verb/modal coverage catches phrasing variance ===");
{
  const variants = [
    "The sandbox was unable to start a process to run git diff.",
    "Codex couldn't create a process inside the workspace.",
    "The tool failed to start a process (sandbox restriction).",
    "The file cannot be accessed by the system.",
    "error 1920 while starting the requested tool"
  ];
  for (const note of variants) {
    check(`recognized: "${note}"`, isTotalInspectionFailure({ findings: [], inspection_limits: [note] }));
  }
}

console.log("\n=== Malformed/missing shape never throws ===");
{
  check("null envelope returns false, does not throw", isTotalInspectionFailure(null) === false);
  check("missing findings/inspection_limits returns false, does not throw", isTotalInspectionFailure({}) === false);
}

console.log("\n=== Security review fix (M1): semanticallyValidate runs BEFORE isTotalInspectionFailure (source-level) ===");
{
  // Not exercisable via a real subprocess call without a real Codex CLI
  // response to feed it (same limitation codex-windows-guardrails-preflight.mjs's
  // own "Prompt-injection guard on instructionBody" scenario documents for
  // an analogous case) -- source-inspection is the cheap, meaningful
  // regression guard instead. Ordering matters here: isTotalInspectionFailure
  // decides whether to escalate the resolver toward Step 2
  // (danger-full-access, no sandbox), and semanticallyValidate is the only
  // check that confirms envelope.dispatch.id/reviewer actually match what
  // this process sent. Checking totality first would let a forged/
  // mismatched dispatch.id ride an unauthenticated envelope straight to
  // isolation_profile_unavailable -- the resolver's fallback trigger --
  // without ever being caught by the check that would have rejected it.
  const source = fs.readFileSync(BRIDGE_INVOKE, "utf8");
  const semanticCallIndex = source.indexOf("const semanticResult = semanticallyValidate(");
  const totalFailureCallIndex = source.indexOf("if (isTotalInspectionFailure(result.data)) {");
  check(
    "both call sites are present in main()",
    semanticCallIndex !== -1 && totalFailureCallIndex !== -1,
    `semanticCallIndex=${semanticCallIndex} totalFailureCallIndex=${totalFailureCallIndex}`
  );
  check(
    "semanticallyValidate's call site appears BEFORE isTotalInspectionFailure's in source order",
    semanticCallIndex !== -1 && totalFailureCallIndex !== -1 && semanticCallIndex < totalFailureCallIndex
  );

  console.log("\n=== Controlled negative: the same assertion logic fails on a pre-fix (reversed) call order ===");
  const preFixOrderSynthetic = [
    "  if (isTotalInspectionFailure(result.data)) {",
    "    ...",
    "  }",
    "",
    "  const semanticResult = semanticallyValidate("
  ].join("\n");
  const tamperedSemanticIndex = preFixOrderSynthetic.indexOf("const semanticResult = semanticallyValidate(");
  const tamperedTotalIndex = preFixOrderSynthetic.indexOf("if (isTotalInspectionFailure(result.data)) {");
  check(
    "the same ordering assertion correctly fails against the pre-fix call order",
    !(tamperedSemanticIndex !== -1 && tamperedTotalIndex !== -1 && tamperedSemanticIndex < tamperedTotalIndex),
    `pre-fix order: semanticIndex=${tamperedSemanticIndex} totalIndex=${tamperedTotalIndex}`
  );
}

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);

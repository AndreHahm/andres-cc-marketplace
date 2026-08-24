#!/usr/bin/env node
// Smoke test: scripts/app-server-broker.mjs, scripts/lib/broker-lifecycle.mjs
//
// Confirms the broker's token-based RPC authentication end-to-end against a
// real spawned broker process: refuses to start without a token (checked via
// a separate direct-spawn assertion below), rejects a missing/wrong token on
// `initialize`, accepts the correct token, rejects any request on a socket
// that never successfully authenticated, and shuts down cleanly.
//
// Run from plugins/codex-kit/: node scripts/smoke-tests/broker-rpc-auth.mjs

import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";

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

function rpcRoundTrip(pipePath, params) {
  return new Promise((resolve) => {
    const s = net.createConnection({ path: pipePath });
    s.setEncoding("utf8");
    const timeout = setTimeout(() => {
      s.destroy();
      resolve({ error: { message: "timeout" } });
    }, 5000);
    s.on("connect", () => s.write(JSON.stringify({ id: 1, method: "initialize", params }) + "\n"));
    s.on("data", (d) => {
      clearTimeout(timeout);
      s.end();
      try {
        resolve(JSON.parse(d.trim()));
      } catch {
        resolve({ error: { message: "invalid JSON response", raw: d.toString() } });
      }
    });
    s.on("error", (e) => {
      clearTimeout(timeout);
      resolve({ error: { message: e.message } });
    });
  });
}

console.log("=== Broker refuses to start without CODEX_KIT_APP_SERVER_TOKEN ===");
{
  let threw = false;
  let stderrText = "";
  try {
    execFileSync("node", ["scripts/app-server-broker.mjs", "serve", "--endpoint", "pipe:\\\\.\\pipe\\smoke-test-no-token"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, CODEX_KIT_APP_SERVER_TOKEN: undefined },
      timeout: 3000
    });
  } catch (e) {
    threw = true;
    stderrText = (e.stderr?.toString() ?? "") + String(e.message ?? "");
  }
  check("refuses to start and exits non-zero when the token env var is missing", threw, stderrText.slice(0, 200));
  check("error message names the missing token requirement", stderrText.includes("CODEX_KIT_APP_SERVER_TOKEN"), stderrText.slice(0, 200));
}

console.log("\n=== State directory permissions are narrowed even when it pre-exists (POSIX only) ===");
if (process.platform !== "win32") {
  // fs.mkdirSync's own `mode` option only applies at creation time -- a
  // no-op on an already-existing directory. saveBrokerSession must
  // therefore also chmodSync unconditionally, or a directory that existed
  // before this narrowing was added (or was otherwise created with a
  // looser mode) stays loose forever. Found by CodeRabbit review, PR #112,
  // 2026-08-24.
  const { saveBrokerSession } = await import("../lib/broker-lifecycle.mjs");
  const { resolveStateDir } = await import("../lib/state.mjs");

  const testCwd = fs.mkdtempSync(path.join(os.tmpdir(), "broker-perm-smoke-"));
  const stateDir = resolveStateDir(testCwd);
  fs.mkdirSync(stateDir, { recursive: true, mode: 0o755 });
  const modeBefore = fs.statSync(stateDir).mode & 0o777;

  saveBrokerSession(testCwd, { endpoint: "pipe:\\\\.\\pipe\\smoke-test", token: "x".repeat(64) });
  const modeAfter = fs.statSync(stateDir).mode & 0o777;

  check(
    "a pre-existing, loosely-permissioned state dir is narrowed to 0o700 on save",
    modeAfter === 0o700,
    `before=0${modeBefore.toString(8)} after=0${modeAfter.toString(8)}`
  );
  fs.rmSync(testCwd, { recursive: true, force: true });
} else {
  console.log("SKIP  state-directory permission narrowing (POSIX-only, not applicable on win32)");
}

console.log("\n=== Real spawned broker: full auth handshake ===");
await (async () => {
  const brokerLifecycle = await import("../lib/broker-lifecycle.mjs");
  const { parseBrokerEndpoint } = await import("../lib/broker-endpoint.mjs");

  const testCwd = fs.mkdtempSync(path.join(os.tmpdir(), "broker-auth-smoke-"));
  const session = await brokerLifecycle.ensureBrokerSession(testCwd, { timeoutMs: 8000 });
  check("broker starts and returns a session with a 64-char hex token", Boolean(session?.token) && session.token.length === 64, JSON.stringify(session));

  if (!session) {
    console.log("\n=== Results: broker did not start, remaining checks skipped ===");
    process.exit(1);
  }

  const target = parseBrokerEndpoint(session.endpoint);

  const noToken = await rpcRoundTrip(target.path, {});
  check("initialize with NO token is rejected", Boolean(noToken.error), JSON.stringify(noToken));

  const wrongToken = await rpcRoundTrip(target.path, { token: "wrong-" + crypto.randomBytes(8).toString("hex") });
  check("initialize with WRONG token (different length) is rejected", Boolean(wrongToken.error), JSON.stringify(wrongToken));
  check("wrong-token rejection uses the dedicated auth RPC error code (-32002)", wrongToken.error?.code === -32002, JSON.stringify(wrongToken));

  // Same length as the real 64-char hex token but wrong content -- exercises
  // tokensMatch's crypto.timingSafeEqual branch specifically, not just its
  // length-mismatch fast-reject branch the case above already covers.
  const sameLengthWrongToken = await rpcRoundTrip(target.path, { token: crypto.randomBytes(32).toString("hex") });
  check(
    "initialize with WRONG token (same length as the real token) is rejected",
    sameLengthWrongToken.error?.code === -32002,
    JSON.stringify(sameLengthWrongToken)
  );

  const nonStringToken = await rpcRoundTrip(target.path, { token: 12345 });
  check(
    "initialize with a non-string token is rejected, not thrown on",
    nonStringToken.error?.code === -32002,
    JSON.stringify(nonStringToken)
  );

  const rightToken = await rpcRoundTrip(target.path, { token: session.token });
  check("initialize with CORRECT token succeeds", Boolean(rightToken.result), JSON.stringify(rightToken));

  const unauthedGeneral = await new Promise((resolve) => {
    const s = net.createConnection({ path: target.path });
    s.setEncoding("utf8");
    const timeout = setTimeout(() => { s.destroy(); resolve({ error: { message: "timeout" } }); }, 5000);
    s.on("connect", () => s.write(JSON.stringify({ id: 2, method: "thread/list", params: {} }) + "\n"));
    s.on("data", (d) => { clearTimeout(timeout); s.end(); resolve(JSON.parse(d.trim())); });
    s.on("error", (e) => { clearTimeout(timeout); resolve({ error: { message: e.message } }); });
  });
  check("a general RPC method on a socket that never authenticated is rejected", Boolean(unauthedGeneral.error), JSON.stringify(unauthedGeneral));

  const shutdownWrongToken = await new Promise((resolve) => {
    const s = net.createConnection({ path: target.path });
    s.setEncoding("utf8");
    const timeout = setTimeout(() => { s.destroy(); resolve({ error: { message: "timeout" } }); }, 5000);
    s.on("connect", () => s.write(JSON.stringify({ id: 3, method: "broker/shutdown", params: { token: "wrong" } }) + "\n"));
    s.on("data", (d) => { clearTimeout(timeout); s.end(); resolve(JSON.parse(d.trim())); });
    s.on("error", (e) => { clearTimeout(timeout); resolve({ error: { message: e.message } }); });
  });
  check("broker/shutdown with a wrong token on an unauthenticated socket is rejected (broker stays up)", Boolean(shutdownWrongToken.error), JSON.stringify(shutdownWrongToken));

  await brokerLifecycle.sendBrokerShutdown(session.endpoint, session.token);
  check("authenticated shutdown completes without throwing", true);

  // Poll rather than a single fixed-delay check -- pipe teardown after
  // shutdown is asynchronous and its exact timing isn't guaranteed.
  let stillUp = true;
  for (let attempt = 0; attempt < 20 && stillUp; attempt += 1) {
    await new Promise((r) => setTimeout(r, 250));
    stillUp = await new Promise((resolve) => {
      const s = net.createConnection({ path: target.path });
      s.on("connect", () => { s.end(); resolve(true); });
      s.on("error", () => resolve(false));
    });
  }
  check("broker process is no longer listening after authenticated shutdown (polled up to 5s)", !stillUp);
})();

console.log(`\n=== Results: ${pass} passed, ${fail} failed ===`);
process.exit(fail > 0 ? 1 : 0);

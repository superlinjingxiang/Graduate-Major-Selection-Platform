import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";

import { resolvePythonRuntime } from "./python-runtime.mjs";

test("prefers the repository virtualenv on Windows", () => {
  const runtime = resolvePythonRuntime({
    platform: "win32",
    root: "E:/GradMatch",
    exists: (candidate) => candidate.endsWith("services/api/.venv/Scripts/python.exe"),
    commandExists: () => {
      throw new Error("global commands must not be probed when the virtualenv exists");
    },
  });

  assert.deepEqual(runtime, {
    command: "E:/GradMatch/services/api/.venv/Scripts/python.exe",
    prefixArgs: [],
  });
});

test("prefers the repository virtualenv on POSIX", () => {
  const runtime = resolvePythonRuntime({
    platform: "linux",
    root: "/workspace/GradMatch",
    exists: (candidate) => candidate.endsWith("services/api/.venv/bin/python"),
    commandExists: () => {
      throw new Error("global commands must not be probed when the virtualenv exists");
    },
  });

  assert.deepEqual(runtime, {
    command: "/workspace/GradMatch/services/api/.venv/bin/python",
    prefixArgs: [],
  });
});

test("uses uv when the repository virtualenv is unavailable", () => {
  const runtime = resolvePythonRuntime({
    platform: "linux",
    root: "/workspace/GradMatch",
    exists: () => false,
    commandExists: (command) => command === "uv",
  });

  assert.deepEqual(runtime, {
    command: "uv",
    prefixArgs: ["run", "--project", "/workspace/GradMatch/services/api", "python"],
  });
});

test("uses python as the final Windows fallback", () => {
  const runtime = resolvePythonRuntime({
    platform: "win32",
    root: "E:/GradMatch",
    exists: () => false,
    commandExists: (command) => command === "python",
  });

  assert.deepEqual(runtime, { command: "python", prefixArgs: [] });
});

test("uses python3 as the final POSIX fallback", () => {
  const runtime = resolvePythonRuntime({
    platform: "linux",
    root: "/workspace/GradMatch",
    exists: () => false,
    commandExists: (command) => command === "python3",
  });

  assert.deepEqual(runtime, { command: "python3", prefixArgs: [] });
});

test("runPython preserves the child process exit code", () => {
  const moduleUrl = new URL("./python-runtime.mjs", import.meta.url).href;
  const program = `
    import { runPython } from ${JSON.stringify(moduleUrl)};
    runPython(["--eval", "process.exit(7)"], {
      runtime: { command: process.execPath, prefixArgs: [] },
    });
  `;

  const result = spawnSync(process.execPath, ["--input-type=module", "--eval", program], {
    encoding: "utf8",
  });

  assert.equal(result.status, 7, result.stderr);
});

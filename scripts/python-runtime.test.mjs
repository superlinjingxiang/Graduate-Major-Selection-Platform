import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";

import { runPythonChecks } from "./check-python.mjs";
import { resolvePythonExecutable, resolvePythonRuntime } from "./python-runtime.mjs";

const fallbackCases = [
  {
    name: "Windows uv",
    platform: "win32",
    cwd: "E:/GradMatch/services/api",
    runtime: {
      command: "uv.exe",
      prefixArgs: ["run", "--project", "E:/GradMatch/services/api", "python"],
    },
    executable: "E:\\GradMatch\\services\\api\\.venv\\Scripts\\python.exe",
  },
  {
    name: "POSIX uv",
    platform: "linux",
    cwd: "/workspace/GradMatch/services/api",
    runtime: {
      command: "uv",
      prefixArgs: ["run", "--project", "/workspace/GradMatch/services/api", "python"],
    },
    executable: "/workspace/GradMatch/services/api/.venv/bin/python",
  },
  {
    name: "Windows global fallback",
    platform: "win32",
    cwd: "E:/GradMatch/services/api",
    runtime: { command: "python", prefixArgs: [] },
    executable: "C:\\Python312\\python.exe",
  },
  {
    name: "POSIX global fallback",
    platform: "linux",
    cwd: "/workspace/GradMatch/services/api",
    runtime: { command: "python3", prefixArgs: [] },
    executable: "/usr/bin/python3",
  },
];

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

for (const testCase of fallbackCases) {
  test(`resolves the ${testCase.name} interpreter to an absolute path`, () => {
    const env = { PATH: "injected-path", TEST_MARKER: testCase.name };
    const calls = [];
    const spawn = (command, args, options) => {
      calls.push({ command, args, options });
      return { status: 0, stdout: `${testCase.executable}\n` };
    };

    const executable = resolvePythonExecutable({
      platform: testCase.platform,
      runtime: testCase.runtime,
      spawn,
      cwd: testCase.cwd,
      env,
    });

    assert.equal(executable, testCase.executable);
    assert.deepEqual(calls, [
      {
        command: testCase.runtime.command,
        args: [...testCase.runtime.prefixArgs, "-c", "import sys; print(sys.executable)"],
        options: {
          cwd: testCase.cwd,
          env,
          encoding: "utf8",
          stdio: ["ignore", "pipe", "inherit"],
        },
      },
    ]);
  });
}

test("resolvePythonExecutable propagates spawn errors", () => {
  const failure = new Error("python launch failed");

  assert.throws(
    () =>
      resolvePythonExecutable({
        runtime: { command: "python", prefixArgs: [] },
        spawn: () => ({ error: failure }),
      }),
    (error) => error === failure,
  );
});

test("resolvePythonExecutable preserves the child process exit code", () => {
  const exitCalled = new Error("exit called");
  let exitCode;

  assert.throws(
    () =>
      resolvePythonExecutable({
        runtime: { command: "python", prefixArgs: [] },
        spawn: () => ({ status: 23, stdout: "" }),
        exit: (code) => {
          exitCode = code;
          throw exitCalled;
        },
      }),
    (error) => error === exitCalled,
  );
  assert.equal(exitCode, 23);
});

for (const testCase of fallbackCases) {
  test(`passes the resolved ${testCase.name} interpreter to Pyright`, () => {
    const env = { PATH: "injected-path", TEST_MARKER: testCase.name };
    const calls = [];
    const spawn = (command, args, options) => {
      calls.push({ command, args, options });
      return calls.length === 1 ? { status: 0, stdout: `${testCase.executable}\n` } : { status: 0 };
    };

    runPythonChecks({
      platform: testCase.platform,
      runtime: testCase.runtime,
      spawn,
      cwd: testCase.cwd,
      env,
    });

    assert.equal(calls.length, 5);
    assert.deepEqual(calls[0], {
      command: testCase.runtime.command,
      args: [...testCase.runtime.prefixArgs, "-c", "import sys; print(sys.executable)"],
      options: {
        cwd: testCase.cwd,
        env,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "inherit"],
      },
    });
    assert.deepEqual(calls[3], {
      command: testCase.runtime.command,
      args: [
        ...testCase.runtime.prefixArgs,
        "-m",
        "pyright",
        "--pythonpath",
        testCase.executable,
        "src",
        "tests",
      ],
      options: { cwd: testCase.cwd, env, stdio: "inherit" },
    });
    assert.deepEqual(calls[4].options, {
      cwd: testCase.cwd,
      env: {
        ...env,
        DJANGO_SETTINGS_MODULE: "gradmatch.config.settings_test",
      },
      stdio: "inherit",
    });
  });
}

test("runPythonChecks propagates check process spawn errors", () => {
  const failure = new Error("pytest launch failed");
  let callCount = 0;

  assert.throws(
    () =>
      runPythonChecks({
        platform: "linux",
        runtime: { command: "python3", prefixArgs: [] },
        spawn: () => {
          callCount += 1;
          return callCount === 1 ? { status: 0, stdout: "/usr/bin/python3\n" } : { error: failure };
        },
      }),
    (error) => error === failure,
  );
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

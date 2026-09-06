import assert from "node:assert/strict";
import test from "node:test";

import { buildNativeCommand, runNativeCommand } from "./native-run.mjs";

test("builds the four supported native service commands", () => {
  assert.deepEqual(buildNativeCommand("migrate"), ["manage.py", "migrate"]);
  assert.deepEqual(buildNativeCommand("api"), [
    "-m",
    "uvicorn",
    "gradmatch.config.asgi:application",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--reload",
  ]);
  assert.deepEqual(buildNativeCommand("worker"), [
    "-m",
    "celery",
    "-A",
    "gradmatch",
    "worker",
    "--loglevel=INFO",
    "--pool=solo",
  ]);
  assert.deepEqual(buildNativeCommand("beat"), [
    "-m",
    "celery",
    "-A",
    "gradmatch",
    "beat",
    "--loglevel=INFO",
  ]);
  assert.throws(() => buildNativeCommand("unknown"), /Unknown native command/u);
});

test("passes .env values to the native process without overriding explicit values", () => {
  let invocation;
  const exitCode = runNativeCommand("migrate", {
    envText: "DATABASE_URL=postgresql://file.example/gradmatch\nREDIS_URL=redis://file:6379/0",
    processEnvironment: { DATABASE_URL: "postgresql://process.example/gradmatch" },
    runtime: { command: "python", prefixArgs: [] },
    spawn: (command, args, options) => {
      invocation = { args, command, options };
      return { status: 0 };
    },
  });

  assert.equal(exitCode, 0);
  assert.equal(invocation.command, "python");
  assert.deepEqual(invocation.args, ["manage.py", "migrate"]);
  assert.equal(invocation.options.env.DATABASE_URL, "postgresql://process.example/gradmatch");
  assert.equal(invocation.options.env.REDIS_URL, "redis://file:6379/0");
});

test("fails without spawning when no existing Python runtime is available", () => {
  let spawned = false;
  const messages = [];
  const exitCode = runNativeCommand("api", {
    runtime: null,
    spawn: () => {
      spawned = true;
      return { status: 0 };
    },
    writeError: (message) => messages.push(message),
  });

  assert.equal(exitCode, 1);
  assert.equal(spawned, false);
  assert.deepEqual(messages, ["未找到已安装的 Python 解释器或项目虚拟环境。"]);
});

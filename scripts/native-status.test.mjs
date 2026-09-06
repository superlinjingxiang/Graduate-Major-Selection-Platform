import assert from "node:assert/strict";
import { createServer } from "node:net";
import test from "node:test";

import {
  checkPortOccupied,
  formatNativeStatus,
  inspectNativeStatus,
  loadNativeEnvironment,
  resolveNativePythonRuntime,
} from "./native-status.mjs";

test("native runtime resolution never falls back to uv", () => {
  const runtime = resolveNativePythonRuntime({
    commandExists: (command) => command === "python3",
    exists: () => false,
    platform: "win32",
    root: "E:/GradMatch",
  });

  assert.deepEqual(runtime, { command: "python3", prefixArgs: [] });
  assert.equal(
    resolveNativePythonRuntime({
      commandExists: () => false,
      exists: () => false,
      platform: "win32",
      root: "E:/GradMatch",
    }),
    null,
  );
});

test("environment values override .env while missing values use native defaults", () => {
  const environment = loadNativeEnvironment({
    processEnvironment: {
      DATABASE_URL: "postgresql://process.example/gradmatch",
    },
    envText: [
      "DATABASE_URL=postgresql://file.example/gradmatch",
      "REDIS_URL=redis://file.example:6379/0",
      "S3_BUCKET_NAME=local-bucket",
    ].join("\n"),
  });

  assert.deepEqual(environment, {
    DATABASE_URL: "postgresql://process.example/gradmatch",
    REDIS_URL: "redis://file.example:6379/0",
    S3_ACCESS_KEY_ID: "gradmatch",
    S3_BUCKET_NAME: "local-bucket",
    S3_ENDPOINT_URL: "http://localhost:9000",
    S3_SECRET_ACCESS_KEY: "gradmatch-secret",
  });
});

test("reports each dependency and port without treating occupied app ports as dependencies", async () => {
  const report = await inspectNativeStatus({
    environment: loadNativeEnvironment({ processEnvironment: {}, envText: "" }),
    probeDependency: async ({ key }) => ({
      detail: key === "redis" ? "连接被拒绝" : "可用",
      ok: key !== "redis",
    }),
    probePort: async ({ port }) => port === 3000,
  });

  assert.equal(report.ready, false);
  assert.deepEqual(
    report.dependencies.map(({ key, ok }) => [key, ok]),
    [
      ["python", true],
      ["postgresql", true],
      ["redis", false],
      ["s3", true],
    ],
  );
  assert.deepEqual(
    report.ports.map(({ port, occupied }) => [port, occupied]),
    [
      [8000, false],
      [3000, true],
    ],
  );

  const output = formatNativeStatus(report);
  assert.match(output, /\[不可用\] Redis：连接被拒绝/u);
  assert.match(output, /\[空闲\] API 端口 8000/u);
  assert.match(output, /\[占用\] Web 端口 3000/u);
  assert.match(output, /结论：原生依赖尚未全部就绪/u);
  assert.doesNotMatch(output, /postgresql:\/\//u);
});

test("reports ready only when all required dependencies are available", async () => {
  const report = await inspectNativeStatus({
    environment: loadNativeEnvironment({ processEnvironment: {}, envText: "" }),
    probeDependency: async () => ({ detail: "可用", ok: true }),
    probePort: async () => false,
  });

  assert.equal(report.ready, true);
  assert.match(formatNativeStatus(report), /结论：原生依赖已就绪/u);
});

test("port occupancy probe distinguishes a local listener from a free port", async () => {
  const server = createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  assert.ok(address && typeof address === "object");

  assert.equal(await checkPortOccupied({ port: address.port, timeoutMs: 500 }), true);
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
  assert.equal(await checkPortOccupied({ port: address.port, timeoutMs: 500 }), false);
});

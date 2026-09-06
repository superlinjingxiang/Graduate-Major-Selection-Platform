import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { createConnection } from "node:net";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { resolvePythonRuntime } from "./python-runtime.mjs";

const workspaceRoot = fileURLToPath(new URL("..", import.meta.url));
const apiRoot = path.join(workspaceRoot, "services", "api");

const nativeDefaults = Object.freeze({
  DATABASE_URL: "postgresql://gradmatch:gradmatch@localhost:5432/gradmatch",
  REDIS_URL: "redis://localhost:6379/0",
  S3_ACCESS_KEY_ID: "gradmatch",
  S3_BUCKET_NAME: "gradmatch",
  S3_ENDPOINT_URL: "http://localhost:9000",
  S3_SECRET_ACCESS_KEY: "gradmatch-secret",
});

const dependencyDefinitions = [
  { key: "python", label: "Python 运行时与项目包" },
  { key: "postgresql", label: "PostgreSQL" },
  { key: "redis", label: "Redis" },
  { key: "s3", label: "S3 兼容对象存储" },
];

const portDefinitions = [
  { key: "api", label: "API 端口 8000", port: 8000 },
  { key: "web", label: "Web 端口 3000", port: 3000 },
];

const pythonProbes = Object.freeze({
  python: [
    "import boto3",
    "import django",
    "import gradmatch",
    "import psycopg",
    "import redis",
  ].join("; "),
  postgresql: [
    "import os, psycopg",
    "connection = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=2)",
    "cursor = connection.cursor()",
    "cursor.execute('SELECT 1')",
    "assert cursor.fetchone() == (1,)",
    "cursor.close()",
    "connection.close()",
  ].join("; "),
  redis: [
    "import os, redis",
    "client = redis.Redis.from_url(os.environ['REDIS_URL'], socket_connect_timeout=2, socket_timeout=2)",
    "assert client.ping()",
    "client.close()",
  ].join("; "),
  s3: [
    "import os, boto3",
    "from botocore.config import Config",
    "client = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT_URL'], aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'], aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'], config=Config(connect_timeout=2, read_timeout=2, retries={'max_attempts': 0}))",
    "client.head_bucket(Bucket=os.environ['S3_BUCKET_NAME'])",
  ].join("; "),
});

function parseEnvText(envText) {
  const parsed = {};
  for (const rawLine of envText.split(/\r?\n/u)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const separator = line.indexOf("=");
    if (separator < 1) continue;
    const key = line
      .slice(0, separator)
      .trim()
      .replace(/^export\s+/u, "");
    if (!/^[A-Z_][A-Z0-9_]*$/u.test(key)) continue;
    let value = line.slice(separator + 1).trim();
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1);
    }
    parsed[key] = value;
  }
  return parsed;
}

export function loadNativeEnvironment(options = {}) {
  const { processEnvironment = process.env, envText = "" } = options;
  const fileEnvironment = parseEnvText(envText);
  return Object.fromEntries(
    Object.entries(nativeDefaults).map(([key, fallback]) => [
      key,
      processEnvironment[key] ?? fileEnvironment[key] ?? fallback,
    ]),
  );
}

function loadProjectEnvironment() {
  const envPath = path.join(workspaceRoot, ".env");
  const envText = existsSync(envPath) ? readFileSync(envPath, "utf8") : "";
  return loadNativeEnvironment({ envText });
}

function probeSuccessDetail(key) {
  return key === "python" ? "运行时与依赖可导入" : "连接成功";
}

export async function probeNativeDependency({ environment, key, runtime }) {
  const code = pythonProbes[key];
  if (!code) return { detail: "未知检查项", ok: false };
  const pythonPath = path.join(apiRoot, "src");
  const result = spawnSync(runtime.command, [...runtime.prefixArgs, "-c", code], {
    cwd: apiRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      ...environment,
      PYTHONPATH: pythonPath,
    },
    stdio: ["ignore", "pipe", "pipe"],
    timeout: 5000,
    windowsHide: true,
  });
  if (!result.error && result.status === 0) {
    return { detail: probeSuccessDetail(key), ok: true };
  }
  if (result.error?.code === "ETIMEDOUT") return { detail: "检查超时", ok: false };
  return {
    detail: key === "python" ? "运行时或依赖不可用" : "连接失败",
    ok: false,
  };
}

export function checkPortOccupied(options) {
  const { host = "127.0.0.1", port, timeoutMs = 1000 } = options;
  return new Promise((resolve) => {
    const socket = createConnection({ host, port });
    let settled = false;
    const finish = (occupied) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve(occupied);
    };
    socket.setTimeout(timeoutMs);
    socket.once("connect", () => finish(true));
    socket.once("error", () => finish(false));
    socket.once("timeout", () => finish(false));
  });
}

export async function inspectNativeStatus(options = {}) {
  const {
    environment = loadProjectEnvironment(),
    probeDependency = probeNativeDependency,
    probePort = checkPortOccupied,
    runtime = resolvePythonRuntime({ root: workspaceRoot }),
  } = options;

  const dependencies = [];
  for (const definition of dependencyDefinitions) {
    const result = await probeDependency({
      environment,
      key: definition.key,
      runtime,
    });
    dependencies.push({ ...definition, ...result });
  }

  const ports = [];
  for (const definition of portDefinitions) {
    const occupied = await probePort({ host: "127.0.0.1", port: definition.port });
    ports.push({ ...definition, occupied });
  }

  return {
    dependencies,
    ports,
    ready: dependencies.every(({ ok }) => ok),
  };
}

export function formatNativeStatus(report) {
  const lines = ["GradMatch 本机原生运行诊断"];
  for (const dependency of report.dependencies) {
    lines.push(`[${dependency.ok ? "正常" : "不可用"}] ${dependency.label}：${dependency.detail}`);
  }
  for (const port of report.ports) {
    lines.push(`[${port.occupied ? "占用" : "空闲"}] ${port.label}`);
  }
  lines.push(`结论：${report.ready ? "原生依赖已就绪" : "原生依赖尚未全部就绪"}`);
  return lines.join("\n");
}

export async function runNativeStatus(options = {}) {
  const { write = (message) => console.log(message), ...inspectionOptions } = options;
  const report = await inspectNativeStatus(inspectionOptions);
  write(formatNativeStatus(report));
  return report.ready ? 0 : 1;
}

const invokedPath = process.argv[1] ? pathToFileURL(path.resolve(process.argv[1])).href : "";
if (invokedPath === import.meta.url) {
  process.exitCode = await runNativeStatus();
}

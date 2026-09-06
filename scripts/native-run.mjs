import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { loadNativeProcessEnvironment, resolveNativePythonRuntime } from "./native-status.mjs";

const workspaceRoot = fileURLToPath(new URL("..", import.meta.url));
const apiRoot = path.join(workspaceRoot, "services", "api");

const commandArguments = Object.freeze({
  api: [
    "-m",
    "uvicorn",
    "gradmatch.config.asgi:application",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--reload",
  ],
  beat: ["-m", "celery", "-A", "gradmatch", "beat", "--loglevel=INFO"],
  migrate: ["manage.py", "migrate"],
  worker: ["-m", "celery", "-A", "gradmatch", "worker", "--loglevel=INFO", "--pool=solo"],
});

export function buildNativeCommand(action) {
  const args = commandArguments[action];
  if (!args) throw new Error(`Unknown native command: ${action}`);
  return [...args];
}

function readWorkspaceEnvironmentFile() {
  const envPath = path.join(workspaceRoot, ".env");
  return existsSync(envPath) ? readFileSync(envPath, "utf8") : "";
}

export function runNativeCommand(action, options = {}) {
  const {
    envText = readWorkspaceEnvironmentFile(),
    processEnvironment = process.env,
    runtime = resolveNativePythonRuntime({ root: workspaceRoot }),
    spawn = spawnSync,
    writeError = (message) => console.error(message),
  } = options;
  if (runtime === null) {
    writeError("未找到已安装的 Python 解释器或项目虚拟环境。");
    return 1;
  }

  const result = spawn(runtime.command, [...runtime.prefixArgs, ...buildNativeCommand(action)], {
    cwd: apiRoot,
    env: loadNativeProcessEnvironment({ envText, processEnvironment }),
    stdio: "inherit",
    windowsHide: false,
  });
  if (result.error) {
    writeError("无法启动本机服务进程。");
    return 1;
  }
  return result.status ?? 1;
}

const invokedPath = process.argv[1] ? pathToFileURL(path.resolve(process.argv[1])).href : "";
if (invokedPath === import.meta.url) {
  try {
    process.exitCode = runNativeCommand(process.argv[2]);
  } catch (error) {
    console.error(error instanceof Error ? error.message : "未知本机启动错误");
    process.exitCode = 1;
  }
}

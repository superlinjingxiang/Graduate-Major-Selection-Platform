import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { posix, win32 } from "node:path";
import { fileURLToPath } from "node:url";

const workspaceRoot = fileURLToPath(new URL("..", import.meta.url));

function appendPath(root, relativePath) {
  const normalizedRoot = root.replaceAll("\\", "/").replace(/\/+$/, "");
  return normalizedRoot ? `${normalizedRoot}/${relativePath}` : `/${relativePath}`;
}

function defaultCommandExists(command) {
  const result = spawnSync(command, ["--version"], { stdio: "ignore" });
  return !result.error && result.status === 0;
}

export function resolvePythonRuntime(options = {}) {
  const {
    platform = process.platform,
    root = workspaceRoot,
    exists = existsSync,
    commandExists = defaultCommandExists,
  } = options;
  const apiProject = appendPath(root, "services/api");
  const virtualenvPython = appendPath(
    apiProject,
    platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python",
  );

  if (exists(virtualenvPython)) {
    return { command: virtualenvPython, prefixArgs: [] };
  }

  const uvCommand = platform === "win32" ? "uv.exe" : "uv";
  if (commandExists(uvCommand)) {
    return {
      command: uvCommand,
      prefixArgs: ["run", "--project", apiProject, "python"],
    };
  }

  const fallbackCommands = platform === "win32" ? ["python", "python3"] : ["python3", "python"];
  const command =
    fallbackCommands.find((candidate) => commandExists(candidate)) ?? fallbackCommands[0];
  return { command, prefixArgs: [] };
}

export function resolvePythonExecutable(options = {}) {
  const {
    platform = process.platform,
    runtime = resolvePythonRuntime(options),
    spawn = spawnSync,
    cwd = workspaceRoot,
    env = process.env,
    exit = process.exit,
  } = options;
  const result = spawn(
    runtime.command,
    [...runtime.prefixArgs, "-c", "import sys; print(sys.executable)"],
    {
      cwd,
      env,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "inherit"],
    },
  );

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    exit(result.status ?? 1);
    throw new Error("Python exit handler returned unexpectedly.");
  }

  const executable = String(result.stdout ?? "").trim();
  const path = platform === "win32" ? win32 : posix;
  if (!path.isAbsolute(executable)) {
    throw new Error(`Python reported a non-absolute executable path: ${executable || "<empty>"}`);
  }
  return executable;
}

export function runPython(args, options = {}) {
  const {
    runtime = resolvePythonRuntime(options),
    spawn = spawnSync,
    cwd = workspaceRoot,
    env = process.env,
  } = options;
  const result = spawn(runtime.command, [...runtime.prefixArgs, ...args], {
    cwd,
    env,
    stdio: "inherit",
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
  return result;
}

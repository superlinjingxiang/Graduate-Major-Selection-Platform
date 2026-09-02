import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

import { resolvePythonExecutable, resolvePythonRuntime, runPython } from "./python-runtime.mjs";

const apiRoot = fileURLToPath(new URL("../services/api/", import.meta.url));

export function runPythonChecks(options = {}) {
  const {
    platform = process.platform,
    cwd = apiRoot,
    env = process.env,
    spawn = spawnSync,
  } = options;
  const runtime = options.runtime ?? resolvePythonRuntime(options);
  const runOptions = { cwd, env, runtime, spawn };
  const pythonPath = resolvePythonExecutable({
    ...runOptions,
    platform,
  });

  runPython(["-m", "pytest", "-p", "no:cacheprovider"], runOptions);
  runPython(["-m", "ruff", "check", "src", "tests"], runOptions);
  runPython(["-m", "pyright", "--pythonpath", pythonPath, "src", "tests"], runOptions);
  runPython(["manage.py", "makemigrations", "--check", "--dry-run"], {
    ...runOptions,
    env: {
      ...env,
      DJANGO_SETTINGS_MODULE: "gradmatch.config.settings_test",
    },
  });
}

const entrypoint = process.argv[1] ? pathToFileURL(process.argv[1]).href : undefined;
if (import.meta.url === entrypoint) {
  runPythonChecks();
}

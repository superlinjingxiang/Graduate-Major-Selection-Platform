import { fileURLToPath } from "node:url";

import { resolvePythonRuntime, runPython } from "./python-runtime.mjs";

const apiRoot = fileURLToPath(new URL("../services/api/", import.meta.url));
const runtime = resolvePythonRuntime();
const pythonPath =
  runtime.prefixArgs.length === 0
    ? runtime.command
    : process.platform === "win32"
      ? "python.exe"
      : "python";

function run(args, env = process.env) {
  runPython(args, { cwd: apiRoot, env, runtime });
}

run(["-m", "pytest", "-p", "no:cacheprovider"]);
run(["-m", "ruff", "check", "src", "tests"]);
run(["-m", "pyright", "--pythonpath", pythonPath, "src", "tests"]);
run(["manage.py", "makemigrations", "--check", "--dry-run"], {
  ...process.env,
  DJANGO_SETTINGS_MODULE: "gradmatch.config.settings_test",
});

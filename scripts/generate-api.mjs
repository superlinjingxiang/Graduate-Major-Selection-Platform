import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { runPython } from "./python-runtime.mjs";

const workspaceRoot = fileURLToPath(new URL("..", import.meta.url));
const apiRoot = fileURLToPath(new URL("../services/api/", import.meta.url));
function execute(command, args) {
  return spawnSync(command, args, {
    cwd: workspaceRoot,
    stdio: "inherit",
  });
}

function assertSuccess(result) {
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function run(command, args) {
  assertSuccess(execute(command, args));
}

runPython(["scripts/export_openapi.py"], { cwd: apiRoot });
run(process.execPath, [
  "node_modules/openapi-typescript/bin/cli.js",
  "packages/api-client/openapi/core.openapi.json",
  "-o",
  "packages/api-client/src/generated/core.ts",
]);
run(process.execPath, [
  "node_modules/openapi-typescript/bin/cli.js",
  "packages/api-client/openapi/auth.openapi.json",
  "-o",
  "packages/api-client/src/generated/auth.ts",
]);

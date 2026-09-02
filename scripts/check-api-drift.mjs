import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const workspaceRoot = fileURLToPath(new URL("..", import.meta.url));
const safeWorkspaceRoot = workspaceRoot.replaceAll("\\", "/").replace(/\/$/u, "");
function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: workspaceRoot,
    stdio: "inherit",
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

run(process.execPath, ["scripts/generate-api.mjs"]);
run("git", [
  "-c",
  `safe.directory=${safeWorkspaceRoot}`,
  "diff",
  "--exit-code",
  "--",
  "packages/api-client/openapi",
  "packages/api-client/src/generated",
]);

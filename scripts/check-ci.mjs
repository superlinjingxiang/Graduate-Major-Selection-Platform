import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parseDocument } from "yaml";

const workflowPath = resolve(import.meta.dirname, "../.github/workflows/ci.yml");
const document = parseDocument(readFileSync(workflowPath, "utf8"));
const errors = document.errors.map((error) => `ci.yml: ${error.message}`);
const workflow = document.toJS() ?? {};
const jobs = workflow.jobs ?? {};

for (const jobName of ["typescript", "python", "contracts-and-containers", "e2e"]) {
  if (!jobs[jobName]) errors.push(`Missing CI job: ${jobName}`);
}
if (!Array.isArray(jobs.e2e?.needs) || jobs.e2e.needs.length === 0) {
  errors.push("The E2E job must wait for its prerequisite quality jobs.");
}

const steps = Object.values(jobs)
  .flatMap((job) => job.steps ?? [])
  .map((step) => step.run ?? "")
  .join("\n");
for (const command of [
  "pnpm lint",
  "pnpm format:check",
  "pnpm check:api-drift",
  "docker compose up --build --wait",
  "pnpm e2e",
]) {
  if (!steps.includes(command)) errors.push(`CI is missing required command: ${command}`);
}

if (errors.length > 0) throw new Error(`CI workflow validation failed:\n- ${errors.join("\n- ")}`);

console.log("CI workflow is structurally valid.");

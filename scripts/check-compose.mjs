import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parseDocument } from "yaml";

const root = resolve(import.meta.dirname, "..");
const composePath = resolve(root, "docker-compose.yml");
const caddyPath = resolve(root, "Caddyfile");
const dockerfiles = [
  resolve(root, "apps/web/Dockerfile"),
  resolve(root, "services/api/Dockerfile"),
];
const requiredServices = [
  "caddy",
  "web",
  "api",
  "worker",
  "beat",
  "postgres",
  "redis",
  "minio",
  "minio-init",
  "mailpit",
  "migrate",
];
const requiredHealthChecks = ["postgres", "redis", "minio", "mailpit", "api", "web", "worker"];
const djangoPaths = ["/api/*", "/_allauth/*", "/accounts/*", "/admin/*", "/static/*", "/media/*"];

const errors = [];
const composeDocument = parseDocument(readFileSync(composePath, "utf8"));
if (composeDocument.errors.length > 0) {
  errors.push(...composeDocument.errors.map((error) => `docker-compose.yml: ${error.message}`));
}

const compose = composeDocument.toJS() ?? {};
const services = compose.services ?? {};
for (const serviceName of requiredServices) {
  if (!services[serviceName]) {
    errors.push(`Missing required Compose service: ${serviceName}`);
  }
}
for (const serviceName of requiredHealthChecks) {
  if (!services[serviceName]?.healthcheck?.test) {
    errors.push(`Missing functional healthcheck for: ${serviceName}`);
  }
}
if (services["minio-init"]?.entrypoint !== "/bin/sh") {
  errors.push("minio-init must override the mc image entrypoint with /bin/sh");
}
if (services.beat?.healthcheck?.disable !== true) {
  errors.push("beat must disable the inherited API HTTP healthcheck");
}
const requiredDependencies = [
  ["migrate", "postgres", "service_healthy"],
  ["migrate", "redis", "service_healthy"],
  ["migrate", "minio-init", "service_completed_successfully"],
  ["api", "migrate", "service_completed_successfully"],
  ["web", "api", "service_healthy"],
  ["worker", "migrate", "service_completed_successfully"],
  ["beat", "migrate", "service_completed_successfully"],
  ["caddy", "api", "service_healthy"],
  ["caddy", "web", "service_healthy"],
];
for (const [serviceName, dependencyName, condition] of requiredDependencies) {
  if (services[serviceName]?.depends_on?.[dependencyName]?.condition !== condition) {
    errors.push(`${serviceName} must wait for ${dependencyName} (${condition})`);
  }
}
for (const volumeName of [
  "postgres_data",
  "minio_data",
  "caddy_data",
  "caddy_config",
  "staticfiles_data",
]) {
  if (!Object.hasOwn(compose.volumes ?? {}, volumeName)) {
    errors.push(`Missing named volume: ${volumeName}`);
  }
}

const secretKeyPattern = /(PASSWORD|SECRET(?:_KEY)?|ACCESS_KEY_ID)$/;
for (const [serviceName, service] of Object.entries(services)) {
  for (const [key, value] of Object.entries(service.environment ?? {})) {
    if (secretKeyPattern.test(key) && (typeof value !== "string" || !value.startsWith("${"))) {
      errors.push(`Service ${serviceName} bakes a secret-like environment value for ${key}`);
    }
  }
}

const trackedEnvironmentFiles = execFileSync("git", ["ls-files"], { cwd: root, encoding: "utf8" })
  .split(/\r?\n/)
  .filter((file) => /(^|\/)\.env(?:\.|$)/.test(file) && file !== ".env.example");
if (trackedEnvironmentFiles.length > 0) {
  errors.push(`Committed environment files are forbidden: ${trackedEnvironmentFiles.join(", ")}`);
}

const caddyfile = readFileSync(caddyPath, "utf8");
for (const path of djangoPaths) {
  if (!caddyfile.includes(path)) {
    errors.push(`Caddyfile does not route ${path} to Django`);
  }
}
for (const fragment of ["reverse_proxy api:8000", "reverse_proxy web:3000", "X-Forwarded-Proto"]) {
  if (!caddyfile.includes(fragment)) {
    errors.push(`Caddyfile is missing required proxy behavior: ${fragment}`);
  }
}
const structuralCaddyfile = caddyfile.replaceAll(/\{[a-zA-Z_.]+\}/g, "");
let braceDepth = 0;
for (const character of structuralCaddyfile) {
  if (character === "{") braceDepth += 1;
  if (character === "}") braceDepth -= 1;
  if (braceDepth < 0) errors.push("Caddyfile contains an unexpected closing brace");
}
if (braceDepth !== 0) {
  errors.push("Caddyfile contains unbalanced braces");
}
try {
  execFileSync("caddy", ["adapt", "--config", caddyPath, "--adapter", "caddyfile"], {
    cwd: root,
    stdio: "pipe",
  });
} catch (error) {
  if (error && typeof error === "object" && "code" in error && error.code !== "ENOENT") {
    errors.push(`Caddyfile failed native adaptation: ${String(error.message)}`);
  }
}

for (const dockerfilePath of dockerfiles) {
  const dockerfile = readFileSync(dockerfilePath, "utf8");
  if (!/^USER\s+\S+/m.test(dockerfile)) {
    errors.push(`${dockerfilePath} must set a non-root runtime USER`);
  }
  if (!/--frozen/.test(dockerfile)) {
    errors.push(`${dockerfilePath} must use a frozen lockfile install`);
  }
  if (!/^HEALTHCHECK\s+/m.test(dockerfile)) {
    errors.push(`${dockerfilePath} must define a runtime healthcheck`);
  }
}

const volumeTarget = "/app/staticfiles";
const migrateStaticMount = services.migrate?.volumes?.find(
  (volume) => volume === `staticfiles_data:${volumeTarget}`,
);
const apiStaticMount = services.api?.volumes?.find(
  (volume) => volume === `staticfiles_data:${volumeTarget}:ro`,
);
if (!migrateStaticMount || !apiStaticMount) {
  errors.push("migrate must write and api must read the shared staticfiles_data volume");
}

if (errors.length > 0) {
  throw new Error(`Compose static validation failed:\n- ${errors.join("\n- ")}`);
}

console.log("Compose, Caddyfile, Dockerfiles, and secret boundaries are structurally valid.");

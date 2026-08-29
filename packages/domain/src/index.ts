export const appEnvironments = ["development", "test", "staging", "production"] as const;

export type AppEnvironment = (typeof appEnvironments)[number];

export interface AppDescriptor {
  readonly name: string;
  readonly environment: AppEnvironment;
  readonly version: string;
}

export interface ServiceDescriptor {
  readonly name: "web" | "api" | "mobile";
  readonly state: "planned" | "ready" | "deferred";
}

export interface FoundationSnapshot {
  readonly app: AppDescriptor;
  readonly services: readonly ServiceDescriptor[];
}

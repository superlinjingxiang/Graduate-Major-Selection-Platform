import createClient from "openapi-fetch";

import type { paths as AuthPaths } from "./generated/auth.js";

export type { CoreComponents, CorePaths } from "./core-client.js";
export { coreClient } from "./core-client.js";
export type { components as AuthComponents, paths as AuthPaths } from "./generated/auth.js";

export const authClient = (baseUrl: string) => createClient<AuthPaths>({ baseUrl });

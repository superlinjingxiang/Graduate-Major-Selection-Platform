import createClient from "openapi-fetch";

import type { paths as CorePaths } from "./generated/core.js";

export type { components as CoreComponents, paths as CorePaths } from "./generated/core.js";

export const coreClient = (baseUrl: string) => createClient<CorePaths>({ baseUrl });

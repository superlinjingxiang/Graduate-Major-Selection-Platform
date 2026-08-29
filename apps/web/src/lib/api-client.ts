import { authClient, coreClient } from "@gradmatch/api-client";

const serverApiBaseUrl = process.env.GRADMATCH_API_BASE_URL ?? "http://localhost:8000";

export const serverCoreClient = coreClient(serverApiBaseUrl);
export const browserCoreClient = coreClient("");
export const browserAuthClient = authClient("");

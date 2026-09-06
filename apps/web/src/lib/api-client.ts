import { authClient } from "@gradmatch/api-client";
import { coreClient } from "@gradmatch/api-client/core-client";

const serverApiBaseUrl = process.env.GRADMATCH_API_BASE_URL ?? "http://localhost:8000";

export const serverCoreClient = coreClient(serverApiBaseUrl);
export const browserCoreClient = coreClient("");
export const browserAuthClient = authClient("");

const unsafeMethods = new Set(["DELETE", "PATCH", "POST", "PUT"]);
const browserAuthPath = { params: { path: { client: "browser" as const } } };

let browserCsrfRequest: Promise<void> | undefined;

function readBrowserCookie(name: string) {
  if (typeof document === "undefined") return undefined;

  const encodedValue = document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${name}=`))
    ?.slice(name.length + 1);

  return encodedValue ? decodeURIComponent(encodedValue) : undefined;
}

function isBrowserMutation(request: Request) {
  return (
    typeof window !== "undefined" &&
    unsafeMethods.has(request.method) &&
    new URL(request.url).origin === window.location.origin
  );
}

async function refreshBrowserCsrf() {
  browserCsrfRequest ??= browserAuthClient
    .GET("/_allauth/{client}/v1/config", browserAuthPath)
    .then(({ response }) => {
      if (!response.ok) throw new Error("CSRF initialization failed");
    })
    .finally(() => {
      browserCsrfRequest = undefined;
    });
  await browserCsrfRequest;
}

const browserCsrfMiddleware = {
  async onRequest({ request }: Readonly<{ request: Request }>) {
    if (!isBrowserMutation(request)) return;

    if (!readBrowserCookie("csrftoken")) await refreshBrowserCsrf();

    const csrfToken = readBrowserCookie("csrftoken");
    if (csrfToken) request.headers.set("X-CSRFToken", csrfToken);
  },
  async onResponse({
    options,
    request,
    response,
  }: Readonly<{
    options: { fetch: typeof globalThis.fetch };
    request: Request;
    response: Response;
  }>) {
    if (response.status !== 403 || !isBrowserMutation(request)) return;

    await refreshBrowserCsrf();
    const csrfToken = readBrowserCookie("csrftoken");
    if (!csrfToken) return;

    const headers = new Headers(request.headers);
    headers.set("X-CSRFToken", csrfToken);
    return options.fetch(new Request(request, { headers }));
  },
};

browserAuthClient.use(browserCsrfMiddleware);
browserCoreClient.use(browserCsrfMiddleware);

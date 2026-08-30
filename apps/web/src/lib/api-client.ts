import { authClient, coreClient } from "@gradmatch/api-client";

const serverApiBaseUrl = process.env.GRADMATCH_API_BASE_URL ?? "http://localhost:8000";

export const serverCoreClient = coreClient(serverApiBaseUrl);
export const browserCoreClient = coreClient("");
export const browserAuthClient = authClient("");

const unsafeMethods = new Set(["DELETE", "PATCH", "POST", "PUT"]);

function readBrowserCookie(name: string) {
  if (typeof document === "undefined") return undefined;

  const encodedValue = document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${name}=`))
    ?.slice(name.length + 1);

  return encodedValue ? decodeURIComponent(encodedValue) : undefined;
}

browserAuthClient.use({
  onRequest({ request }) {
    if (typeof window === "undefined" || !unsafeMethods.has(request.method)) return;
    if (new URL(request.url).origin !== window.location.origin) return;

    const csrfToken = readBrowserCookie("csrftoken");
    if (csrfToken) request.headers.set("X-CSRFToken", csrfToken);
  },
});

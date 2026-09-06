import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const NativeRequest = globalThis.Request;

class BrowserRequest extends NativeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(typeof input === "string" ? new URL(input, window.location.origin) : input, init);
  }
}

describe("browser API CSRF middleware", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubGlobal("Request", BrowserRequest);
    // biome-ignore lint/suspicious/noDocumentCookie: these tests exercise the browser CSRF flow.
    document.cookie = "csrftoken=; Max-Age=0; path=/";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("initializes CSRF and attaches it to core mutations", async () => {
    const fetchMock = vi.fn(async (request: Request) => {
      const pathname = new URL(request.url).pathname;
      if (pathname === "/_allauth/browser/v1/config") {
        // biome-ignore lint/suspicious/noDocumentCookie: simulates Django setting the readable CSRF cookie.
        document.cookie = "csrftoken=pilot-token; path=/";
        return Response.json({}, { status: 200 });
      }
      expect(pathname).toBe("/api/v1/fact-sets");
      expect(request.headers.get("X-CSRFToken")).toBe("pilot-token");
      return Response.json(
        {
          confirmed_facts: { target_year: 2027 },
          fact_set_id: "56d1aa4c-a22e-46c5-b69d-3228f408a92a",
          input_hash: "a".repeat(64),
          version: 1,
        },
        { status: 201 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const { browserCoreClient } = await import("./api-client");

    const result = await browserCoreClient.POST("/api/v1/fact-sets", {
      body: { confirmed_facts: { target_year: 2027 } },
    });

    expect(result.response.status).toBe(201);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("refreshes a stale CSRF token and retries a rejected mutation once", async () => {
    // biome-ignore lint/suspicious/noDocumentCookie: simulates a stale browser CSRF cookie.
    document.cookie = "csrftoken=stale-token; path=/";
    let mutationAttempts = 0;
    const mutationBodies: unknown[] = [];
    const fetchMock = vi.fn(async (request: Request) => {
      const pathname = new URL(request.url).pathname;
      if (pathname === "/_allauth/browser/v1/config") {
        // biome-ignore lint/suspicious/noDocumentCookie: simulates Django rotating the CSRF cookie.
        document.cookie = "csrftoken=fresh-token; path=/";
        return Response.json({}, { status: 200 });
      }
      mutationAttempts += 1;
      mutationBodies.push(await request.json());
      if (mutationAttempts === 1) {
        expect(request.headers.get("X-CSRFToken")).toBe("stale-token");
        return Response.json({ detail: "CSRF Failed" }, { status: 403 });
      }
      expect(request.headers.get("X-CSRFToken")).toBe("fresh-token");
      return Response.json(
        {
          confirmed_facts: { target_year: 2027 },
          fact_set_id: "56d1aa4c-a22e-46c5-b69d-3228f408a92a",
          input_hash: "a".repeat(64),
          version: 1,
        },
        { status: 201 },
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const { browserCoreClient } = await import("./api-client");

    const result = await browserCoreClient.POST("/api/v1/fact-sets", {
      body: { confirmed_facts: { target_year: 2027 } },
    });

    expect(result.response.status).toBe(201);
    expect(mutationAttempts).toBe(2);
    expect(mutationBodies).toEqual([
      { confirmed_facts: { target_year: 2027 } },
      { confirmed_facts: { target_year: 2027 } },
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});

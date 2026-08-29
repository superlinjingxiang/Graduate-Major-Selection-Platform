export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface ApiClientConfig {
  readonly baseUrl: string;
  readonly timeoutMs?: number;
  readonly userAgent?: string;
}

export interface ApiRequest<Body = unknown> {
  readonly method: HttpMethod;
  readonly path: `/${string}`;
  readonly headers?: Readonly<Record<string, string>>;
  readonly query?: Readonly<Record<string, string | number | boolean>>;
  readonly body?: Body;
}

export interface ApiResponse<Data = unknown> {
  readonly status: number;
  readonly data: Data;
  readonly headers?: Readonly<Record<string, string>>;
}

export interface PendingGeneratedClients {
  readonly coreClient: "pending-task-3";
  readonly authClient: "pending-task-3";
}

export const GENERATED_CLIENT_STATUS: PendingGeneratedClients = {
  coreClient: "pending-task-3",
  authClient: "pending-task-3",
};

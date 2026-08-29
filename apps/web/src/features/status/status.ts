import type { CoreComponents } from "@gradmatch/api-client";

import { serverCoreClient } from "../../lib/api-client";

type Metadata = CoreComponents["schemas"]["MetaResponse"];
type Readiness = CoreComponents["schemas"]["ReadinessResponse"];

export type StatusPresentation =
  | {
      kind: "ready" | "degraded";
      metadata: Metadata;
      message: string;
      title: string;
    }
  | {
      kind: "error";
      message: string;
      title: string;
    };

export function toStatusPresentation(metadata: Metadata, readiness: Readiness): StatusPresentation {
  if (readiness.status === "ok") {
    return {
      kind: "ready",
      metadata,
      message: "系统基础服务连接正常，可以继续构建下一段体验。",
      title: "服务已准备就绪",
    };
  }

  return {
    kind: "degraded",
    metadata,
    message: "部分底层服务暂不可用，平台会在恢复后自动继续提供完整能力。",
    title: "服务暂未完全就绪",
  };
}

export async function loadServerStatus(): Promise<StatusPresentation> {
  try {
    const [metadataResponse, readinessResponse] = await Promise.all([
      serverCoreClient.GET("/api/v1/meta"),
      serverCoreClient.GET("/api/v1/health/ready"),
    ]);
    if (!metadataResponse.data || !readinessResponse.data) {
      throw new Error("The API did not provide status data.");
    }

    return toStatusPresentation(metadataResponse.data, readinessResponse.data);
  } catch {
    return {
      kind: "error",
      message: "暂时无法读取服务状态，请稍后刷新页面。",
      title: "状态读取暂不可用",
    };
  }
}

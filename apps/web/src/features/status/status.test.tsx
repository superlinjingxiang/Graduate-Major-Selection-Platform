import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { toStatusPresentation } from "./status";
import { StatusPanel } from "./status-panel";

describe("toStatusPresentation", () => {
  it("turns healthy server responses into a ready state", () => {
    const presentation = toStatusPresentation(
      { name: "GradMatch", environment: "development", version: "0.1.0" },
      { status: "ok", checks: { database: "ok", redis: "ok", object_storage: "ok" } },
    );

    expect(presentation.kind).toBe("ready");
    expect(presentation.title).toBe("服务已准备就绪");
  });

  it("turns an unavailable readiness response into a degraded state", () => {
    const presentation = toStatusPresentation(
      { name: "GradMatch", environment: "development", version: "0.1.0" },
      { status: "error", checks: { database: "ok", redis: "error", object_storage: "ok" } },
    );

    expect(presentation.kind).toBe("degraded");
    render(<StatusPanel presentation={presentation} />);
    expect(screen.getByText("服务暂未完全就绪")).toBeInTheDocument();
    expect(screen.queryByText("redis")).not.toBeInTheDocument();
  });
});

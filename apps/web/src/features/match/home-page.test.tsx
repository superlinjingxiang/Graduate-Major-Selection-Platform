import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../../app/page";

describe("pilot home entry", () => {
  it("presents the data-first discovery entry without exposing internal status copy", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { name: "把分散的招生信息，变成清晰的选择。" }),
    ).toBeVisible();
    expect(screen.getByRole("searchbox", { name: "搜索院校、专业或专业代码" })).toBeVisible();
    expect(screen.getByText("343 万")).toBeVisible();
    expect(screen.getByText("演示结构数据")).toBeVisible();
    expect(
      screen.queryByText(/平台状态|development|2027 北京全日制计算机统考/u),
    ).not.toBeInTheDocument();
  });

  it("binds each registration year to its own visible official source", () => {
    render(<HomePage />);

    expect(screen.getByRole("link", { name: "2025 年报名人数来源（教育部）" })).toHaveAttribute(
      "href",
      "https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/moe_1485/202411/t20241121_1163982.html",
    );
    expect(screen.getByRole("link", { name: "2026 年报名人数来源（教育部）" })).toHaveAttribute(
      "href",
      "https://www.moe.gov.cn/jyb_xwfb/gzdt_gzdt/moe_1485/202511/t20251124_1421370.html",
    );
  });
});

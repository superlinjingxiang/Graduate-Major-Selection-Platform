import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../../app/page";

describe("pilot home entry", () => {
  it("leads directly to the pilot flow without exposing internal status copy", () => {
    render(<HomePage />);

    expect(screen.getByRole("link", { name: "开始资格核对" })).toHaveAttribute("href", "/match");
    expect(screen.getByText("2027 北京全日制计算机统考")).toBeInTheDocument();
    expect(screen.queryByText(/平台状态|development|v0\.1|基础设施/u)).not.toBeInTheDocument();
  });
});

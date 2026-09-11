import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const navigationState = { pathname: "/programs/bnu-applied-psychology-045400" };

vi.mock("next/navigation", () => ({
  usePathname: () => navigationState.pathname,
}));

import { CompareAction } from "./compare-action";
import { CompareProvider } from "./compare-provider";
import { CompareTray } from "./compare-tray";
import { ComparisonView } from "./comparison-view";

describe("guest comparison experience", () => {
  beforeEach(() => {
    localStorage.clear();
    navigationState.pathname = "/programs/bnu-applied-psychology-045400";
  });

  it("adds a program and exposes the comparison tray", async () => {
    const user = userEvent.setup();
    render(
      <CompareProvider>
        <CompareAction programSlug="bnu-applied-psychology-045400" />
        <CompareTray />
      </CompareProvider>,
    );

    await user.click(screen.getByRole("button", { name: "加入对比" }));

    expect(screen.getByRole("button", { name: "移出对比" })).toBeVisible();
    expect(screen.getByText("已选择 1 个项目")).toBeVisible();
    expect(screen.getByRole("link", { name: "查看对比" })).toHaveAttribute("href", "/compare");
  });

  it("renders selected projects as a table and gates cloud saving behind login", async () => {
    localStorage.setItem(
      "gradmatch.demo.compare",
      JSON.stringify(["bnu-applied-psychology-045400", "sufe-finance-025100"]),
    );
    render(
      <CompareProvider>
        <ComparisonView />
      </CompareProvider>,
    );

    const table = await screen.findByRole("table", { name: "项目对比" });
    expect(within(table).getByText("应用心理")).toBeVisible();
    expect(within(table).getByText("金融")).toBeVisible();
    expect(screen.getByRole("link", { name: "保存这组对比" })).toHaveAttribute(
      "href",
      "/account/login?next=/compare&intent=save",
    );
  });

  it("shows a useful empty state when no project is selected", async () => {
    render(
      <CompareProvider>
        <ComparisonView />
      </CompareProvider>,
    );

    await waitFor(() => expect(screen.getByText("还没有选择对比项目")).toBeVisible());
    expect(screen.getByRole("link", { name: "去搜索项目" })).toHaveAttribute("href", "/search");
  });

  it("hides the global tray while the comparison table is open", async () => {
    navigationState.pathname = "/compare";
    localStorage.setItem(
      "gradmatch.demo.compare",
      JSON.stringify(["bnu-applied-psychology-045400"]),
    );
    render(
      <CompareProvider>
        <CompareTray />
      </CompareProvider>,
    );

    await waitFor(() => expect(screen.queryByLabelText("临时对比")).not.toBeInTheDocument());
  });
});

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { demoPrograms } from "../../lib/demo-catalog";
import { SearchExplorer } from "./search-explorer";

describe("SearchExplorer", () => {
  it("searches by program name and exposes only matching results", async () => {
    const user = userEvent.setup();
    render(<SearchExplorer initialQuery="" programs={demoPrograms} />);

    await user.type(screen.getByRole("searchbox", { name: "搜索院校、专业或专业代码" }), "法律");

    expect(screen.getByText("法律（非法学）")).toBeVisible();
    expect(screen.queryByText("应用心理")).not.toBeInTheDocument();
  });

  it("filters real non-empty results by region and degree type", async () => {
    const user = userEvent.setup();
    render(<SearchExplorer initialQuery="" programs={demoPrograms} />);

    await user.selectOptions(screen.getByLabelText("地区"), "上海");
    await user.selectOptions(screen.getByLabelText("学位类型"), "academic");

    const cards = screen.getAllByTestId("program-card");
    expect(cards).toHaveLength(1);
    const card = cards[0];
    if (!card) throw new Error("Expected one matching program card");
    expect(within(card).getByText("复旦大学")).toBeVisible();
    expect(within(card).getByText("学术学位")).toBeVisible();
  });

  it("supports an initial code query from the homepage", () => {
    render(<SearchExplorer initialQuery="045400" programs={demoPrograms} />);

    expect(screen.getByText("应用心理")).toBeVisible();
    expect(screen.getByRole("searchbox")).toHaveValue("045400");
  });

  it("shows a recoverable empty state and clears every filter", async () => {
    const user = userEvent.setup();
    render(<SearchExplorer initialQuery="不存在的专业" programs={demoPrograms} />);

    const emptyHeading = screen.getByText("暂未找到匹配项目");
    expect(emptyHeading).toBeVisible();
    const emptyState = emptyHeading.closest("div");
    if (!emptyState) throw new Error("Expected an empty-state container");
    await user.click(within(emptyState).getByRole("button", { name: "清除筛选" }));

    expect(screen.getAllByTestId("program-card")).toHaveLength(demoPrograms.length);
    expect(screen.getByRole("searchbox")).toHaveValue("");
  });
});

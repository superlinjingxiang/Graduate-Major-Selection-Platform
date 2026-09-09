import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { demoPrograms } from "../../lib/demo-catalog";
import { CatalogSearch } from "./catalog-search";

describe("CatalogSearch", () => {
  it("links a matching program suggestion to its detail page", async () => {
    const user = userEvent.setup();
    render(<CatalogSearch programs={demoPrograms} />);

    await user.type(screen.getByRole("searchbox"), "045400");

    expect(screen.getByRole("link", { name: /北京师范大学.*应用心理/u })).toHaveAttribute(
      "href",
      "/programs/bnu-applied-psychology-045400",
    );
  });

  it("submits the query through the unified search route", () => {
    render(<CatalogSearch programs={demoPrograms} />);

    const searchbox = screen.getByRole("searchbox", { name: "搜索院校、专业或专业代码" });
    expect(searchbox).toHaveAttribute("name", "q");
    expect(searchbox.closest("form")).toHaveAttribute("action", "/search");
    expect(searchbox.closest("form")).toHaveAttribute("method", "get");
  });

  it("closes visible suggestions when Escape is pressed", async () => {
    const user = userEvent.setup();
    render(<CatalogSearch programs={demoPrograms} />);

    const searchbox = screen.getByRole("searchbox");
    await user.type(searchbox, "045400");
    expect(screen.getByRole("link", { name: /北京师范大学.*应用心理/u })).toBeVisible();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("link", { name: /北京师范大学.*应用心理/u })).not.toBeInTheDocument();
  });

  it("limits a broad query to six suggestions", async () => {
    const user = userEvent.setup();
    const financeProgram = demoPrograms.find((program) => program.title === "金融");
    if (!financeProgram) throw new Error("The finance demo fixture is required for this test.");
    const programs = Array.from({ length: 7 }, (_, index) => ({
      ...financeProgram,
      slug: `finance-${index}`,
    }));
    render(<CatalogSearch programs={programs} />);

    await user.type(screen.getByRole("searchbox"), "金融");

    expect(screen.getAllByRole("link")).toHaveLength(6);
  });
});

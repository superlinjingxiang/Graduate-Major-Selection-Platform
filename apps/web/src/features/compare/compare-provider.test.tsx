import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { CompareProvider, useCompare } from "./compare-provider";

function CompareProbe() {
  const compare = useCompare();
  return (
    <div>
      <output aria-label="已选项目">{compare.slugs.join(",")}</output>
      <output aria-label="是否已满">{String(compare.isFull)}</output>
      {[
        "sufe-finance-025100",
        "cupl-juris-master-035101",
        "bnu-applied-psychology-045400",
        "bupt-computer-science-081200",
      ].map((slug) => (
        <button key={slug} onClick={() => compare.toggle(slug)} type="button">
          {slug}
        </button>
      ))}
      <button onClick={compare.clear} type="button">
        清空
      </button>
    </div>
  );
}

describe("CompareProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("persists at most three unique comparison slugs", async () => {
    const user = userEvent.setup();
    render(
      <CompareProvider>
        <CompareProbe />
      </CompareProvider>,
    );

    await user.click(screen.getByRole("button", { name: "sufe-finance-025100" }));
    await user.click(screen.getByRole("button", { name: "cupl-juris-master-035101" }));
    await user.click(screen.getByRole("button", { name: "bnu-applied-psychology-045400" }));
    await user.click(screen.getByRole("button", { name: "bupt-computer-science-081200" }));

    expect(screen.getByLabelText("已选项目")).toHaveTextContent(
      "sufe-finance-025100,cupl-juris-master-035101,bnu-applied-psychology-045400",
    );
    expect(screen.getByLabelText("是否已满")).toHaveTextContent("true");
    expect(localStorage.getItem("gradmatch.demo.compare")).toBe(
      '["sufe-finance-025100","cupl-juris-master-035101","bnu-applied-psychology-045400"]',
    );
  });

  it("removes an already selected item and can clear the comparison", async () => {
    const user = userEvent.setup();
    render(
      <CompareProvider>
        <CompareProbe />
      </CompareProvider>,
    );

    await user.click(screen.getByRole("button", { name: "sufe-finance-025100" }));
    await user.click(screen.getByRole("button", { name: "cupl-juris-master-035101" }));
    await user.click(screen.getByRole("button", { name: "sufe-finance-025100" }));
    expect(screen.getByLabelText("已选项目")).toHaveTextContent("cupl-juris-master-035101");

    await user.click(screen.getByRole("button", { name: "清空" }));
    expect(screen.getByLabelText("已选项目")).toBeEmptyDOMElement();
    expect(localStorage.getItem("gradmatch.demo.compare")).toBe("[]");
  });

  it("restores only valid unique strings from storage", async () => {
    localStorage.setItem(
      "gradmatch.demo.compare",
      JSON.stringify(["sufe-finance-025100", 9, "sufe-finance-025100", "cupl-juris-master-035101"]),
    );

    render(
      <CompareProvider>
        <CompareProbe />
      </CompareProvider>,
    );

    await waitFor(() =>
      expect(screen.getByLabelText("已选项目")).toHaveTextContent(
        "sufe-finance-025100,cupl-juris-master-035101",
      ),
    );
  });
});

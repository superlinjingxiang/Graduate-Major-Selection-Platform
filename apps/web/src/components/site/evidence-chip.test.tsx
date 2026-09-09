import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvidenceChip } from "./evidence-chip";

describe("EvidenceChip", () => {
  it.each([
    ["demo", "演示数据"],
    ["pending", "待发布"],
    ["conflict", "来源冲突"],
  ] as const)("renders visible text for the %s evidence state", (state, label) => {
    render(<EvidenceChip state={state} />);

    expect(screen.getByText(label)).toBeVisible();
  });
});

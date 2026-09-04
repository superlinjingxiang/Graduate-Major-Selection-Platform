import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DecisionSummary } from "./decision-summary";

const snapshot = {
  snapshot_id: "839585c6-d9ed-44e3-8e5a-284c51fc22fa",
  comparison_run_id: "d50b61bc-a118-4be4-a0b5-e9515ed54775",
  comparison_result_version: 1,
  comparison_result_hash: "a".repeat(64),
  outcome: "awaiting_official_information" as const,
  retained: [],
  excluded: [],
  deferred: [
    "ao_2027_bupt_081200_ft_unified_plan01",
    "ao_2027_bit_085404_ft_unified_plan01",
    "ao_2027_bjut_085410_ft_unified_plan01",
  ],
  user_confirmed_reasons: [],
  key_unknowns: ["rule_unpublished"],
  next_actions: ["等待并复核 2027 官方招生信息"],
  revisit_date: null,
  snapshot_hash: "b".repeat(64),
  created_at: "2026-09-02T00:00:00Z",
};

const offerings = [
  {
    id: "ao_2027_bupt_081200_ft_unified_plan01",
    institution_name: "北京邮电大学",
    program_code: "081200",
    title: "计算机科学与技术",
    publication_status: "pending_publication",
  },
  {
    id: "ao_2027_bit_085404_ft_unified_plan01",
    institution_name: "北京理工大学",
    program_code: "085404",
    title: "计算机技术",
    publication_status: "pending_publication",
  },
  {
    id: "ao_2027_bjut_085410_ft_unified_plan01",
    institution_name: "北京工业大学",
    program_code: "085410",
    title: "人工智能",
    publication_status: "pending_publication",
  },
];

describe("decision summary", () => {
  it("explains the current uncertainty without ranking or acceptance claims", () => {
    render(<DecisionSummary offerings={offerings} snapshot={snapshot} />);

    expect(screen.getByRole("heading", { name: "等待 2027 官方信息" })).toBeInTheDocument();
    expect(screen.getByText("2027 年官方资格规则尚未发布")).toBeInTheDocument();
    expect(screen.getByText("等待并复核 2027 官方招生信息")).toBeInTheDocument();
    expect(screen.getByText("北京邮电大学 · 081200 计算机科学与技术")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提交信息纠错" })).toBeInTheDocument();
    expect(screen.queryByText(/概率|排名|推荐分|录取把握/u)).not.toBeInTheDocument();
    expect(screen.queryByText(/development|v0\.1|平台状态/u)).not.toBeInTheDocument();
  });
});

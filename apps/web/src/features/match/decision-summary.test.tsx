import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const transport = vi.hoisted(() => ({ POST: vi.fn() }));

vi.mock("../../lib/api-client", () => ({ browserCoreClient: transport }));

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
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  it.each([
    ["shortlist_ready", "可以开始核对候选清单"],
    ["no_suitable_offering", "当前范围内没有可继续的项目"],
    ["awaiting_official_information", "等待 2027 官方信息"],
    ["postpone_application", "暂缓本轮申请准备"],
  ] as const)("renders the %s outcome without turning it into a ranking", (outcome, title) => {
    const publishedOfferings = offerings.map((offering) => ({
      ...offering,
      publication_status: "published",
    }));
    render(<DecisionSummary offerings={publishedOfferings} snapshot={{ ...snapshot, outcome }} />);

    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.queryByText(/概率|排名|推荐分|录取把握/u)).not.toBeInTheDocument();
  });

  it("opens a usable correction form and submits the generated request shape", async () => {
    transport.POST.mockResolvedValue({
      data: {
        correction_id: "32e89961-aae0-42f9-a121-aa817c42557e",
        explanation: "学校官网的招生说明与当前展示的信息不一致。",
        field_key: "eligibility.requirements",
        offering_id: offerings[0]?.id,
        proposed_source_url: "https://yzb.example.edu/2027/rules",
        status: "submitted",
      },
      response: new Response(null, { status: 201 }),
    });
    const user = userEvent.setup();
    render(<DecisionSummary offerings={offerings} snapshot={snapshot} />);

    await user.click(screen.getByRole("button", { name: "提交信息纠错" }));
    await user.selectOptions(screen.getByLabelText("需要纠错的项目"), offerings[0]?.id ?? "");
    await user.selectOptions(screen.getByLabelText("需要纠错的信息"), "eligibility.requirements");
    await user.type(screen.getByLabelText("官方来源链接"), "https://yzb.example.edu/2027/rules");
    await user.type(
      screen.getByLabelText("情况说明"),
      "学校官网的招生说明与当前展示的信息不一致。",
    );
    await user.click(screen.getByRole("button", { name: "确认提交纠错" }));

    expect(await screen.findByText("纠错已提交，我们会依据官方来源复核。")).toBeInTheDocument();
    expect(transport.POST).toHaveBeenCalledWith("/api/v1/corrections", {
      body: {
        explanation: "学校官网的招生说明与当前展示的信息不一致。",
        field_key: "eligibility.requirements",
        offering_id: offerings[0]?.id,
        proposed_source_url: "https://yzb.example.edu/2027/rules",
      },
    });
  });

  it("announces a correction network failure and allows another attempt", async () => {
    transport.POST.mockRejectedValue(new Error("network unavailable"));
    const user = userEvent.setup();
    render(<DecisionSummary offerings={offerings} snapshot={snapshot} />);

    await user.click(screen.getByRole("button", { name: "提交信息纠错" }));
    await user.selectOptions(screen.getByLabelText("需要纠错的项目"), offerings[0]?.id ?? "");
    await user.selectOptions(screen.getByLabelText("需要纠错的信息"), "eligibility.requirements");
    await user.type(screen.getByLabelText("官方来源链接"), "https://yzb.example.edu/2027/rules");
    await user.type(screen.getByLabelText("情况说明"), "学校官网信息需要重新核对。 ");
    await user.click(screen.getByRole("button", { name: "确认提交纠错" }));

    expect(await screen.findByText("纠错暂未提交，请稍后重试。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认提交纠错" })).toBeEnabled();
  });
});

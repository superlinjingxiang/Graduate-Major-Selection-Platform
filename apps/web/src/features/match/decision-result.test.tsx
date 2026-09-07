import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const transport = vi.hoisted(() => ({ GET: vi.fn(), POST: vi.fn() }));

vi.mock("../../lib/api-client", () => ({ browserCoreClient: transport }));

import { DecisionResult } from "./decision-result";

const snapshotId = "839585c6-d9ed-44e3-8e5a-284c51fc22fa";
const snapshot = {
  snapshot_id: snapshotId,
  comparison_run_id: "d50b61bc-a118-4be4-a0b5-e9515ed54775",
  comparison_result_version: 1,
  comparison_result_hash: "a".repeat(64),
  outcome: "awaiting_official_information",
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
  updates: [],
};
const offerings = [
  {
    id: "ao_2027_bupt_081200_ft_unified_plan01",
    institution_name: "北京邮电大学",
    program_code: "081200",
    publication_status: "pending_publication",
    title: "计算机科学与技术",
  },
  {
    id: "ao_2027_bit_085404_ft_unified_plan01",
    institution_name: "北京理工大学",
    program_code: "085404",
    publication_status: "pending_publication",
    title: "计算机技术",
  },
  {
    id: "ao_2027_bjut_085410_ft_unified_plan01",
    institution_name: "北京工业大学",
    program_code: "085410",
    publication_status: "pending_publication",
    title: "人工智能",
  },
];

function renderResult() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <DecisionResult offerings={offerings} snapshotId={snapshotId} />
    </QueryClientProvider>,
  );
}

describe("decision result", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads the protected snapshot in the browser with the path-scoped capability", async () => {
    transport.GET.mockResolvedValue({
      data: snapshot,
      response: new Response(null, { status: 200 }),
    });

    renderResult();

    expect(screen.getByText("正在读取资格快照…")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "等待 2027 官方信息" })).toBeInTheDocument();
    expect(transport.GET).toHaveBeenCalledWith("/api/v1/decision-snapshots/{snapshot_id}", {
      params: { path: { snapshot_id: snapshotId } },
    });
    expect(screen.queryByText(snapshotId)).not.toBeInTheDocument();
    expect(screen.queryByText(snapshot.snapshot_hash)).not.toBeInTheDocument();
  });

  it("shows a safe recovery message when the snapshot is unavailable", async () => {
    transport.GET.mockResolvedValue({
      error: { detail: "Decision snapshot not found." },
      response: new Response(null, { status: 404 }),
    });

    renderResult();

    expect(
      await screen.findByRole("heading", { name: "无法读取这份资格快照" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "重新填写信息" })).toHaveAttribute("href", "/match");
    expect(screen.queryByText(/Decision snapshot|404|capability|token/u)).not.toBeInTheDocument();
  });

  it.each([
    [
      "a non-awaiting outcome",
      { outcome: "shortlist_ready", retained: [], excluded: [], deferred: snapshot.deferred },
    ],
    [
      "a snapshot that does not defer every pending offering",
      {
        outcome: "awaiting_official_information",
        retained: [offerings[0]?.id],
        excluded: [],
        deferred: snapshot.deferred.slice(1),
      },
    ],
  ])("rejects %s at the pending pilot boundary", async (_case, invalidState) => {
    transport.GET.mockResolvedValue({
      data: { ...snapshot, ...invalidState },
      response: new Response(null, { status: 200 }),
    });

    renderResult();

    expect(
      await screen.findByRole("heading", { name: "无法读取这份资格快照" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "可以开始核对候选清单" })).not.toBeInTheDocument();
    expect(screen.queryByText("资格状态：符合已确认条件")).not.toBeInTheDocument();
  });
});

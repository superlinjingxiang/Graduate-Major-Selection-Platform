import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const loadPilotData = vi.hoisted(() => vi.fn());

vi.mock("../../lib/pilot-api", () => ({ loadPilotData }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import MatchPage from "../../app/match/page";

const scope = {
  key: "coverage_2027_beijing_cs_ft_unified_v1" as const,
  version: 1,
  target_year: 2027 as const,
  region: "北京" as const,
  study_mode: "full_time" as const,
  admission_pathway: "unified_exam" as const,
  discipline: "computer_related" as const,
  decision_stage: "shortlist_convergence" as const,
  offering_count: 10 as const,
  frozen_at: "2026-09-02T00:00:00Z",
};

const offerings = [
  {
    id: "ao_2027_bupt_081200_ft_unified_plan01",
    target_year: 2027,
    institution_key: "bupt",
    institution_name: "北京邮电大学",
    program_code: "081200",
    title: "计算机科学与技术",
    degree_type: "academic",
    study_mode: "full_time",
    admission_pathway: "unified_exam",
    publication_status: "pending_publication",
  },
  {
    id: "ao_2027_bit_085404_ft_unified_plan01",
    target_year: 2027,
    institution_key: "bit",
    institution_name: "北京理工大学",
    program_code: "085404",
    title: "计算机技术",
    degree_type: "professional",
    study_mode: "full_time",
    admission_pathway: "unified_exam",
    publication_status: "pending_publication",
  },
  {
    id: "ao_2027_bjut_085410_ft_unified_plan01",
    target_year: 2027,
    institution_key: "bjut",
    institution_name: "北京工业大学",
    program_code: "085410",
    title: "人工智能",
    degree_type: "professional",
    study_mode: "full_time",
    admission_pathway: "unified_exam",
    publication_status: "pending_publication",
  },
];

describe("match page", () => {
  it("renders the server-loaded frozen pilot without infrastructure details", async () => {
    loadPilotData.mockResolvedValue({ offerings, scope });
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
    });

    render(<QueryClientProvider client={queryClient}>{await MatchPage()}</QueryClientProvider>);

    expect(screen.getByRole("heading", { name: "先确认范围，再判断资格" })).toBeInTheDocument();
    expect(screen.getByText("北京邮电大学")).toBeInTheDocument();
    expect(screen.getByText("北京理工大学")).toBeInTheDocument();
    expect(screen.getByText("北京工业大学")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "生成资格快照" })).toBeInTheDocument();
    expect(screen.queryByText("平台状态")).not.toBeInTheDocument();
    expect(screen.queryByText("development")).not.toBeInTheDocument();
    expect(screen.queryByText(/v0\.1/u)).not.toBeInTheDocument();
  });
});

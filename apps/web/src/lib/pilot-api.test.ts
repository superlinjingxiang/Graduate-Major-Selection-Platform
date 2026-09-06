import { beforeEach, describe, expect, it, vi } from "vitest";

const transport = vi.hoisted(() => ({ GET: vi.fn() }));

vi.mock("./api-client", () => ({ serverCoreClient: transport }));

import { ENGINEERING_SLICE_OFFERING_IDS, loadPilotData } from "./pilot-api";

const scope = {
  admission_pathway: "unified_exam",
  decision_stage: "shortlist_convergence",
  discipline: "computer_related",
  frozen_at: "2026-09-02T00:00:00Z",
  key: "coverage_2027_beijing_cs_ft_unified_v1",
  offering_count: 10,
  region: "北京",
  study_mode: "full_time",
  target_year: 2027,
  version: 1,
};

const engineeringOfferings = [
  [
    "ao_2027_bupt_081200_ft_unified_plan01",
    "bupt",
    "北京邮电大学",
    "081200",
    "计算机科学与技术",
    "academic",
  ],
  [
    "ao_2027_bit_085404_ft_unified_plan01",
    "bit",
    "北京理工大学",
    "085404",
    "计算机技术",
    "professional",
  ],
  [
    "ao_2027_bjut_085410_ft_unified_plan01",
    "bjut",
    "北京工业大学",
    "085410",
    "人工智能",
    "professional",
  ],
].map(([id, institution_key, institution_name, program_code, title, degree_type]) => ({
  admission_pathway: "unified_exam",
  degree_type,
  id,
  institution_key,
  institution_name,
  program_code,
  publication_status: "pending_publication",
  study_mode: "full_time",
  target_year: 2027,
  title,
}));

describe("pilot API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns only the three frozen engineering offerings in their canonical order", async () => {
    transport.GET.mockResolvedValueOnce({ data: scope }).mockResolvedValueOnce({
      data: {
        count: 4,
        items: [
          {
            ...engineeringOfferings[0],
            id: "ao_2027_bupt_085404_ft_unified_plan01",
            program_code: "085404",
            title: "非工程链路项目",
          },
          ...engineeringOfferings.slice().reverse(),
        ],
        manifest_key: scope.key,
      },
    });

    const result = await loadPilotData();

    expect(result.scope).toEqual(scope);
    expect(result.offerings.map(({ id }) => id)).toEqual([...ENGINEERING_SLICE_OFFERING_IDS]);
  });

  it("rejects catalog data that does not match the frozen public scope", async () => {
    transport.GET.mockResolvedValueOnce({
      data: { ...scope, target_year: 2026 },
    }).mockResolvedValueOnce({
      data: { count: 3, items: engineeringOfferings, manifest_key: scope.key },
    });

    await expect(loadPilotData()).rejects.toThrow();
  });
});

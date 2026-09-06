import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const transport = vi.hoisted(() => ({ POST: vi.fn() }));
const push = vi.hoisted(() => vi.fn());

vi.mock("../../lib/api-client", () => ({ browserCoreClient: transport }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { FactForm } from "./fact-form";

const offeringIds = [
  "ao_2027_bupt_081200_ft_unified_plan01",
  "ao_2027_bit_085404_ft_unified_plan01",
  "ao_2027_bjut_085410_ft_unified_plan01",
] as const;

function renderForm() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <FactForm offeringIds={offeringIds} />
    </QueryClientProvider>,
  );
}

describe("fact form", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("requires an explicit scope confirmation before sending data", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "生成资格快照" }));

    expect(await screen.findByText("请先确认报考范围")).toBeInTheDocument();
    expect(transport.POST).not.toHaveBeenCalled();
  });

  it("creates facts, three assessments, a comparison and a snapshot in order", async () => {
    transport.POST.mockImplementation((path: string) => {
      if (path === "/api/v1/fact-sets") {
        return Promise.resolve({
          data: {
            fact_set_id: "56d1aa4c-a22e-46c5-b69d-3228f408a92a",
            version: 1,
            confirmed_facts: {},
            input_hash: "a".repeat(64),
          },
        });
      }
      if (path === "/api/v1/eligibility-assessments") {
        return Promise.resolve({ data: { status: "needs_confirmation" } });
      }
      if (path === "/api/v1/comparison-runs") {
        return Promise.resolve({
          data: {
            comparison_run_id: "d50b61bc-a118-4be4-a0b5-e9515ed54775",
          },
        });
      }
      if (path === "/api/v1/decision-snapshots") {
        return Promise.resolve({
          data: { snapshot_id: "839585c6-d9ed-44e3-8e5a-284c51fc22fa" },
        });
      }
      return Promise.resolve({ error: { detail: "unexpected path" } });
    });
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByLabelText("我确认以上报考范围"));
    await user.selectOptions(screen.getByLabelText("当前学历情况（可选）"), "bachelor");
    await user.type(screen.getByLabelText("本科专业（可选）"), "软件工程");
    await user.click(screen.getByRole("button", { name: "生成资格快照" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/match/result/839585c6-d9ed-44e3-8e5a-284c51fc22fa"),
    );
    expect(transport.POST.mock.calls.map(([path]) => path)).toEqual([
      "/api/v1/fact-sets",
      "/api/v1/eligibility-assessments",
      "/api/v1/eligibility-assessments",
      "/api/v1/eligibility-assessments",
      "/api/v1/comparison-runs",
      "/api/v1/decision-snapshots",
    ]);
    expect(transport.POST).toHaveBeenNthCalledWith(1, "/api/v1/fact-sets", {
      body: {
        confirmed_facts: {
          admission_pathway: "unified_exam",
          education_level: "bachelor",
          region: "北京",
          study_mode: "full_time",
          target_year: 2027,
          undergraduate_major: "软件工程",
        },
      },
    });
    for (const [index, offeringId] of offeringIds.entries()) {
      expect(transport.POST).toHaveBeenNthCalledWith(index + 2, "/api/v1/eligibility-assessments", {
        body: {
          fact_revision: 1,
          fact_set_id: "56d1aa4c-a22e-46c5-b69d-3228f408a92a",
          offering_id: offeringId,
        },
      });
    }
    expect(transport.POST).toHaveBeenNthCalledWith(5, "/api/v1/comparison-runs", {
      body: {
        fact_revision: 1,
        fact_set_id: "56d1aa4c-a22e-46c5-b69d-3228f408a92a",
        offering_ids: [...offeringIds],
      },
    });
    expect(transport.POST).toHaveBeenNthCalledWith(6, "/api/v1/decision-snapshots", {
      body: { comparison_run_id: "d50b61bc-a118-4be4-a0b5-e9515ed54775" },
    });
  });

  it("keeps the user on the form and announces an API failure", async () => {
    transport.POST.mockResolvedValue({
      error: { detail: "service unavailable" },
      response: new Response(null, { status: 503 }),
    });
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByLabelText("我确认以上报考范围"));
    await user.click(screen.getByRole("button", { name: "生成资格快照" }));

    expect(await screen.findByText("暂时无法生成资格快照，请稍后重试。")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});

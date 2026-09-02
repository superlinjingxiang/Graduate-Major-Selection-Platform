import { describe, expect, it } from "vitest";

import { pilotScopeSchema } from "../src/pilot.js";

const validPilotScope = {
  key: "coverage_2027_beijing_cs_ft_unified_v1",
  version: 1,
  target_year: 2027,
  region: "北京",
  study_mode: "full_time",
  admission_pathway: "unified_exam",
  discipline: "computer_related",
  decision_stage: "shortlist_convergence",
  offering_count: 10,
  frozen_at: "2026-09-02T00:00:00Z",
};

describe("pilot scope contract", () => {
  it("parses the frozen public 2027 pilot scope", () => {
    expect(pilotScopeSchema.parse(validPilotScope)).toEqual(validPilotScope);
  });

  it("rejects a scope outside the production pilot", () => {
    expect(
      pilotScopeSchema.safeParse({
        ...validPilotScope,
        target_year: 2026,
      }).success,
    ).toBe(false);
  });

  it("rejects internal or fixture fields instead of silently stripping them", () => {
    expect(
      pilotScopeSchema.safeParse({
        ...validPilotScope,
        environment: "development",
        reference_year: 2026,
        namespace: "test_fixture",
      }).success,
    ).toBe(false);
  });
});

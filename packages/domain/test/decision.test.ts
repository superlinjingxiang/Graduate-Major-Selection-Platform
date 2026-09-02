import { describe, expect, it } from "vitest";

import {
  decisionOutcomeSchema,
  decisionSnapshotSchema,
  eligibilityStatusSchema,
  publicReasonCopy,
} from "../src/decision.js";

describe("decision contracts", () => {
  it("accepts exactly the eligibility three-state model", () => {
    expect(eligibilityStatusSchema.parse("eligible_known")).toBe("eligible_known");
    expect(eligibilityStatusSchema.parse("ineligible_known")).toBe("ineligible_known");
    expect(eligibilityStatusSchema.parse("needs_confirmation")).toBe("needs_confirmation");
    expect(eligibilityStatusSchema.safeParse("recommended").success).toBe(false);
  });

  it("accepts exactly the four decision outcomes", () => {
    for (const outcome of [
      "shortlist_ready",
      "no_suitable_offering",
      "awaiting_official_information",
      "postpone_application",
    ]) {
      expect(decisionOutcomeSchema.safeParse(outcome).success).toBe(true);
    }
    expect(decisionOutcomeSchema.safeParse("high_probability").success).toBe(false);
  });

  it("parses a public snapshot and rejects internal review data", () => {
    const snapshot = {
      snapshot_id: "71e5d27d-1f8a-45bc-a99d-a07005f53dd9",
      comparison_run_id: "94865ae0-bb5a-44d5-9b53-a351f0812ba5",
      comparison_result_version: 1,
      comparison_result_hash: "a".repeat(64),
      outcome: "awaiting_official_information",
      retained: [],
      excluded: [],
      deferred: ["ao_2027_bupt_081200_ft_unified_plan01"],
      user_confirmed_reasons: [],
      key_unknowns: ["rule_unpublished"],
      next_actions: ["等待并复核 2027 官方招生信息"],
      revisit_date: null,
      snapshot_hash: "b".repeat(64),
      created_at: "2026-09-02T00:00:00Z",
    };

    expect(decisionSnapshotSchema.parse(snapshot)).toEqual(snapshot);
    expect(
      decisionSnapshotSchema.safeParse({
        ...snapshot,
        reviewer_note: "internal only",
      }).success,
    ).toBe(false);
  });

  it("maps uncertainty reasons to stable, non-promissory Chinese copy", () => {
    expect(publicReasonCopy("rule_unpublished")).toBe("2027 年官方资格规则尚未发布");
    expect(publicReasonCopy("rule_set_incomplete")).toContain("仍需复核");
    expect(publicReasonCopy("user_fact_missing")).toContain("需要你确认");
    expect(publicReasonCopy("rule_unpublished")).not.toContain("录取");
    expect(publicReasonCopy("rule_unpublished")).not.toContain("推荐");
  });
});

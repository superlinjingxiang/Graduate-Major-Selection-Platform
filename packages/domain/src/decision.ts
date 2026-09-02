import type { CoreComponents } from "@gradmatch/api-client";
import { z } from "zod";

type EligibilityAssessmentResponse = CoreComponents["schemas"]["EligibilityAssessmentResponse"];
type DecisionSnapshotResponse = CoreComponents["schemas"]["DecisionSnapshotResponse"];

export const eligibilityStatusSchema = z.enum([
  "eligible_known",
  "ineligible_known",
  "needs_confirmation",
]);

export const decisionOutcomeSchema = z.enum([
  "shortlist_ready",
  "no_suitable_offering",
  "awaiting_official_information",
  "postpone_application",
]);

export const eligibilityReasonSchema = z
  .object({
    code: z.string().min(1),
    fact_key: z.string().min(1).nullable(),
    rule_key: z.string().min(1).nullable(),
  })
  .strict();

export const eligibilityAssessmentSchema = z
  .object({
    assessment_id: z.number().int().positive(),
    offering_id: z.string().min(1),
    fact_set_id: z.uuid(),
    fact_revision: z.number().int().positive(),
    rule_set_key: z.string().min(1).nullable(),
    rule_set_revision: z.number().int().positive().nullable(),
    status: eligibilityStatusSchema,
    reasons: z.array(eligibilityReasonSchema),
    input_hash: z.string().regex(/^[a-f0-9]{64}$/u),
  })
  .strict() satisfies z.ZodType<EligibilityAssessmentResponse>;

export const decisionSnapshotSchema = z
  .object({
    snapshot_id: z.uuid(),
    comparison_run_id: z.uuid(),
    comparison_result_version: z.number().int().positive(),
    comparison_result_hash: z.string().regex(/^[a-f0-9]{64}$/u),
    outcome: decisionOutcomeSchema,
    retained: z.array(z.string().min(1)),
    excluded: z.array(z.string().min(1)),
    deferred: z.array(z.string().min(1)),
    user_confirmed_reasons: z.array(z.string().min(1)),
    key_unknowns: z.array(z.string().min(1)),
    next_actions: z.array(z.string().min(1)),
    revisit_date: z.iso.date().nullable(),
    snapshot_hash: z.string().regex(/^[a-f0-9]{64}$/u),
    created_at: z.iso.datetime(),
  })
  .strict() satisfies z.ZodType<DecisionSnapshotResponse>;

export type EligibilityStatus = z.infer<typeof eligibilityStatusSchema>;
export type DecisionOutcome = z.infer<typeof decisionOutcomeSchema>;
export type EligibilityAssessment = z.infer<typeof eligibilityAssessmentSchema>;
export type DecisionSnapshot = z.infer<typeof decisionSnapshotSchema>;

const PUBLIC_REASON_COPY = {
  rule_unpublished: "2027 年官方资格规则尚未发布",
  rule_set_incomplete: "当前资格规则仍需复核，请等待官方信息补齐",
  user_fact_missing: "需要你确认一项会影响报考资格的个人信息",
} as const;

export function publicReasonCopy(code: string): string {
  if (code in PUBLIC_REASON_COPY) {
    return PUBLIC_REASON_COPY[code as keyof typeof PUBLIC_REASON_COPY];
  }
  return "存在一项需要人工复核的资格条件";
}

import type { CoreComponents } from "@gradmatch/api-client";
import { z } from "zod";

type PilotScopeResponse = CoreComponents["schemas"]["PilotScopeResponse"];

export const pilotScopeSchema = z
  .object({
    key: z.literal("coverage_2027_beijing_cs_ft_unified_v1"),
    version: z.number().int().positive(),
    target_year: z.literal(2027),
    region: z.literal("北京"),
    study_mode: z.literal("full_time"),
    admission_pathway: z.literal("unified_exam"),
    discipline: z.literal("computer_related"),
    decision_stage: z.literal("shortlist_convergence"),
    offering_count: z.literal(10),
    frozen_at: z.iso.datetime(),
  })
  .strict() satisfies z.ZodType<PilotScopeResponse>;

export type PilotScope = z.infer<typeof pilotScopeSchema>;

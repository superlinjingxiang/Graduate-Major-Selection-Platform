import type { CoreComponents } from "@gradmatch/api-client/core-client";
import { type PilotScope, pilotScopeSchema } from "@gradmatch/domain/pilot";

import { serverCoreClient } from "./api-client";

type Offering = CoreComponents["schemas"]["OfferingResponse"];

export type PilotOffering = Pick<
  Offering,
  "id" | "institution_name" | "program_code" | "publication_status" | "title"
>;

export const ENGINEERING_SLICE_OFFERING_IDS = [
  "ao_2027_bupt_081200_ft_unified_plan01",
  "ao_2027_bit_085404_ft_unified_plan01",
  "ao_2027_bjut_085410_ft_unified_plan01",
] as const;

export type PilotData = Readonly<{
  offerings: PilotOffering[];
  scope: PilotScope;
}>;

export async function loadPilotData(): Promise<PilotData> {
  const [scopeResult, offeringsResult] = await Promise.all([
    serverCoreClient.GET("/api/v1/pilot-scope"),
    serverCoreClient.GET("/api/v1/offerings"),
  ]);
  if (!scopeResult.data || !offeringsResult.data) {
    throw new Error("Pilot catalog is unavailable");
  }

  const scope = pilotScopeSchema.parse(scopeResult.data);
  if (offeringsResult.data.manifest_key !== scope.key) {
    throw new Error("Pilot catalog does not match the frozen scope");
  }

  const offerings = ENGINEERING_SLICE_OFFERING_IDS.map((offeringId) => {
    const offering = offeringsResult.data.items.find(({ id }) => id === offeringId);
    if (
      !offering ||
      offering.target_year !== scope.target_year ||
      offering.study_mode !== scope.study_mode ||
      offering.admission_pathway !== scope.admission_pathway ||
      offering.publication_status !== "pending_publication"
    ) {
      throw new Error("Frozen engineering offering is missing or out of scope");
    }
    return offering;
  });

  return { offerings, scope };
}

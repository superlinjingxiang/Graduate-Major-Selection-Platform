"use client";

import { decisionSnapshotSchema } from "@gradmatch/domain/decision";
import { useQuery } from "@tanstack/react-query";

import { browserCoreClient } from "../../lib/api-client";
import type { PilotOffering } from "../../lib/pilot-api";
import { DecisionSummary } from "./decision-summary";

type DecisionResultProps = Readonly<{
  offerings: readonly PilotOffering[];
  snapshotId: string;
}>;

function assertPendingPilotSnapshot(
  offerings: readonly PilotOffering[],
  snapshot: ReturnType<typeof decisionSnapshotSchema.parse>,
) {
  if (!offerings.every(({ publication_status }) => publication_status === "pending_publication")) {
    return snapshot;
  }

  const deferred = new Set(snapshot.deferred);
  const allOfferingsDeferred =
    snapshot.deferred.length === offerings.length && offerings.every(({ id }) => deferred.has(id));
  if (
    snapshot.outcome !== "awaiting_official_information" ||
    snapshot.retained.length > 0 ||
    snapshot.excluded.length > 0 ||
    !allOfferingsDeferred
  ) {
    throw new Error("Pending pilot snapshot is inconsistent with its evidence state");
  }

  return snapshot;
}

export function DecisionResult({ offerings, snapshotId }: DecisionResultProps) {
  const snapshot = useQuery({
    queryKey: ["decision-snapshot", snapshotId],
    queryFn: async () => {
      const result = await browserCoreClient.GET("/api/v1/decision-snapshots/{snapshot_id}", {
        params: { path: { snapshot_id: snapshotId } },
      });
      if (!result.data) throw new Error("Snapshot unavailable");
      return assertPendingPilotSnapshot(offerings, decisionSnapshotSchema.parse(result.data));
    },
  });

  if (snapshot.isPending) {
    return (
      <section className="result-state panel" aria-live="polite">
        <p>正在读取资格快照…</p>
      </section>
    );
  }

  if (snapshot.isError) {
    return (
      <section className="result-state panel" role="alert">
        <h1>无法读取这份资格快照</h1>
        <p>它可能已失效，或不属于当前浏览器。请重新填写已确认的信息。</p>
        <a className="button button-primary" href="/match">
          重新填写信息
        </a>
      </section>
    );
  }

  return <DecisionSummary offerings={offerings} snapshot={snapshot.data} />;
}

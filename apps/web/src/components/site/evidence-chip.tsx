import type { EvidenceState } from "../../lib/demo-catalog";

const evidenceLabels = {
  confirmed: "已核验",
  pending: "待发布",
  conflict: "来源冲突",
  stale: "待更新",
  demo: "演示数据",
} satisfies Record<EvidenceState, string>;

type EvidenceChipProps = Readonly<{
  state: EvidenceState;
}>;

export function EvidenceChip({ state }: EvidenceChipProps) {
  return (
    <span className="evidence-chip" data-state={state}>
      {evidenceLabels[state]}
    </span>
  );
}

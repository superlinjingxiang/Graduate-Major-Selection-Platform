"use client";

import { useCompare } from "./compare-provider";

export function CompareAction({ programSlug }: Readonly<{ programSlug: string }>) {
  const { isFull, slugs, toggle } = useCompare();
  const isSelected = slugs.includes(programSlug);
  const isDisabled = isFull && !isSelected;

  return (
    <button
      aria-pressed={isSelected}
      className="compare-action"
      disabled={isDisabled}
      onClick={() => toggle(programSlug)}
      type="button"
    >
      {isSelected ? "移出对比" : isDisabled ? "最多对比 3 个" : "加入对比"}
    </button>
  );
}

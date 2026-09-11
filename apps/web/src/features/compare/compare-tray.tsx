"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { getDemoProgramBySlug } from "../../lib/demo-catalog";
import { useCompare } from "./compare-provider";

export function CompareTray() {
  const { clear, slugs, toggle } = useCompare();
  const pathname = usePathname();
  if (!slugs.length || pathname === "/compare") return null;

  return (
    <aside aria-label="临时对比" className="compare-tray">
      <div>
        <strong>已选择 {slugs.length} 个项目</strong>
        <ul aria-label="已选项目">
          {slugs.map((slug) => {
            const program = getDemoProgramBySlug(slug);
            return (
              <li key={slug}>
                <span>{program ? `${program.institution} · ${program.title}` : slug}</span>
                <button
                  aria-label={`移除${program?.title ?? slug}`}
                  onClick={() => toggle(slug)}
                  type="button"
                >
                  ×
                </button>
              </li>
            );
          })}
        </ul>
      </div>
      <div className="compare-tray-actions">
        <button onClick={clear} type="button">
          清空
        </button>
        <Link href="/compare">查看对比</Link>
      </div>
    </aside>
  );
}

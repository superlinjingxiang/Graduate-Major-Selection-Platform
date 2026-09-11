import type { Metadata } from "next";

import { SiteFooter } from "../../components/site/site-footer";
import { SiteHeader } from "../../components/site/site-header";
import { ComparisonView } from "../../features/compare/comparison-view";

export const metadata: Metadata = {
  title: "项目对比｜GradMatch",
  description: "用统一字段并排比较研究生招生项目演示数据。",
};

export default function ComparePage() {
  return (
    <main className="product-page">
      <SiteHeader />
      <div className="content-shell comparison-page">
        <ComparisonView />
      </div>
      <SiteFooter />
    </main>
  );
}

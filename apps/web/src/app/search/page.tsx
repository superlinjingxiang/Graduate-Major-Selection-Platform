import type { Metadata } from "next";

import { SiteFooter } from "../../components/site/site-footer";
import { SiteHeader } from "../../components/site/site-header";
import { SearchExplorer } from "../../features/discovery/search-explorer";
import { demoPrograms } from "../../lib/demo-catalog";

export const metadata: Metadata = {
  title: "搜索院校与专业｜GradMatch",
  description: "按院校、专业名称或专业代码搜索研究生招生项目演示数据。",
};

export default async function SearchPage({ searchParams }: PageProps<"/search">) {
  const { q } = await searchParams;
  const initialQuery = typeof q === "string" ? q : "";

  return (
    <main className="product-page">
      <SiteHeader />
      <SearchExplorer initialQuery={initialQuery} programs={demoPrograms} />
      <SiteFooter />
    </main>
  );
}

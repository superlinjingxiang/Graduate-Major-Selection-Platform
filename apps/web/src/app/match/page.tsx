import { FactForm } from "../../features/match/fact-form";
import { OfferingList } from "../../features/match/offering-list";
import { loadPilotData } from "../../lib/pilot-api";

export const dynamic = "force-dynamic";

export default async function MatchPage() {
  const { offerings } = await loadPilotData();

  return (
    <main className="page-shell match-shell">
      <div className="page-content">
        <header className="site-header compact-header">
          <a className="brand" href="/">
            <span className="brand-mark" aria-hidden="true">
              G
            </span>
            <span>GradMatch</span>
          </a>
          <a className="text-link" href="/">
            返回首页
          </a>
        </header>

        <section className="match-intro">
          <p className="eyebrow">2027 北京 · 全日制 · 统考</p>
          <h1>先确认范围，再判断资格</h1>
          <p className="match-lede">
            本次仅核对 3 个计算机相关计划项目。我们只保存你明确确认的事实，未知信息不会被猜测。
          </p>
        </section>

        <OfferingList offerings={offerings} />
        <section aria-labelledby="fact-form-title" className="fact-section">
          <h2 className="visually-hidden" id="fact-form-title">
            填写已确认信息
          </h2>
          <FactForm offeringIds={offerings.map(({ id }) => id)} />
        </section>
      </div>
    </main>
  );
}

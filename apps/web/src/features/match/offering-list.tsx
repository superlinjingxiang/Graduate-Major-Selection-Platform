import type { PilotOffering } from "../../lib/pilot-api";

type OfferingListProps = Readonly<{
  offerings: readonly PilotOffering[];
}>;

export function OfferingList({ offerings }: OfferingListProps) {
  return (
    <section aria-labelledby="pilot-offerings-title" className="pilot-offerings">
      <div className="section-heading">
        <p className="eyebrow">固定试点清单</p>
        <h2 id="pilot-offerings-title">本次只核对这 3 个计划项目</h2>
        <p className="section-copy">范围之外的学校和专业不会进入本次资格判断。</p>
      </div>
      <div className="offering-grid">
        {offerings.map((offering, index) => (
          <article className="offering-card panel" key={offering.id}>
            <span className="offering-index" aria-hidden="true">
              0{index + 1}
            </span>
            <p className="offering-school">{offering.institution_name}</p>
            <h3>
              {offering.program_code} · {offering.title}
            </h3>
            <p className="evidence-state">2027 官方招生信息待发布</p>
          </article>
        ))}
      </div>
    </section>
  );
}

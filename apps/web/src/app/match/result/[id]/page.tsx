import { DecisionResult } from "../../../../features/match/decision-result";
import { loadPilotData } from "../../../../lib/pilot-api";

export const dynamic = "force-dynamic";

type ResultPageProps = Readonly<{
  params: Promise<{ id: string }>;
}>;

export default async function ResultPage({ params }: ResultPageProps) {
  const [{ id }, { offerings }] = await Promise.all([params, loadPilotData()]);

  return (
    <main className="page-shell match-shell">
      <div className="page-content result-page">
        <header className="site-header compact-header">
          <a className="brand" href="/">
            <span className="brand-mark" aria-hidden="true">
              G
            </span>
            <span>GradMatch</span>
          </a>
          <a className="text-link" href="/match">
            重新核对
          </a>
        </header>
        <DecisionResult offerings={offerings} snapshotId={id} />
      </div>
    </main>
  );
}

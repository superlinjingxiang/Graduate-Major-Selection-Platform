export default function MatchLoading() {
  return (
    <main className="page-shell match-shell">
      <div className="page-content loading-state" aria-live="polite">
        <p className="eyebrow">资格核对</p>
        <h1>正在加载试点范围…</h1>
        <div className="loading-bars" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </main>
  );
}

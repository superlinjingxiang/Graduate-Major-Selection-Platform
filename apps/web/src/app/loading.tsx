export default function Loading() {
  return (
    <main className="page-shell">
      <div className="page-content loading-state" aria-live="polite">
        <p className="eyebrow">GradMatch</p>
        <h1>正在加载页面…</h1>
        <div className="loading-bars" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </main>
  );
}

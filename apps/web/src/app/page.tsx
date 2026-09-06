import { Panel } from "../components/ui/panel";

const foundations = [
  ["固定范围", "只核对 3 个北京全日制计算机统考计划项目。"],
  ["未知保持未知", "只使用你明确确认的事实，不替你猜测关键信息。"],
  ["证据可复核", "清楚说明信息来源、当前状态和下一步行动。"],
] as const;

export default function HomePage() {
  return (
    <main className="page-shell">
      <div className="ambient-orb ambient-orb-one" aria-hidden="true" />
      <div className="ambient-orb ambient-orb-two" aria-hidden="true" />
      <div className="page-content">
        <header className="site-header">
          <a className="brand" href="/">
            <span className="brand-mark" aria-hidden="true">
              G
            </span>
            <span>GradMatch</span>
          </a>
          <nav aria-label="账户导航" className="header-nav">
            <a href="/account/login">登录</a>
            <a className="nav-emphasis" href="/account/signup">
              创建账户
            </a>
          </nav>
        </header>

        <section className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">2027 北京全日制计算机统考</p>
            <h1>先把报考资格，核对清楚。</h1>
            <p className="hero-lede">
              根据你确认的事实核对固定试点范围；官方信息尚未发布的部分会明确保留为未知。
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="/match">
                开始资格核对
              </a>
              <a className="text-link" href="/account/login">
                已有账户，前往登录
              </a>
            </div>
          </div>
        </section>

        <section aria-label="资格核对说明" className="foundation-grid">
          {foundations.map(([title, description], index) => (
            <Panel className="foundation-card" key={title}>
              <span className="foundation-index">0{index + 1}</span>
              <h2>{title}</h2>
              <p>{description}</p>
            </Panel>
          ))}
        </section>
      </div>
    </main>
  );
}

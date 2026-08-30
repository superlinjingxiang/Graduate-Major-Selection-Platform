import { Panel } from "../components/ui/panel";

const foundations = [
  ["Web 优先", "以轻量服务端渲染呈现清晰、快速的首屏体验。"],
  ["统一身份", "同一套受保护会话可在浏览器与未来移动端使用。"],
  ["可靠数据", "采集链路保留原始快照，让后续推荐可以追溯。"],
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
            <p className="eyebrow">研究生申请的可信起点</p>
            <h1>把复杂选择，变成更笃定的下一步。</h1>
            <p className="hero-lede">
              GradMatch
              正在搭建一个可验证、可迁移的匹配基础：先让信息、身份与体验都足够可靠，再逐步走向更广阔的平台。
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="/account/signup">
                开始建立账户
              </a>
              <a className="text-link" href="/account/code">
                使用验证码登录
              </a>
            </div>
          </div>
        </section>

        <section aria-label="平台基础能力" className="foundation-grid">
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

import Link from "next/link";

const labels = ["数据", "院校", "专业", "择校工具", "资讯"] as const;

export function SiteHeader() {
  return (
    <header className="global-header">
      <div className="content-shell global-header-inner">
        <Link className="brand" href="/" aria-label="GradMatch 首页">
          <span className="brand-mark" aria-hidden="true">
            G
          </span>
          <span>GradMatch</span>
        </Link>

        <nav className="global-nav" aria-label="主导航">
          {labels.map((label) => (
            <Link href="/search" key={label}>
              {label}
            </Link>
          ))}
        </nav>

        <div className="header-actions">
          <Link className="header-search" href="/search">
            搜索
          </Link>
          <Link className="header-login" href="/account/login">
            登录
          </Link>
        </div>
      </div>
    </header>
  );
}

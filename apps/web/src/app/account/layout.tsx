import type { ReactNode } from "react";

type AccountLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function AccountLayout({ children }: AccountLayoutProps) {
  return (
    <main className="account-shell">
      <a className="brand account-brand" href="/">
        <span className="brand-mark" aria-hidden="true">
          G
        </span>
        <span>GradMatch</span>
      </a>
      <section className="account-card">{children}</section>
      <p className="account-security-note">身份服务由 GradMatch 统一管理</p>
    </main>
  );
}

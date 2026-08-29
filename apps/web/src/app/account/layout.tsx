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
    </main>
  );
}

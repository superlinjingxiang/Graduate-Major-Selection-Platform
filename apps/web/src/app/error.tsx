"use client";

import { Button } from "../components/ui/button";

type ErrorPageProps = Readonly<{
  reset: () => void;
}>;

export default function ErrorPage({ reset }: ErrorPageProps) {
  return (
    <main className="page-shell">
      <section className="page-content error-state" aria-live="assertive">
        <p className="eyebrow">GradMatch</p>
        <h1>页面暂时无法完成加载</h1>
        <p>请检查网络后重试；你的账户信息不会因此丢失。</p>
        <Button onClick={reset}>重新尝试</Button>
      </section>
    </main>
  );
}

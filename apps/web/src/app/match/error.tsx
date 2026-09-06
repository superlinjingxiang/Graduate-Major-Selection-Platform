"use client";

import { Button } from "../../components/ui/button";

type MatchErrorProps = Readonly<{
  retry: () => void;
}>;

export default function MatchError({ retry }: MatchErrorProps) {
  return (
    <main className="page-shell match-shell">
      <section className="page-content error-state" role="alert">
        <p className="eyebrow">资格核对</p>
        <h1>暂时无法加载试点范围</h1>
        <p>请稍后重试；尚未提交的信息不会受到影响。</p>
        <Button onClick={retry}>重新尝试</Button>
      </section>
    </main>
  );
}

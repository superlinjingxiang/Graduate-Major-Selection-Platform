"use client";

import { useQuery } from "@tanstack/react-query";

import { browserCoreClient } from "../../lib/api-client";
import { LogoutButton } from "../auth/auth-forms";

export function AccountPanel() {
  const accountQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: async () => {
      const result = await browserCoreClient.GET("/api/v1/me");
      if (!result.data) {
        throw new Error("current user unavailable");
      }
      return result.data;
    },
  });

  if (accountQuery.isPending) {
    return <p aria-live="polite">正在读取账户信息…</p>;
  }

  if (accountQuery.isError) {
    return <p aria-live="polite">暂时无法读取账户信息。</p>;
  }

  return (
    <section className="account-panel">
      <p className="eyebrow">已验证账户</p>
      <h1>
        你好，<span>{accountQuery.data.email}</span>
      </h1>
      <p>你的邮箱已通过验证，可以安全地继续使用 GradMatch。</p>
      <LogoutButton />
    </section>
  );
}

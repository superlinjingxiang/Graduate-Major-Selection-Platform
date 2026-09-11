import type { Metadata } from "next";

import { DemoLogin } from "../../../features/auth/demo-login";
import { sanitizeNextPath } from "../../../features/auth/login-path";

export const metadata: Metadata = {
  title: "登录｜GradMatch",
  description: "登录后保存研究生院校与专业选择。",
};

export default async function LoginPage({ searchParams }: PageProps<"/account/login">) {
  const { next } = await searchParams;
  const nextPath = sanitizeNextPath(typeof next === "string" ? next : undefined);

  return <DemoLogin nextPath={nextPath} />;
}

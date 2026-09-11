import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DemoLogin } from "./demo-login";
import { sanitizeNextPath } from "./login-path";

function renderLogin(nextPath = "/compare") {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DemoLogin nextPath={nextPath} />
    </QueryClientProvider>,
  );
}

describe("DemoLogin", () => {
  it("presents WeChat and phone as primary demo methods without implying real authorization", () => {
    renderLogin();

    expect(screen.getByRole("heading", { name: "登录后继续你的选择" })).toBeVisible();
    expect(screen.getByRole("tab", { name: "微信扫码" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "手机验证码" })).toBeVisible();
    expect(screen.getByText("演示二维码")).toBeVisible();
    expect(screen.getByText("演示模式不会发送短信或发起第三方授权")).toBeVisible();
    expect(screen.getByRole("button", { name: "QQ 登录（演示）" })).toBeVisible();
  });

  it("completes the local phone demo and returns to the requested in-app page", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("tab", { name: "手机验证码" }));
    await user.type(screen.getByLabelText("手机号"), "13800138000");
    await user.click(screen.getByRole("button", { name: "获取演示验证码" }));

    expect(screen.getByText("演示验证码已就绪")).toBeVisible();
    await user.type(screen.getByLabelText("验证码"), "123456");
    await user.click(screen.getByRole("button", { name: "完成演示登录" }));

    expect(screen.getByText("演示登录已完成")).toBeVisible();
    expect(screen.getByRole("link", { name: "继续返回对比" })).toHaveAttribute("href", "/compare");
  });

  it("rejects invalid phone numbers and incorrect demo codes", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("tab", { name: "手机验证码" }));
    await user.type(screen.getByLabelText("手机号"), "123");
    await user.click(screen.getByRole("button", { name: "获取演示验证码" }));
    expect(screen.getByText("请输入 11 位手机号")).toBeVisible();

    await user.clear(screen.getByLabelText("手机号"));
    await user.type(screen.getByLabelText("手机号"), "13800138000");
    await user.click(screen.getByRole("button", { name: "获取演示验证码" }));
    await user.type(screen.getByLabelText("验证码"), "654321");
    await user.click(screen.getByRole("button", { name: "完成演示登录" }));
    expect(screen.getByText("演示验证码为 123456")).toBeVisible();
  });

  it("keeps return navigation inside the site", () => {
    expect(sanitizeNextPath("/compare")).toBe("/compare");
    expect(sanitizeNextPath("//example.com/steal")).toBe("/");
    expect(sanitizeNextPath("https://example.com/steal")).toBe("/");
    expect(sanitizeNextPath(undefined)).toBe("/");
  });
});

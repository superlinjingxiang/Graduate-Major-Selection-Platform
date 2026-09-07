import { type APIRequestContext, expect, test } from "@playwright/test";

const mailpitBaseUrl = process.env.MAILPIT_BASE_URL ?? "http://127.0.0.1:8025";

function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.test`;
}

async function waitForMailText(request: APIRequestContext, email: string) {
  const deadline = Date.now() + 30_000;
  const mailboxUrl = new URL("/view/latest.txt", mailpitBaseUrl);
  mailboxUrl.searchParams.set("query", `to:${email}`);

  while (Date.now() < deadline) {
    const response = await request.get(mailboxUrl.toString());
    if (response.ok()) {
      return response.text();
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error(`Mailpit did not receive an email for ${email}`);
}

function extractVerificationPath(emailText: string) {
  const verificationPath = emailText.match(
    /https?:\/\/[^\s]+(\/account\/verify-email\/[^\s]+)/,
  )?.[1];
  if (!verificationPath) throw new Error("Verification path was not found in Mailpit email text.");
  return verificationPath.replace(/[)>.,]+$/, "");
}

function extractOneTimeCode(emailText: string) {
  const match = emailText.match(/\b\d{6}\b/);
  if (!match) throw new Error("One-time code was not found in Mailpit email text.");
  return match[0];
}

test("renders a product homepage without operational details", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "先把报考资格，核对清楚。" })).toBeVisible();
  await expect(page.getByRole("link", { name: "创建账户" })).toBeVisible();
  await expect(page.getByText("平台状态")).toHaveCount(0);
  await expect(page.getByText("服务已准备就绪")).toHaveCount(0);
  await expect(page.getByText("development", { exact: true })).toHaveCount(0);
  await expect(page.getByText(/\b(?:v)?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?\b/i)).toHaveCount(0);
});

test("does not place a signup password in the URL when JavaScript is unavailable", async ({
  baseURL,
  browser,
}) => {
  if (!baseURL) throw new Error("Playwright baseURL is required for this test.");
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  try {
    await page.goto(new URL("/account/signup", baseURL).toString());
    await page.getByLabel("邮箱").fill("no-js@example.test");
    await page.getByLabel("密码", { exact: true }).fill("private-password");
    const submission = page.waitForRequest((request) => request.url().includes("/account/signup"));
    await page.getByRole("button", { name: "创建账户" }).click();
    const request = await submission;

    expect(request.method()).toBe("POST");
    expect(request.url()).not.toContain("private-password");
  } finally {
    await context.close();
  }
});

test("does not place a login password in the URL when JavaScript is unavailable", async ({
  baseURL,
  browser,
}) => {
  if (!baseURL) throw new Error("Playwright baseURL is required for this test.");
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  try {
    await page.goto(new URL("/account/login", baseURL).toString());
    await page.getByLabel("邮箱").fill("no-js-login@example.test");
    await page.getByLabel("密码", { exact: true }).fill("private-login-password");
    const submission = page.waitForRequest((request) => request.url().includes("/account/login"));
    await page.getByRole("button", { name: "密码登录" }).click();
    const request = await submission;

    expect(request.method()).toBe("POST");
    expect(request.url()).not.toContain("private-login-password");
  } finally {
    await context.close();
  }
});

test("completes email verification, password and code login, account display, and logout", async ({
  page,
  request,
}) => {
  const email = uniqueEmail();
  const password = "e2e-password-123";

  await page.goto("/account/signup");
  await page.getByLabel("邮箱").fill(email);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "创建账户" }).click();
  await expect(page.getByText("验证邮件已发送，请完成邮箱验证。")).toBeVisible();

  const verificationEmail = await waitForMailText(request, email);
  await page.goto(extractVerificationPath(verificationEmail));
  await page.getByRole("button", { name: "确认邮箱" }).click();
  await expect(page.getByText("邮箱已验证，现在可以登录。")).toBeVisible();

  await page.goto("/account/login");
  await page.getByLabel("邮箱").fill(email);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "密码登录" }).click();
  await expect(page.getByText("登录成功。")).toBeVisible();

  await page.goto("/account");
  await expect(page.getByText(email, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByText("你已安全退出。")).toBeVisible();

  await page.goto("/account/code");
  await page.getByLabel("邮箱").fill(email);
  await page.getByRole("button", { name: "发送登录验证码" }).click();
  await expect(page.getByLabel("验证码")).toBeVisible();

  const codeEmail = await waitForMailText(request, email);
  await page.getByLabel("验证码").fill(extractOneTimeCode(codeEmail));
  await page.getByRole("button", { name: "确认登录" }).click();
  await expect(page.getByText("登录成功。")).toBeVisible();

  await page.goto("/account");
  await expect(page.getByText(email, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByText("你已安全退出。")).toBeVisible();
});

import { expect, test } from "@playwright/test";

test("访客从首页发现项目、建立对比并进入演示登录", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "把分散的招生信息，变成清晰的选择。" }),
  ).toBeVisible();
  await expect(page.getByText(/平台状态|development|服务已准备就绪/u)).toHaveCount(0);

  const homeSearch = page.getByRole("searchbox", { name: "搜索院校、专业或专业代码" });
  await homeSearch.fill("045400");
  await page
    .locator("#catalog-suggestions")
    .getByRole("link", { name: /北京师范大学.*应用心理/u })
    .click();

  await expect(page.getByRole("heading", { name: "应用心理" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "演示样本，不可作为报考依据" })).toBeVisible();
  await page.getByRole("button", { name: "加入对比" }).click();

  const trayClearButton = page.getByRole("button", { name: "清空" });
  const clearButtonBox = await trayClearButton.boundingBox();
  expect(clearButtonBox?.height).toBeGreaterThanOrEqual(44);

  await page.getByRole("link", { name: "继续搜索" }).click();
  await page.getByRole("searchbox", { name: "搜索院校、专业或专业代码" }).fill("金融");
  await page.getByRole("button", { name: "加入对比" }).first().click();
  await page.getByRole("link", { name: "查看对比" }).click();

  const comparison = page.getByRole("table", { name: "项目对比" });
  await expect(comparison).toBeVisible();
  await expect(comparison.getByText("应用心理")).toBeVisible();
  await expect(comparison.getByText("金融", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "保存这组对比" }).click();

  await expect(page.getByRole("heading", { name: "登录后继续你的选择" })).toBeVisible();
  await expect(page.getByText("演示模式不会发送短信或发起第三方授权")).toBeVisible();
});

test("公开 Demo 在当前视口中没有页面级横向溢出", async ({ page }) => {
  for (const path of [
    "/",
    "/search?q=045400",
    "/programs/bnu-applied-psychology-045400",
    "/compare",
    "/account/login?next=/compare",
  ]) {
    await page.goto(path);
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth, `${path} should not overflow the viewport`).toBeLessThanOrEqual(
      dimensions.clientWidth,
    );
  }
});

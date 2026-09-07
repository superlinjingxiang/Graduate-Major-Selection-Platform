import { expect, test } from "@playwright/test";

test("creates an anonymous decision snapshot for the frozen pilot scope", async ({ page }) => {
  await page.goto("/match");

  await expect(page.getByRole("heading", { name: "先确认范围，再判断资格" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "本次只核对这 3 个计划项目" })).toBeVisible();
  await expect(page.getByText("2027 官方招生信息待发布", { exact: true })).toHaveCount(3);
  for (const offering of [
    { institution: "北京邮电大学", program: "081200 · 计算机科学与技术" },
    { institution: "北京理工大学", program: "085404 · 计算机技术" },
    { institution: "北京工业大学", program: "085410 · 人工智能" },
  ]) {
    await expect(
      page
        .locator("article")
        .filter({ hasText: offering.institution })
        .filter({ hasText: offering.program }),
    ).toHaveCount(1);
  }

  await page.getByRole("checkbox", { name: "我确认以上报考范围" }).check();
  await page.getByRole("button", { name: "生成资格快照" }).click();

  await expect(page).toHaveURL(/\/match\/result\/[0-9a-f-]{36}$/u);
  await expect(page.getByRole("heading", { name: "等待 2027 官方信息" })).toBeVisible();
  await expect(page.getByText("资格状态：等待官方信息", { exact: true })).toHaveCount(3);
  await expect(page.getByRole("heading", { name: "下一步行动" })).toBeVisible();
});

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mockAuthenticatedGrcApi } from "./helpers/api";

test("login page has no detected accessibility violations", async ({ page }) => {
  await page.goto("/login");

  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("dashboard has no detected accessibility violations", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await page.goto("/login?tenant=demo");
  await page.getByLabel("Email").fill("user@example.com");
  await page.getByLabel("Password").fill("E2ePassw0rd!");
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/?tenant=demo");
  await expect(page.getByRole("heading", { name: /control room/i })).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

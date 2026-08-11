import { expect, test } from "@playwright/test";
import { mockAuthenticatedGrcApi } from "./helpers/api";

test("assessment setup and account menu expose only working actions", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);

  await page.goto("/login?tenant=demo");
  await page.getByLabel("Email").fill("user@example.com");
  await page.getByLabel("Password").fill("E2ePassw0rd!");
  await page.getByRole("button", { name: "Login" }).click();

  await page.getByRole("link", { name: "Assessments", exact: true }).click();
  await expect(page).toHaveURL(/\/assessments$/);
  await expect(page.getByRole("heading", { name: "Prepare your assessment catalogue" })).toBeVisible();

  await page.getByRole("link", { name: "Import a framework" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "System administration" })).toBeVisible();

  await page.getByText("TU", { exact: true }).click();
  await page.getByRole("link", { name: "Profile settings" }).click();
  await expect(page).toHaveURL(/\/account\/profile$/);
  await expect(page.getByRole("heading", { name: "Profile settings" })).toBeVisible();

  await page.getByText("TU", { exact: true }).click();
  await page.getByRole("menuitem", { name: "Sign Out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

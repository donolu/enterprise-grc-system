import { expect, test } from "@playwright/test";
import { mockAuthenticatedGrcApi } from "./helpers/api";

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login?tenant=demo");
  await page.getByLabel("Email").fill("user@example.com");
  await page.getByLabel("Password").fill("E2ePassw0rd!");
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

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

test("global search uses tenant data and opens the selected record", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await signIn(page);

  let searchRequestSent = false;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/search/" && url.searchParams.get("q") === "supplier") {
      searchRequestSent = true;
    }
  });

  const search = page.getByRole("combobox", { name: "Global search" });
  await search.fill("supplier");

  const searchResult = page
    .locator(".ant-select-dropdown .ant-select-item-option")
    .filter({ hasText: "Supplier access review overdue" });
  await expect(searchResult).toBeVisible();
  await expect.poll(() => searchRequestSent).toBe(true);
  await searchResult.click();

  await expect(page).toHaveURL(/\/risk\/1/);
  await expect(
    page.getByRole("cell", { name: "Supplier access review overdue" }).getByRole("strong"),
  ).toBeVisible();
});

test("global search makes an unavailable service explicit", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await page.route("**/api/search/**", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Search service unavailable." }),
    });
  });
  await signIn(page);

  await page.getByRole("combobox", { name: "Global search" }).fill("supplier");

  await expect(page.getByText("Search is unavailable: Search service unavailable.")).toBeVisible();
});

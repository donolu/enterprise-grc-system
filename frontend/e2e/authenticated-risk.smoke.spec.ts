import { expect, test } from "@playwright/test";
import { mockAuthenticatedGrcApi } from "./helpers/api";

test("authenticated users can open the risk register with tenant-scoped API requests", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);

  let riskRequestHeaders: Record<string, string> | null = null;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/risk/risks/") {
      riskRequestHeaders = request.headers();
    }
  });

  await page.goto("/login?tenant=demo");
  await page.getByLabel("Email").fill("user@example.com");
  await page.getByLabel("Password").fill("E2ePassw0rd!");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page).toHaveURL(/\/$/);

  await page.goto("/risk?tenant=demo");

  await expect(page.getByRole("heading", { name: "Risk Management" })).toBeVisible();
  await expect(page.getByText("Active Risk Register")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Supplier access review overdue" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Ada Lovelace" })).toBeVisible();

  expect(riskRequestHeaders).toMatchObject({
    authorization: "Bearer test-access-token",
    "x-tenancy-mode": "header",
    "x-tenant-id": "demo",
  });
});

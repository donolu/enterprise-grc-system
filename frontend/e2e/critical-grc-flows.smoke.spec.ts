import { expect, test, type Page } from "@playwright/test";
import { mockAuthenticatedGrcApi } from "./helpers/api";

async function signIn(page: Page) {
  await page.goto("/login?tenant=demo");
  await page.getByLabel("Email").fill("user@example.com");
  await page.getByLabel("Password").fill("E2ePassw0rd!");
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function chooseSelectOption(page: Page, fieldId: string, option: string) {
  await page.locator(`#${fieldId}`).click({ force: true });
  await page.getByTitle(option).click({ force: true });
}

test("users can acknowledge assigned policies", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await signIn(page);

  let acknowledgementRequestSent = false;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/policies/policies/1/acknowledge/" && request.method() === "POST") {
      acknowledgementRequestSent = true;
    }
  });

  await page.goto("/policies?tenant=demo");

  await expect(page.getByRole("heading", { name: "Policy Acknowledgments" })).toBeVisible();
  await expect(page.getByText("Information Security Policy")).toBeVisible();
  await expect(page.getByText("2 policies require your acknowledgment")).toBeVisible();

  const policyCard = page.locator(".ant-card").filter({ hasText: "Information Security Policy" });
  await policyCard.getByRole("button", { name: "Acknowledge" }).click();

  await expect.poll(() => acknowledgementRequestSent).toBe(true);
  await expect(page.getByText("Information Security Policy")).toHaveCount(0);
  await expect(page.getByText("1 policies require your acknowledgment")).toBeVisible();
});

test("users can open a vendor profile from the vendor directory", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await signIn(page);

  await page.goto("/vendors?tenant=demo");

  await expect(page.getByRole("heading", { name: "Vendor Management" })).toBeVisible();
  await expect(page.getByText("Vendor Directory")).toBeVisible();

  await page.getByRole("button", { name: /Axim Cloud Services/ }).click();

  await expect(page).toHaveURL(/\/vendors\/1/);
  await expect(page.getByText("Axim Cloud Services Ltd")).toBeVisible();
  await expect(page.getByText("Compliance & Security")).toBeVisible();
  await expect(page.getByText("ISO 27001")).toBeVisible();
  await expect(page.getByText("Ada Lovelace")).toBeVisible();
});

test("users can complete the assessment creation wizard", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await signIn(page);

  await page.goto("/assessments/create?tenant=demo");

  await expect(page.getByRole("heading", { name: "Create New Assessment" })).toBeVisible();
  await expect(page.getByText("Risk Assessment")).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await page.getByPlaceholder("Enter assessment title").fill("Quarterly risk assessment");
  await page.getByPlaceholder("Enter assessor name").fill("Ada Lovelace");
  await page
    .getByPlaceholder("Describe the assessment scope and objectives")
    .fill("Review supplier access and control evidence for the quarter.");

  const dateInputs = page.locator(".ant-picker input");
  await dateInputs.nth(0).fill("2026-07-20");
  await dateInputs.nth(0).press("Enter");
  await dateInputs.nth(1).fill("2026-08-20");
  await dateInputs.nth(1).press("Enter");
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Next", exact: true }).click();

  await page
    .getByPlaceholder("Define what will be assessed, boundaries, and exclusions")
    .fill("Supplier privileged access, approval evidence, and review records.");
  await chooseSelectOption(page, "methodology", "ISO 27001");
  await page
    .getByPlaceholder("Define what constitutes successful completion of this assessment")
    .fill("All sampled access rights have valid owners and evidence.");
  await chooseSelectOption(page, "priority", "High");

  await page.getByRole("button", { name: "Create Assessment" }).click();

  await expect(page).toHaveURL(/\/assessments$/);
  await expect(page.getByRole("heading", { name: "Compliance Assessments" })).toBeVisible();
});

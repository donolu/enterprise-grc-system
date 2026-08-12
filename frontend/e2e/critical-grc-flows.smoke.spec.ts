import { expect, test, type Page } from "@playwright/test";
import { mockAuthenticatedGrcApi } from "./helpers/api";

async function signIn(page: Page) {
  await page.goto("/login?tenant=demo");
  await page.getByLabel("Email").fill("user@example.com");
  await page.getByLabel("Password").fill("E2ePassw0rd!");
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

test("users can acknowledge assigned policies", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await signIn(page);

  let acknowledgementRequestSent = false;
  let pendingPoliciesRequestSent = false;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/policies/policies/my_policies/" && request.method() === "GET") {
      pendingPoliciesRequestSent = true;
    }
    if (url.pathname === "/api/policies/policies/1/acknowledge/" && request.method() === "POST") {
      acknowledgementRequestSent = true;
    }
  });

  await page.goto("/policies?tenant=demo");

  await expect(page.getByRole("heading", { name: "Policy Acknowledgments" })).toBeVisible();
  await expect(page.getByText("Information Security Policy")).toBeVisible();
  await expect(page.getByText("1 policies require your acknowledgment")).toBeVisible();
  await expect.poll(() => pendingPoliciesRequestSent).toBe(true);

  const policyCard = page.locator(".ant-card").filter({ hasText: "Information Security Policy" });
  await policyCard.getByRole("button", { name: "Acknowledge" }).click();

  await expect.poll(() => acknowledgementRequestSent).toBe(true);
  await expect(page.getByText("Information Security Policy")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "All caught up" })).toBeVisible();
});

test("policy acknowledgements show a retryable error when the API is unavailable", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await page.route("**/api/policies/policies/my_policies/", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Policy service unavailable." }),
    });
  });
  await signIn(page);

  await page.goto("/policies?tenant=demo");

  await expect(page.getByRole("heading", { name: "Policies could not be loaded" })).toBeVisible();
  await expect(page.getByText("Policy service unavailable.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByText("Information Security Policy")).toHaveCount(0);
});

test("training library loads live content and routes to the selected video", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await signIn(page);

  let videosRequestSent = false;
  let categoriesRequestSent = false;
  page.on("request", (request) => {
    const url = new URL(request.url());
    videosRequestSent ||= url.pathname === "/api/training/videos/" && request.method() === "GET";
    categoriesRequestSent ||= url.pathname === "/api/training/categories/" && request.method() === "GET";
  });

  await page.goto("/training?tenant=demo");

  await expect(page.getByRole("heading", { name: "Training library" })).toBeVisible();
  await expect(page.getByText("Recognising phishing attempts")).toBeVisible();
  await expect.poll(() => videosRequestSent && categoriesRequestSent).toBe(true);

  await page.getByText("Recognising phishing attempts").click();
  await expect(page).toHaveURL(/\/training\/video\/training-video-1/);
  await expect(page.getByRole("heading", { name: "Recognising phishing attempts" })).toBeVisible();
});

test("training library shows a retryable error when the API is unavailable", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await page.route("**/api/training/videos/", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Training service unavailable." }),
    });
  });
  await signIn(page);

  await page.goto("/training?tenant=demo");

  await expect(page.getByRole("heading", { name: "Training content could not be loaded" })).toBeVisible();
  await expect(page.getByText("Training service unavailable.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByText("Recognising phishing attempts")).toHaveCount(0);
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

test("assessment and treatment setup never simulate saved work", async ({ page }) => {
  await mockAuthenticatedGrcApi(page);
  await signIn(page);

  await page.goto("/assessments/create?tenant=demo");

  await expect(page.getByRole("heading", { name: "Assessment setup" })).toBeVisible();
  await page.getByRole("link", { name: "Import a framework" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  await page.goto("/risk/mitigation?tenant=demo");
  await expect(page.getByRole("heading", { name: "Risk treatment" })).toBeVisible();
  await page.getByRole("link", { name: "Open risk register" }).click();
  await expect(page).toHaveURL(/\/risk$/);
});

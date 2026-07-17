import type { Page, Route } from "@playwright/test";

const risk = {
  id: 1,
  risk_id: "RISK-001",
  title: "Supplier access review overdue",
  description: "Privileged supplier access has not been reviewed this quarter.",
  category: {
    id: 1,
    name: "Vendor Risk",
    description: "Third-party risk",
    color: "#E5484D",
  },
  impact: 4,
  likelihood: 3,
  risk_level: "high",
  status: "identified",
  risk_owner: {
    id: 1,
    username: "owner",
    first_name: "Ada",
    last_name: "Lovelace",
    email: "ada@example.com",
  },
  identified_date: "2026-07-01",
  next_review_date: "2026-07-31",
  risk_matrix: null,
  created_at: "2026-07-01T09:00:00Z",
  updated_at: "2026-07-01T09:00:00Z",
  created_by: {
    id: 1,
    username: "admin",
    first_name: "Grace",
    last_name: "Hopper",
  },
  risk_score: 12,
  is_overdue_for_review: false,
  days_until_review: 14,
  is_active: true,
};

const analytics = {
  totalRisks: 1,
  highRiskItems: 1,
  overdueActions: 0,
  avgRiskScore: 12,
  riskTrend: -1,
};

const executiveDashboard = {
  summary_metrics: {
    total_risks: { title: "Total Risks", value: 1 },
    high_priority_risks: { title: "High Priority", value: 1 },
    policy_compliance: { title: "Policy Compliance", value: 91, format: "percentage" },
    training_completion: { title: "Training Completion", value: 88, format: "percentage" },
    vendor_assessments: { title: "Vendor Assessments", value: 3 },
  },
  risk_trend_chart: { labels: [], datasets: [] },
  compliance_by_category: { labels: [], datasets: [] },
  recent_activities: [],
};

async function fulfilJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

export async function mockAuthenticatedGrcApi(page: Page) {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/auth/login/" && request.method() === "POST") {
      await fulfilJson(route, { access: "test-access-token" });
      return;
    }

    if (path === "/api/auth/refresh/" && request.method() === "POST") {
      await fulfilJson(route, { access: "test-access-token" });
      return;
    }

    if (path === "/api/billing/current_subscription/" && request.method() === "GET") {
      await fulfilJson(route, {
        enabled_module_keys: [
          "frameworks",
          "risk",
          "assets",
          "vendors",
          "policies",
          "training",
          "analytics",
          "vulnerability_scanning",
        ],
        trial_module: "",
        module_catalog: [],
      });
      return;
    }

    if (path === "/api/risk/risks/" && request.method() === "GET") {
      await fulfilJson(route, {
        results: [risk],
        count: 1,
        next: null,
        previous: null,
      });
      return;
    }

    if (path === "/api/risk/analytics/dashboard/" && request.method() === "GET") {
      await fulfilJson(route, analytics);
      return;
    }

    if (path === "/api/risk/categories/" && request.method() === "GET") {
      await fulfilJson(route, {
        results: [risk.category],
        count: 1,
        next: null,
        previous: null,
      });
      return;
    }

    if (path === "/api/risk/choices/" && request.method() === "GET") {
      await fulfilJson(route, {
        risk_levels: [{ value: "high", label: "High" }],
        status_choices: [{ value: "identified", label: "Identified" }],
        treatment_strategies: [{ value: "mitigate", label: "Mitigate" }],
      });
      return;
    }

    if (path === "/api/analytics/executive/" && request.method() === "GET") {
      await fulfilJson(route, executiveDashboard);
      return;
    }

    await fulfilJson(route, { detail: `Unhandled test route: ${path}` }, 404);
  });
}

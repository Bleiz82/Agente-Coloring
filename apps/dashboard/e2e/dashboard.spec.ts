import { test, expect, type Page } from "@playwright/test";

/** Helper: login before tests that need auth */
async function loginAs(
  page: Page,
  email = "admin@colorforge.ai",
  password = "colorforge2025",
): Promise<void> {
  await page.goto("/login");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL("/");
}

test.describe("dashboard E2E", () => {
  test("unauthenticated user is redirected to /login", async ({ page }) => {
    await page.goto("/");
    await page.waitForURL(/\/login/);
    expect(page.url()).toContain("/login");
  });

  test("login with valid credentials redirects to overview", async ({
    page,
  }) => {
    await loginAs(page);
    await expect(page.locator("h1")).toContainText("ColorForge AI");
  });

  test("login with wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@colorforge.ai");
    await page.fill('input[type="password"]', "wrongpassword");
    await page.click('button[type="submit"]');
    // Should stay on login page and show error
    expect(page.url()).toContain("/login");
    await expect(
      page.locator('[role="alert"], .text-red-500, .error'),
    ).toBeVisible();
  });

  test("overview page shows system status and KPI cards", async ({ page }) => {
    await loginAs(page);
    // System status section
    await expect(
      page.locator('text=/system|status|health/i').first(),
    ).toBeVisible();
    // KPI cards should be present
    await expect(
      page.locator('[data-testid="kpi-card"], .kpi-card, article').first(),
    ).toBeVisible();
  });

  test("alerts page shows alerts list or empty state", async ({ page }) => {
    await loginAs(page);
    await page.goto("/alerts");
    // Either shows alerts or "No active alerts" empty state
    const content = await page.textContent("body");
    const hasAlerts =
      content?.includes("alert") || content?.includes("No active");
    expect(hasAlerts).toBe(true);
  });

  test("policies page shows policies or empty state", async ({ page }) => {
    await loginAs(page);
    await page.goto("/policies");
    const content = await page.textContent("body");
    const hasPolicies =
      content?.includes("polic") || content?.includes("No ") || content?.includes("empty");
    expect(hasPolicies).toBe(true);
  });

  test("settings page shows killswitch with confirmation dialog", async ({
    page,
  }) => {
    await loginAs(page);
    await page.goto("/settings");
    // Find killswitch button
    const killswitchBtn = page.locator(
      'button:has-text("killswitch"), button:has-text("Killswitch"), button:has-text("Kill")',
    );
    await expect(killswitchBtn.first()).toBeVisible();
    // Click should show confirmation dialog
    await killswitchBtn.first().click();
    await expect(
      page.locator(
        '[role="dialog"], [role="alertdialog"], .modal, .dialog',
      ),
    ).toBeVisible();
  });

  test("login page is accessible when already authenticated", async ({
    page,
  }) => {
    await loginAs(page);
    // Navigate to login page (testing logout flow accessibility)
    await page.goto("/login");
    // Should be able to reach the login page
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });
});

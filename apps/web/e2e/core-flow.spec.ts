import { expect, test } from "@playwright/test";

// Scenario 1 (plan Task 7): the walking skeleton end to end, against the real checker.
test("creator checks sample post", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Try as Creator" }).click();
  await expect(page).toHaveURL(/\/check/, { timeout: 30_000 });
  await page.getByRole("button", { name: "Load sample post" }).click();
  await page.getByRole("button", { name: "Check", exact: true }).click();
  // Generous timeout: a sleeping free-tier checker takes ~25 s to wake.
  await expect(page.getByText("TN-02").first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("heading", { name: "Not checked" })).toBeVisible();
  // Evidence or silence: never a pass badge or "compliant" label.
  await expect(page.getByText(/compliant|all clear|passed/i)).toHaveCount(0);
});

test("signed-out visitors are sent to the login page", async ({ page }) => {
  await page.goto("/check");
  await expect(page).toHaveURL(/\/login/);
});

test("every demo role can sign in", async ({ page }) => {
  const roles = [
    ["Creator", "Creator Asha"],
    ["Agency", "Agency Sana"],
    ["Reviewer", "Reviewer Meera"],
    ["Compliance", "Compliance Arjun"],
    ["Brand owner", "Brand owner Kabir"],
  ];
  for (const [label, name] of roles) {
    await page.goto("/login");
    await page.getByRole("button", { name: `Try as ${label}` }).click();
    await expect(page.getByText(`Signed in as ${name}`)).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);
  }
});

test("a sleeping checker shows the waking banner, then the check succeeds", async ({ page }) => {
  // Simulate Render's cold start: the first two health probes fail, the third gets through.
  let probes = 0;
  await page.route("**/health", (route) => (++probes <= 2 ? route.abort() : route.continue()));
  await page.goto("/login");
  await page.getByRole("button", { name: "Try as Creator" }).click();
  await expect(page).toHaveURL(/\/check/, { timeout: 30_000 });
  await page.getByRole("button", { name: "Load sample post" }).click();
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Waking the checker");
  await expect(page.getByText("TN-02").first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("status")).toHaveCount(0);
  expect(probes).toBe(3);
});

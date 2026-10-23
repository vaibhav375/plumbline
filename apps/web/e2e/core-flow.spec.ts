import { expect, type Page, test } from "@playwright/test";

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

async function signInAndCheck(page: Page, text?: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Try as Creator" }).click();
  await expect(page).toHaveURL(/\/check/, { timeout: 30_000 });
  if (text) await page.getByLabel("Paste a post, or upload a file").fill(text);
  else await page.getByRole("button", { name: "Load sample post" }).click();
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await expect(page.getByTestId("blocking-count")).toBeVisible({ timeout: 120_000 });
}

const blockingCount = async (page: Page) => Number(await page.getByTestId("blocking-count").getAttribute("data-count"));

// Scenario 2 (plan Task 15).
test("creator fixes and submits", async ({ page }) => {
  await signInAndCheck(page);
  const before = await blockingCount(page);
  expect(before).toBeGreaterThan(0);
  await page.getByRole("article").filter({ hasText: "AW-014b" }).getByRole("button", { name: "Accept fix" }).click();
  await page.getByRole("article").filter({ hasText: "TM-007" }).getByRole("button", { name: "Accept fix" }).click();
  await page.getByRole("button", { name: "Apply accepted fixes & re-check" }).click();
  await expect.poll(() => blockingCount(page), { timeout: 120_000 }).toBeLessThan(before);
  const changes = page.getByRole("region", { name: "Changes" });
  await expect(changes.locator("ins").filter({ hasText: "Vitamin C Brightening Serum" }).first()).toBeVisible();
  await expect(changes.locator("del").filter({ hasText: "60%" }).first()).toBeVisible();
  await expect(changes.locator("ins").filter({ hasText: "32%" }).first()).toBeVisible();
  const submit = page.getByRole("button", { name: /Submit for review/ });
  await expect(submit).toBeDisabled();
  await expect(submit).toContainText("blocking");
  // A blocking finding can't be dismissed, and the page says why.
  const blocking = page.getByRole("article").filter({ hasText: "Blocking" }).first();
  await expect(blocking.getByRole("button", { name: "Dismiss" })).toBeDisabled();
});

test("highlights land on the right words after an emoji", async ({ page }) => {
  await signInAndCheck(page, "Got my PR package from Aurelle today ✨ The vit C serum smells like nothing. Shop now.");
  await expect(page.locator("mark").filter({ hasText: /^vit C serum/ }).first()).toBeVisible();
});

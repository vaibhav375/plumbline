import fs from "node:fs";
import path from "node:path";

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

// Scenario 3 (plan Task 16): a creator submits with blocking findings sent to a reviewer;
// Compliance decides them and approves; the status and timeline show every step.
test("compliance approves", async ({ page }) => {
  test.setTimeout(300_000);
  await signInAndCheck(page);
  const asks = page.getByRole("button", { name: "Ask a reviewer" });
  while ((await asks.count()) > 0) {
    const before = await asks.count();
    await asks.first().click();
    await page.getByLabel("What should the reviewer know? (required)").fill("No approved wording I can use here.");
    await page.getByRole("button", { name: "Send to a reviewer" }).click();
    await expect(asks).toHaveCount(before - 1, { timeout: 60_000 });
  }
  await page.getByRole("button", { name: "Submit for review", exact: true }).click();
  const done = page.getByRole("status").filter({ hasText: "Submitted for review" });
  await expect(done).toBeVisible({ timeout: 120_000 });
  const versionId = await done.getAttribute("data-version-id");
  expect(versionId).toBeTruthy();
  await page.getByRole("button", { name: "Sign out" }).click();

  await page.getByRole("button", { name: "Try as Compliance" }).click();
  await expect(page).toHaveURL(/\/check/, { timeout: 30_000 });
  await page.getByRole("link", { name: "Review queue" }).click();
  await page.locator(`a[href="/review/${versionId}"]`).click();
  await expect(page.getByText("still to decide")).toBeVisible({ timeout: 120_000 });
  const fact014 = page.getByRole("article").filter({ hasText: "FACT-014" });
  await expect(fact014.getByText("asked a reviewer")).toBeVisible(); // the writer's note carried over
  // Only blocking findings need a decision before approval; decided cards keep their buttons (a reviewer
  // can change their mind), so walk the blocking cards once each.
  const blocking = page.getByRole("article").filter({ hasText: "Blocking" });
  const n = await blocking.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const card = blocking.nth(i);
    await card.getByRole("button", { name: "Uphold", exact: true }).click();
    await card.getByLabel(/Reason for upholding/).fill("Agreed: publish only with the approved wording.");
    await card.getByRole("button", { name: "Uphold with reason" }).click();
    await expect(card.getByLabel(/Reason for upholding/)).toHaveCount(0, { timeout: 60_000 });
  }
  await expect(page.getByText(/· 0 still to decide/)).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByTestId("version-status")).toContainText("approved", { timeout: 60_000 });
  const timeline = page.getByRole("region", { name: "Timeline" });
  for (const step of ["submitted for review", "asked a reviewer about", "upheld FACT-014", "approved the first stage",
    "approved the compliance stage"]) {
    await expect(timeline.getByText(step).first()).toBeVisible();
  }
});

// Plan Task 17: the audit chain verifies, and the export is the whole chain with exact payloads.
test("audit log verifies and exports", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Try as Compliance" }).click();
  await expect(page).toHaveURL(/\/check/, { timeout: 30_000 });
  await page.getByRole("link", { name: "Audit log" }).click();
  const status = page.getByTestId("chain-status");
  await expect(status).toContainText(/Chain verified ✓ \(\d+ events\)/, { timeout: 90_000 });
  const total = Number((await status.textContent())!.match(/\((\d+) events\)/)![1]);
  await expect(page.getByRole("row").nth(1)).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  const csv = await (await download).createReadStream().then(async (s) => {
    let out = "";
    for await (const chunk of s) out += chunk;
    return out;
  });
  expect(csv.split("\n")[0].trim()).toBe("at,actor,kind,entity,entity_id,prev_hash,hash,payload");
  // At least as many events as verified a moment ago (other runs may have added more since).
  const rows = csv.match(/^\d{4}-\d\d-\d\dT/gm) ?? [];
  expect(rows.length).toBeGreaterThanOrEqual(total);
});

async function signInAs(page: Page, label: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: `Try as ${label}` }).click();
  await expect(page).toHaveURL(/\/check/, { timeout: 30_000 });
}

// Plan Task 18: the rulebook shows linter warnings, and an import reports what needs clarification.
test("brand owner previews and imports rules", async ({ page }) => {
  await signInAs(page, "Brand owner");
  await page.getByRole("link", { name: "Rulebook" }).click();
  const gm08 = page.getByRole("row").filter({ hasText: "GM08" });
  await expect(gm08.getByText(/Linter: .*sparingly/)).toBeVisible({ timeout: 90_000 });
  // Two seed rules, unchanged, so the live rulebook stays the same.
  const seed = fs.readFileSync(path.join(__dirname, "../../../supabase/seed/aurelle/rules.csv"), "utf8").split("\n");
  const csv = [seed[0], ...seed.filter((l) => /^(TN-02|GM08),/.test(l))].join("\n");
  await page.getByLabel("Rules CSV file").setInputFiles({ name: "rules.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByTestId("import-result")).toHaveText("Preview: 2 would be imported, 1 need clarification");
  await page.getByRole("button", { name: "Import 2 rules" }).click();
  await expect(page.getByTestId("import-result")).toHaveText("2 imported, 1 need clarification");
});

test("fact ledger hides restricted facts from an agency writer", async ({ page }) => {
  await signInAs(page, "Agency");
  await page.getByRole("link", { name: "Facts" }).click();
  await expect(page.getByText("Some facts are restricted")).toBeVisible({ timeout: 90_000 });
  const expired = page.getByRole("article", { name: "FACT-029" });
  await expect(expired.getByText("Expired", { exact: true })).toBeVisible();
  await expect(page.getByRole("article", { name: "FACT-031" })).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await signInAs(page, "Compliance");
  await page.getByRole("link", { name: "Facts" }).click();
  await expect(page.getByRole("article", { name: "FACT-031" })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText("Some facts are restricted")).toHaveCount(0);
});

// Plan Task 19: guideline health. Brand owner sees the org view; a creator sees only their own work.
test("guideline health shows unclear rules and graduation status", async ({ page }) => {
  await signInAs(page, "Brand owner");
  await page.getByRole("link", { name: "Guideline health" }).click();
  await expect(page.getByText("Includes synthetic demo history")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("unclear-count")).toContainText(/\d+ rules? may be unclear/);
  const tn03 = page.locator('tr[data-rule="TN-03"]');
  await expect(tn03.getByText("May be unclear")).toBeVisible();
  await expect(page.locator('tr[data-rule="TN-02"]').getByText("Ready to block")).toBeVisible();
  await expect(page.locator('tr[data-rule="GM07"]').getByText("Too few decisions (n < 10)")).toBeVisible();
  await expect(page.getByRole("heading", { name: "By origin" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Freelancers" })).toHaveCount(0); // 2 people: hidden
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await signInAs(page, "Creator");
  await page.getByRole("link", { name: "Guideline health" }).click();
  await expect(page.getByText("Your submitted drafts only.")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText("Includes synthetic demo history")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "By origin" })).toHaveCount(0);
  await page.getByRole("link", { name: "Audit log" }).click();
  await expect(page.getByTestId("chain-status")).toContainText("Events about your work", { timeout: 90_000 });
});

// Plan Task 20, scenario 4: the image accessibility floor, end to end.
test("an image without alt text or enough contrast is caught", async ({ page }) => {
  await signInAs(page, "Creator");
  await page.getByLabel("Upload a file", { exact: true }).setInputFiles(path.join(__dirname, "../../../supabase/seed/aurelle/banner_v1.png"));
  await expect(page.getByLabel(/Alt text: what must someone who can.t see this image learn from it\?/)).toBeVisible();
  await page.getByRole("button", { name: "Check", exact: true }).click();

  const contrast = page.getByRole("article").filter({ hasText: "A11Y-CONTRAST" });
  await expect(contrast).toContainText("Mandatory accessibility", { timeout: 90_000 });
  await expect(contrast).toContainText("1.96:1");
  const alt = page.getByRole("article").filter({ hasText: "A11Y-ALT" });
  await expect(alt).toContainText("No alt text");
  await expect(alt).toContainText("What must someone who can't see this image learn from it?");
  // The contrast finding's box is drawn on the thumbnail with the finding's number.
  const n = (await contrast.getAttribute("aria-label"))!.match(/Finding (\d+)/)![1];
  await expect(page.getByTestId(`image-box-${n}`)).toBeVisible();

  // Writing alt text clears that finding; the contrast problem stays.
  await page.getByLabel(/Alt text:/).fill("Aurelle banner: Glow in 2 weeks");
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await expect(page.getByRole("article").filter({ hasText: "A11Y-ALT" })).toHaveCount(0, { timeout: 90_000 });
  await expect(page.getByRole("article").filter({ hasText: "A11Y-CONTRAST" })).toBeVisible();
});

// Plan Task 21 and pre-submission audit item 1: the page's numbers are exactly latest.json's.
test("the evaluation page matches latest.json and is public", async ({ page }) => {
  const latest = JSON.parse(fs.readFileSync(path.join(__dirname, "../public/eval/latest.json"), "utf8"));
  await page.goto("/about"); // signed out: no redirect
  await expect(page).toHaveURL(/\/about/);
  await expect(page.getByText("Dev set written by the builder; held-out human-labelled set arrives in Round 3.")).toBeVisible();
  const pct = (x: number) => `${Math.round(x * 100)}%`;
  for (const mode of ["plumbline", "baseline"]) {
    const r = latest.results[mode];
    await expect(page.getByTestId(`recall-${mode}`)).toHaveText(pct(r.recall));
    await expect(page.getByTestId(`precision-${mode}`)).toHaveText(pct(r.precision));
    await expect(page.getByTestId(`citations-${mode}`)).toHaveText(pct(r.citation_valid_rate));
    await expect(page.getByTestId(`clean-${mode}`)).toHaveText(pct(r.counts.clean_with_alarm[0] / r.counts.clean_with_alarm[1]));
    await expect(page.getByTestId(`latency-${mode}`)).toHaveText(`${(r.ms_p95 / 1000).toFixed(1)} s`);
  }
  await expect(page.getByText(`${latest.results.plumbline.counts.recall[0]} / ${latest.results.plumbline.counts.recall[1]}`).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "What leaves this system" })).toBeVisible();
});

// Round 2 PDF: the Round 1 plan, unchanged, with the Round 2 progress section after the cover.
// Same pipeline as Round 1: headless Chrome printing the HTML at A4 with its own @page rules.
// Run with `make pdf`.
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(require.resolve("@playwright/test", { paths: [path.join(__dirname, "../../apps/web")] }));

const round1 = fs.readFileSync(path.join(__dirname, "../round1/plumbline_round1_plan.html"), "utf8");
const section = fs.readFileSync(path.join(__dirname, "round2_section.html"), "utf8");
const marker = "<!-- ============ 1. PROBLEM ============ -->";
if (!round1.includes(marker)) throw new Error("Round 1 HTML changed: section marker not found");

const html = round1
  .replace("<title>Plumbline: Round 1 Plan (Team AtoZ)</title>", "<title>Plumbline: Round 2 Build (Team AtoZ)</title>")
  .replace('content:"Plumbline · Team AtoZ · Round 1: The Plan"', 'content:"Plumbline · Team AtoZ · Round 2: The Build (Round 1 plan included)"')
  .replace('<div class="kicker">Round 1 · The Plan</div>', '<div class="kicker">Round 2 · The Build</div>')
  .replace(marker, section + "\n" + marker);

const out = path.join(__dirname, "plumbline_round2.html");
fs.writeFileSync(out, html);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + out, { waitUntil: "load" });
  await page.pdf({ path: path.join(__dirname, "../AtoZ_Plumbline_Round2.pdf"), preferCSSPageSize: true, printBackground: true });
  await browser.close();
  console.log("wrote docs/AtoZ_Plumbline_Round2.pdf");
})();

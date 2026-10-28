// Round 3 PDF: Round 3 section, then the Round 2 progress section, then the Round 1 plan unchanged.
// Citation and fix-audit status text is read from docs/round3/audit_status.json (written by hand after the checks).
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(require.resolve("@playwright/test", { paths: [path.join(__dirname, "../../apps/web")] }));

const round1 = fs.readFileSync(path.join(__dirname, "../round1/plumbline_round1_plan.html"), "utf8");
const r2 = fs.readFileSync(path.join(__dirname, "../round2/round2_section.html"), "utf8");
let r3 = fs.readFileSync(path.join(__dirname, "round3_section.html"), "utf8");
const st = JSON.parse(fs.readFileSync(path.join(__dirname, "audit_status.json"), "utf8"));
r3 = r3.replace("@@CITATIONS@@", st.citations).replace("@@FIXES@@", st.fixes);
const marker = "<!-- ============ 1. PROBLEM ============ -->";
if (!round1.includes(marker)) throw new Error("Round 1 HTML changed: section marker not found");

const html = round1
  .replace("<title>Plumbline: Round 1 Plan (Team AtoZ)</title>", "<title>Plumbline: Round 3 Final Build (Team AtoZ)</title>")
  .replace('content:"Plumbline · Team AtoZ · Round 1: The Plan"', 'content:"Plumbline · Team AtoZ · Round 3: The Final Build (Rounds 2 and 1 included)"')
  .replace('<div class="kicker">Round 1 · The Plan</div>', '<div class="kicker">Round 3 · The Final Build</div>')
  .replace(marker, r3 + "\n" + r2 + "\n" + marker);

const out = path.join(__dirname, "plumbline_round3.html");
fs.writeFileSync(out, html);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + out, { waitUntil: "load" });
  await page.pdf({ path: path.join(__dirname, "../AtoZ_Plumbline_Round3.pdf"), preferCSSPageSize: true, printBackground: true });
  await browser.close();
  console.log("wrote docs/AtoZ_Plumbline_Round3.pdf");
})();

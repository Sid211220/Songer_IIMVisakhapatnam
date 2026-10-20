// Records a silent walkthrough of the dashboard (docs/index.html) for the demo video.
// node docs/src/record_demo.js <outdir>   -> <outdir>/*.webm ; timings match docs/VIDEO_SCRIPT.md (part B)
const { chromium } = require("playwright");
const path = require("path");
const out = process.argv[2] || ".";
const page_url = "file://" + path.resolve(__dirname, "..", "index.html");
const log = [];
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM || "/opt/pw-browsers/chromium" });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, recordVideo: { dir: out, size: { width: 1440, height: 900 } } });
  const pg = await ctx.newPage();
  const t0 = Date.now();
  const mark = (s) => log.push(`${((Date.now() - t0) / 1000).toFixed(0)}s  ${s}`);
  const wait = (s) => pg.waitForTimeout(s * 1000);
  // a soft highlight ring so the viewer sees what is being discussed
  const ring = async (sel) => pg.evaluate((sel) => {
    document.querySelectorAll(".__ring").forEach((e) => e.classList.remove("__ring"));
    if (!document.getElementById("__rs")) { const st = document.createElement("style"); st.id = "__rs"; st.textContent = ".__ring{outline:4px solid #f59e0b!important;outline-offset:3px;transition:outline .2s}"; document.head.appendChild(st); }
    const e = document.querySelector(sel); if (e) { e.classList.add("__ring"); e.scrollIntoView({ behavior: "smooth", block: "center" }); }
  }, sel);
  const slide = async (sel, v) => pg.evaluate(([sel, v]) => { const e = document.querySelector(sel); e.value = v; e.dispatchEvent(new Event("input")); }, [sel, v]);
  await pg.goto(page_url); await wait(3);
  mark("B1 clinic overview at the default replay moment"); await wait(25);
  mark("B2 patient list"); await ring(".list"); await wait(20);
  mark("B3 patient record card"); await ring("#ptCard"); await wait(15);
  mark("B4 alert card"); await ring("#alertCard"); await wait(30);
  mark("B5 forecast chart"); await ring("#chMain"); await wait(35);
  mark("B6 what-if: walk 0 -> 15 -> 30 min"); await ring("#chWhatIf"); await slide("#wiWalk", 0); await wait(8); await slide("#wiWalk", 15); await wait(8); await slide("#wiWalk", 30); await wait(10);
  mark("B7 what-if: a full 7.5-hour night"); await slide("#wiWalk", 15); const s0 = await pg.$eval("#wiSleep", (e) => e.value); await slide("#wiSleep", 7.5); await wait(14); await slide("#wiSleep", s0);
  mark("B8 twin card"); await ring("#paramTable"); await wait(25);
  mark("B9 wearables and 7-day profile"); await ring("#chWear"); await wait(15); await ring("#chAgp"); await wait(15);
  mark("B10 replay: play forward to the evening"); await ring("#playBtn"); await pg.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" })); await wait(2);
  await pg.click("#playBtn"); await wait(17.5); await pg.click("#playBtn"); await pg.evaluate(() => setNow(Math.floor(nowMin / 1440) * 1440 + 20 * 60)); await wait(12);
  mark("B11 what-if: dinner in 30 min, rice vs chapati, smaller portion"); await ring("#chWhatIf"); await slide("#wiWhen", 30); await slide("#wiMeal", 1); await wait(12); await slide("#wiMeal", 2); await wait(12); await slide("#wiPortion", 70); await wait(12);
  mark("B12 another patient (prediabetes)"); await pg.evaluate(() => window.scrollTo({ top: 0 }));
  await pg.click(".chip[data-f=prediabetes]"); await wait(4); await pg.click("#ptList .pt:nth-child(1)"); await wait(20);
  mark("B13 alerts filter"); await pg.click(".chip[data-f=alert]"); await wait(10); await pg.click(".chip[data-f=all]");
  mark("B14 model evidence tab"); await pg.click("button[data-v=evidence]"); await wait(15);
  for (const sel of ["#fTable", "#aTable", "#figShap", "#figIdent", "#sTable"]) { await ring(sel); await wait(11); }
  mark("B15 how it works tab"); await pg.click("button[data-v=about]"); await pg.evaluate(() => window.scrollTo({ top: 0 })); await wait(18);
  mark("end"); await wait(2);
  await ctx.close(); await b.close();
  console.log(log.join("\n"));
})();

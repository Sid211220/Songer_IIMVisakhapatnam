// Reads the built dashboard (docs/index.html) and saves the numbers the demo narration quotes
// to docs/src/demo_facts.json.   node docs/src/demo_facts.js
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM || "/opt/pw-browsers/chromium" });
  const pg = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await pg.goto("file://" + path.resolve(__dirname, "..", "index.html"));
  await pg.waitForTimeout(2000);
  const set = (id, v) => pg.evaluate(([id, v]) => { const e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event("input")); }, [id, v]);
  const wi = () => pg.evaluate(() => [...document.querySelectorAll("#wiOut b")].map((e) => e.innerText));
  const F = {};
  F.start = await pg.evaluate(() => {
    const p = sel, i = aidx(nowMin), [g] = lastReading(p, nowMin);
    const meal = p.meals.filter((x) => x[0] < nowMin).slice(-1)[0];
    const base = twinRun(p, nowMin, { minutes: 180, keepU: true }), walk = twinRun(p, nowMin, { minutes: 180, keepU: true, walkAt: 0, walkMin: 15 });
    return { now: tlabel(nowMin), pt: p.pt, sex: p.sex, age: p.age, status: p.status, hba1c: p.hba1c, meds: p.meds, comorb: p.comorb,
      g: g, risk: p.risk[i], risk250: p.risk250[i], pred: [30, 60, 90, 120].map((h) => p.pred[h][i]), reasons: D.reasons[p.reasons[i]],
      meal_carbs: meal ? meal[1] : null, meal_min_ago: meal ? nowMin - meal[0] : null, meal_desc: meal ? meal[4] : null,
      nudge_drop: Math.round(Math.max(...base) - Math.max(...walk)),
      list_top: [...document.querySelectorAll("#ptList .pt")].slice(0, 4).map((e) => e.innerText.replace(/\n/g, " ")),
      params: document.getElementById("paramTable").innerText.split("\n"), summary: document.getElementById("sumOut").innerText.replace(/\n/g, " "),
      threshold: THR };
  });
  F.walk = {};
  for (const w of [0, 15, 30]) { await set("wiWalk", w); F.walk[w] = await wi(); }
  await set("wiWalk", 15); const s0 = await pg.$eval("#wiSleep", (e) => e.value); F.sleep_last = s0; await set("wiSleep", 7.5); F.full_night = await wi(); await set("wiSleep", s0);
  await pg.evaluate(() => setNow(Math.floor(nowMin / 1440) * 1440 + 20 * 60));
  F.evening = await pg.evaluate(() => ({ now: tlabel(nowMin), card: document.getElementById("alertCard").innerText.replace(/\n/g, " "),
    list_top: [...document.querySelectorAll("#ptList .pt")].slice(0, 5).map((e) => e.innerText.replace(/\n/g, " ")) }));
  await set("wiWhen", 30);
  await set("wiMeal", 1); F.dinner_rice = await wi();
  await set("wiMeal", 2); F.dinner_chapati = await wi();
  await set("wiPortion", 70); F.dinner_chapati70 = await wi();
  await pg.click(".chip[data-f=prediabetes]"); await pg.click("#ptList .pt:nth-child(1)"); await pg.waitForTimeout(300);
  F.pre_patient = await pg.evaluate(() => document.getElementById("ptCard").innerText.replace(/\n/g, " ") + " || " + document.getElementById("alertCard").innerText.replace(/\n/g, " "));
  await pg.click(".chip[data-f=alert]");
  F.alerts_at_8pm = await pg.evaluate(() => document.querySelectorAll("#ptList .pt").length);
  F.n_panel = await pg.evaluate(() => D.patients.length);
  fs.writeFileSync(path.join(__dirname, "demo_facts.json"), JSON.stringify(F, null, 1));
  console.log(JSON.stringify(F, null, 1));
  await b.close();
})();

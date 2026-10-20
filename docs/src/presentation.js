// Prahari presentation -> docs/Prahari_Presentation.pptx (PDF via LibreOffice)
// NODE_PATH=<global node_modules> node docs/src/presentation.js
const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");
const M = JSON.parse(fs.readFileSync(path.join(__dirname, "../../results/metrics.json")));
const IMG = (p) => path.join(__dirname, "..", p);
const FIG = (p) => path.join(__dirname, "../../results/figures", p);

const VIDEO = process.env.VIDEO === "1";   // video deck: live demo slide replaces the two dashboard slides
const FX = JSON.parse(fs.readFileSync(path.join(__dirname, "facts.json")));
const SV = FX.sim_validation;   // [check, short, simulated, published]
const NARR = JSON.parse(fs.readFileSync(path.join(__dirname, "demo_narration.json")));
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Prahari: a digital twin for type 2 diabetes";
pres.author = "Siddharth Yadav";
pres.company = "Team Songer, IIM Visakhapatnam";

const INK = "13202B", INK2 = "4A5565", MUTED = "7A8494", LINE = "DDE2E8", BG = "FFFFFF", SOFT = "F3F5F8";
const TEAL = "0F766E", TEAL_S = "E3F2EF", AMBER = "B45309", AMBER_S = "FDF1E1", RED = "B42318", BLUE = "1F4E8C", BLUE_S = "E8EEF7";
const H = "Cambria", B = "Calibri";
const W = 13.333;
let n = 0;

function slide(title, kicker) {
  const s = pres.addSlide();
  n += 1;
  s.background = { color: BG };
  if (kicker) s.addText(kicker.toUpperCase(), { x: 0.6, y: 0.35, w: 9, h: 0.28, fontFace: B, fontSize: 11, bold: true, color: TEAL, charSpacing: 2, margin: 0, isTextBox: true });
  s.addText(title, { x: 0.6, y: 0.62, w: 12.1, h: 0.95, fontFace: H, fontSize: 28, bold: true, color: INK, margin: 0, valign: "top", isTextBox: true });
  s.addText(`Prahari · Team Songer, IIM Visakhapatnam · synthetic data, research prototype`, { x: 0.6, y: 7.05, w: 9, h: 0.25, fontFace: B, fontSize: 9, color: MUTED, margin: 0, isTextBox: true });
  s.addText(String(n), { x: 12.2, y: 7.05, w: 0.5, h: 0.25, fontFace: B, fontSize: 9, color: MUTED, align: "right", margin: 0, isTextBox: true });
  return s;
}
function txt(s, text, o) { s.addText(text, Object.assign({ fontFace: B, fontSize: 15, color: INK, margin: 0, valign: "top", isTextBox: true }, o)); }
function card(s, x, y, w, h, fill) { s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill || SOFT }, line: { color: fill || SOFT, width: 0.5 }, rectRadius: 0.08 }); }
function stat(s, x, y, w, big, label, color) {
  txt(s, big, { x, y, w, h: 0.75, fontFace: H, fontSize: 36, bold: true, color: color || TEAL });
  txt(s, label, { x, y: y + 0.78, w, h: 0.75, fontSize: 13, color: INK2 });
}
function bullets(s, items, o) {
  s.addText(items.map((t, i) => (typeof t === "string" ? { text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1 } } :
    { text: t.text, options: Object.assign({ bullet: { indent: 14 }, breakLine: i < items.length - 1 }, t.options) })),
    Object.assign({ fontFace: B, fontSize: 15, color: INK, margin: 0, valign: "top", paraSpaceAfter: 6, isTextBox: true }, o));
}
function img(s, file, x, y, w, h) { s.addImage({ path: file, x, y, w, h }); }
function fit(file, maxW, maxH, pxW, pxH) { const r = Math.min(maxW / pxW, maxH / pxH); return [pxW * r, pxH * r]; }
// horizontal bar chart drawn with shapes (portable in every PowerPoint)
function hbars(s, x, y, w, rows, max, unit, labelW = 3.3, barH = 0.36, gap = 0.16) {
  rows.forEach((r, i) => {
    const yy = y + i * (barH + gap);
    txt(s, r[0], { x, y: yy, w: labelW - 0.1, h: barH, fontSize: 12.5, color: r[2] ? INK : INK2, bold: !!r[2], valign: "middle", align: "right" });
    const bw = (w - labelW - 0.8) * r[1] / max;
    s.addShape(pres.ShapeType.rect, { x: x + labelW, y: yy + 0.04, w: Math.max(bw, 0.02), h: barH - 0.08, fill: { color: r[2] ? TEAL : "B8C1CC" }, line: { color: r[2] ? TEAL : "B8C1CC", width: 0.5 } });
    txt(s, `${r[1].toFixed(1)}${unit}`, { x: x + labelW + bw + 0.08, y: yy, w: 0.9, h: barH, fontSize: 12.5, bold: !!r[2], color: r[2] ? TEAL : INK2, valign: "middle" });
  });
}

const R = M.regression, A = M.classification, F = "full (with twin)";

// 1 ─ title
{
  const s = pres.addSlide(); n += 1;
  s.background = { color: "0E1A24" };
  txt(s, "DIGITAL TWIN CHALLENGE 2026 · TYPE 2 DIABETES", { x: 0.8, y: 1.2, w: 11, h: 0.35, fontSize: 13, bold: true, color: "5EEAD4", charSpacing: 2 });
  txt(s, "Prahari", { x: 0.8, y: 1.75, w: 11, h: 1.2, fontFace: H, fontSize: 60, bold: true, color: "FFFFFF" });
  txt(s, "A digital twin that warns of a glucose spike up to two hours before it happens, explains why, and simulates what would prevent it", { x: 0.8, y: 3.05, w: 10.5, h: 1.2, fontSize: 22, color: "C9D6E2" });
  txt(s, "Team Songer · Siddharth Yadav · IIM Visakhapatnam", { x: 0.8, y: 5.3, w: 11, h: 0.4, fontSize: 16, bold: true, color: "FFFFFF" });
  txt(s, "All patients are synthetic (Synthea EHR + simulated CGM and smartwatch). Research prototype, not a medical device.", { x: 0.8, y: 5.75, w: 11, h: 0.4, fontSize: 12, color: "9FB3C4" });
  s.addNotes("Hello, I am Siddharth Yadav from IIM Visakhapatnam, and this is Prahari, my entry for the Digital Twin Challenge 2026. Prahari means sentinel. It is a digital twin for people with type 2 diabetes. It joins a patient's medical record with their continuous glucose monitor and smartwatch, keeps a personal model of their body up to date, and warns the doctor and the patient about a glucose spike up to two hours before it happens. It also explains why, and it lets you simulate what would prevent it. Everything you will see runs on synthetic patients, so no real person's data was used.");
}

// 2 ─ problem
{
  const s = slide("India's diabetes problem is a timing problem: the spikes happen after meals, the doctor sees one number every three months", "The problem");
  const xs = [0.6, 3.75, 6.9, 10.05];
  [["101 M", "adults in India with diabetes, plus 136 M with prediabetes (ICMR-INDIAB, 2023)"],
   ["43%", "of adults with diabetes in India are undiagnosed (IDF Diabetes Atlas, 11th ed.)"],
   ["62%", "of daily energy in Indian diets comes from carbohydrate (Anjana et al., 2025)"],
   ["1 number", "HbA1c, every few months, is what most doctors see. It says nothing about when or why"]].forEach((d, i) => {
    card(s, xs[i], 1.9, 2.9, 2.35, i === 3 ? AMBER_S : TEAL_S);
    stat(s, xs[i] + 0.22, 2.08, 2.5, d[0], d[1], i === 3 ? AMBER : TEAL);
  });
  txt(s, "What is missing", { x: 0.6, y: 4.6, w: 6, h: 0.4, fontFace: H, fontSize: 18, bold: true });
  bullets(s, ["CGMs and smartwatches now record every 5 minutes, but the data sits in separate apps, away from the medical record",
    "No one turns it into a warning early enough to act: a walk, a smaller portion, a call from the doctor",
    "Doctors have no way to test \"what if she walked after lunch?\" for one specific patient"], { x: 0.6, y: 5.05, w: 12.1, h: 1.8, fontSize: 15 });
  s.addNotes("Start with the scale. ICMR-INDIAB estimates that about 101 million Indian adults have diabetes and another 136 million have prediabetes. The IDF estimates that 43 percent of adults with diabetes in India do not even know it. And our diets are heavy in carbohydrate: about 62 percent of daily energy, according to the ICMR-INDIAB diet study. So the real damage happens after meals, many times a day. But what does the doctor see? Usually one HbA1c value every three months. It tells you the average. It does not tell you when glucose goes high, why, or what would have stopped it. CGMs and watches now capture that detail every five minutes, but the data sits in separate apps, nobody joins it to the medical record, and nobody turns it into a warning early enough to act on. That is the gap Prahari fills.");
}

// 3 ─ what Prahari does
{
  const s = slide("Prahari gives the doctor four things today's care cannot: a warning, a reason, a personal model and a what-if", "The idea");
  const items = [["Warn", "Probability of a spike above 180 and above 250 mg/dL in the next 2 hours, every 15 minutes, with a 2-hour forecast and an 80% band", TEAL_S, TEAL],
    ["Explain", "The top three reasons behind each alert in plain words (SHAP): the meal just logged, the twin's predicted peak, a short night", BLUE_S, BLUE],
    ["Personalise", "A twin per patient: insulin sensitivity, fasting level, meal response, absorption speed, dawn effect, re-fitted every night", TEAL_S, TEAL],
    ["Act", "What-if in the browser: walk 15 minutes, smaller portion, rice or chapati, a short night. At most one nudge per 2 hours for the patient", AMBER_S, AMBER]];
  items.forEach((d, i) => {
    const x = 0.6 + (i % 2) * 6.15, y = 1.9 + Math.floor(i / 2) * 2.45;
    card(s, x, y, 5.95, 2.2, d[2]);
    txt(s, d[0], { x: x + 0.3, y: y + 0.25, w: 5.3, h: 0.5, fontFace: H, fontSize: 22, bold: true, color: d[3] });
    txt(s, d[1], { x: x + 0.3, y: y + 0.85, w: 5.4, h: 1.2, fontSize: 15 });
  });
  s.addNotes("So what does Prahari actually give the doctor? Four things. First, a warning: every 15 minutes it estimates the chance of a spike above 180, and of a severe spike above 250, in the next two hours, with a forecast and an uncertainty band. Second, an explanation: the top three reasons behind each alert, in plain words, so the doctor is never asked to trust a black box. Third, personalisation: every patient has a twin with five physiological parameters that are re-fitted every night. And fourth, action: the doctor can ask the twin what would happen if the patient walked for 15 minutes, ate a smaller portion or slept badly, and the patient gets at most one heads-up every two hours, with an action the twin has simulated for them.");
}

// 4 ─ architecture
{
  const s = slide("Five layers: data in, ingest and protect, the digital twin, hybrid AI, and the clinic", "Architecture");
  const [w, h] = fit(IMG("img/architecture-1.png"), 11.6, 5.25, 2667, 1500);
  img(s, IMG("img/architecture-1.png"), (W - w) / 2, 1.7, w, h);
  s.addNotes("Here is the architecture. On the left, two kinds of data come in: the static health record, which gives age, diagnosis, HbA1c, kidney function, medicines and genetic risk; and the dynamic streams: CGM every five minutes, heart rate, heart-rate variability, steps and sleep stages from a watch, plus meals and insulin doses the patient logs. The ingestion layer converts the record to FHIR R4, the standard India's ABDM uses, keeps only the fields the model needs, and enforces one rule everywhere: at time t, only use information from before t. The third layer is the digital twin itself. It starts from a prior set by the record, is fitted to the patient in the first week, stays in sync with every CGM reading, and re-fits every night. The fourth layer is a hybrid AI model that combines the twin's forecast with all the other data. And the fifth layer is the clinic: a dashboard for the doctor and nudges for the patient.");
}

// 5 ─ data
{
  const s = slide("204 synthetic people lived 21 days of Indian routines, with a hidden physiology the twin never sees", "Data");
  card(s, 0.6, 1.85, 3.9, 4.95, BLUE_S);
  txt(s, "Static record (Synthea)", { x: 0.85, y: 2.05, w: 3.5, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: BLUE });
  bullets(s, [`${FX.t2d} with type 2 diabetes, ${FX.pre} with prediabetes; ${FX.women} women`, "Age, years since diagnosis, HbA1c, BMI, eGFR, BP, lipids", `Metformin, premixed insulin (${FX.insulin_users} users), comorbidities`, "Synthetic family history and polygenic risk, labelled as synthetic", "HbA1c values that contradict the diagnosis are repaired and flagged"], { x: 0.85, y: 2.55, w: 3.5, h: 4.1, fontSize: 14.5 });
  card(s, 4.72, 1.85, 3.9, 4.95, TEAL_S);
  txt(s, "Daily life (simulated)", { x: 4.97, y: 2.05, w: 3.5, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: TEAL });
  bullets(s, ["North or south Indian meals: rice, chapati, idli, dosa, poha, biryani, chai with sugar", `${FX.meals.toLocaleString("en-IN")} meals; ${FX.logged_pct}% logged, with carb-counting error`, "Walks, commutes, short nights, stressful work days", "Insulin before breakfast and dinner"], { x: 4.97, y: 2.55, w: 3.5, h: 4.1, fontSize: 14.5 });
  card(s, 8.84, 1.85, 3.9, 4.95, AMBER_S);
  txt(s, "What the devices record", { x: 9.09, y: 2.05, w: 3.5, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: AMBER });
  bullets(s, [`CGM every 5 minutes, sensor error ${FX.mard}% MARD, gaps, sensor change on day 11`, "Watch: heart rate, HRV (RMSSD), steps, sleep stages", `${FX.readings_m} million 5-minute time points`, "A richer hidden physiology produces the truth; the twin is simpler, so it must cope with mismatch"], { x: 9.09, y: 2.55, w: 3.5, h: 4.1, fontSize: 14.5 });
  s.addNotes("The challenge allows synthetic data, so I built a virtual population. The static record comes from Synthea, an open-source synthetic patient generator. I kept 204 adults: all 94 with type 2 diabetes and 110 with prediabetes, with their labs, medicines and conditions. Synthea has no genetics, so I added a synthetic family history and a polygenic risk percentile, clearly labelled. Synthea sometimes produces an HbA1c that contradicts the diagnosis, like 2.4 percent, so I repair those within the right range and flag every repair. Then each person lives 21 days of an Indian routine: north or south Indian meals, tea with sugar, late dinners, walks, short nights and stressful days. A hidden physiology turns that into true glucose minute by minute, and I simulate what a CGM and a watch would record, including sensor noise and gaps. Importantly, this hidden physiology is richer than the twin. The twin never sees it, so it faces real model mismatch, just as it would with a real patient.");
}

// 6 ─ realism
{
  const s = slide("The virtual patients respond the way published studies say real patients do", "Is the simulation realistic?");
  const rows = [["Check", "Simulator", "Published"], ["15-min walk after a meal", SV[0][1], "-12% overall, -22% after dinner (Reynolds 2016)"],
    ["One 4-hour night", SV[1][1], "about -25% glucose infusion rate (Donga 2010)"], ["Dawn rise in T2D", SV[2][1], "median 16 mg/dL (Monnier 2013)"],
    ["Mean glucose vs HbA1c", SV[3][1], "r = 0.92, eAG formula (Nathan 2008)"], ["Time in range vs HbA1c", SV[4][1], "about -17 points per 1% (Beck 2019)"],
    ["CGM error (MARD)", SV[5][1], "8.2-9.1%, Dexcom G7 (Garg 2022)"]];
  s.addTable(rows.map((r, i) => r.map((c) => ({ text: c, options: { bold: i === 0, color: i === 0 ? "FFFFFF" : INK, fill: { color: i === 0 ? TEAL : (i % 2 ? "FFFFFF" : SOFT) } } }))),
    { x: 0.6, y: 1.85, w: 7.4, colW: [2.2, 1.9, 3.3], fontFace: B, fontSize: 12.5, border: { type: "solid", color: LINE, pt: 0.5 }, rowH: 0.55, valign: "middle" });
  const [w, h] = fit(FIG("sim_validation.png"), 4.6, 4.2, 975, 540);
  img(s, FIG("sim_validation.png"), 8.2, 1.9, w, h);
  txt(s, "Same lunch, three days: usual, with a 15-minute walk, and after a 4-hour night.", { x: 8.2, y: 1.95 + h, w: 4.6, h: 0.6, fontSize: 12, color: INK2 });
  s.addNotes("A synthetic population is only useful if it behaves like real people, so I checked it against published studies. A 15-minute walk after a meal lowers post-meal glucose by 16 percent in my simulator; Reynolds and colleagues found 12 percent overall and 22 percent after dinner. A four-hour night cuts insulin sensitivity by a quarter, in line with Donga's study. The dawn rise, mean glucose against HbA1c, the slope of time in range against HbA1c and the CGM sensor error all sit close to published values. The chart on the right shows one virtual patient eating the same lunch on three days: a normal day, with a walk, and after a short night.");
}

// 7 ─ the twin
{
  const s = slide("The twin is a living model: built from the record, fitted in week one, synced every 5 minutes, re-fitted every night", "The digital twin");
  const steps = [["1  Prior", "HbA1c, BMI, diagnosis and medicines set starting values"], ["2  Onboard", "Days 1-7: five personal parameters fitted by MAP on its own forecasts"],
    ["3  Sync", "Each CGM reading corrects the state; estimates unlogged food"], ["4  Re-fit", "Every midnight on the last 7 days; day d only uses data before d"]];
  steps.forEach((d, i) => {
    const y = 1.85 + i * 1.22;
    card(s, 0.6, y, 5.3, 1.05, i % 2 ? SOFT : TEAL_S);
    txt(s, d[0], { x: 0.85, y: y + 0.12, w: 4.9, h: 0.35, fontFace: H, fontSize: 16, bold: true, color: TEAL });
    txt(s, d[1], { x: 0.85, y: y + 0.5, w: 4.9, h: 0.5, fontSize: 13.5 });
  });
  const [w, h] = fit(FIG("twin_identifiability.png"), 6.6, 3.4, 1275, 570);
  img(s, FIG("twin_identifiability.png"), 6.2, 1.85, w, h);
  const ti = M.twin_identifiability, lt = M.living_twin;
  txt(s, [{ text: `It recovers the hidden physiology. `, options: { bold: true, color: TEAL } },
    { text: `The record alone ranks insulin sensitivity poorly (Spearman ${ti.spearman_SI_ehr_prior_only.toFixed(2)} against the hidden truth). After week one the twin reaches ${ti.spearman_SI_onboarding.toFixed(2)}, and ${ti.spearman_SI_day21.toFixed(2)} by day 21. Re-fitting nightly beats freezing it after week one: 60-min error ${lt.nightly["60"].toFixed(1)} vs ${lt.frozen_after_week1["60"].toFixed(1)} mg/dL.` }],
    { x: 6.2, y: 2.0 + h, w: 6.5, h: 1.5, fontSize: 13.5 });
  s.addNotes("Now the heart of it: the twin. It is a compact physiological model of glucose and insulin, based on the Bergman minimal model, with a gut, insulin injections, exercise and the effect of sleep loss. It works in four steps. First, a prior from the medical record: HbA1c, BMI, diagnosis and medicines set the starting values. Second, onboarding: in the first week I fit five personal parameters, insulin sensitivity, fasting level, meal response, absorption speed and the dawn effect, by asking the twin to forecast glucose two hours ahead and correcting it where it was wrong. Third, synchronisation: every five-minute CGM reading nudges the twin's state, and a disturbance term soaks up food the patient forgot to log. Fourth, it re-fits every night on the last seven days. Does the twin learn something real? Because I know the hidden truth, I can check. From the record alone you can barely rank patients by insulin sensitivity: the rank correlation with the truth is 0.37. After one week of wearing a CGM, the twin reaches 0.81. That is information the record simply does not contain. And a twin that re-fits every night forecasts better than one frozen after week one.");
}

// 8 ─ hybrid AI
{
  const s = slide("A hybrid model: the twin's physics plus machine learning on every data source, with no look-ahead", "Hybrid AI");
  const groups = [["CGM", "25 features", "level, trends over 5-120 min, variability, gaps", BLUE_S, BLUE], ["Lifestyle", "27 features", "meals logged, habitual meal times from week 1, insulin, steps, heart rate, HRV vs own baseline, sleep", BLUE_S, BLUE],
    ["EHR", "18 features", "age, HbA1c, BMI, eGFR, medicines, comorbidities, genetic risk", BLUE_S, BLUE], ["Twin", "17 features", "its 30-120 min forecast, predicted peak and timing, personal parameters, unexplained glucose", TEAL_S, TEAL]];
  groups.forEach((g, i) => {
    const y = 1.85 + i * 1.18;
    card(s, 0.6, y, 6.1, 1.02, g[3]);
    txt(s, g[0], { x: 0.85, y: y + 0.13, w: 1.6, h: 0.4, fontFace: H, fontSize: 17, bold: true, color: g[4] });
    txt(s, g[1], { x: 0.85, y: y + 0.55, w: 1.6, h: 0.35, fontSize: 12, color: INK2 });
    txt(s, g[2], { x: 2.5, y: y + 0.15, w: 4.05, h: 0.8, fontSize: 13 });
  });
  txt(s, "Models (LightGBM)", { x: 7.1, y: 1.85, w: 5.6, h: 0.4, fontFace: H, fontSize: 18, bold: true });
  bullets(s, ["Glucose at 30, 60, 90 and 120 minutes, plus 10th and 90th percentiles for an 80% band", "Spike risk: onset above 180 (and above 250) mg/dL for at least 15 minutes within 2 hours", "Alert threshold frozen on validation patients at 70% precision; one notification per 120 minutes", "SHAP reasons for every alert"], { x: 7.1, y: 2.35, w: 5.6, h: 2.6, fontSize: 14 });
  txt(s, "Leakage controls", { x: 7.1, y: 4.85, w: 5.6, h: 0.4, fontFace: H, fontSize: 18, bold: true });
  bullets(s, ["Train, validation and test are different patients (122 / 41 / 41)", "Only data before the moment of prediction; meals count once logged", "Results on days 8-21, after the twin's onboarding week"], { x: 7.1, y: 5.3, w: 5.6, h: 1.6, fontSize: 14 });
  s.addNotes("The twin alone is good, but physics cannot know everything, for example that this person always has a big dinner at 9. So Prahari is hybrid. A LightGBM model gets 87 features from four groups: the CGM history, lifestyle signals from the watch and the meal log, the medical record, and the twin's own forecast and parameters. It predicts glucose at 30, 60, 90 and 120 minutes, with an uncertainty band, and the probability of a spike. The alert threshold is fixed on separate validation patients and never touched again. I was strict about leakage: test patients are never seen in training, every feature uses only information from before the moment of prediction, and a meal counts only once the patient has logged it.");
}

// 9 ─ forecast results
{
  const s = slide(`Prahari forecasts glucose 2 hours ahead with an error of ${R[F + "|120"].rmse.toFixed(1)} mg/dL, less than half of 'no change'`, "Results: forecasting");
  txt(s, "RMSE at 120 minutes, mg/dL (41 held-out patients, days 8-21)", { x: 0.6, y: 1.8, w: 7.2, h: 0.35, fontSize: 13, bold: true, color: INK2 });
  hbars(s, 0.6, 2.25, 7.4, [["Persistence (no change)", R["persist|120"].rmse], ["Linear model on CGM", R["linear|120"].rmse], ["Twin alone (physics)", R["twin|120"].rmse],
    ["LightGBM on CGM only", R["cgm|120"].rmse], ["+ wearables and meals", R["cgm+life|120"].rmse], ["+ EHR", R["cgm+life+ehr|120"].rmse], ["Prahari: + twin", R[F + "|120"].rmse, true]], 60, "");
  const b = M.bootstrap_rmse_gain_twin, pm = M.regression_post_meal;
  card(s, 8.3, 1.85, 4.45, 1.55, TEAL_S);
  stat(s, 8.55, 1.95, 4.0, `${R[F + "|30"].rmse.toFixed(1)} · ${R[F + "|60"].rmse.toFixed(1)} · ${R[F + "|120"].rmse.toFixed(1)}`, "RMSE at 30 · 60 · 120 minutes (mg/dL)");
  card(s, 8.3, 3.55, 4.45, 1.55, SOFT);
  stat(s, 8.55, 3.65, 4.0, `${pm["cgm|60"].toFixed(0)} → ${pm[F + "|60"].toFixed(0)}`, "60-min error in the 45 min after a meal: CGM-only vs Prahari", AMBER);
  card(s, 8.3, 5.25, 4.45, 1.55, SOFT);
  stat(s, 8.55, 5.35, 4.0, `${R[F + "|60"].clarke_ab.toFixed(1)}%`, "of 60-min forecasts in Clarke zones A+B (clinically acceptable)", BLUE);
  txt(s, `The twin's features cut error by ${b["60"].mean.toFixed(1)} mg/dL at 60 min (95% CI ${b["60"].lo95.toFixed(1)}-${b["60"].hi95.toFixed(1)}) over the same model without them.`, { x: 0.6, y: 6.05, w: 7.4, h: 0.7, fontSize: 13, color: INK2 });
  s.addNotes(`Here are the forecasting results on 41 patients the model had never seen, over two weeks. The bars show the error two hours ahead. Assuming glucose stays where it is gives an error of ${R["persist|120"].rmse.toFixed(0)} milligrams per decilitre. The twin alone gets ${R["twin|120"].rmse.toFixed(0)}. Machine learning on CGM alone gets ${R["cgm|120"].rmse.toFixed(1)}. Adding wearables and meals helps, and adding the twin gives the best result, ${R[F + "|120"].rmse.toFixed(1)}. The twin's contribution is small on average but statistically solid: about ${b["60"].mean.toFixed(1)} milligrams per decilitre at one hour, with a confidence interval well above zero. Where it really matters is right after a meal, which is exactly when a spike is building: there, the one-hour error drops from ${pm["cgm|60"].toFixed(0)} with CGM alone to ${pm[F + "|60"].toFixed(0)} with Prahari. And ${R[F + "|60"].clarke_ab.toFixed(1)} percent of forecasts fall in the clinically acceptable zones of the Clarke error grid.`);
}

// 10 ─ alert results (fair comparison: every model sends as many notifications as Prahari)
{
  const s = slide("It flags 3 in 4 spikes about 85 minutes before they start; severe spikes remain the hard part", "Results: spike warnings");
  const MB = M.matched_alert_budget, b1 = MB.spike, b2 = MB.spike250;
  card(s, 0.6, 1.85, 3.95, 2.1, TEAL_S); stat(s, 0.85, 2.0, 3.5, `${b1[F].sensitivity.toFixed(0)}%`, `of spikes above 180 flagged 15-120 min ahead`);
  card(s, 4.7, 1.85, 3.95, 2.1, TEAL_S); stat(s, 4.95, 2.0, 3.5, `${b1[F].median_lead_min.toFixed(0)} min`, "median warning before the spike starts");
  card(s, 8.8, 1.85, 3.95, 2.1, SOFT); stat(s, 9.05, 2.0, 3.5, `${b1[F].alert_precision.toFixed(0)}%`, `of notifications followed by a spike (${b1.budget_alerts_per_patient_day.toFixed(1)} per patient-day)`, BLUE);
  txt(s, `Spikes above 180 flagged early, every model at the same alert budget (AUPRC in brackets)`, { x: 0.6, y: 4.2, w: 7.6, h: 0.35, fontSize: 13, bold: true, color: INK2 });
  const C = A.spike;
  hbars(s, 0.6, 4.6, 7.6, [[`CGM only (${C.cgm.auprc.toFixed(2)})`, b1.cgm.sensitivity], [`+ wearables, meals (${C["cgm+life"].auprc.toFixed(2)})`, b1["cgm+life"].sensitivity],
    [`+ EHR (${C["cgm+life+ehr"].auprc.toFixed(2)})`, b1["cgm+life+ehr"].sensitivity], [`Prahari: + twin (${C[F].auprc.toFixed(2)})`, b1[F].sensitivity, true]], 100, "%", 3.3, 0.36, 0.12);
  bullets(s, [`The twin's physics alone flags ${b1["twin-only"].sensitivity.toFixed(0)}%, but only ${b1["twin-only"].median_lead_min.toFixed(0)} min ahead; learning routines stretches it to ${b1[F].median_lead_min.toFixed(0)}`,
    `Wearables and meal logs add most to alerts; the twin adds little on top`,
    `Severe spikes above 250: ${b2[F].sensitivity.toFixed(0)}% flagged (CGM only ${b2.cgm.sensitivity.toFixed(0)}%) at ${b2.budget_alerts_per_patient_day.toFixed(1)} notifications a day`], { x: 8.5, y: 4.2, w: 4.3, h: 2.7, fontSize: 13.5 });
  s.addNotes(`Now the adverse-event prediction the challenge asks for. A spike means glucose above 180 for at least 15 minutes. To compare models fairly, I set every model to send the same number of notifications, about ${b1.budget_alerts_per_patient_day.toFixed(0)} per patient per day. At that budget Prahari flags ${b1[F].sensitivity.toFixed(0)} percent of spikes at least 15 minutes before they start, with a median warning of ${b1[F].median_lead_min.toFixed(0)} minutes, and ${b1[F].alert_precision.toFixed(0)} percent of its notifications are followed by a spike. I want to be honest about what does the work here. For alerts, the wearables and the meal log add the most, from ${b1.cgm.sensitivity.toFixed(0)} to ${b1["cgm+life"].sensitivity.toFixed(0)} percent, and the twin adds only a little on top. Interestingly, the twin's physics on its own flags ${b1["twin-only"].sensitivity.toFixed(0)} percent of spikes, but only ${b1["twin-only"].median_lead_min.toFixed(0)} minutes ahead, because it only knows about meals already eaten. The learned model stretches that warning to ${b1[F].median_lead_min.toFixed(0)} minutes by learning each person's routine. Severe spikes above 250 are still hard: about ${b2[F].sensitivity.toFixed(0)} percent are flagged early. So the twin earns its place through better forecasts, the reasons it gives and the what-if answers, more than through the alert score.`);
}

// 11 ─ dashboard
if (VIDEO) {
  const s = slide("Live demo: the doctor's dashboard", "Clinic dashboard");
  s.addMedia({ type: "video", path: process.env.DEMO_MP4, x: 2.35, y: 1.5, w: 8.64, h: 5.4 });
  s.addNotes(NARR.map((x) => `[${x[0]}] ${x[2]}`).join("\n\n"));
}
if (!VIDEO) {
  const s = slide("The doctor's dashboard: who needs attention now, what will happen, and why", "Clinic dashboard");
  const [w, h] = fit(IMG("img/dash_overview.png"), 8.3, 5.2, 2880, 1800);
  img(s, IMG("img/dash_overview.png"), 0.6, 1.75, w, h);
  bullets(s, ["Patients ranked by spike risk in the next 2 hours", "Alert card: risk above 180 and 250, forecast high, top three reasons, suggested nudge", "12 hours of CGM, meals and insulin, then the 2-hour forecast with its 80% band and the twin's own line", "Replay any moment of the test fortnight; works offline, one HTML file"], { x: 9.15, y: 1.8, w: 3.6, h: 5.0, fontSize: 13.5 });
  s.addNotes("This is the dashboard a doctor would use. It is a single HTML file, so it works on any laptop, offline, and on GitHub Pages. On the left, patients are ranked by their risk of a spike in the next two hours. When you click a patient, you see their record, the alert card with the risk, the forecast high and the top three reasons, and a suggested nudge. Below that, the last twelve hours of glucose, meals and insulin, then the two-hour forecast with its band. You can replay any moment of the two test weeks. I will show it live in a moment.");
}

// 12 ─ what-if + twin card
if (!VIDEO) {
  const d = FX.demo.start, wk = FX.demo.walk, sx = { F: "woman", M: "man" }[d.sex];
  const s = slide(`The twin answers what-if questions for this patient: a 15-minute walk takes ${wk[0][0] - wk[15][1]} mg/dL off her peak`, `Use case: ${d.pt}`);
  const [w1, h1] = fit(IMG("img/dash_alert.png"), 4.1, 3.1, 950, 718);
  img(s, IMG("img/dash_alert.png"), 0.6, 1.8, w1, h1);
  const [w2, h2] = fit(IMG("img/dash_whatif.png"), 4.0, 4.9, 1188, 1086);
  img(s, IMG("img/dash_whatif.png"), 4.95, 1.8, w2, h2);
  const [w3, h3] = fit(IMG("img/dash_twin.png"), 3.6, 4.9, 950, 1086);
  img(s, IMG("img/dash_twin.png"), 9.15, 1.8, w3, h3);
  txt(s, `${d.age}-year-old ${sx} with T2D, HbA1c ${d.hba1c}%, on ${d.meds.join(", ") || "no medicines"}. ${d.now}, ${d.meal_min_ago} minutes after a ${d.meal_carbs} g lunch; glucose ${d.g}. Prahari: ${d.risk}% risk above 180, forecast high ${Math.max(...d.pred)}. A 15-minute walk: peak ${wk[0][0]} → ${wk[15][1]}, time above 180 ${wk[15][2]} min.`, { x: 0.6, y: 1.95 + h1, w: 4.1, h: 2.0, fontSize: 12.5, color: INK2 });
  s.addNotes(`Let me make it concrete with one patient, ${d.pt}: a ${d.age}-year-old ${sx} with type 2 diabetes, HbA1c ${d.hba1c} percent, on ${d.meds.join(" and ") || "no medicines"}. It is ${d.now} and she logged a ${d.meal_carbs}-gram rice lunch ${d.meal_min_ago} minutes ago. Her glucose is ${d.g}, but Prahari gives a ${d.risk} percent risk of going above 180, with a forecast high of about ${Math.max(...d.pred)} within the hour. The top reason is the twin's predicted peak. In the what-if panel the doctor can ask the twin: what if she walks for 15 minutes? The twin says the peak drops from ${wk[0][0]} to ${wk[15][1]} and she spends ${wk[15][2].split("→")[0].trim() - wk[15][2].split("→")[1].trim()} fewer minutes above 180. On the right is her twin: her parameters against the other patients and how they changed day by day.`);
}

// 13 ─ India deployment
{
  const s = slide("Built for India's health stack: FHIR records, data minimisation, and a clear path through regulation", "Deployment in India");
  const cols = [["Interoperability", ["Records exchanged as FHIR R4, the standard of the ABDM FHIR implementation guide (v6.5.0)", "Over 93 crore ABHA accounts already exist (PIB, July 2026) to link records"], BLUE_S, BLUE],
    ["Privacy", ["Only the fields the model needs are kept, no names or identifiers", "Designed for consent and purpose limits under the DPDP Rules 2025, whose main duties apply from 13 May 2027"], TEAL_S, TEAL],
    ["Regulation and pilot", ["As decision-support software it would be a medical device under CDSCO's risk classes A-D", "Next: validate on real CGM data, then a 12-week pilot with one diabetology clinic measuring time in range"], AMBER_S, AMBER]];
  cols.forEach((c, i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.85, 3.9, 3.35, c[2]);
    txt(s, c[0], { x: x + 0.25, y: 2.05, w: 3.4, h: 0.45, fontFace: H, fontSize: 18, bold: true, color: c[3] });
    bullets(s, c[1], { x: x + 0.25, y: 2.65, w: 3.45, h: 2.45, fontSize: 15 });
  });
  card(s, 0.6, 5.45, 12.1, 1.3, SOFT);
  txt(s, [{ text: "What a pilot would measure: ", options: { bold: true, color: TEAL } }, { text: "time in range and time above 250 mg/dL before and after 12 weeks, share of alerts the doctor found useful, false alerts per patient-day, and minutes of doctor time per patient review." }],
    { x: 0.85, y: 5.6, w: 11.6, h: 1.0, fontSize: 15, valign: "middle" });
  s.addNotes("How would this work in India? On interoperability, records move as FHIR R4, the standard in ABDM's FHIR implementation guide, and more than 93 crore ABHA accounts already exist to link them. On privacy, Prahari keeps only the fields the model needs and is designed around consent and purpose limits under the DPDP Rules, whose main duties apply from May 2027. On regulation, a tool that supports clinical decisions would be software as a medical device under CDSCO's risk-based classes, so the honest next step is validation on real CGM data and then a 12-week pilot with one diabetology clinic, measuring whether patients spend more time in range.");
}

// 14 ─ limits + next
{
  const s = slide("What these results do not show yet, and what I would do next", "Limits and next steps");
  card(s, 0.6, 1.85, 5.95, 3.75, SOFT);
  txt(s, "Limits", { x: 0.85, y: 2.05, w: 5.4, h: 0.4, fontFace: H, fontSize: 18, bold: true, color: RED });
  bullets(s, ["All patients are synthetic and more regular than real people, so real-world error will be higher. On the real OhioT1DM data, published deep models reach 55-66 mg/dL at 2 hours (Tena 2021)",
    "At HbA1c 7% my virtual patients have more time in range than real cohorts", "No hypoglycaemia in the simulated cohort, so lows are not predicted yet",
    `The 80% band covers ${M.band80_coverage["60"].toFixed(0)}% of outcomes at 60 min; it needs calibration`, "Many alerts come before habitual meals: the model learns routines"], { x: 0.85, y: 2.55, w: 5.5, h: 3.0, fontSize: 14 });
  card(s, 6.8, 1.85, 5.95, 3.75, TEAL_S);
  txt(s, "Next", { x: 7.05, y: 2.05, w: 5.4, h: 0.4, fontFace: H, fontSize: 18, bold: true, color: TEAL });
  bullets(s, ["Validate on open real-world T2D CGM data, then a consented Indian cohort", "Add hypoglycaemia risk for insulin users and conformal prediction bands", "Estimate carbs from meal photos, so logging takes one tap", "12-week clinic pilot: doctor dashboard plus patient nudges, measured by time in range"], { x: 7.05, y: 2.55, w: 5.5, h: 3.0, fontSize: 15 });
  card(s, 0.6, 5.8, 12.1, 0.95, AMBER_S);
  txt(s, [{ text: "The bar to clear on real data: ", options: { bold: true, color: AMBER } }, { text: "on the real ShanghaiT2DM CGM dataset, a published Bayesian model reaches 13.5 and 21.4 mg/dL at 30 and 60 minutes (Sun & Kosmas, 2024)." }],
    { x: 0.85, y: 5.9, w: 11.6, h: 0.75, fontSize: 15, valign: "middle" });
  s.addNotes("I want to be clear about what these results do not show. Every patient here is synthetic, and synthetic people are more regular than real ones, so error on real data will be higher. For comparison, published deep-learning models on the real OhioT1DM dataset have errors of 55 to 66 at two hours. My virtual patients are also a little steadier than real ones, there are no lows in the cohort, so Prahari does not predict hypoglycaemia yet, and the uncertainty band is slightly too narrow. Next, I would validate on real CGM data, add low-glucose risk for insulin users, estimate carbs from meal photos so logging takes one tap, and run a 12-week pilot with a clinic.");
}

// 15 ─ close
{
  const s = pres.addSlide(); n += 1;
  s.background = { color: "0E1A24" };
  txt(s, "Prahari", { x: 0.8, y: 1.3, w: 11, h: 1.0, fontFace: H, fontSize: 48, bold: true, color: "FFFFFF" });
  txt(s, "A twin for every patient. An early warning for most spikes. A reason for every warning. An action the twin has simulated.", { x: 0.8, y: 2.4, w: 11.5, h: 1.1, fontSize: 22, color: "C9D6E2" });
  bullets(s, [{ text: "Code, data, models and results: public GitHub repository Songer_IIMVisakhapatnam (MIT licence)", options: { color: "FFFFFF" } },
    { text: "Dashboard: docs/index.html, also on GitHub Pages", options: { color: "FFFFFF" } },
    { text: "Reproduce everything: python scripts/run_all.py", options: { color: "FFFFFF" } }], { x: 0.8, y: 4.0, w: 11.5, h: 1.6, fontSize: 16 });
  txt(s, "Siddharth Yadav · Team Songer · IIM Visakhapatnam", { x: 0.8, y: 6.2, w: 11, h: 0.4, fontSize: 15, bold: true, color: "5EEAD4" });
  s.addNotes("To sum up: Prahari gives every patient a twin, gives early warning of most spikes, explains every warning, and suggests an action the twin has already simulated. The code, data, models and results are all in the public GitHub repository under an MIT licence, and you can rebuild everything with one command. Thank you for watching.");
}

pres.writeFile({ fileName: VIDEO ? (process.env.OUT || "Prahari_Video_Deck.pptx") : path.join(__dirname, "..", "Prahari_Presentation.pptx") }).then((f) => console.log("wrote", f));

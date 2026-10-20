// Architecture diagram for Prahari -> docs/Prahari_Architecture.pptx (then PDF via LibreOffice)
// node docs/src/architecture.js
const pptxgen = require("pptxgenjs");
const path = require("path");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "Prahari architecture";
pres.author = "Siddharth Yadav (Team Songer, IIM Visakhapatnam)";
const INK = "1D2733", MUTED = "5B6675", TEAL = "0F766E", TEAL_S = "E6F3F1", BLUE = "1F4E8C", BLUE_S = "E8EEF7",
  AMBER = "B45309", AMBER_S = "FDF3E4", GREY_S = "F3F5F8", LINE = "C9D0D9", WHITE = "FFFFFF", PURPLE = "5B3FB0", PURPLE_S = "F1EEFB";
const F = "Calibri";
const s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Prahari: how the digital twin works", { x: 0.4, y: 0.25, w: 9, h: 0.5, fontFace: F, fontSize: 24, bold: true, color: INK, margin: 0, isTextBox: true });
s.addText("Proof of concept for type 2 diabetes · Team Songer, IIM Visakhapatnam · all data synthetic", { x: 0.4, y: 0.72, w: 9, h: 0.3, fontFace: F, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });

function box(x, y, w, h, fill, title, lines, tcolor, opts = {}) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: opts.line || fill, width: 1 }, rectRadius: 0.08 });
  s.addText(title, { x: x + 0.12, y: y + 0.08, w: w - 0.24, h: 0.3, fontFace: F, fontSize: opts.ts || 12.5, bold: true, color: tcolor, margin: 0, isTextBox: true, valign: "top" });
  if (lines) s.addText(lines.map((t, i) => ({ text: t, options: { bullet: { indent: 10 }, breakLine: i < lines.length - 1 } })),
    { x: x + 0.12, y: y + 0.4, w: w - 0.2, h: h - 0.46, fontFace: F, fontSize: opts.fs || 10.5, color: INK, margin: 0, valign: "top", paraSpaceAfter: 2, isTextBox: true });
}
function col(x, label, color) {
  s.addText(label, { x, y: 1.12, w: 2.35, h: 0.3, fontFace: F, fontSize: 10.5, bold: true, color, charSpacing: 1.5, margin: 0, isTextBox: true });
}
function arrow(x1, y, x2, color = MUTED) {
  s.addShape(pres.ShapeType.line, { x: x1, y, w: x2 - x1, h: 0, line: { color, width: 1.75, endArrowType: "triangle" } });
}
function down(x, y1, y2, color = MUTED) {
  s.addShape(pres.ShapeType.line, { x, y: y1, w: 0, h: y2 - y1, line: { color, width: 1.5, endArrowType: "triangle" } });
}
// columns
const X = [0.4, 3.0, 5.6, 8.2, 10.8], W = 2.25;
col(X[0], "1  DATA IN", BLUE); col(X[1], "2  INGEST & PROTECT", PURPLE); col(X[2], "3  DIGITAL TWIN", TEAL); col(X[3], "4  HYBRID AI", AMBER); col(X[4], "5  CLINIC", INK);

box(X[0], 1.45, W, 1.55, BLUE_S, "Static EHR (Synthea)", ["Age, sex, diagnosis, years since diagnosis", "HbA1c, BMI, eGFR, BP, lipids", "Medicines, comorbidities", "Synthetic genetic risk + family history"], BLUE);
box(X[0], 3.12, W, 1.6, BLUE_S, "Dynamic streams", ["CGM glucose every 5 min", "Watch: heart rate, HRV (RMSSD), steps, sleep stages", "Meal log (photo/app), insulin pen"], BLUE);
box(X[0], 4.84, W, 1.15, GREY_S, "Virtual patient simulator", ["204 people x 21 days, Indian routines, hidden physiology richer than the twin"], INK, { fs: 10 });

box(X[1], 1.45, W, 2.2, PURPLE_S, "Ingestion layer", ["FHIR R4 bundles (ABDM-style) for the record", "Time-aligned 5-min grid, gaps flagged", "Pseudonymous IDs, only fields the model needs (DPDP data minimisation)", "Consent + audit trail (design)"], PURPLE);
box(X[1], 3.77, W, 2.22, PURPLE_S, "Leakage guard", ["At time t, use only data before t", "Meals count once logged", "Habits learned in week 1 only", "Patient-level train / validation / test split"], PURPLE);

box(X[2], 1.45, W, 1.0, TEAL_S, "EHR prior", ["HbA1c, BMI, diagnosis, medicines set starting values"], TEAL, { fs: 10 });
box(X[2], 2.57, W, 1.1, TEAL_S, "Onboarding fit (days 1-7)", ["5 personal parameters by MAP: sensitivity, fasting level, meal gain, absorption, dawn"], TEAL, { fs: 10 });
box(X[2], 3.79, W, 1.1, TEAL_S, "Stay in sync (every 5 min)", ["Observer corrects state from CGM, estimates unlogged food"], TEAL, { fs: 10 });
box(X[2], 5.01, W, 0.98, TEAL_S, "Re-fit every night", ["Trailing 7 days, warm start"], TEAL, { fs: 10 });
down(X[2] + W / 2, 2.45, 2.57, TEAL); down(X[2] + W / 2, 3.67, 3.79, TEAL); down(X[2] + W / 2, 4.89, 5.01, TEAL);

box(X[3], 1.45, W, 1.5, AMBER_S, "Feature store", ["CGM history and trend", "Meals, insulin, steps, HR, HRV, sleep", "EHR features", "Twin forecast, peak, parameters"], AMBER, { fs: 10 });
box(X[3], 3.07, W, 1.55, AMBER_S, "LightGBM models", ["Glucose at 30/60/90/120 min", "80% prediction band (quantiles)", "Spike risk: >180 and >250 in 2 h", "SHAP: top 3 reasons"], AMBER, { fs: 10 });
box(X[3], 4.74, W, 1.25, AMBER_S, "Evaluation", ["Held-out patients, days 8-21", "Ablation, Clarke grid, AUROC, lead time"], AMBER, { fs: 10 });
down(X[3] + W / 2, 2.95, 3.07, AMBER);

box(X[4], 1.45, W, 2.45, "EEF2F5", "Doctor dashboard", ["Patients ranked by spike risk", "2-hour forecast with band", "Why: top reasons", "Twin parameters over time", "What-if: walk, portion, sleep"], INK, { fs: 10 });
box(X[4], 4.02, W, 1.97, "EEF2F5", "Patient nudge", ["One heads-up per meal, 120-min cooldown", "Suggested action from the twin (e.g. 15-min walk)", "Doctor sets thresholds"], INK, { fs: 10 });

// arrows between columns
arrow(X[0] + W, 2.2, X[1]); arrow(X[0] + W, 3.9, X[1]);
arrow(X[1] + W, 2.0, X[2]); arrow(X[1] + W, 4.3, X[2]);
arrow(X[2] + W, 2.0, X[3]); arrow(X[2] + W, 4.3, X[3]);
arrow(X[3] + W, 2.2, X[4]); arrow(X[3] + W, 4.4, X[4]);
// feedback loop label
s.addShape(pres.ShapeType.roundRect, { x: 0.4, y: 6.18, w: 12.65, h: 0.85, fill: { color: GREY_S }, line: { color: LINE, width: 0.75 }, rectRadius: 0.06 });
s.addText([
  { text: "Closed loop. ", options: { bold: true, color: TEAL } },
  { text: "Every new CGM reading updates the twin's state; every night the twin re-fits its parameters; the hybrid model re-scores risk every 15 minutes. Stack: Python 3, NumPy, SciPy, Numba, pandas, LightGBM, SHAP, scikit-learn, Plotly.js dashboard (static, works offline). Not a medical device.", options: { color: INK } }],
  { x: 0.55, y: 6.24, w: 12.35, h: 0.73, fontFace: F, fontSize: 11, margin: 0, valign: "middle", isTextBox: true });

pres.writeFile({ fileName: path.join(__dirname, "..", "Prahari_Architecture.pptx") }).then(f => console.log("wrote", f));

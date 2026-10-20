# Prahari: a digital twin that warns of a glucose spike up to two hours before it happens

**Digital Twin Challenge 2026 · Proof of concept for type 2 diabetes · Team Songer, IIM Visakhapatnam**

> Prahari (प्रहरी) means "sentinel". It keeps a living model of each patient, watches every CGM reading, and tells the doctor (and the patient) when a spike is coming, why, and what would prevent it.

| | |
|---|---|
| Live dashboard | `https://sid211220.github.io/Songer_IIMVisakhapatnam/` (GitHub Pages; the same file is [`docs/index.html`](docs/index.html) and works offline) |
| Demo video (unlisted YouTube) | **[Youtube](https://youtu.be/8H4d_eYjANs)** |
| Presentation (PDF / PPTX) | [`docs/Prahari_Presentation.pdf`](docs/Prahari_Presentation.pdf) · [`docs/Prahari_Presentation.pptx`](docs/Prahari_Presentation.pptx) |
| Architecture diagram (PDF / PPTX) | [`docs/Prahari_Architecture.pdf`](docs/Prahari_Architecture.pdf) · [`docs/Prahari_Architecture.pptx`](docs/Prahari_Architecture.pptx) |
| Licence | MIT ([`LICENSE`](LICENSE)) |

---

## 1. Team details

| Team name | Songer |
|---|---|
| Members | Siddharth Yadav (team lead; sole member: research, modelling, code, dashboard, presentation) |
| Team size | 1 |

## 2. College / incubator

**Indian Institute of Management Visakhapatnam (IIM Visakhapatnam)**, Andhra Pradesh, India.

## 3. Project title

**Prahari: a hybrid physiological-AI digital twin that predicts type 2 diabetes glucose spikes two hours ahead**

## 4. Problem statement

India has about **101 million adults with diabetes and 136 million with prediabetes** (ICMR-INDIAB, Anjana et al., 2023). The IDF estimates that **43% of adults with diabetes in India are undiagnosed** (IDF Diabetes Atlas, 11th ed.). About **62% of daily energy in Indian diets comes from carbohydrate** (Anjana et al., 2025), so large after-meal glucose spikes are part of everyday life for most patients.

Today a doctor sees a patient every few months and gets one number, HbA1c. It says nothing about *when* glucose goes high, *why*, or *what would have stopped it*. Continuous glucose monitors and smartwatches now produce that detail, but nobody joins it to the patient's medical record, and nobody turns it into a warning in time to act on it.

**The challenge asks for a digital twin that fuses the static record with live wearable data and predicts an adverse event.** Prahari predicts a hyperglycaemic spike (glucose above 180 mg/dL for at least 15 minutes, and a severe spike above 250 mg/dL) up to two hours ahead, explains the prediction, and lets the doctor test what would change it.

## 5. Healthcare use case

**Who:** adults with type 2 diabetes or prediabetes who wear a CGM (sensors lasting up to 14 days are sold in India) and a smartwatch, and their diabetologist or primary-care doctor.

**What the doctor gets (the dashboard):**
1. **A ranked list** of their patients by the risk of a spike in the next 2 hours.
2. **A 2-hour forecast** with an 80% band, next to the last 12 hours of CGM, meals and insulin.
3. **The reasons** for each alert (SHAP), in plain words: "the meal just logged is large", "the twin predicts a peak of 300", "short night".
4. **The patient's twin:** five personal physiological parameters (insulin sensitivity, fasting level, meal response, absorption speed, dawn effect), how they compare with other patients, and how they change day by day.
5. **What-if:** the twin runs in the browser. For PT-185, 14 minutes after a 132 g rice lunch, the twin says a 15-minute walk would cut her predicted peak from 297 to 283 mg/dL and her time above 180 from 120 to 105 minutes. At dinner, chapati instead of rice, a 70% portion and a walk bring the predicted peak from 268 to 195. This turns a consult into a concrete plan.
6. **The last 7 days:** ambulatory glucose profile, time in range, GMI and variability.

**What the patient gets:** at most one heads-up per 120 minutes, with one suggested action that the twin has simulated for them, for example a 15-minute walk now.

**Why it matters:** each 5% more time in range brings clinically meaningful benefit (Battelino et al., 2019). A walk after meals lowers post-meal glucose by 12% overall and by 22% after dinner (Reynolds et al., 2016). Prahari tells the patient *which* meal to walk after, before it happens.

## 6. What I built

```
Synthea EHR ─┐                         ┌─> 30/60/90/120-min forecast + 80% band
             ├─> ingestion ─> DIGITAL ─┼─> spike risk (>180, >250) + SHAP reasons
CGM + watch ─┘   (FHIR R4)    TWIN     └─> what-if answers ─> doctor dashboard / patient nudge
 + meal log
```

1. **A virtual population of 204 people** (94 with T2D, 110 with prediabetes; 107 women) taken from a Synthea run: age, sex, diagnosis, HbA1c, BMI, eGFR, blood pressure, lipids, medicines and comorbidities. A synthetic family history and polygenic risk percentile stand in for genetic markers, clearly labelled.
2. **21 days of Indian life per person:** north or south Indian meals (rice, chapati, idli, dosa, poha, biryani, chai with sugar), late dinners, walks, commutes, short nights, stressful work days, premixed insulin before breakfast and dinner. A hidden "true" physiology (Bergman minimal model with a two-speed gut, circadian and day-to-day sensitivity, stress, dawn effect, exercise, renal glucose loss) generates glucose minute by minute. From it I simulate what a **CGM** (5-min, MARD 9.5%, sensor change on day 11, gaps) and a **smartwatch** (heart rate, HRV as RMSSD, steps, sleep stages) would record, and what the patient **logs** (76% of meals, with carb-counting error).
3. **The digital twin** (`prahari/twin.py`) is deliberately simpler than the hidden physiology, so it faces real model mismatch:
   - **Prior from the EHR** (HbA1c, BMI, diagnosis, medicines).
   - **Onboarding week (days 1-7):** five personal parameters fitted by maximum a posteriori estimation, scoring the twin's own 30/60/120-min forecasts against CGM.
   - **Stays in sync:** every 5-min CGM reading corrects the twin's state; an observer term estimates glucose from food the patient did not log.
   - **Re-fits every night** on the trailing 7 days. Forecasts for a day use only parameters fitted before that day.
4. **The hybrid AI** (`prahari/models.py`): LightGBM uses the twin's forecasts and parameters together with CGM history, meals, insulin, steps, heart rate, HRV, sleep and the EHR. It predicts glucose at 30/60/90/120 minutes (with 10th/90th percentile models for the band) and the probability of a spike in the next 2 hours. SHAP gives the top reasons for every alert.
5. **The dashboard** (`docs/index.html`): one self-contained file, no server. It replays the held-out test fortnight for 14 test patients.

## 7. Results (41 held-out patients, days 8-21, 54,776 forecast moments)

All patients in the test set were unseen in training; thresholds were frozen on a separate validation set.

**Glucose forecast error (RMSE, mg/dL, against measured CGM)**

| Method | 30 min | 60 min | 120 min |
|---|---|---|---|
| Persistence (glucose stays where it is) | 32.2 | 46.4 | 57.3 |
| Linear autoregression on CGM | 26.7 | 35.2 | 37.8 |
| Digital twin alone (physiology only) | 21.9 | 28.8 | 39.0 |
| LightGBM, CGM only | 21.1 | 25.6 | 27.4 |
| LightGBM, + wearables + meal log | 18.3 | 22.3 | 25.3 |
| LightGBM, + EHR | 18.5 | 22.7 | 25.6 |
| **Prahari (all of the above + twin)** | **17.2** | **21.1** | **24.2** |

- **The twin adds forecasting accuracy that the data alone does not.** Against the same model without twin features, RMSE falls by 1.7 mg/dL at 60 min (95% CI 1.2-2.2, patient-level bootstrap) and 1.3 mg/dL at 120 min (CI 0.8-1.8).
- **It matters most right after a meal.** In the 45 minutes after a logged meal, 60-min RMSE is 41.3 with CGM only and **24.8 with Prahari**.
- **Errors in clinically acceptable zones:** 99.6% of 60-min forecasts fall in Clarke error grid zones A+B (87.2% in zone A).
- **The 80% band** contains the outcome 77-78% of the time (slightly narrow; noted under limits).

**Spike warnings.** To compare alert models fairly, each model's threshold is set on validation patients so that it sends the same number of notifications as Prahari's 70%-precision operating point (one notification at most every 120 minutes); results are on test patients.

| Spike above 180 mg/dL (about 2.9 notifications per patient-day) | AUROC | AUPRC | Spikes caught 15-120 min ahead | Median warning | Notifications that were right |
|---|---|---|---|---|---|
| LightGBM, CGM only | 21.1 | 25.6 | 27.4 |
| LightGBM, + wearables + meal log | 18.3 | 22.3 | 25.3 |
| LightGBM, + EHR | 18.5 | 22.7 | 25.6 |
| **Prahari (+ twin)** | **0.934** | **0.750** | **76%** | **85 min** | 60% |
| Twin's predicted peak alone | 0.684 | 0.468 | 78% | 35 min | 56% |

| Severe spike above 250 mg/dL (about 0.5 notifications per patient-day) | AUROC | AUPRC | Caught early | Median warning |
|---|---|---|---|---|
| LightGBM, CGM only | 21.1 | 25.6 | 27.4 |
| LightGBM, + wearables + meal log | 18.3 | 22.3 | 25.3 |
| **Prahari (+ twin)** | 0.953 | 0.546 | 37% | 70 min |
| Twin's predicted peak alone | 0.742 | 0.312 | 40% | 40 min |

What this says, plainly: **three in four spikes are flagged about 85 minutes before they start.** For alerts, the wearables and meal log add the most; the twin's features add little on top. The twin's own physics catches as many spikes, but only 35-40 minutes ahead; the learned model stretches the warning to 85 minutes by learning each person's routine. **Severe spikes stay hard** (about 4 in 10 caught). The twin earns its place through better forecasts, the reasons it gives, and the what-if answers, not through the alert score.

**The twin learns what the record cannot tell it.** The EHR prior alone ranks patients' insulin sensitivity poorly against the hidden truth (Spearman 0.37). After the onboarding week the twin reaches **0.81**, and 0.82 by day 21. (Basal glucose is mostly predictable from HbA1c already: 0.80 from the prior, 0.83 after onboarding.) A twin re-fitted every night forecasts better than one frozen after week 1 (60-min RMSE 28.8 vs 30.5).

**The virtual population behaves like real people** (`results/simulator_validation.csv`):

| Check | Prahari simulator | Published |
|---|---|---|
| 15-min walk after a meal | 16% less post-meal glucose (IQR 12-19%) | 12% overall, 22% after dinner (Reynolds et al., 2016) |
| One 4-hour night | sensitivity -25%, +10% breakfast response | glucose infusion rate about -25% (Donga et al., 2010) |
| Dawn rise in T2D | median 12 mg/dL | median 16 mg/dL (Monnier et al., 2013) |
| Mean glucose vs HbA1c | r = 0.96 | r = 0.92, eAG = 28.7 x A1c - 46.7 (Nathan et al., 2008) |
| Time in range vs HbA1c | -18.5 points per 1% HbA1c | about -17 points per 1% (Beck et al., 2019) |
| CGM error (MARD) | 9.5% | 8.2-9.1% for Dexcom G7 (Garg et al., 2022) |

## 8. Technical stack

| Layer | Tools |
|---|---|
| Synthetic EHR | Synthea (Apache-2.0; build 29a7d63, seed 20261020, 1,500 people), filtered and minimised in `prahari/ehr.py`; FHIR R4 export (`docs/example_fhir_bundle_PT-164.json`) |
| Simulation and twin | Python 3.11+, NumPy, Numba (JIT, optional), SciPy (Nelder-Mead MAP fit) |
| Data | pandas, PyArrow (Parquet) |
| Machine learning | LightGBM (regression, quantile regression, classification), scikit-learn (ridge baseline, metrics), SHAP |
| Evaluation and figures | Matplotlib, custom Clarke error grid, patient-level bootstrap |
| Dashboard | Single HTML file, Plotly.js, vanilla JavaScript; the twin's equations are ported to JS for live what-if |
| Docs | pptxgenjs (architecture diagram and deck), LibreOffice (PDF) |
| Tests | pytest (`tests/test_core.py`) |

## 9. AI / ML model and framework details

**Digital twin (mechanistic).** State: plasma glucose, remote insulin action, plasma insulin, a two-compartment gut, two-compartment regular and NPH insulin depots, exercise sensitivity boost, interstitial glucose (8-min lag) and an unexplained-appearance term. Equations follow the Bergman minimal model (Bergman et al., 1979) with a simplified Dalla Man-style gut (Dalla Man et al., 2007). Personal parameters: insulin sensitivity, basal glucose, meal gain, absorption rate, dawn amplitude. Fit: MAP with EHR-informed Gaussian priors (log scale), loss = squared error of the twin's own open-loop 30/60/120-min forecasts on CGM every 30 min. Synchronisation: a fixed-gain observer (gain 0.25 on glucose, 0.0025 on the disturbance term, 45-min decay).

**Hybrid learner.** 87 features, one row per patient per 15 minutes, built only from information available before that moment (`prahari/features.py`): 25 CGM features, 27 lifestyle features (meals, habitual-meal timing learned in week 1, insulin, steps, heart rate, HRV z-score against the person's own baseline, sleep, a stress proxy), 18 EHR features, 17 twin features. LightGBM (500 trees for regression, 400 for classification; 31 leaves; learning rate 0.04) predicts the change in glucose at each horizon; quantile models give the 80% band; a classifier gives spike probability. Patient-level 60/20/20 split stratified by diagnosis. Ablation with growing feature groups shows what each data source adds.

**Explainability.** SHAP TreeExplainer (Lundberg & Lee, 2017) on the spike classifier; the top three features pushing risk up are shown as plain-language reasons, de-duplicated.

**Leakage controls.** Patient-level split; features use readings up to t-5 min; meals count only once logged; habits come from the onboarding week; last night's sleep counts only once the watch sees the patient wake; twin parameters used on day d are fitted only on CGM from before day d; spike episodes need 30 minutes of in-range readings (gaps do not count) before onset.

## 10. Data, privacy and regulation

- **Only synthetic data.** Synthea patients are entirely synthetic (Walonoski et al., 2018). Lifestyle, CGM and watch data are simulated by this repo. No real person's data was used.
- `data/synthea/` keeps only the fields the model needs (no names, addresses or identifiers), following the data-minimisation idea of India's DPDP Act 2023; the DPDP Rules' main obligations apply from 13 May 2027.
- Records export as FHIR R4, the standard used by ABDM's FHIR implementation guide (v6.5.0).
- Synthea's HbA1c sometimes conflicts with the coded diagnosis (for example 2.4%). I repair these values within the diagnosis range and flag them (`hba1c_repaired`); every repair is reproducible.
- A real deployment would be software as a medical device in India (CDSCO risk-based classes A-D) and would need clinical validation. **Prahari is a research prototype, not a medical device.**

## 11. How to run it

```bash
pip install -r requirements.txt
python scripts/run_all.py          # simulate -> twins -> features -> models -> evaluation (~15-20 min, 2 cores)
python -m prahari.dashboard        # rebuild docs/index.html
python -m pytest -q                # 9 tests
```

Already included, so you can look without running anything: the dashboard (`docs/index.html`), trained models (`models/`), metrics and figures (`results/`), the simulated cohort (`data/processed/`). Large intermediate files (feature table, predictions) are regenerated by `run_all.py`.

```
prahari/        ehr.py · foods.py · simulate.py · cohort.py · twin.py · features.py · models.py · evaluate.py · validate_sim.py · dashboard.py
dashboard/      template.html (dashboard source)
docs/           index.html (dashboard) · architecture · presentation · SOURCES.md · MODEL_CARD.md · VIDEO_SCRIPT.md
data/synthea/   filtered Synthea CSVs (EHR layer)
data/processed/ simulated cohort and twin outputs (Parquet)
models/         LightGBM models, thresholds, patient split
results/        metrics.json, tables, figures
```

## 12. Limits (read before trusting any number)

- **Every result comes from synthetic people.** The virtual patients follow routines more regular than real life, so these errors are lower than on real CGM data. On the real OhioT1DM dataset, published deep models reach about 20-24 mg/dL at 30 min and 55-66 mg/dL at 120 min (Tena et al., 2021); a real-world study is the only fair test.
- At HbA1c about 7%, my virtual patients spend about 81% of time in range against about 70% in real cohorts (Beck et al., 2019): they are a little steadier than real patients.
- The simulated cohort has no true hypoglycaemia (lowest simulated glucose 75 mg/dL; only sensor noise dips below 70), so Prahari does not yet predict lows.
- Many alerts fire before habitual meals: the model learns each person's routine. That is useful (plan the meal) but it is not magic.
- The 80% band covers 77-78% of outcomes; it needs conformal calibration before clinical use.
- About 4 in 10 notifications are not followed by a spike, and only about 4 in 10 severe spikes are caught early. Both need work before patients get phone alerts.
- Not a medical device; not for clinical decisions.

## 13. Next steps

1. Validate on real CGM data (e.g. open T2D CGM datasets such as ShanghaiT2DM) and on a small consented cohort in India.
2. Add hypoglycaemia risk for insulin users, conformal prediction bands, and meal-photo carb estimation.
3. Pilot with one diabetology clinic: doctor dashboard plus patient nudges, measuring change in time in range over 12 weeks.

## 14. Open-source licence

Code: **MIT** (see [`LICENSE`](LICENSE)). Synthea is Apache-2.0; its synthetic output is used under that licence. The dashboard embeds Plotly.js (MIT). All files and links in this repository are public.

## 15. References

Full APA list with links: [`docs/SOURCES.md`](docs/SOURCES.md).

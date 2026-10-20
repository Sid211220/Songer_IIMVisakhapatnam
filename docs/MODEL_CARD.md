# Model and data card: Prahari v1.0

## Intended use
Research prototype for the Digital Twin Challenge 2026. It shows how a personal physiological twin and machine learning could warn a clinician about a hyperglycaemic spike in adults with type 2 diabetes or prediabetes who wear a CGM and a smartwatch. **Not a medical device. Not for diagnosis, dosing or any clinical decision.**

## Data
| Item | Detail |
|---|---|
| EHR | Synthea, 1,500 synthetic people generated (seed 20261020); 204 adults aged 25-80 kept: all 94 alive with active T2D, plus 110 sampled with prediabetes |
| Fields kept | birth date, sex, conditions, medicines, HbA1c, glucose, BMI, weight, height, heart rate, BP, eGFR, lipids, urine albumin-creatinine ratio |
| Repairs | HbA1c outside the diagnosis range re-drawn inside it (T2D 6.0-12%, prediabetes 5.7-6.4%); flagged in `hba1c_repaired` (T2D 36%, prediabetes 5%). Insulin removed from prediabetes records (`insulin_repaired`) |
| Synthetic genetics | `syn_family_history`, `syn_prs_percentile`: seeded random draws, labelled synthetic |
| Streams | 21 days per person, 5-min CGM, heart rate, RMSSD, steps, sleep stage; 16,354 meals (76% logged); insulin doses for the 18 insulin users |
| Split | patients 60/20/20 (122/41/41), stratified by diagnosis; days 1-7 onboarding, days 8-21 evaluation |

## Models
| Component | Method |
|---|---|
| Twin | Minimal-model ODE, 1-min Euler; 5 personal parameters by MAP (Nelder-Mead) with EHR priors; fixed-gain observer for synchronisation; nightly re-fit on the trailing 7 days, scored only on CGM inside that window |
| Forecast | LightGBM regression of glucose change at 30/60/90/120 min; quantile models (10th/90th) |
| Spike risk | LightGBM classifier: onset >180 (or >250) mg/dL sustained >= 15 min within 120 min, after >= 30 min in range |
| Alert rule | threshold = lowest score reaching 70% per-moment precision on validation patients; 120-min cooldown (about 60% of notifications are right on test) |
| Explanations | SHAP TreeExplainer, top 3 risk-raising features in plain words |

## Performance (test patients, days 8-21)
See `results/metrics.json`, `results/forecast_metrics.csv`, `results/alert_metrics.csv`. Headline: RMSE 17.2 / 21.1 / 24.2 mg/dL at 30 / 60 / 120 min; 99.6% Clarke A+B at 60 min; at about 2.9 notifications per patient-day, 76% of spikes >180 are flagged 15-120 min ahead (median 85 min) and 60% of notifications are followed by a spike; severe spikes >250 are caught 37% of the time at about 0.5 notifications per patient-day.

## Known limitations
- Synthetic people are more regular than real ones; expect higher error on real data.
- No hypoglycaemia in the simulated cohort; lows are not predicted.
- The 80% band covers 77-78% of outcomes (under-dispersed).
- Twin features improve forecasts but add little to alert discrimination over wearables and meal logs.
- Population follows Synthea's US demographics; only the lifestyle layer is India-calibrated.
- Alerts before habitual meals reflect routine, not physiology alone.

## Ethical notes
No real person's data. A real deployment needs informed consent under India's DPDP framework, ABDM-compliant data exchange, CDSCO software-as-medical-device classification and a prospective clinical study. Alerts should go to a clinician-configured workflow, not replace medical advice.

# Sources (APA 7)

Every external number used in the README, dashboard or presentation, with where it was checked. "Secondary" means the number was read on a reputable secondary page because the primary page was not reachable from my build environment.

## Burden and diet in India
- Anjana, R. M., Unnikrishnan, R., Deepa, M., et al. (2023). Metabolic non-communicable disease health report of India: The ICMR-INDIAB national cross-sectional study (ICMR-INDIAB-17). *The Lancet Diabetes & Endocrinology, 11*(7), 474–489. https://doi.org/10.1016/S2213-8587(23)00119-5 — diabetes 11.4%, prediabetes 15.3% (abstract); 101 million and 136 million (secondary: IANS report, 9 June 2023).
- International Diabetes Federation. (2025). *IDF Diabetes Atlas* (11th ed.). India country page: https://diabetesatlas.org/data-by-location/country/india/ — 89.8 million adults (20–79) with diabetes in 2024; 43.0% undiagnosed.
- Anjana, R. M., Sudha, V., Abirami, K., et al. (2025). Dietary profiles and associated metabolic risk factors in India from the ICMR-INDIAB survey-21. *Nature Medicine*. https://doi.org/10.1038/s41591-025-03949-4 — 62% of energy from carbohydrate (secondary: ETV Bharat, 30 Sept 2025).
- Henry, C. J., Quek, R. Y. C., Kaur, B., Shyam, S., & Singh, H. K. G. (2021). A glycaemic index compendium of non-western foods. *Nutrition & Diabetes, 11*, 2. https://doi.org/10.1038/s41387-020-00145-w — GI values in `prahari/foods.py` marked "Henry2021".
- National Institute of Nutrition (ICMR) GI measurements, chapati 62 and plain dosa 79 (secondary: The South First, 27 Jan 2025) — marked "NIN" in `prahari/foods.py`.

## Glucose targets and CGM
- Battelino, T., Danne, T., Bergenstal, R. M., et al. (2019). Clinical targets for continuous glucose monitoring data interpretation: Recommendations from the international consensus on time in range. *Diabetes Care, 42*(8), 1593–1603. https://doi.org/10.2337/dci19-0028 — TIR 70–180 > 70%; level 2 hyperglycaemia > 250 mg/dL.
- Beck, R. W., Bergenstal, R. M., Cheng, P., Kollman, C., Carlson, A. L., Johnson, M. L., & Rodbard, D. (2019). The relationships between time in range, hyperglycemia metrics, and HbA1c. *Journal of Diabetes Science and Technology, 13*(4), 614–626. https://doi.org/10.1177/1932296818822496 — TIR 70% ≈ HbA1c 7%; +10% TIR ≈ −0.6% HbA1c.
- Nathan, D. M., Kuenen, J., Borg, R., Zheng, H., Schoenfeld, D., & Heine, R. J., for the ADAG Study Group. (2008). Translating the A1C assay into estimated average glucose values. *Diabetes Care, 31*(8), 1473–1478. https://doi.org/10.2337/dc08-0545 — eAG = 28.7 × A1C − 46.7; r = 0.92.
- Garg, S. K., Kipnes, M., Castorino, K., et al. (2022). Accuracy and safety of Dexcom G7 continuous glucose monitoring in adults with diabetes. *Diabetes Technology & Therapeutics, 24*(6), 373–380. https://doi.org/10.1089/dia.2022.0011 — MARD 8.2% (arm), 9.1% (abdomen).
- American Diabetes Association Professional Practice Committee. (2025). 6. Glycemic goals and hypoglycemia: Standards of care in diabetes—2025. *Diabetes Care, 48*(Suppl. 1), S128–S145. https://doi.org/10.2337/dc25-S006 — peak post-meal glucose < 180 mg/dL.
- Clarke, W. L., Cox, D., Gonder-Frederick, L. A., Carter, W., & Pohl, S. L. (1987). Evaluating clinical accuracy of systems for self-monitoring of blood glucose. *Diabetes Care, 10*(5), 622–628.

## Lifestyle effects used to build and check the simulator
- Reynolds, A. N., Mann, J. I., Williams, S., & Venn, B. J. (2016). Advice to walk after meals is more effective for lowering postprandial glycaemia in type 2 diabetes mellitus than advice that does not specify timing: A randomised crossover study. *Diabetologia, 59*(12), 2572–2578. https://doi.org/10.1007/s00125-016-4085-2 — 12% lower overall, 22% after the evening meal (secondary: HCPLive).
- Buffey, A. J., Herring, M. P., Langley, C. K., Donnelly, A. E., & Carson, B. P. (2022). The acute effects of interrupting prolonged sitting time in adults with standing and light-intensity walking on biomarkers of cardiometabolic health in adults: A systematic review and meta-analysis. *Sports Medicine, 52*(8), 1765–1787. https://doi.org/10.1007/s40279-022-01649-4
- Donga, E., van Dijk, M., van Dijk, J. G., Biermasz, N. R., Lammers, G.-J., van Kralingen, K. W., Corssmit, E. P. M., & Romijn, J. A. (2010). A single night of partial sleep deprivation induces insulin resistance in multiple metabolic pathways in healthy subjects. *The Journal of Clinical Endocrinology & Metabolism, 95*(6), 2963–2968. https://doi.org/10.1210/jc.2009-2430 — glucose infusion rate about −25% after ~4 h sleep.
- Monnier, L., Colette, C., Dejager, S., & Owens, D. (2013). Magnitude of the dawn phenomenon and its impact on the overall glucose exposure in type 2 diabetes: Is this of concern? *Diabetes Care, 36*(12), 4057–4062. https://doi.org/10.2337/dc12-2127 — median dawn rise 16 mg/dL (range 0–31.5), 248 people.
- Coopmans, C., et al. (2020). Both prediabetes and type 2 diabetes are associated with lower heart rate variability: The Maastricht Study. *Diabetes Care*. PMID 32161051 — direction of HRV effect used in the watch simulator.

## Models and methods
- Bergman, R. N., Ider, Y. Z., Bowden, C. R., & Cobelli, C. (1979). Quantitative estimation of insulin sensitivity. *American Journal of Physiology, 236*(6), E667–E677. https://doi.org/10.1152/ajpendo.1979.236.6.E667
- Dalla Man, C., Rizza, R. A., & Cobelli, C. (2007). Meal simulation model of the glucose-insulin system. *IEEE Transactions on Biomedical Engineering, 54*(10), 1740–1749. https://doi.org/10.1109/TBME.2007.893506
- Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., & Liu, T.-Y. (2017). LightGBM: A highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems, 30*.
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems, 30*.
- Walonoski, J., Kramer, M., Nichols, J., Quina, A., Moesel, C., Hall, D., Duffett, C., Dube, K., Gallagher, T., & McLachlan, S. (2018). Synthea: An approach, method, and software mechanism for generating synthetic patients and the synthetic electronic health care record. *Journal of the American Medical Informatics Association, 25*(3), 230–238. https://doi.org/10.1093/jamia/ocx079
- Tena, F., Garnica, O., Lanchares, J., & Hidalgo, J. I. (2021). *A critical review of the state-of-the-art on deep neural networks for blood glucose prediction in patients with diabetes* (arXiv:2109.02178). https://arxiv.org/abs/2109.02178 — OhioT1DM RMSE 19.7–23.6 (30 min), 54.7–65.8 (120 min).
- Sun, Y., & Kosmas, P. (2024). *Integrating Bayesian approaches and expert knowledge for forecasting continuous glucose monitoring values in type 2 diabetes mellitus* (arXiv:2409.07315). https://arxiv.org/abs/2409.07315 — ShanghaiT2DM RMSE 13.5 (30 min), 21.4 (60 min).

## Digital twins
- National Academies of Sciences, Engineering, and Medicine. (2024). *Foundational research gaps and future directions for digital twins*. The National Academies Press. https://doi.org/10.17226/26894 — definition of a digital twin.
- Shamanna, P., Joshi, S., Thajudeen, M., Shah, L., Poon, T., Mohamed, M., & Mohammed, J. (2024). Personalized nutrition in type 2 diabetes remission: Application of digital twin technology for predictive glycemic control. *Frontiers in Endocrinology, 15*, 1485464. https://doi.org/10.3389/fendo.2024.1485464 — Indian randomised trial, HbA1c 9.0% → 6.1% at one year in the twin arm (interim).

## India: data protection, health data standards, devices
- Ministry of Electronics and Information Technology. (2025). *Digital Personal Data Protection Rules, 2025* (notified 13 November 2025; main duties from 13 May 2027). Secondary: AZB & Partners via Mondaq, 21 Nov 2025.
- National Resource Centre for EHR Standards. (2025). *ABDM FHIR implementation guide* (v6.5.0, FHIR R4). https://nrces.in/ndhm/fhir/r4/index.html
- Press Information Bureau. (2026, July 6). *Ayushman Bharat Digital Mission* — over 93 crore ABHA accounts. https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/jul/doc202676912801.pdf
- Emergo by UL. (2026, July 30). *India CDSCO finalizes guidance on medical device software* — risk classes A–D. https://www.emergobyul.com/news/india-cdsco-finalizes-guidance-medical-device-software
- IDC. (2026, March 2). *India wearables market, full-year 2025* — 114.2 million units. https://www.idc.com/resource-center/press-releases/india-wearables-market-fy2025/

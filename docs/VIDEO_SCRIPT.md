# Demo video script (about 20-21 minutes)

Word-for-word narration for the submission video. It follows `Prahari_Video_Deck.pptx`: the presentation with the live dashboard demo embedded as slide 11. Speak at a relaxed pace, about 125-130 words a minute; a one-second pause between slides is fine.

## How to record (PowerPoint, about 30 minutes of work)

1. Open `Prahari_Video_Deck.pptx` in PowerPoint (Microsoft 365 or 2019 and later, Windows or Mac).
2. Use earphones with a mic in a quiet room. Go to **Slide Show > Record** (or **Record > From Beginning**). The speaker notes show as a teleprompter; they are the same words as this script.
3. Read each slide's notes, then press the right arrow.
4. On slide 11 (*Live demo*), **click the video once to start it**, then read the demo narration below. Timestamps are video time, so glance at the video's timer and keep pace. If you are ahead, pause; if you fall behind, skip a sentence.
5. Stop recording after the last slide. Then **File > Export > Create a Video > Full HD (1080p) > Use Recorded Timings and Narrations > Create Video**.
6. Upload the MP4 to YouTube as **Unlisted**, title it *Prahari: Digital Twin Challenge 2026, Team Songer (IIM Visakhapatnam)*, and paste the link into `README.md` in place of `REPLACE_WITH_YOUR_UNLISTED_LINK`.

If PowerPoint recording gives trouble, any screen recorder works: show the slides full screen, and for the demo part play `Prahari_Dashboard_Demo_silent.mp4` full screen while you read.

---

## 0:00 · Slide 1 · Title

Hello, I am Siddharth Yadav from IIM Visakhapatnam, and this is Prahari, my entry for the Digital Twin Challenge 2026. Prahari means sentinel. It is a digital twin for people with type 2 diabetes. It joins a patient's medical record with their continuous glucose monitor and smartwatch, keeps a personal model of their body up to date, and warns the doctor and the patient about a glucose spike up to two hours before it happens. It also explains why, and it lets you simulate what would prevent it. Everything you will see runs on synthetic patients, so no real person's data was used.

## 0:51 · Slide 2 · India's diabetes problem is a timing problem: the spikes happen after meals, the doctor sees one number every three months

Start with the scale. ICMR-INDIAB estimates that about 101 million Indian adults have diabetes and another 136 million have prediabetes. The IDF estimates that 43 percent of adults with diabetes in India do not even know it. And our diets are heavy in carbohydrate: about 62 percent of daily energy, according to the ICMR-INDIAB diet study. So the real damage happens after meals, many times a day. But what does the doctor see? Usually one HbA1c value every three months. It tells you the average. It does not tell you when glucose goes high, why, or what would have stopped it. CGMs and watches now capture that detail every five minutes, but the data sits in separate apps, nobody joins it to the medical record, and nobody turns it into a warning early enough to act on. That is the gap Prahari fills.

## 2:01 · Slide 3 · Prahari gives the doctor four things today's care cannot: a warning, a reason, a personal model and a what-if

So what does Prahari actually give the doctor? Four things. First, a warning: every 15 minutes it estimates the chance of a spike above 180, and of a severe spike above 250, in the next two hours, with a forecast and an uncertainty band. Second, an explanation: the top three reasons behind each alert, in plain words, so the doctor is never asked to trust a black box. Third, personalisation: every patient has a twin with five physiological parameters that are re-fitted every night. And fourth, action: the doctor can ask the twin what would happen if the patient walked for 15 minutes, ate a smaller portion or slept badly, and the patient gets at most one heads-up every two hours, with an action the twin has simulated for them.

## 3:05 · Slide 4 · Five layers: data in, ingest and protect, the digital twin, hybrid AI, and the clinic

Here is the architecture. On the left, two kinds of data come in: the static health record, which gives age, diagnosis, HbA1c, kidney function, medicines and genetic risk; and the dynamic streams: CGM every five minutes, heart rate, heart-rate variability, steps and sleep stages from a watch, plus meals and insulin doses the patient logs. The ingestion layer converts the record to FHIR R4, the standard India's ABDM uses, keeps only the fields the model needs, and enforces one rule everywhere: at time t, only use information from before t. The third layer is the digital twin itself. It starts from a prior set by the record, is fitted to the patient in the first week, stays in sync with every CGM reading, and re-fits every night. The fourth layer is a hybrid AI model that combines the twin's forecast with all the other data. And the fifth layer is the clinic: a dashboard for the doctor and nudges for the patient.

## 4:24 · Slide 5 · 204 synthetic people lived 21 days of Indian routines, with a hidden physiology the twin never sees

The challenge allows synthetic data, so I built a virtual population. The static record comes from Synthea, an open-source synthetic patient generator. I kept 204 adults: all 94 with type 2 diabetes and 110 with prediabetes, with their labs, medicines and conditions. Synthea has no genetics, so I added a synthetic family history and a polygenic risk percentile, clearly labelled. Synthea sometimes produces an HbA1c that contradicts the diagnosis, like 2.4 percent, so I repair those within the right range and flag every repair. Then each person lives 21 days of an Indian routine: north or south Indian meals, tea with sugar, late dinners, walks, short nights and stressful days. A hidden physiology turns that into true glucose minute by minute, and I simulate what a CGM and a watch would record, including sensor noise and gaps. Importantly, this hidden physiology is richer than the twin. The twin never sees it, so it faces real model mismatch, just as it would with a real patient.

## 5:44 · Slide 6 · The virtual patients respond the way published studies say real patients do

A synthetic population is only useful if it behaves like real people, so I checked it against published studies. A 15-minute walk after a meal lowers post-meal glucose by 16 percent in my simulator; Reynolds and colleagues found 12 percent overall and 22 percent after dinner. A four-hour night cuts insulin sensitivity by a quarter, in line with Donga's study. The dawn rise, mean glucose against HbA1c, the slope of time in range against HbA1c and the CGM sensor error all sit close to published values. The chart on the right shows one virtual patient eating the same lunch on three days: a normal day, with a walk, and after a short night.

## 6:40 · Slide 7 · The twin is a living model: built from the record, fitted in week one, synced every 5 minutes, re-fitted every night

Now the heart of it: the twin. It is a compact physiological model of glucose and insulin, based on the Bergman minimal model, with a gut, insulin injections, exercise and the effect of sleep loss. It works in four steps. First, a prior from the medical record: HbA1c, BMI, diagnosis and medicines set the starting values. Second, onboarding: in the first week I fit five personal parameters, insulin sensitivity, fasting level, meal response, absorption speed and the dawn effect, by asking the twin to forecast glucose two hours ahead and correcting it where it was wrong. Third, synchronisation: every five-minute CGM reading nudges the twin's state, and a disturbance term soaks up food the patient forgot to log. Fourth, it re-fits every night on the last seven days. Does the twin learn something real? Because I know the hidden truth, I can check. From the record alone you can barely rank patients by insulin sensitivity: the rank correlation with the truth is 0.37. After one week of wearing a CGM, the twin reaches 0.81. That is information the record simply does not contain. And a twin that re-fits every night forecasts better than one frozen after week one.

## 8:16 · Slide 8 · A hybrid model: the twin's physics plus machine learning on every data source, with no look-ahead

The twin alone is good, but physics cannot know everything, for example that this person always has a big dinner at 9. So Prahari is hybrid. A LightGBM model gets 87 features from four groups: the CGM history, lifestyle signals from the watch and the meal log, the medical record, and the twin's own forecast and parameters. It predicts glucose at 30, 60, 90 and 120 minutes, with an uncertainty band, and the probability of a spike. The alert threshold is fixed on separate validation patients and never touched again. I was strict about leakage: test patients are never seen in training, every feature uses only information from before the moment of prediction, and a meal counts only once the patient has logged it.

## 9:17 · Slide 9 · Prahari forecasts glucose 2 hours ahead with an error of 24.2 mg/dL, less than half of 'no change'

Here are the forecasting results on 41 patients the model had never seen, over two weeks. The bars show the error two hours ahead. Assuming glucose stays where it is gives an error of 57 milligrams per decilitre. The twin alone gets 39. Machine learning on CGM alone gets 27.4. Adding wearables and meals helps, and adding the twin gives the best result, 24.2. The twin's contribution is small on average but statistically solid: about 1.7 milligrams per decilitre at one hour, with a confidence interval well above zero. Where it really matters is right after a meal, which is exactly when a spike is building: there, the one-hour error drops from 41 with CGM alone to 25 with Prahari. And 99.6 percent of forecasts fall in the clinically acceptable zones of the Clarke error grid.

## 10:24 · Slide 10 · It flags 3 in 4 spikes about 85 minutes before they start; severe spikes remain the hard part

Now the adverse-event prediction the challenge asks for. A spike means glucose above 180 for at least 15 minutes. To compare models fairly, I set every model to send the same number of notifications, about 3 per patient per day. At that budget Prahari flags 76 percent of spikes at least 15 minutes before they start, with a median warning of 85 minutes, and 60 percent of its notifications are followed by a spike. I want to be honest about what does the work here. For alerts, the wearables and the meal log add the most, from 73 to 75 percent, and the twin adds only a little on top. Interestingly, the twin's physics on its own flags 78 percent of spikes, but only 35 minutes ahead, because it only knows about meals already eaten. The learned model stretches that warning to 85 minutes by learning each person's routine. Severe spikes above 250 are still hard: about 37 percent are flagged early. So the twin earns its place through better forecasts, the reasons it gives and the what-if answers, more than through the alert score.

## 11:53 · Slide 11 · Live demo (video, 7 minutes)

*Click the video to start it. Times below are video time.*

**[0:05]** Here is the dashboard running live. It is one HTML file in the repository, so it opens on any laptop without a server, and it is also on GitHub Pages. I am replaying the test fortnight. Right now it is 2:15 in the afternoon on Monday the 21st of September, day 15.

**[0:30]** On the left is the clinic's patient list: fourteen held-out test patients, ranked by the risk of a spike above 180 in the next two hours. Each row shows the current glucose, a trend arrow and the risk. 'High now' means the patient is already above 180.

**[0:50]** The top patient is PT-185: a 44-year-old woman with type 2 diabetes, HbA1c 7.3 percent, on metformin, with hypertension and obesity. This comes from her synthetic health record.

**[1:05]** The alert card says 95 percent risk of going above 180 and 38 percent risk of going above 250, with a forecast high of about 307 within the hour. Her glucose right now is only 141, so the number alone looks fine. The reasons: the twin's predicted peak, the time of day, and how variable her glucose has been in the last three hours. And the suggested nudge: a 15-minute walk now would take about 14 off her peak.

**[1:35]** This chart shows why. In black, her last twelve hours of CGM. The orange triangle is the lunch she logged 14 minutes ago: two katori of rice with dal and curd, about 132 grams of carbohydrate. The teal line is Prahari's forecast with its 80 percent band, and the dashed orange line is the twin on its own. In grey, because this is a replay, you can see what actually happened: she peaked at about 339, higher than forecast. It was a short night and a stressful working day for her, and the model cannot see stress directly. That is a real limit, and the band shows the uncertainty.

**[2:10]** Now the what-if panel. This runs her calibrated twin inside the browser. With no walk, the twin predicts a peak of 297 and two hours above 180. A 15-minute walk brings the peak to 283 and saves fifteen minutes above 180. A 30-minute walk brings it to 269.

**[2:36]** She slept only 4.9 hours last night. If she had slept a full seven and a half hours, the same walk would bring the peak to 275, because sleep loss lowers insulin sensitivity.

**[2:50]** Here is her twin. Her record suggested an insulin sensitivity of 2.9; after two weeks of CGM, the twin estimates 5.4, so she responds to insulin better than her record implied. But her fasting level is higher than expected, 149 against 130. That tells a doctor where to look first: her mornings and her large meals.

**[3:15]** Below are the wearables for the last 24 hours: steps, heart rate, heart-rate variability and last night's sleep stages. You can see the short night. On the right, her last seven days as an ambulatory glucose profile: 77 percent time in range, with clear peaks after lunch and dinner.

**[3:45]** Let me press play and move time forward. Every step is 15 minutes, and the list re-ranks itself as patients eat, walk and sleep. I will stop at 8 pm, before dinner.

**[4:17]** It is 8 pm and dinner is coming. The doctor can plan it with her. Two katori of rice would take her to a predicted 268. Switching to chapati, dal and sabzi brings that to 224, and with a 15-minute walk, 215. Cut the portion to 70 percent as well and the peak is 195, and time above 180 falls from two hours to about 70 minutes. This is the kind of concrete, personal advice that a single HbA1c number cannot give.

**[4:53]** Now another patient: PT-046, a 58-year-old man with prediabetes. His risk is 56 percent, just over the alert threshold, with a forecast high of 193 in two hours. The reasons say his usual dinner time is approaching. Prahari learned his routine in the first week, so it can warn before a meal, not only after it.

**[5:17]** The alerts filter shows only the patients above the alert threshold right now. At 8 pm on this Monday, that is four of the fourteen.

**[5:27]** The model evidence tab is for the jury and for clinicians who want to check the numbers. First, forecast error on the 41 held-out patients: Prahari is the best at every horizon, 17.2 at 30 minutes and 24.2 at two hours. Next, the alerts: about three in four spikes above 180 are flagged with a median 85-minute warning. Severe spikes above 250 remain hard. Then the SHAP chart, what drives an alert overall; teal bars come from the twin. Then the identifiability check: the twin's estimates against the hidden truth, a rank correlation of 0.81 for insulin sensitivity, against 0.37 from the record alone. And at the bottom, the realism checks against published studies.

**[6:38]** Finally, the How it works tab summarises the five layers and the limits, so anyone opening the page understands what they are looking at. That is the live demo. Let me close with how this would work in India.

## 18:53 · Slide 12 · Built for India's health stack: FHIR records, data minimisation, and a clear path through regulation

How would this work in India? On interoperability, records move as FHIR R4, the standard in ABDM's FHIR implementation guide, and more than 93 crore ABHA accounts already exist to link them. On privacy, Prahari keeps only the fields the model needs and is designed around consent and purpose limits under the DPDP Rules, whose main duties apply from May 2027. On regulation, a tool that supports clinical decisions would be software as a medical device under CDSCO's risk-based classes, so the honest next step is validation on real CGM data and then a 12-week pilot with one diabetology clinic, measuring whether patients spend more time in range.

## 19:47 · Slide 13 · What these results do not show yet, and what I would do next

I want to be clear about what these results do not show. Every patient here is synthetic, and synthetic people are more regular than real ones, so error on real data will be higher. For comparison, published deep-learning models on the real OhioT1DM dataset have errors of 55 to 66 at two hours. My virtual patients are also a little steadier than real ones, there are no lows in the cohort, so Prahari does not predict hypoglycaemia yet, and the uncertainty band is slightly too narrow. Next, I would validate on real CGM data, add low-glucose risk for insulin users, estimate carbs from meal photos so logging takes one tap, and run a 12-week pilot with a clinic.

## 20:45 · Slide 14 · Close

To sum up: Prahari gives every patient a twin, gives early warning of most spikes, explains every warning, and suggests an action the twin has already simulated. The code, data, models and results are all in the public GitHub repository under an MIT licence, and you can rebuild everything with one command. Thank you for watching.

---

Estimated total: about 21 minutes 15 seconds.
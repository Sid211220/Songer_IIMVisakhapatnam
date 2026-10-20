"""The 'physical twin' stand-in: a virtual patient population that lives 21 days.

For every Synthea patient we generate an India-calibrated daily routine, run a
glucose-insulin physiology model minute by minute, and derive what a phone, a
smartwatch and a continuous glucose monitor (CGM) would record.

Important: this "true patient" model is deliberately RICHER than the twin's own
model (prahari/twin.py). It has two-speed gut absorption, circadian insulin
sensitivity, day-to-day variability, stress days, exercise after-effects,
counter-regulation, unlogged snacks, carb-counting errors and CGM sensor error.
The twin never sees these hidden parts, so its forecasts face real model mismatch.

Physiology follows the Bergman minimal model (Bergman et al., 1979) with a
Dalla Man et al. (2007)-style gastric emptying and gut absorption chain.
Lifestyle effect sizes are anchored to published studies (see docs/SOURCES.md):
 - one 4-hour night lowers insulin sensitivity ~20-25% (Donga et al., 2010)
 - walking after meals lowers post-meal glucose ~12-22% (Reynolds et al., 2016)
 - HbA1c -> mean glucose: eAG = 28.7 x HbA1c - 46.7 (Nathan et al., 2008)
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .config import DAYS, SEED, STEP_MIN
from .foods import MEALS, meal_totals, describe

try:
    from numba import njit
except Exception:  # numba is optional; pure Python works, just slower
    def njit(*a, **k):
        def wrap(f):
            return f
        return wrap(a[0]) if a and callable(a[0]) else wrap

START_DATE = pd.Timestamp("2026-09-07")  # a Monday
MIN_PER_DAY = 1440
T = DAYS * MIN_PER_DAY


def _rng(pid: str, salt: int = 0) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha256(f"{pid}|{SEED}|{salt}".encode()).hexdigest()[:12], 16))


# ----------------------------------------------------------------------------- persona
def make_persona(p: dict) -> dict:
    g = _rng(p["patient_id"], 1)
    region = "south" if g.random() < 0.5 else "north"
    level = g.choice(["sedentary", "moderate", "active"], p=[0.5, 0.35, 0.15])
    return dict(
        region=region,
        activity=level,
        wake=float(g.normal(6.6, 0.45)),              # hours
        bedtime=float(g.normal(23.2, 0.6)),
        portion=float(np.clip(g.normal(1.0, 0.13), 0.75, 1.3)) * (1.05 if p["sex"] == "M" else 0.92),
        p_post_dinner_walk=float(np.clip(g.beta(1.5, 3.0), 0, 0.85)),
        p_morning_walk={"sedentary": 0.05, "moderate": 0.3, "active": 0.7}[level],
        p_commute_walk={"sedentary": 0.3, "moderate": 0.6, "active": 0.8}[level],
        base_steps={"sedentary": 2.2, "moderate": 3.5, "active": 4.5}[level],
        p_short_night=float(np.clip(g.normal(0.12, 0.05), 0.02, 0.3)),
        p_stress=float(np.clip(g.normal(0.15, 0.06), 0.03, 0.35)),
        log_adherence=float(np.clip(g.normal(0.85, 0.08), 0.6, 0.98)),
        p_evening_snack=float(np.clip(g.normal(0.7, 0.15), 0.2, 0.95)),
    )


# ----------------------------------------------------------------------------- lifestyle
def make_lifestyle(p: dict, persona: dict):
    """Minute-level inputs plus event logs (meals, doses, sleep) for DAYS days."""
    g = _rng(p["patient_id"], 2)
    fast = np.zeros(T)            # mg of fast-absorbing carbohydrate eaten at minute t
    slow = np.zeros(T)
    steps = np.zeros(T)
    asleep = np.zeros(T, dtype=np.int8)
    stage = np.zeros(T, dtype=np.int8)       # 0 wake, 1 light, 2 deep, 3 REM
    dose = np.zeros(T)                       # premixed insulin units injected at minute t
    meals, nights, days = [], [], []
    tdd = 0.0
    if p["insulin"]:
        tdd = float(p["weight_kg"] * 0.35 * np.exp(g.normal(0, 0.2)))

    def add_meal(t, kind, items, logged_p):
        if t < 0 or t >= T:
            return
        scale = persona["portion"] * float(np.exp(g.normal(0, 0.12)))
        carbs, gi = meal_totals(items, scale)
        ffast = float(np.clip((gi - 40) / 50, 0, 1))
        fast[t] += carbs * 1000 * ffast
        slow[t] += carbs * 1000 * (1 - ffast)
        logged = g.random() < logged_p
        meals.append(dict(minute=int(t), kind=kind, desc=describe(items, scale), carbs=round(carbs, 1), gi=round(gi, 1),
                          logged=bool(logged),
                          logged_minute=int(np.clip(t + g.integers(-5, 11), 0, T - 1)) if logged else -1,
                          logged_carbs=round(float(carbs * np.exp(g.normal(0, 0.25))), 1) if logged else np.nan,
                          logged_gi=round(gi, 1) if logged else np.nan))

    def walk(t0, dur, cadence):
        t0 = int(t0)
        dur = int(dur)
        if t0 >= T:
            return
        steps[t0:min(T, t0 + dur)] = np.maximum(steps[t0:min(T, t0 + dur)], cadence + g.normal(0, 5, size=min(T, t0 + dur) - t0))

    region = MEALS[persona["region"]]
    prev_wake = None
    for d in range(DAYS):
        base = d * MIN_PER_DAY
        weekend = (START_DATE + pd.Timedelta(days=d)).dayofweek >= 5
        short = g.random() < persona["p_short_night"]
        stress = (not weekend) and g.random() < persona["p_stress"]
        wake_h = persona["wake"] + g.normal(0, 0.3) + (0.75 if weekend else 0)
        bed_h = persona["bedtime"] + g.normal(0, 0.35) - 24  # previous evening, relative to this day's midnight
        if short:
            if g.random() < 0.6:
                bed_h = float(g.uniform(1.0, 2.5))   # went to bed after midnight
            else:
                wake_h = float(g.uniform(4.3, 5.2))
        wake = base + int(wake_h * 60)
        bed = base + int(bed_h * 60)
        # night that ends this morning
        s0, s1 = max(0, bed), wake
        asleep[s0:s1] = 1
        sl = s1 - s0
        if sl > 0:  # simple hypnogram: 90-min cycles, more deep early, more REM late
            m = np.arange(sl)
            cyc = (m % 90) / 90.0
            frac = m / max(sl, 1)
            st = np.where(cyc < 0.15, 1, np.where(cyc < 0.15 + 0.35 * (1 - frac), 2, np.where(cyc > 0.75 - 0.2 * frac, 3, 1)))
            wakebits = g.random(sl) < 0.03
            st[wakebits] = 0
            stage[s0:s1] = st
        sleep_hours = (s1 - (bed if d > 0 or bed >= 0 else bed)) / 60.0
        nights.append(dict(day=d, bed_minute=int(bed), wake_minute=int(wake), hours=round(sleep_hours, 2), short=bool(short)))
        days.append(dict(day=d, weekend=bool(weekend), stress=bool(stress), sleep_hours=round(sleep_hours, 2),
                         bed_minute=int(bed), wake_minute=int(wake)))

        # meals
        bf = wake + int(g.uniform(30, 75))
        lunch = base + int(g.normal(13.4, 0.35) * 60)
        snack = base + int(g.normal(17.2, 0.3) * 60)
        dinner = base + int(g.normal(21.0, 0.4) * 60)
        if tdd > 0:
            dose[max(0, bf - 10)] += tdd * 2 / 3
            dose[max(0, dinner - 10)] += tdd / 3
        add_meal(bf, "breakfast", region["breakfast"][g.integers(len(region["breakfast"]))], persona["log_adherence"])
        lunch_items = list(region["lunch"][g.integers(len(region["lunch"]))])
        dinner_items = list(region["dinner"][g.integers(len(region["dinner"]))])
        if g.random() < 0.08:
            (lunch_items if g.random() < 0.5 else dinner_items).extend(MEALS["sweet"][0])
        if tdd > 0 and g.random() < 0.08:
            pass                                   # skipped lunch after the morning premix dose (hypo risk)
        else:
            add_meal(lunch, "lunch", lunch_items, persona["log_adherence"])
        if g.random() < persona["p_evening_snack"]:
            add_meal(snack, "snack", MEALS["snack"][g.integers(len(MEALS["snack"]))], persona["log_adherence"] * 0.55)
        if tdd > 0 and g.random() < 0.10:
            dinner_items = [(f, n * 0.4) for f, n in dinner_items]    # light dinner, full dose
        add_meal(dinner, "dinner", dinner_items, persona["log_adherence"])
        if g.random() < 0.10:
            add_meal(dinner + int(g.uniform(80, 120)), "late snack", MEALS["snack"][g.integers(len(MEALS["snack"]))], 0.3)

        # activity
        awake = slice(wake, min(T, base + MIN_PER_DAY + int((persona["bedtime"] - 24) * 60)))
        n_aw = awake.stop - awake.start
        if n_aw > 0:
            bg = g.poisson(persona["base_steps"], size=n_aw).astype(float)
            bursts = g.random(n_aw) < 0.02
            bg[bursts] += g.uniform(30, 70, size=bursts.sum())
            steps[awake] = np.maximum(steps[awake], bg)
        if g.random() < persona["p_morning_walk"]:
            walk(wake + int(g.uniform(10, 30)), g.uniform(25, 40), 105)
        if not weekend and g.random() < persona["p_commute_walk"]:
            walk(base + int(g.normal(9.0, 0.3) * 60), g.uniform(10, 20), 95)
            walk(base + int(g.normal(18.6, 0.3) * 60), g.uniform(10, 20), 95)
        if g.random() < persona["p_post_dinner_walk"]:
            walk(dinner + int(g.uniform(10, 25)), g.uniform(10, 30), 100)
    steps = np.clip(steps, 0, 140)
    return dict(fast=fast, slow=slow, steps=steps, asleep=asleep, stage=stage, dose=dose,
                meals=pd.DataFrame(meals), nights=pd.DataFrame(nights), days=pd.DataFrame(days), tdd=tdd)


# ----------------------------------------------------------------------------- physiology
def true_params(p: dict) -> dict:
    """Hidden 'true' physiology for a patient, anchored to the EHR."""
    g = _rng(p["patient_id"], 3)
    t2d = p["status"] == "T2D"
    bmi_f = (25.0 / p["bmi"]) ** 1.2
    age_f = 1.0 - 0.004 * max(0, p["age"] - 40)
    SI = (1.8e-4 if t2d else 3.6e-4) * bmi_f * age_f * float(np.exp(g.normal(0, 0.25)))
    SI *= 1.0 - 0.15 * (p["syn_prs_percentile"] - 50) / 50 * 0.5
    # glucose-stimulated secretion, (uU/mL)/min per mg/dL above basal; gives post-meal insulin of
    # roughly 25-60 uU/mL above fasting, in line with mixed-meal studies in T2D / prediabetes
    gamma = (0.032 if t2d else 0.045) * float(np.exp(g.normal(0, 0.2)))
    gamma *= 1.0 - 0.10 * (p["syn_prs_percentile"] - 50) / 50
    if p["insulin"]:
        gamma *= 0.6          # beta-cell decline in insulin-treated patients
    if p["glp1"]:
        gamma *= 1.4
    eag = 28.7 * p["hba1c"] - 46.7      # ADAG (Nathan et al., 2008)
    target_mean = eag * float(np.exp(g.normal(0, 0.05)))    # glycation gap: lab vs CGM discordance
    return dict(
        SI=SI, SG=(0.011 if t2d else 0.015) * float(np.exp(g.normal(0, 0.15))), p2=0.025,
        Ib=(15.0 if t2d else 11.0) * p["bmi"] / 27.0, n=0.14 * (0.85 if p["egfr"] < 60 else 1.0), gamma=gamma,
        Gb=float(np.clip((0.80 if t2d else 0.82) * target_mean * np.exp(g.normal(0, 0.04)), 85.0, 200.0)),
        target_mean=target_mean, si_scale=1.0,
        VG=1.9, BW=float(p["weight_kg"]), f=0.9,
        kgri=0.06, kempt_f=0.045 * (0.7 if p["glp1"] else 1.0), kempt_s=0.02 * (0.7 if p["glp1"] else 1.0),
        kabs_f=0.035, kabs_s=0.012,
        e_up=0.004, k_boost=0.04, tau_boost=240.0,
        dawn=float(np.clip(g.normal(0.42 if t2d else 0.18, 0.12), 0.0, 0.9)) * (0.7 if p["metformin"] else 1.0),
        circ_amp=0.10, day_sd=0.08, stress_si=0.85, stress_egp=0.04,
        ka_r=0.025, ka_n=0.006, Vi_ml=120.0 * float(p["weight_kg"]),
        tau_ig=8.0,
    )


@njit(cache=True)
def _simulate(fast, slow, steps, sleep_mult, day_mult, stress, dose, minute_of_day,
              SI, SG, p2, Ib, n, gamma, Gb, VG, BW, f, kgri, kempt_f, kempt_s, kabs_f, kabs_s,
              e_up, k_boost, tau_boost, dawn, circ_amp, stress_si, stress_egp, ka_r, ka_n, Vi_ml, tau_ig):
    T = fast.shape[0]
    G = np.empty(T)
    IG = np.empty(T)
    INS = np.empty(T)
    g, x, ins, ig = Gb, 0.0, Ib, Gb
    s1f = s2f = qf = 0.0
    s1s = s2s = qs = 0.0
    r1 = r2 = n1 = n2 = 0.0
    boost = 0.0
    for t in range(T):
        # meals enter the stomach
        s1f += fast[t]
        s1s += slow[t]
        # exogenous premixed insulin 30% regular / 70% NPH (units)
        r1 += 0.3 * dose[t]
        n1 += 0.7 * dose[t]
        h = minute_of_day[t] / 60.0
        a = steps[t] / 100.0
        circ = 1.0 + circ_amp * np.cos(2 * np.pi * (h - 9.0) / 24.0)
        si = SI * circ * day_mult[t] * sleep_mult[t] * (stress_si if stress[t] > 0 else 1.0) * (1.0 + boost)
        p3 = si * p2
        # gut (two speeds, Dalla Man-style chain)
        ds1f = -kgri * s1f
        ds2f = kgri * s1f - kempt_f * s2f
        dqf = kempt_f * s2f - kabs_f * qf
        ds1s = -kgri * s1s
        ds2s = kgri * s1s - kempt_s * s2s
        dqs = kempt_s * s2s - kabs_s * qs
        ra = f * (kabs_f * qf + kabs_s * qs) / BW          # mg/kg/min
        # dawn phenomenon: extra hepatic output 04:00-08:00
        dwn = 0.0
        if 4.0 <= h < 9.0:
            dwn = dawn * np.sin(np.pi * (h - 4.0) / 5.0)
        egp_x = dwn + (stress_egp if stress[t] > 0 else 0.0)
        if g > 180.0:
            egp_x -= 0.0016 * (g - 180.0)                 # renal glucose excretion above threshold
        if g < 70.0:
            egp_x += 0.03 * (70.0 - g)                    # counter-regulation
        dg = -(SG + x) * g + SG * Gb + ra / VG + egp_x - e_up * a * g
        dx = -p2 * x + p3 * (ins - Ib)
        sec = gamma * max(g - Gb, 0.0)
        app = (ka_r * r2 + ka_n * n2) * 1e6 / Vi_ml
        dins = -n * (ins - Ib) + sec + app
        dr1 = -ka_r * r1
        dr2 = ka_r * r1 - ka_r * r2
        dn1 = -ka_n * n1
        dn2 = ka_n * n1 - ka_n * n2
        dboost = -boost / tau_boost + k_boost * a
        g = max(25.0, g + dg)
        x = max(-0.02, x + dx)
        ins = max(0.0, ins + dins)
        s1f += ds1f
        s2f += ds2f
        qf += dqf
        s1s += ds1s
        s2s += ds2s
        qs += dqs
        r1 += dr1
        r2 += dr2
        n1 += dn1
        n2 += dn2
        boost = max(0.0, boost + dboost)
        ig += (g - ig) / tau_ig
        G[t] = g
        IG[t] = ig
        INS[t] = ins
    return G, IG, INS


def sleep_multiplier(hours):
    """Insulin-sensitivity multiplier the day after a night of `hours` sleep (Donga et al., 2010)."""
    return 1.0 - 0.25 * np.clip((7.5 - np.asarray(hours)) / 3.5, 0.0, 1.0)


def run_physiology(life: dict, prm: dict, p: dict):
    g = _rng(p["patient_id"], 4)
    mod = np.tile(np.arange(MIN_PER_DAY), DAYS).astype(float)
    sleep_mult = np.repeat(sleep_multiplier(life["days"].sleep_hours.values), MIN_PER_DAY)
    day_mult = np.repeat(np.exp(g.normal(0, prm["day_sd"], size=DAYS)), MIN_PER_DAY)
    stress = np.repeat(life["days"].stress.values.astype(np.int8), MIN_PER_DAY)
    keys = ["SI", "SG", "p2", "Ib", "n", "gamma", "Gb", "VG", "BW", "f", "kgri", "kempt_f", "kempt_s", "kabs_f", "kabs_s",
            "e_up", "k_boost", "tau_boost", "dawn", "circ_amp", "stress_si", "stress_egp", "ka_r", "ka_n", "Vi_ml", "tau_ig"]
    # EHR anchoring: fasting level Gb comes from HbA1c; insulin sensitivity is then scaled (bisection on
    # a log scale) so the 21-day mean glucose matches the HbA1c-implied mean (ADAG). If sensitivity
    # hits its bounds, basal glucose absorbs the remainder.
    base_SI = prm["SI"]

    def run(scale):
        prm["SI"] = base_SI * scale
        return _simulate(life["fast"], life["slow"], life["steps"], sleep_mult, day_mult, stress, life["dose"], mod,
                         *[float(prm[k]) for k in keys])

    lo, hi = np.log(0.3), np.log(4.0)
    for _ in range(3):
        for _ in range(14):
            mid = 0.5 * (lo + hi)
            G, IG, INS = run(np.exp(mid))
            err = G.mean() - prm["target_mean"]
            if abs(err) < 0.5:
                break
            if err > 0:
                lo = mid
            else:
                hi = mid
        if abs(err) < 1.5:
            break
        prm["Gb"] = float(np.clip(prm["Gb"] - 0.8 * err, 70.0, 220.0))
        lo, hi = np.log(0.3), np.log(4.0)
    prm["si_scale"] = float(np.exp(mid))
    return G, IG, INS, dict(sleep_mult=sleep_mult, stress=stress)


# ----------------------------------------------------------------------------- sensors
def cgm_sensor(IG: np.ndarray, p: dict) -> np.ndarray:
    """5-minute CGM readings: interstitial lag already in IG; add calibration error, colored noise, gaps."""
    g = _rng(p["patient_id"], 5)
    x = IG[::STEP_MIN].copy()
    n = len(x)
    # two 10/11-day sensors, each with its own calibration error; first-day sensors read noisier
    sensor = (np.arange(n) * STEP_MIN >= 10 * MIN_PER_DAY).astype(int)
    gain = g.normal(1.0, 0.06, size=2)[sensor]
    off = g.normal(0, 5.0, size=2)[sensor]
    age_d = (np.arange(n) * STEP_MIN / MIN_PER_DAY) - 10 * sensor
    e = np.zeros(n)
    for i in range(1, n):
        e[i] = 0.75 * e[i - 1] + g.normal(0, 1.0)
    e = e / np.sqrt(1 / (1 - 0.75 ** 2))           # unit-variance AR(1)
    sd = (0.065 * x + 3.0) * np.where(age_d < 1.0, 1.4, 1.0)
    y = np.clip(gain * x + off + sd * e, 40, 400)
    miss = g.random(n) < 0.015
    for _ in range(g.integers(1, 4)):                 # a few longer gaps (signal loss)
        s = g.integers(0, n - 30)
        miss[s:s + g.integers(6, 24)] = True
    y[miss] = np.nan
    return y


def wearables(life: dict, G: np.ndarray, p: dict, stress_min: np.ndarray) -> pd.DataFrame:
    """Smartwatch-style streams aggregated to 5 minutes: HR, RMSSD (HRV), steps, sleep stage."""
    g = _rng(p["patient_id"], 6)
    t = np.arange(T)
    h = (t % MIN_PER_DAY) / 60.0
    hr_rest = float(np.clip(p["heart_rate"] - 4, 55, 92))
    since_meal = np.full(T, 1e9)
    meal_t = np.where((life["fast"] + life["slow"]) > 0)[0]
    last = -1e9
    j = 0
    for i in range(T):
        while j < len(meal_t) and meal_t[j] <= i:
            last = meal_t[j]
            j += 1
        since_meal[i] = i - last
    st = life["stage"]
    hr = (hr_rest + 3 * np.sin(2 * np.pi * (h - 15) / 24) - life["asleep"] * (7 + 3 * (st == 2))
          + np.minimum(0.32 * life["steps"], 45) + 5 * stress_min + 3 * ((since_meal > 10) & (since_meal < 90)))
    ar = np.zeros(T)
    for i in range(1, T):
        ar[i] = 0.95 * ar[i - 1] + g.normal(0, 0.6)
    hr = hr + ar
    t2d = p["status"] == "T2D"
    base = float(np.clip(42 - 0.45 * (p["age"] - 30), 12, 45)) * (0.8 if t2d else 1.0) * (0.75 if p["neuropathy"] else 1.0)
    rm = (base * (1 + 0.25 * life["asleep"] + 0.15 * (st == 2)) * np.where(life["steps"] > 60, 0.6, 1.0)
          * np.where(stress_min > 0, 0.78, 1.0) * np.exp(-0.0015 * np.maximum(G - 110, 0)))
    df = pd.DataFrame({"hr": hr, "rmssd": rm, "steps": life["steps"], "stage": st})
    k = np.arange(T) // STEP_MIN
    agg = df.groupby(k).agg(hr=("hr", "mean"), rmssd=("rmssd", "mean"), steps=("steps", "sum"),
                            stage=("stage", lambda s: int(np.bincount(s.astype(int), minlength=4).argmax())))
    agg["rmssd"] = agg.rmssd * np.exp(g.normal(0, 0.15, size=len(agg)))
    agg["hr"] = agg.hr.round(1)
    agg["rmssd"] = agg.rmssd.round(1)
    drop = g.random(len(agg)) < 0.01          # watch off the wrist
    agg.loc[drop, ["hr", "rmssd"]] = np.nan
    return agg.reset_index(drop=True)


# ----------------------------------------------------------------------------- one patient
def simulate_patient(p: dict) -> dict:
    persona = make_persona(p)
    life = make_lifestyle(p, persona)
    prm = true_params(p)
    G, IG, INS, extra = run_physiology(life, prm, p)
    cgm = cgm_sensor(IG, p)
    wear = wearables(life, G, p, extra["stress"])
    idx = np.arange(0, T, STEP_MIN)
    ts = START_DATE + pd.to_timedelta(idx, unit="min")
    streams = pd.DataFrame({"pt": p["pt"], "minute": idx, "time": ts, "cgm": np.round(cgm, 1),
                            "glucose_true": np.round(G[idx], 1)})
    streams = pd.concat([streams, wear], axis=1)
    doses = pd.DataFrame({"minute": np.where(life["dose"] > 0)[0], "units": life["dose"][life["dose"] > 0].round(1)})
    meals = life["meals"].assign(pt=p["pt"])
    return dict(streams=streams, meals=meals, nights=life["nights"].assign(pt=p["pt"]),
                days=life["days"].assign(pt=p["pt"]), doses=doses.assign(pt=p["pt"]),
                persona=dict(pt=p["pt"], **persona), truth=dict(pt=p["pt"], **{k: v for k, v in prm.items()}))

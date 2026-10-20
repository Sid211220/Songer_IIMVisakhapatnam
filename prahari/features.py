"""Leakage-safe feature table: one row per patient per forecast anchor (every 15 minutes).

At anchor minute t a feature may only use information available strictly before t:
CGM readings up to t-5, meals the patient had LOGGED before t, pen doses before t, watch data
before t, last night's sleep (known from 08:00), the static EHR, and the twin's forecast made
at t from the synchronised state. Habit features come from the onboarding week only.

Targets: CGM at t+30/60/90/120, and the spike label (see config): a spike is an onset of CGM
above 180 mg/dL sustained for >= 15 minutes (3 readings) within the next 120 minutes, for an
anchor whose last reading is below 180.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

from .config import (HORIZONS, HYPER_L1, HYPER_L2, ONBOARD_DAYS, PROCESSED, SPIKE_SUSTAIN_MIN, STEP_MIN)
from .simulate import MIN_PER_DAY, T, START_DATE

EHR_FEATURES = ["age", "male", "bmi", "hba1c", "diabetes_years", "egfr", "sbp", "ldl", "triglycerides", "insulin",
                "metformin", "glp1", "hypertension", "neuropathy", "ckd", "syn_prs_percentile",
                "syn_family_history", "t2d"]
CGM_FEATURES = ["g0", "g_age", "d5", "d10", "d15", "d30", "d45", "d60", "d90", "d120", "slope15", "slope30", "accel",
                "mean60", "sd60", "min60", "max60", "mean180", "sd180", "max180", "miss60", "tod_sin", "tod_cos",
                "hour", "weekend"]
LIFE_FEATURES = ["min_since_meal", "last_carbs", "last_gi", "carbs60", "carbs120", "carbs240", "gl120",
                 "next_habit_min", "next_habit_carbs", "next_habit_done", "ins_2h", "ins_6h", "min_since_dose",
                 "steps15", "steps30", "steps60", "steps180", "steps_today", "hr", "hr30", "hr_delta",
                 "rmssd60", "rmssd_z", "asleep", "sleep_last", "deep_frac", "stress_proxy"]
TWIN_FEATURES = [f"twin_{h}" for h in HORIZONS] + [f"twin_d{h}" for h in HORIZONS] + [
    "twin_peak120", "twin_tpeak", "twin_now", "twin_innov60", "tw_SI", "tw_Gb", "tw_meal_gain", "tw_kabs", "tw_dawn"]
GROUPS = {
    "cgm": CGM_FEATURES,
    "cgm+life": CGM_FEATURES + LIFE_FEATURES,
    "cgm+life+ehr": CGM_FEATURES + LIFE_FEATURES + EHR_FEATURES,
    "full (with twin)": CGM_FEATURES + LIFE_FEATURES + EHR_FEATURES + TWIN_FEATURES,
}

READABLE = {
    "g0": "current glucose", "d15": "15-min glucose change", "d30": "30-min glucose change", "slope15": "glucose rising now",
    "slope30": "30-min glucose trend", "min_since_meal": "time since last meal", "last_carbs": "carbs in last meal",
    "last_gi": "glycaemic index of last meal", "carbs60": "carbs logged in last hour", "carbs120": "carbs logged in last 2 h",
    "gl120": "glycaemic load in last 2 h", "next_habit_min": "habitual meal time approaching",
    "next_habit_carbs": "size of habitual next meal", "next_habit_done": "next habitual meal already eaten",
    "steps15": "steps in last 15 min", "steps30": "steps in last 30 min", "steps60": "steps in last hour",
    "steps_today": "steps so far today", "sleep_last": "last night's sleep", "deep_frac": "deep-sleep share",
    "rmssd_z": "HRV below personal baseline", "stress_proxy": "stress signal (HRV + heart rate)", "hr_delta": "heart rate vs resting",
    "hba1c": "HbA1c", "bmi": "BMI", "insulin": "on insulin", "twin_peak120": "twin-predicted 2-h peak",
    "twin_120": "twin 2-h forecast", "twin_60": "twin 1-h forecast", "twin_d60": "twin-predicted 1-h rise",
    "twin_d120": "twin-predicted 2-h rise", "twin_innov60": "unexplained glucose (likely unlogged food)",
    "twin_tpeak": "time to twin-predicted peak", "tw_SI": "personal insulin sensitivity (twin)",
    "tw_Gb": "personal fasting level (twin)", "tw_dawn": "personal dawn effect (twin)", "max180": "highest glucose in last 3 h",
    "mean60": "average glucose last hour", "hour": "time of day (daily routine)", "tod_sin": "time of day (daily routine)",
    "tod_cos": "time of day (daily routine)", "d5": "5-min glucose change", "d10": "10-min glucose change", "accel": "glucose rise speeding up",
    "sd180": "glucose variability last 3 h", "mean180": "average glucose last 3 h", "min60": "lowest glucose last hour",
    "ins_2h": "insulin in last 2 h", "min_since_dose": "time since insulin", "hr": "heart rate", "hr30": "heart rate (30 min)",
    "rmssd60": "HRV last hour", "asleep": "asleep", "twin_30": "twin 30-min forecast", "twin_90": "twin 90-min forecast",
    "twin_d30": "twin-predicted 30-min rise", "twin_d90": "twin-predicted 90-min rise", "twin_now": "twin current estimate",
    "tw_meal_gain": "personal meal response (twin)", "tw_kabs": "personal absorption speed (twin)", "weekend": "weekend",
    "diabetes_years": "years since diagnosis", "age": "age", "carbs240": "carbs logged in last 4 h", "steps180": "steps in last 3 h",
    "miss60": "CGM gaps last hour", "g_age": "minutes since last CGM reading", "d45": "45-min glucose change", "d60": "1-h glucose change",
    "d90": "90-min glucose change", "d120": "2-h glucose change", "max60": "highest glucose last hour", "sd60": "glucose variability last hour",
}


def _ffill(a):
    idx = np.where(~np.isnan(a), np.arange(len(a)), 0)
    np.maximum.accumulate(idx, out=idx)
    out = a[idx]
    age = (np.arange(len(a)) - idx) * STEP_MIN
    out[: np.argmax(~np.isnan(a))] = np.nan
    return out, age.astype(float)


def _roll(a, w, fn):
    return getattr(pd.Series(a).rolling(w, min_periods=max(1, w // 3)), fn)().values


def _spike_onsets(cgm, thr):
    """Boolean per 5-min index: a spike episode starts here.

    Start of a run of >= SPIKE_SUSTAIN_MIN above thr, after >= 30 minutes at or below thr
    (hysteresis, so sensor noise around the threshold does not create extra episodes)."""
    k = SPIKE_SUSTAIN_MIN // STEP_MIN
    above = np.nan_to_num(cgm, nan=-1) > thr
    run = np.ones(len(cgm), bool)
    for j in range(k):
        run &= np.roll(above, -j)
    run[len(cgm) - k + 1:] = False
    high_or_gap = above | np.isnan(cgm)          # a gap is not evidence of being in range
    quiet = np.ones(len(cgm), bool)
    for j in range(1, 7):
        quiet &= ~np.roll(high_or_gap, j)
    quiet[:6] = False
    return run & quiet


def patient_features(pt, prof, s, meals, doses, days, twin_fc, twin_par):
    n = len(s)
    cgm = s.cgm.values.astype(float)
    g, gage = _ffill(cgm)
    # anchors: every 15 min from day ONBOARD_DAYS (test period), need 120 min of future
    anchors = twin_fc.minute.values
    i = anchors // STEP_MIN - 1                       # index of last reading available
    F = pd.DataFrame({"pt": pt, "minute": anchors, "day": anchors // MIN_PER_DAY})
    F["g0"] = g[i]
    F["g_age"] = gage[i]
    for L in (5, 10, 15, 30, 45, 60, 90, 120):
        F[f"d{L}"] = g[i] - g[np.maximum(i - L // STEP_MIN, 0)]
    F["slope15"] = F.d15 / 15
    F["slope30"] = F.d30 / 30
    F["accel"] = (g[i] - g[i - 3]) - (g[i - 3] - g[i - 6])
    for w, nm in ((12, "60"), (36, "180")):
        F[f"mean{nm}"] = _roll(g, w, "mean")[i]
        F[f"sd{nm}"] = _roll(g, w, "std")[i]
        F[f"max{nm}"] = _roll(g, w, "max")[i]
    F["min60"] = _roll(g, 12, "min")[i]
    F["miss60"] = pd.Series(np.isnan(cgm).astype(float)).rolling(12, min_periods=1).sum().values[i]
    mod = anchors % MIN_PER_DAY
    F["hour"] = mod / 60
    F["tod_sin"] = np.sin(2 * np.pi * mod / MIN_PER_DAY)
    F["tod_cos"] = np.cos(2 * np.pi * mod / MIN_PER_DAY)
    F["weekend"] = ((START_DATE + pd.to_timedelta(F.day, unit="D")).dt.dayofweek >= 5).astype(int)

    # ---------------- meals (logged only, before t)
    lm = meals[meals.logged].sort_values("logged_minute")
    lt = lm.logged_minute.values
    lc = lm.logged_carbs.values
    lg = lm.logged_gi.values
    j = np.searchsorted(lt, anchors, side="left") - 1          # last logged meal strictly before t
    F["min_since_meal"] = np.where(j >= 0, anchors - lt[np.maximum(j, 0)], 1440).clip(0, 1440)
    F["last_carbs"] = np.where(j >= 0, lc[np.maximum(j, 0)], 0)
    F["last_gi"] = np.where(j >= 0, lg[np.maximum(j, 0)], 0)
    cum_c = np.concatenate([[0], np.cumsum(lc)])
    cum_gl = np.concatenate([[0], np.cumsum(lc * lg / 100)])
    for w in (60, 120, 240):
        a = np.searchsorted(lt, anchors - w, side="left")
        F[f"carbs{w}"] = cum_c[j + 1] - cum_c[a]
        if w == 120:
            F["gl120"] = cum_gl[j + 1] - cum_gl[a]
    # habits learned in the onboarding week: typical time and size of each main meal
    on = lm[lm.logged_minute < ONBOARD_DAYS * MIN_PER_DAY]
    habit = []
    for kind in ("breakfast", "lunch", "dinner"):
        k = on[on.kind == kind]
        if len(k):
            habit.append((kind, float(np.median(k.logged_minute % MIN_PER_DAY)), float(np.median(k.logged_carbs))))
    nh_min = np.full(len(F), 1440.0)
    nh_carbs = np.zeros(len(F))
    nh_done = np.zeros(len(F))
    for kind, hm, hc in habit:
        until = (hm - mod) % MIN_PER_DAY
        better = until < nh_min
        # was this kind of meal already logged today before t?
        today = lm[lm.kind == kind]
        tdays = today.logged_minute.values // MIN_PER_DAY
        tmin = today.logged_minute.values
        done = np.array([np.any((tdays == d) & (tmin < t)) for d, t in zip(F.day.values, anchors)])
        nh_min = np.where(better, until, nh_min)
        nh_carbs = np.where(better, hc, nh_carbs)
        nh_done = np.where(better, done.astype(float), nh_done)
    F["next_habit_min"] = nh_min
    F["next_habit_carbs"] = nh_carbs
    F["next_habit_done"] = nh_done

    # ---------------- insulin pen
    dt_ = doses.minute.values
    du = doses.units.values
    cum_u = np.concatenate([[0], np.cumsum(du)])
    jd = np.searchsorted(dt_, anchors, side="left") - 1
    for w, nm in ((120, "ins_2h"), (360, "ins_6h")):
        a = np.searchsorted(dt_, anchors - w, side="left")
        F[nm] = cum_u[jd + 1] - cum_u[a] if len(dt_) else 0.0
    F["min_since_dose"] = np.where(jd >= 0, anchors - dt_[np.maximum(jd, 0)], 1440).clip(0, 1440) if len(dt_) else 1440

    # ---------------- watch
    st = s.steps.values.astype(float)
    cs = np.concatenate([[0], np.cumsum(st)])
    for w in (15, 30, 60, 180):
        F[f"steps{w}"] = cs[i + 1] - cs[np.maximum(i + 1 - w // STEP_MIN, 0)]
    day_start = (anchors // MIN_PER_DAY) * MIN_PER_DAY // STEP_MIN
    F["steps_today"] = cs[i + 1] - cs[day_start]
    hr, _ = _ffill(s.hr.values.astype(float))
    rm, _ = _ffill(s.rmssd.values.astype(float))
    stage = s.stage.values
    onb = np.arange(n) < ONBOARD_DAYS * MIN_PER_DAY // STEP_MIN
    rest_hr = np.nanmedian(hr[onb & (stage > 0)])
    day_mask = onb & (stage == 0) & (st < 30)
    rm_mu, rm_sd = np.nanmean(rm[day_mask]), np.nanstd(rm[day_mask]) + 1e-6
    F["hr"] = hr[i]
    F["hr30"] = _roll(hr, 6, "mean")[i]
    F["hr_delta"] = F.hr30 - rest_hr
    F["rmssd60"] = _roll(rm, 12, "mean")[i]
    F["rmssd_z"] = (F.rmssd60 - rm_mu) / rm_sd
    F["asleep"] = (stage[i] > 0).astype(int)
    # last night's sleep, known once the watch sees the patient wake: hours and deep-sleep share
    dd = days.sort_values("day")
    sh, wk, bd = dd.sleep_hours.values, dd.wake_minute.values, dd.bed_minute.values
    d_eff = np.where(anchors >= wk[np.clip(F.day.values, 0, len(wk) - 1)], F.day.values, F.day.values - 1)
    F["sleep_last"] = np.where(d_eff >= 0, sh[np.clip(d_eff, 0, len(sh) - 1)], 7.5)
    deep = np.zeros(len(sh))
    for d in range(len(sh)):
        seg = stage[max(0, bd[d]) // STEP_MIN: wk[d] // STEP_MIN]
        deep[d] = (seg == 2).sum() / max((seg > 0).sum(), 1)
    F["deep_frac"] = np.where(d_eff >= 0, deep[np.clip(d_eff, 0, len(sh) - 1)], 0.2)
    F["stress_proxy"] = (-F.rmssd_z.clip(-4, 4) + (F.hr_delta - F.steps30 / 60).clip(-10, 30) / 10) * (1 - F.asleep)

    F = F.copy()
    # ---------------- EHR (static)
    for c in EHR_FEATURES:
        if c == "male":
            F[c] = int(prof["sex"] == "M")
        elif c == "t2d":
            F[c] = int(prof["status"] == "T2D")
        else:
            F[c] = float(prof[c])

    # ---------------- twin
    tf = twin_fc.reset_index(drop=True)
    for c in tf.columns:
        if c.startswith("twin_"):
            F[c] = tf[c].values
    for h in HORIZONS:
        F[f"twin_d{h}"] = F[f"twin_{h}"] - F.g0
    par = twin_par.set_index("day")
    for k in ("SI", "Gb", "meal_gain", "kabs", "dawn"):
        F[f"tw_{k}"] = par[k].reindex(F.day.values).values

    # ---------------- targets
    gt = s.glucose_true.values.astype(float)
    for h in HORIZONS:
        idx = np.minimum(anchors // STEP_MIN + h // STEP_MIN, n - 1)
        F[f"y_{h}"] = np.where(anchors // STEP_MIN + h // STEP_MIN < n, cgm[idx], np.nan)
        F[f"ytrue_{h}"] = np.where(anchors // STEP_MIN + h // STEP_MIN < n, gt[idx], np.nan)
    for thr, nm in ((HYPER_L1, "spike"), (HYPER_L2, "spike250")):
        on = _spike_onsets(cgm, thr)
        on_idx = np.where(on)[0]
        nxt = np.searchsorted(on_idx, anchors // STEP_MIN, side="left")
        if len(on_idx):
            nxt_idx = np.where(nxt < len(on_idx), on_idx[np.minimum(nxt, len(on_idx) - 1)], 10 ** 9)
        else:
            nxt_idx = np.full(len(anchors), 10 ** 9)
        lead = nxt_idx * STEP_MIN - anchors
        F[f"{nm}_lead"] = np.where(lead <= 120, lead, np.nan)
        F[nm] = ((lead >= 0) & (lead <= 120)).astype(int)
        last30 = pd.Series(np.nan_to_num(cgm, nan=-1)).rolling(6, min_periods=1).max().values[i]
        gaps30 = pd.Series(np.isnan(cgm).astype(float)).rolling(6, min_periods=1).sum().values[i]
        F[f"{nm}_eligible"] = ((last30 <= thr) & (gaps30 < 3) & (anchors // STEP_MIN + 24 < n)).astype(int)
    return F


def build(save: bool = True) -> pd.DataFrame:
    from .cohort import load
    D = load()
    fc = pd.read_parquet(PROCESSED / "twin_forecasts.parquet")
    par = pd.read_parquet(PROCESSED / "twin_params.parquet")
    prof = D["profiles"].set_index("pt")
    out = []
    for pt in prof.index:
        f = fc[(fc.pt == pt) & (fc.minute >= ONBOARD_DAYS * MIN_PER_DAY) & (fc.minute <= T - 125)]
        out.append(patient_features(
            pt, prof.loc[pt], D["streams"][D["streams"].pt == pt].sort_values("minute"),
            D["meals"][D["meals"].pt == pt], D["doses"][D["doses"].pt == pt].sort_values("minute"),
            D["days"][D["days"].pt == pt], f, par[par.pt == pt]))
    X = pd.concat(out, ignore_index=True)
    if save:
        X.to_parquet(PROCESSED / "features.parquet", index=False, compression="zstd")
    print(f"features: {len(X):,} anchors x {X.shape[1]} columns; spike rate {X[X.spike_eligible == 1].spike.mean():.3f}")
    return X


if __name__ == "__main__":
    build()

"""The Digital Twin: a personal glucose-insulin model that is calibrated, kept in sync and queried.

What the twin is
----------------
A compact Bergman minimal model (Bergman et al., 1979) with one gut absorption chain, exercise
glucose uptake, premixed-insulin pharmacokinetics and a sleep-loss term. It is deliberately
SIMPLER than the simulator in simulate.py (no circadian or day-to-day sensitivity swings, no
stress physiology, no two-speed gut, no counter-regulation), so it faces real model mismatch.

How it stays a twin (not just a model)
--------------------------------------
1. Prior from the EHR. HbA1c, BMI, diagnosis, medicines and the synthetic risk score set prior
   values for insulin sensitivity, fasting glucose and insulin secretion.
2. Calibration in the onboarding week (days 1-7). Five personal parameters are fitted by
   maximum a posteriori estimation: the loss is the error of the twin's own 30/60/120-minute
   open-loop forecasts against CGM, plus a penalty for straying from the EHR prior.
3. Synchronisation (data assimilation). Every 5 minutes the CGM reading corrects the twin's
   state with an observer (nudging) that also estimates an "unexplained glucose appearance"
   term, which soaks up unlogged snacks and stress.
4. Nightly re-calibration (from the second week). Every midnight the parameters are re-fitted on
   the trailing 7 days, warm-started from yesterday; every CGM target used in a fit lies before
   that midnight, so forecasts for a day only use parameters fitted on earlier data.
5. Queries. From the synchronised state the twin forecasts the next 2 hours and answers
   what-if questions (walk after the meal, smaller portion, rice -> roti, a short night).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .config import DAYS, ONBOARD_DAYS, STEP_MIN, HORIZONS
from .simulate import MIN_PER_DAY, T, sleep_multiplier

try:
    from numba import njit
except Exception:  # pragma: no cover
    def njit(*a, **k):
        def wrap(f):
            return f
        return wrap(a[0]) if a and callable(a[0]) else wrap

# fixed (literature / population) constants of the twin
SG, P2, N_CLEAR, VG, F_BIO = 0.012, 0.025, 0.14, 1.9, 0.9
E_UP, K_BOOST, TAU_BOOST = 0.004, 0.04, 240.0     # exercise: literature-level priors, not fitted
KA_R, KA_N, TAU_IG = 0.025, 0.006, 8.0
K_OBS_G, K_OBS_U, TAU_U = 0.25, 0.0025, 45.0       # observer gains and decay of the disturbance term
H_MAX = max(HORIZONS)
PARAMS = ["SI", "Gb", "meal_gain", "kabs", "dawn"]
NSTATE = 13   # g, x, i, q1, q2, r1, r2, n1, n2, boost, ig, u, (spare)


@njit(cache=True)
def _step(s, SI, Gb, mg, kabs, dawn, gamma, BW, Vi_ml, meal, a, sm, dose, h):
    """Advance the twin state s by one minute (in place)."""
    g, x, ins, q1, q2 = s[0], s[1], s[2], s[3], s[4]
    r1, r2, n1, n2, boost, ig, u = s[5], s[6], s[7], s[8], s[9], s[10], s[11]
    q1 += meal * mg
    r1 += 0.3 * dose
    n1 += 0.7 * dose
    si = SI * sm * (1.0 + boost)
    ra = F_BIO * kabs * q2 / BW
    dwn = 0.0
    if 4.0 <= h < 9.0:
        dwn = dawn * np.sin(np.pi * (h - 4.0) / 5.0)
    dg = -(SG + x) * g + SG * Gb + ra / VG + dwn + u - E_UP * a * g
    dx = -P2 * x + si * P2 * (ins - 0.0)
    sec = gamma * max(g - Gb, 0.0)
    app = (KA_R * r2 + KA_N * n2) * 1e6 / Vi_ml
    dins = -N_CLEAR * ins + sec + app
    s[0] = max(30.0, g + dg)
    s[1] = max(-0.02, x + dx)
    s[2] = max(0.0, ins + dins)
    s[3] = q1 - kabs * q1
    s[4] = q2 + kabs * q1 - kabs * q2
    s[5] = r1 - KA_R * r1
    s[6] = r2 + KA_R * r1 - KA_R * r2
    s[7] = n1 - KA_N * n1
    s[8] = n2 + KA_N * n1 - KA_N * n2
    s[9] = max(0.0, boost - boost / TAU_BOOST + K_BOOST * a)
    s[10] = ig + (s[0] - ig) / TAU_IG
    s[11] = u - u / TAU_U


@njit(cache=True)
def _run(theta_days, gamma, BW, Vi_ml, meal, steps, sm, dose, cgm, t0, t1, anchor_every, horizon, assimilate):
    """Assimilate CGM from t0 to t1 and issue an open-loop forecast at every anchor.

    theta_days: (DAYS, 5) parameters in force on each day.
    Returns: ig track (t1-t0), anchors (n,), forecasts (n, horizon//5) of interstitial glucose,
    innovations at CGM times.
    """
    n_anchor = 0
    for t in range(t0, t1):
        if (t - t0) % anchor_every == 0 and t > t0:
            n_anchor += 1
    nh = horizon // 5
    anchors = np.empty(n_anchor, dtype=np.int64)
    fc = np.full((n_anchor, nh), np.nan)
    track = np.empty(t1 - t0)
    innov = np.full(t1 - t0, np.nan)
    s = np.zeros(13)
    d0 = t0 // 1440
    s[0] = theta_days[d0, 1]
    s[10] = theta_days[d0, 1]
    f = np.zeros(13)
    k = 0
    for t in range(t0, t1):
        d = t // 1440
        th = theta_days[d]
        h = (t % 1440) / 60.0
        if (t - t0) % anchor_every == 0 and t > t0:
            # open-loop forecast from the synchronised state; only inputs already logged by t
            for j in range(13):
                f[j] = s[j]
            for m in range(1, horizon + 1):
                tt = t + m - 1
                _step(f, th[0], th[1], th[2], th[3], th[4], gamma, BW, Vi_ml,
                      0.0, 0.0, sm[t], 0.0, (tt % 1440) / 60.0)
                if m % 5 == 0:
                    fc[k, m // 5 - 1] = f[10]
            anchors[k] = t
            k += 1
        _step(s, th[0], th[1], th[2], th[3], th[4], gamma, BW, Vi_ml, meal[t], steps[t], sm[t], dose[t], h)
        if assimilate and t % 5 == 0 and not np.isnan(cgm[t // 5]):
            e = cgm[t // 5] - s[10]
            innov[t - t0] = e
            s[0] += K_OBS_G * e
            s[10] += K_OBS_G * e
            s[11] += K_OBS_U * e
        track[t - t0] = s[10]
    return track, anchors, fc, innov


# ----------------------------------------------------------------------------- inputs
def twin_inputs(pt: str, streams: pd.DataFrame, meals: pd.DataFrame, doses: pd.DataFrame, days: pd.DataFrame) -> dict:
    """Minute-level arrays of what the twin is allowed to know (logged meals, watch, pen, CGM)."""
    s = streams[streams.pt == pt].sort_values("minute")
    meal = np.zeros(T)
    m = meals[(meals.pt == pt) & meals.logged]
    np.add.at(meal, m.logged_minute.values.astype(int), m.logged_carbs.values * 1000.0)
    st = np.repeat(s.steps.values.astype(float) / STEP_MIN, STEP_MIN) / 100.0   # activity, 1 = 100 steps/min
    dose = np.zeros(T)
    dz = doses[doses.pt == pt]
    np.add.at(dose, dz.minute.values.astype(int), dz.units.values)
    # sleep: last night's duration (from the watch), known once the watch sees the patient wake up
    dd = days[days.pt == pt].sort_values("day")
    mult = sleep_multiplier(dd.sleep_hours.values)
    wake = dd.wake_minute.values
    sm = np.ones(T)
    for d in range(DAYS):
        b = wake[d + 1] if d + 1 < DAYS else T
        sm[wake[d]:min(b, T)] = mult[d]
    return dict(meal=meal, steps=st, dose=dose, sm=sm, cgm=s.cgm.values.astype(float),
                meal_gi=m[["logged_minute", "logged_gi", "logged_carbs"]].values)


def prior(p: dict) -> dict:
    """EHR-informed prior for the five personal parameters and fixed secretion gain."""
    t2d = p["status"] == "T2D"
    eag = 28.7 * p["hba1c"] - 46.7
    SI = (1.8e-4 if t2d else 3.6e-4) * (25.0 / p["bmi"]) ** 1.2 * 2.0
    gamma = (0.032 if t2d else 0.045) * (0.6 if p["insulin"] else 1.0) * (1.4 if p["glp1"] else 1.0)
    th = dict(SI=SI, Gb=0.80 * eag, meal_gain=1.0, kabs=0.03, dawn=0.35 if t2d else 0.15)
    sd = dict(SI=0.7, Gb=0.15, meal_gain=0.35, kabs=0.4, dawn=0.15)   # log-scale sd except dawn (abs)
    return dict(theta=th, sd=sd, gamma=gamma, BW=float(p["weight_kg"]), Vi_ml=120.0 * float(p["weight_kg"]))


def _vec(th):
    return np.array([np.log(th["SI"]), np.log(th["Gb"]), np.log(th["meal_gain"]), np.log(th["kabs"]), th["dawn"]])


def _unvec(v):
    return dict(SI=float(np.exp(v[0])), Gb=float(np.exp(v[1])), meal_gain=float(np.exp(v[2])),
                kabs=float(np.exp(np.clip(v[3], np.log(0.005), np.log(0.2)))), dawn=float(np.clip(v[4], 0.0, 1.0)))


def _theta_arr(th):
    return np.array([th[k] for k in PARAMS])


def _loss(v, inp, pr, t0, t1, v0, sdv):
    th = _unvec(v)
    td = np.tile(_theta_arr(th), (DAYS, 1))
    _, anchors, fc, _ = _run(td, pr["gamma"], pr["BW"], pr["Vi_ml"], inp["meal"], inp["steps"], inp["sm"],
                             inp["dose"], inp["cgm"], t0, t1, 30, H_MAX, True)
    keep = anchors >= t0 + 360                     # 6-hour warm-up
    anchors, fc = anchors[keep], fc[keep]
    err = []
    for hz in (30, 60, 120):
        idx = (anchors + hz) // 5
        ok = (idx < len(inp["cgm"])) & (anchors + hz < t1)     # targets must lie inside the fit window
        y = np.full(len(anchors), np.nan)
        y[ok] = inp["cgm"][idx[ok]]
        e = fc[:, hz // 5 - 1] - y
        err.append(e[~np.isnan(e)])
    e = np.concatenate(err)
    mse = float(np.mean(e ** 2)) if len(e) else 1e6
    pen = float(np.sum(((v - v0) / sdv) ** 2))
    return mse / 400.0 + pen / len(e) * 50.0 if len(e) else 1e6


def calibrate(inp: dict, pr: dict, t0: int, t1: int, start: np.ndarray | None = None, maxiter: int = 300) -> dict:
    v0 = _vec(pr["theta"])
    sdv = np.array([pr["sd"]["SI"], pr["sd"]["Gb"], pr["sd"]["meal_gain"], pr["sd"]["kabs"], pr["sd"]["dawn"]])
    x0 = v0 if start is None else start
    step = np.array([0.4, 0.08, 0.25, 0.3, 0.12]) * (1.0 if start is None else 0.4)
    simplex = np.vstack([x0] + [x0 + np.eye(5)[i] * step[i] for i in range(5)])
    res = minimize(_loss, x0, args=(inp, pr, t0, t1, v0, sdv), method="Nelder-Mead",
                   options=dict(maxiter=maxiter, xatol=1e-3, fatol=1e-4, initial_simplex=simplex))
    return dict(theta=_unvec(res.x), v=res.x, loss=float(res.fun), nfev=int(res.nfev))


def build_twin(p: dict, inp: dict, nightly: bool = True) -> dict:
    """Onboarding calibration (days 1-7), then optional nightly re-calibration on a trailing week."""
    pr = prior(p)
    cal = calibrate(inp, pr, 0, ONBOARD_DAYS * MIN_PER_DAY)
    theta_days = np.tile(_theta_arr(cal["theta"]), (DAYS, 1))
    history = [dict(day=d, **cal["theta"]) for d in range(ONBOARD_DAYS + 1)]
    v = cal["v"]
    for d in range(ONBOARD_DAYS + 1, DAYS):
        if nightly:
            c = calibrate(inp, pr, (d - 7) * MIN_PER_DAY, d * MIN_PER_DAY, start=v, maxiter=120)
            v = c["v"]
            theta_days[d] = _theta_arr(c["theta"])
            history.append(dict(day=d, **c["theta"]))
        else:
            theta_days[d] = theta_days[ONBOARD_DAYS]
            history.append(dict(day=d, **cal["theta"]))
    return dict(prior=pr, onboarding=cal, theta_days=theta_days, history=pd.DataFrame(history))


def run_twin(tw: dict, inp: dict, anchor_every: int = 15) -> dict:
    pr = tw["prior"]
    track, anchors, fc, innov = _run(tw["theta_days"], pr["gamma"], pr["BW"], pr["Vi_ml"], inp["meal"], inp["steps"],
                                     inp["sm"], inp["dose"], inp["cgm"], 0, T, anchor_every, H_MAX, True)
    return dict(track=track, anchors=anchors, forecast=fc, innov=innov)


# ----------------------------------------------------------------------------- what-if
def state_at(tw: dict, inp: dict, t: int) -> np.ndarray:
    """Synchronised twin state at minute t (assimilating all CGM up to t)."""
    pr = tw["prior"]
    s = np.zeros(NSTATE)
    th0 = tw["theta_days"][0]
    s[0] = s[10] = th0[1]
    for m in range(t):
        th = tw["theta_days"][m // MIN_PER_DAY]
        _step(s, th[0], th[1], th[2], th[3], th[4], pr["gamma"], pr["BW"], pr["Vi_ml"], inp["meal"][m], inp["steps"][m],
              inp["sm"][m], inp["dose"][m], (m % MIN_PER_DAY) / 60.0)
        if m % 5 == 0 and not np.isnan(inp["cgm"][m // 5]):
            e = inp["cgm"][m // 5] - s[10]
            s[0] += K_OBS_G * e
            s[10] += K_OBS_G * e
            s[11] += K_OBS_U * e
    return s


def what_if(tw: dict, s0: np.ndarray, t: int, minutes: int = 240, carbs_g: float = 0.0, meal_at: int = 0,
            walk_at: int | None = None, walk_min: int = 15, walk_cadence: float = 100.0,
            sleep_hours: float | None = None, dose_units: float = 0.0, dose_at: int = 0) -> np.ndarray:
    """Simulate the twin forward from state s0 under a scenario. Returns glucose every 5 minutes."""
    pr = tw["prior"]
    th = tw["theta_days"][min(t // MIN_PER_DAY, DAYS - 1)]
    sm = 1.0 if sleep_hours is None else float(sleep_multiplier(sleep_hours))
    s = s0.copy()
    s[11] = 0.0
    out = []
    for m in range(minutes):
        meal = carbs_g * 1000.0 if m == meal_at else 0.0
        a = walk_cadence / 100.0 if (walk_at is not None and walk_at <= m < walk_at + walk_min) else 0.0
        dz = dose_units if (dose_units and m == dose_at) else 0.0
        _step(s, th[0], th[1], th[2], th[3], th[4], pr["gamma"], pr["BW"], pr["Vi_ml"], meal, a, sm, dz,
              ((t + m) % MIN_PER_DAY) / 60.0)
        if (m + 1) % 5 == 0:
            out.append(s[10])
    return np.array(out)


# ----------------------------------------------------------------------------- cohort
def _one(args):
    p, streams, meals, doses, days, nightly = args
    inp = twin_inputs(p["pt"], streams, meals, doses, days)
    tw = build_twin(p, inp, nightly=nightly)
    r = run_twin(tw, inp)
    a, fc = r["anchors"], r["forecast"]
    innov = r["innov"]
    # recent innovation: mean CGM-minus-twin over the last hour before each anchor (model mismatch signal)
    inn = pd.Series(innov).rolling(60, min_periods=1).mean().values
    df = pd.DataFrame({"pt": p["pt"], "minute": a.astype("int32")})
    for h in HORIZONS:
        df[f"twin_{h}"] = fc[:, h // 5 - 1].astype("float32")
    df["twin_peak120"] = np.nanmax(fc, axis=1).astype("float32")
    df["twin_tpeak"] = ((np.nanargmax(fc, axis=1) + 1) * 5).astype("int16")
    df["twin_now"] = r["track"][a - 1].astype("float32")
    df["twin_innov60"] = inn[a - 1].astype("float32")
    hist = tw["history"].assign(pt=p["pt"])
    pri = dict(pt=p["pt"], gamma=tw["prior"]["gamma"], **{f"prior_{k}": v for k, v in tw["prior"]["theta"].items()},
               onboard_loss=tw["onboarding"]["loss"])
    return df, hist, pri


def run_cohort(nightly: bool = True, processes: int = 2, limit: int | None = None):
    """Build and run a twin for every patient; saves twin_forecasts / twin_params / twin_priors parquet."""
    import multiprocessing as mp
    import time
    from .cohort import load
    from .config import PROCESSED
    D = load()
    prof = D["profiles"].to_dict("records")[:limit]
    jobs = [(p, D["streams"][D["streams"].pt == p["pt"]], D["meals"][D["meals"].pt == p["pt"]],
             D["doses"][D["doses"].pt == p["pt"]], D["days"][D["days"].pt == p["pt"]], nightly) for p in prof]
    t0 = time.time()
    _one(jobs[0])  # compile numba once before forking
    with mp.get_context("fork").Pool(processes) as pool:
        res = []
        for i, r in enumerate(pool.imap(_one, jobs, chunksize=2)):
            res.append(r)
            if (i + 1) % 25 == 0:
                print(f"  twins built {i + 1}/{len(jobs)} ({time.time() - t0:.0f}s)")
    fc = pd.concat([r[0] for r in res], ignore_index=True)
    hist = pd.concat([r[1] for r in res], ignore_index=True)
    pri = pd.DataFrame([r[2] for r in res])
    tag = "" if nightly else "_static"
    fc.to_parquet(PROCESSED / f"twin_forecasts{tag}.parquet", index=False, compression="zstd")
    hist.to_parquet(PROCESSED / f"twin_params{tag}.parquet", index=False)
    pri.to_parquet(PROCESSED / f"twin_priors{tag}.parquet", index=False)
    print(f"twins: {len(prof)} patients, {len(fc):,} forecasts ({time.time() - t0:.0f}s)")
    return fc, hist, pri


if __name__ == "__main__":
    import sys
    run_cohort(nightly="--static" not in sys.argv)

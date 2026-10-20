"""Face-validity checks of the virtual patient simulator against published effect sizes.

    python -m prahari.validate_sim

A synthetic cohort is only useful if it behaves like real people. Each check below runs the
hidden 'true patient' simulator (not the twin) and compares the result with a published range.
Results go to results/simulator_validation.csv and results/figures/sim_validation.png.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FIGURES, PROCESSED, RESULTS
from .simulate import MIN_PER_DAY, _simulate, sleep_multiplier

KEYS = ["SI", "SG", "p2", "Ib", "n", "gamma", "Gb", "VG", "BW", "f", "kgri", "kempt_f", "kempt_s", "kabs_f", "kabs_s",
        "e_up", "k_boost", "tau_boost", "dawn", "circ_amp", "stress_si", "stress_egp", "ka_r", "ka_n", "Vi_ml", "tau_ig"]


def _day(prm, meal_min=13 * 60, carbs=60.0, gi=75.0, walk_at=None, walk_min=15, sleep_h=7.5, days=2):
    """Run the true simulator for `days` days with a single test meal on the last day."""
    T = days * MIN_PER_DAY
    fast = np.zeros(T)
    slow = np.zeros(T)
    t = (days - 1) * MIN_PER_DAY + meal_min
    ff = np.clip((gi - 40) / 50, 0, 1)
    fast[t] = carbs * 1000 * ff
    slow[t] = carbs * 1000 * (1 - ff)
    steps = np.zeros(T)
    if walk_at is not None:
        steps[t + walk_at: t + walk_at + walk_min] = 100.0
    sm = np.full(T, float(sleep_multiplier(sleep_h)))
    G, _, _ = _simulate(fast, slow, steps, sm, np.ones(T), np.zeros(T, np.int8), np.zeros(T),
                        np.tile(np.arange(MIN_PER_DAY), days).astype(float), *[float(prm[k]) for k in KEYS])
    return G[t - 5:t + 180], G


def run():
    truth = pd.read_parquet(PROCESSED / "truth.parquet")
    prof = pd.read_parquet(PROCESSED / "profiles.parquet").set_index("pt")
    streams = pd.read_parquet(PROCESSED / "streams.parquet")
    t2d = truth[truth.pt.map(prof.status) == "T2D"]
    rows = []

    # 1. a 15-minute walk starting 15 minutes after a 60 g meal (Reynolds et al., 2016; Buffey et al., 2022)
    red_peak, red_iauc = [], []
    for _, prm in t2d.iterrows():
        a, _ = _day(prm)
        b, _ = _day(prm, walk_at=15)
        base = a[0]
        red_iauc.append(1 - np.clip(b - base, 0, None).sum() / np.clip(a - base, 0, None).sum())
        red_peak.append(1 - (b.max() - base) / (a.max() - base))
    rows.append(dict(check="Post-meal walk (15 min) lowers 3-h incremental glucose",
                     short=f"-{np.median(red_iauc) * 100:.0f}% post-meal glucose", simulated=f"{np.median(red_iauc) * 100:.0f}% (IQR {np.percentile(red_iauc, 25) * 100:.0f}-{np.percentile(red_iauc, 75) * 100:.0f}%)",
                     published="12% overall, 22% after the evening meal (Reynolds 2016); light walking lowers post-meal glucose (Buffey 2022)",
                     ok=bool(0.08 <= np.median(red_iauc) <= 0.35)))

    # 2. one 4-hour night (Donga et al., 2010)
    inc = []
    for _, prm in t2d.iterrows():
        a, _ = _day(prm, meal_min=8 * 60)
        b, _ = _day(prm, meal_min=8 * 60, sleep_h=4.0)
        inc.append((np.clip(b - b[0], 0, None).sum() / np.clip(a - a[0], 0, None).sum()) - 1)
    rows.append(dict(check="Breakfast response after one 4-hour night (sensitivity -25% in the model)",
                     short=f"sensitivity -25%, +{np.median(inc) * 100:.0f}% breakfast rise", simulated=f"+{np.median(inc) * 100:.0f}% incremental glucose (sensitivity multiplier {float(sleep_multiplier(4.0)):.2f})",
                     published="One night of ~4 h sleep lowered the glucose infusion rate (insulin sensitivity) by about 25% (Donga 2010)",
                     ok=bool(np.median(inc) > 0)))

    # 3. dawn phenomenon in T2D: rise from the night-time nadir to pre-breakfast
    s = streams.merge(prof[["status"]], left_on="pt", right_index=True)
    s["mod"] = s.minute % MIN_PER_DAY
    s["day"] = s.minute // MIN_PER_DAY
    night = s[(s.status == "T2D") & (s["mod"] >= 0) & (s["mod"] < 4 * 60)].groupby(["pt", "day"]).glucose_true.min()
    pre = s[(s.status == "T2D") & (s["mod"] >= 6 * 60) & (s["mod"] < 6 * 60 + 30)].groupby(["pt", "day"]).glucose_true.mean()
    dawn = (pre - night).dropna()
    rows.append(dict(check="Dawn rise in T2D (night nadir to 06:00-06:30)",
                     short=f"median {dawn.median():.0f} mg/dL", simulated=f"median {dawn.median():.0f} mg/dL",
                     published="Median dawn rise 16 mg/dL (range 0-31.5) in 248 people with T2D (Monnier 2013)",
                     ok=bool(5 <= dawn.median() <= 35)))

    # 4. mean glucose follows HbA1c (ADAG)
    m = streams.groupby("pt").glucose_true.mean()
    eag = 28.7 * prof.hba1c - 46.7
    r = np.corrcoef(m.reindex(prof.index), eag)[0, 1]
    rows.append(dict(check="21-day mean glucose vs HbA1c-implied mean",
                     short=f"r = {r:.2f}", simulated=f"r = {r:.2f}; mean difference {float((m.reindex(prof.index) - eag).mean()):+.1f} mg/dL",
                     published="eAG = 28.7 x HbA1c - 46.7, r = 0.92 in the ADAG study (Nathan 2008); glycation gap added on purpose",
                     ok=bool(r > 0.85)))

    # 5. time in range vs HbA1c
    tir = streams.groupby("pt").glucose_true.apply(lambda x: ((x >= 70) & (x <= 180)).mean() * 100)
    d = pd.DataFrame({"tir": tir, "a1c": prof.hba1c})
    slope = np.polyfit(d.a1c, d.tir, 1)[0]
    near7 = d[(d.a1c >= 6.8) & (d.a1c <= 7.2)].tir.median()
    rows.append(dict(check="Time in range (70-180) vs HbA1c",
                     short=f"{slope:.0f} points per 1%", simulated=f"TIR at HbA1c 6.8-7.2%: {near7:.0f}%; slope {slope:.1f} points per 1% HbA1c",
                     published="TIR 70% corresponds to HbA1c about 7%; +10 points TIR is about -0.6% HbA1c, i.e. ~17 points per 1% (Beck 2019)",
                     ok=bool(60 <= near7 <= 85)))

    # 6. CGM accuracy
    ok = streams.cgm.notna()
    mard = (abs(streams.cgm - streams.glucose_true) / streams.glucose_true)[ok].mean() * 100
    rows.append(dict(check="Simulated CGM accuracy vs true glucose (MARD)",
                     short=f"{mard:.1f}%", simulated=f"{mard:.1f}%",
                     published="Dexcom G7 pivotal study: MARD 8.2% (arm), 9.1% (abdomen) (Garg 2022)",
                     ok=bool(7 <= mard <= 12)))
    R = pd.DataFrame(rows)
    R.to_csv(RESULTS / "simulator_validation.csv", index=False)
    _figure(t2d)
    print(R.to_string())
    return R


def _figure(t2d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    prm = t2d.iloc[len(t2d) // 2]
    x = np.arange(-5, 180)
    a, _ = _day(prm)
    b, _ = _day(prm, walk_at=15)
    c, _ = _day(prm, sleep_h=4.0)
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.plot(x, a, color="#1d2733", lw=2, label="60 g lunch, usual day")
    ax.plot(x, b, color="#0f766e", lw=2, label="same lunch + 15-min walk")
    ax.plot(x, c, color="#c2410c", lw=2, ls="--", label="same lunch after a 4-h night")
    ax.axvspan(15, 30, color="#0f766e", alpha=0.08)
    ax.axhline(180, color="#8a94a3", lw=0.8, ls=":")
    ax.set_xlabel("Minutes after the meal")
    ax.set_ylabel("Plasma glucose (mg/dL)")
    ax.set_title(f"Simulator face validity: one T2D virtual patient ({prm.pt})", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "sim_validation.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    run()

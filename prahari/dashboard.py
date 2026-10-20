"""Build the doctor dashboard: one self-contained HTML file (docs/index.html).

    python -m prahari.dashboard

The page works offline and on GitHub Pages. It replays the test period (days 8-21) for a
panel of held-out test patients: pick a moment, and the page shows what the clinic would have
seen then (risk-ranked patients, 2-hour forecast with 80% band, alert reasons, wearables,
twin parameters) plus a live what-if simulator that runs the patient's twin in the browser.
"""
from __future__ import annotations

import base64
import json
import os

import numpy as np
import pandas as pd

from .config import FIGURES, HORIZONS, MODELS, PROCESSED, RESULTS, ROOT, ONBOARD_DAYS
from .simulate import MIN_PER_DAY, START_DATE, T
from .twin import (E_UP, F_BIO, K_BOOST, K_OBS_G, K_OBS_U, KA_N, KA_R, N_CLEAR, P2, PARAMS, SG, TAU_BOOST, TAU_IG,
                   TAU_U, VG, NSTATE, _step, prior, twin_inputs)

OUT = ROOT / "docs" / "index.html"
TEMPLATE = ROOT / "dashboard" / "template.html"


def _r(a, nd=0):
    a = np.asarray(a, dtype=float)
    out = np.round(a, nd)
    return [None if np.isnan(v) else (int(v) if nd == 0 else float(v)) for v in out]


def _anchor_states(p, inp, theta_days, anchors):
    """Twin state at each anchor (after assimilating CGM up to the anchor), for the browser what-if."""
    pr = prior(p)
    s = np.zeros(NSTATE)
    s[0] = s[10] = theta_days[0][1]
    want = set(int(a) for a in anchors)
    out = {}
    for m in range(int(max(anchors)) + 1):
        if m in want:
            out[m] = s[:12].copy()
        th = theta_days[m // MIN_PER_DAY]
        _step(s, th[0], th[1], th[2], th[3], th[4], pr["gamma"], pr["BW"], pr["Vi_ml"], inp["meal"][m], inp["steps"][m],
              inp["sm"][m], inp["dose"][m], (m % MIN_PER_DAY) / 60.0)
        if m % 5 == 0 and not np.isnan(inp["cgm"][m // 5]):
            e = inp["cgm"][m // 5] - s[10]
            s[0] += K_OBS_G * e
            s[10] += K_OBS_G * e
            s[11] += K_OBS_U * e
    return np.array([out[int(a)] for a in anchors]), pr


def pick_panel(P, prof, n_t2d=8, n_pre=6):
    te = P[P.set == "test"]
    pts = te.pt.unique()
    pr = prof.set_index("pt").loc[pts]
    t2d = pr[pr.status == "T2D"].sort_values("hba1c")
    pre = pr[pr.status != "T2D"].sort_values("hba1c")
    pick = lambda d, k: list(d.index[np.linspace(0, len(d) - 1, k).round().astype(int)])
    return list(dict.fromkeys(pick(t2d, n_t2d) + pick(pre, n_pre)))


def build():
    prof = pd.read_parquet(PROCESSED / "profiles.parquet")
    streams = pd.read_parquet(PROCESSED / "streams.parquet")
    meals = pd.read_parquet(PROCESSED / "meals.parquet")
    doses = pd.read_parquet(PROCESSED / "doses.parquet")
    days = pd.read_parquet(PROCESSED / "days.parquet")
    P = pd.read_parquet(PROCESSED / "predictions.parquet")
    reasons = pd.read_parquet(PROCESSED / "alert_reasons.parquet")
    par = pd.read_parquet(PROCESSED / "twin_params.parquet")
    thr = json.loads((MODELS / "thresholds.json").read_text())
    metrics = json.loads((RESULTS / "metrics.json").read_text())
    panel = pick_panel(P, prof)
    pidx = prof.set_index("pt")
    reason_vocab, patients = [], []
    for pt in panel:
        p = pidx.loc[pt].to_dict()
        p["pt"] = pt
        s = streams[streams.pt == pt].sort_values("minute")
        inp = twin_inputs(pt, streams, meals, doses, days)
        hist = par[par.pt == pt].sort_values("day")
        theta_days = hist[PARAMS].values
        pp = P[P.pt == pt].sort_values("minute")
        pp = pp.merge(reasons[reasons.pt == pt], on=["pt", "minute"], how="left")
        anchors = pp.minute.values
        states, pr = _anchor_states(p, inp, theta_days, anchors)
        rs = []
        for r in pp.reasons.fillna(""):
            if r not in reason_vocab:
                reason_vocab.append(r)
            rs.append(reason_vocab.index(r))
        m = meals[(meals.pt == pt) & meals.logged]
        d = doses[doses.pt == pt]
        dd = days[days.pt == pt].sort_values("day")
        patients.append(dict(
            pt=pt, sex=p["sex"], age=int(p["age"]), status=p["status"], hba1c=round(float(p["hba1c"]), 1),
            bmi=round(float(p["bmi"]), 1), egfr=round(float(p["egfr"])), sbp=round(float(p["sbp"])), ldl=round(float(p["ldl"])),
            dyears=round(float(p["diabetes_years"]), 1), weight=round(float(p["weight_kg"]), 1),
            meds=[k for k in ("metformin", "insulin", "glp1") if p[k]], comorb=[k for k in ("hypertension", "obesity", "ckd",
                  "neuropathy", "retinopathy", "nephropathy") if p.get(k)], prs=round(float(p["syn_prs_percentile"])),
            fh=int(p["syn_family_history"]), hba1c_repaired=int(p["hba1c_repaired"]),
            cgm=_r(s.cgm), steps=_r(s.steps), hr=_r(s.hr), rmssd=_r(s.rmssd, 0), stage=_r(s.stage),
            meals=[[int(a), round(float(b)), int(round(c)), k, desc] for a, b, c, k, desc in
                   zip(m.logged_minute, m.logged_carbs, m.logged_gi, m.kind, m.desc)],
            doses=[[int(a), round(float(b), 1)] for a, b in zip(d.minute, d.units)],
            sleep=[round(float(x), 2) for x in dd.sleep_hours], wake=[int(x) for x in dd.wake_minute],
            anchors=[int(a) for a in anchors],
            pred={h: _r(pp[f"full (with twin)_{h}"]) for h in HORIZONS},
            q10={h: _r(pp[f"q10_{h}"]) for h in HORIZONS}, q90={h: _r(pp[f"q90_{h}"]) for h in HORIZONS},
            twin={h: _r(pp[f"twin_{h}"]) for h in HORIZONS},
            risk=_r(pp["p_spike_full (with twin)"] * 100), risk250=_r(pp["p_spike250_full (with twin)"] * 100),
            reasons=rs,
            theta=[[round(float(v), 7) for v in row] for row in theta_days],
            prior=dict(gamma=pr["gamma"], BW=pr["BW"], Vi_ml=pr["Vi_ml"], **{f"p_{k}": v for k, v in pr["theta"].items()}),
            states=[[round(float(v), 6) for v in st] for st in states],
        ))
    # default replay moment: a logged meal has just happened and the twin's predicted peak drives an alert
    best = None
    for p in patients:
        for k, (a, r) in enumerate(zip(p["anchors"], p["risk"])):
            if r is None or r < thr["spike|full (with twin)"] * 100 or a < 8 * MIN_PER_DAY:
                continue
            if not reason_vocab[p["reasons"][k]].startswith("twin-predicted"):
                continue
            recent = [m for m in p["meals"] if 10 <= a - m[0] <= 30 and m[3] in ("lunch", "dinner", "breakfast")]
            if recent and 11 * 60 <= a % MIN_PER_DAY <= 21 * 60 + 30:
                score = r + (20 if p["status"] == "T2D" else 0)
                if best is None or score > best[0]:
                    best = (score, p["pt"], a)
    default = dict(pt=best[1], minute=int(best[2])) if best else dict(pt=patients[0]["pt"], minute=int(patients[0]["anchors"][0] + 13 * 60))
    figs = {}
    for f in ("rmse_by_horizon", "spike_roc_pr", "shap_importance", "twin_identifiability", "clarke_60", "sim_validation"):
        fp = FIGURES / f"{f}.png"
        if fp.exists():
            figs[f] = "data:image/png;base64," + base64.b64encode(fp.read_bytes()).decode()
    fm = pd.read_csv(RESULTS / "forecast_metrics.csv")
    am = pd.read_csv(RESULTS / "alert_metrics.csv")
    sv = pd.read_csv(RESULTS / "simulator_validation.csv") if (RESULTS / "simulator_validation.csv").exists() else None
    data = dict(
        start=str(START_DATE.date()), onboard_days=ONBOARD_DAYS, default=default, T=T, patients=patients, reasons=reason_vocab,
        thresholds={k: v * 100 for k, v in thr.items()}, metrics=metrics, figs=figs,
        forecast_table=fm.to_dict("records"), alert_table=am.to_dict("records"),
        sim_validation=sv.to_dict("records") if sv is not None else [],
        consts=dict(SG=SG, P2=P2, N=N_CLEAR, VG=VG, F=F_BIO, E_UP=E_UP, K_BOOST=K_BOOST, TAU_BOOST=TAU_BOOST,
                    KA_R=KA_R, KA_N=KA_N, TAU_IG=TAU_IG, TAU_U=TAU_U),
        cohort=dict(n=int(len(prof)), t2d=int((prof.status == "T2D").sum()), pre=int((prof.status != "T2D").sum())),
    )
    import plotly
    pjs = (os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js"))
    html = TEMPLATE.read_text()
    html = html.replace("/*__PLOTLY__*/", open(pjs).read())
    html = html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"), default=float))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    print(f"dashboard: {len(patients)} patients -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    build()

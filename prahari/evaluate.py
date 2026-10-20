"""Evaluation on held-out test patients, days 8-21 (after the onboarding week).

    python -m prahari.evaluate

Outputs results/metrics.json, results/*.csv and results/figures/*.png.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

from .config import ALERT_COOLDOWN_MIN, FIGURES, HORIZONS, MODELS, PROCESSED, RESULTS, SEED
from .features import GROUPS

METHODS = ["persist", "linear", "twin"] + list(GROUPS)
LABEL = {"persist": "Persistence (no change)", "linear": "Linear autoregression (CGM only)",
         "twin": "Digital twin alone (physiology)", "cgm": "LightGBM: CGM only",
         "cgm+life": "LightGBM: CGM + wearables + meal log", "cgm+life+ehr": "LightGBM: + EHR",
         "full (with twin)": "Prahari hybrid: + twin (full)"}
INK, MUTED, ACCENT, ACCENT2, GRID = "#1d2733", "#8a94a3", "#0f766e", "#c2410c", "#e6e9ee"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "figure.dpi": 150})


# ----------------------------------------------------------------------------- Clarke error grid
def clarke_zones(ref, pred):
    """Clarke et al. (1987) error grid zone for each (reference, prediction) pair, mg/dL."""
    ref, pred = np.asarray(ref, float), np.asarray(pred, float)
    z = np.full(len(ref), "B", dtype="<U1")
    a = ((ref <= 70) & (pred <= 70)) | (np.abs(pred - ref) <= 0.2 * ref)
    e = ((ref <= 70) & (pred >= 180)) | ((ref >= 180) & (pred <= 70))
    c = ((ref >= 70) & (ref <= 290) & (pred >= ref + 110)) | ((ref >= 130) & (ref <= 180) & (pred <= (7 / 5) * ref - 182))
    d = ((ref >= 240) & (pred >= 70) & (pred <= 180)) | ((ref <= 175 / 3) & (pred <= 180) & (pred >= 70)) | \
        ((ref >= 175 / 3) & (ref <= 70) & (pred >= (6 / 5) * ref))
    z[d] = "D"
    z[c] = "C"
    z[e] = "E"
    z[a] = "A"
    return z


def reg_metrics(y, p):
    ok = ~np.isnan(y) & ~np.isnan(p)
    y, p = y[ok], p[ok]
    z = clarke_zones(y, p)
    return dict(rmse=float(np.sqrt(np.mean((p - y) ** 2))), mae=float(np.mean(np.abs(p - y))),
                mard=float(np.mean(np.abs(p - y) / y) * 100), clarke_a=float(np.mean(z == "A") * 100),
                clarke_ab=float(np.mean(np.isin(z, ["A", "B"])) * 100), n=int(len(y)))


def boot_rmse_gain(df, a, b, h, n=1000):
    """Patient-level bootstrap of RMSE(a) - RMSE(b); positive = b is better."""
    rng = np.random.default_rng(SEED)
    pts = df.pt.unique()
    per = {pt: g for pt, g in df.groupby("pt")}
    out = []
    for _ in range(n):
        s = rng.choice(pts, len(pts), replace=True)
        d = pd.concat([per[p] for p in s])
        y = d[f"y_{h}"].values
        ok = ~np.isnan(y)
        ra = np.sqrt(np.nanmean((d[f"{a}_{h}"].values[ok] - y[ok]) ** 2))
        rb = np.sqrt(np.nanmean((d[f"{b}_{h}"].values[ok] - y[ok]) ** 2))
        out.append(ra - rb)
    return float(np.mean(out)), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


# ----------------------------------------------------------------------------- alerts
def alert_metrics(d: pd.DataFrame, score: str, thr: float, target: str = "spike") -> dict:
    """Event-level alert performance on eligible anchors.

    Alerts are de-duplicated: after an alert, no new alert for ALERT_COOLDOWN_MIN minutes.
    sensitivity = share of spike onsets preceded by an alert 15-120 minutes before onset.
    lead time   = minutes from the first alert to the onset, for detected spikes.
    false alerts/day = notifications not followed by an onset within 120 minutes, per patient-day.
    """
    det, leads, fa, n_alert, n_events, days = 0, [], 0, 0, 0, 0
    for pt, g in d.groupby("pt"):
        g = g.sort_values("minute")
        days += g.day.nunique()
        t = g.minute.values
        fire = (g[score].values >= thr) & (g[f"{target}_eligible"].values == 1)
        alerts, last = [], -10 ** 9
        for ti, f in zip(t, fire):
            if f and ti - last >= ALERT_COOLDOWN_MIN:
                alerts.append(ti)
                last = ti
        onsets = np.unique((g.minute + g[f"{target}_lead"]).dropna().values)
        n_events += len(onsets)
        al = np.array(alerts)
        n_alert += len(al)
        for o in onsets:
            w = al[(al <= o - 15) & (al >= o - 120)] if len(al) else []
            if len(w):
                det += 1
                leads.append(o - w.min())
        for a in al:
            if not np.any((onsets >= a) & (onsets <= a + 120)):
                fa += 1
    return dict(events=int(n_events), detected=int(det), sensitivity=float(det / max(n_events, 1) * 100),
                median_lead_min=float(np.median(leads)) if leads else float("nan"),
                alerts_per_patient_day=float(n_alert / max(days, 1)), false_alerts_per_patient_day=float(fa / max(days, 1)),
                alert_precision=float((n_alert - fa) / max(n_alert, 1) * 100))


# ----------------------------------------------------------------------------- main
def run(verbose: bool = True) -> dict:
    P = pd.read_parquet(PROCESSED / "predictions.parquet")
    thr = json.loads((MODELS / "thresholds.json").read_text())
    te = P[P.set == "test"].copy()
    for h in HORIZONS:
        te[f"twin_{h}"] = te[f"twin_{h}"]
    out = {"n_test_patients": int(te.pt.nunique()), "n_test_anchors": int(len(te)), "regression": {}, "classification": {}}

    # regression table
    rows = []
    for m in METHODS:
        for h in HORIZONS:
            r = reg_metrics(te[f"y_{h}"].values, te[f"{m}_{h}"].values)
            rows.append(dict(method=LABEL[m], key=m, horizon=h, **r))
    R = pd.DataFrame(rows)
    R.to_csv(RESULTS / "forecast_metrics.csv", index=False)
    out["regression"] = {f"{r.key}|{r.horizon}": {k: round(getattr(r, k), 3) for k in ("rmse", "mae", "mard", "clarke_a", "clarke_ab")}
                         for r in R.itertuples()}
    # after a logged meal (the moment a spike warning matters most)
    pm = te[te.min_since_meal <= 45]
    out["regression_post_meal"] = {f"{m}|{h}": round(reg_metrics(pm[f"y_{h}"].values, pm[f"{m}_{h}"].values)["rmse"], 3)
                                   for m in METHODS for h in HORIZONS}
    # against true (noise-free) glucose, full model
    out["regression_vs_true_glucose"] = {h: round(reg_metrics(te[f"ytrue_{h}"].values, te[f"full (with twin)_{h}"].values)["rmse"], 2)
                                         for h in HORIZONS}
    # band coverage
    out["band80_coverage"] = {}
    for h in HORIZONS:
        d = te[te[f"y_{h}"].notna()]
        out["band80_coverage"][h] = round(float(((d[f"y_{h}"] >= d[f"q10_{h}"]) & (d[f"y_{h}"] <= d[f"q90_{h}"])).mean() * 100), 1)
    out["bootstrap_rmse_gain_twin"] = {h: dict(zip(("mean", "lo95", "hi95"), boot_rmse_gain(te, "cgm+life+ehr", "full (with twin)", h, 500)))
                                       for h in (60, 120)}
    out["bootstrap_rmse_gain_vs_cgm"] = {h: dict(zip(("mean", "lo95", "hi95"), boot_rmse_gain(te, "cgm", "full (with twin)", h, 500)))
                                         for h in (60, 120)}

    # classification
    crow = []
    for target in ("spike", "spike250"):
        el = te[te[f"{target}_eligible"] == 1]
        out["classification"][target] = {"prevalence": round(float(el[target].mean()) * 100, 2)}
        for name in list(GROUPS) + ["twin-only"]:
            s = el[f"p_{target}_{name}"].values
            y = el[target].values
            am = alert_metrics(el, f"p_{target}_{name}", thr[f"{target}|{name}"], target)
            row = dict(target=target, model=name, auroc=roc_auc_score(y, s), auprc=average_precision_score(y, s), **am)
            crow.append(row)
            out["classification"][target][name] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()
                                                   if k not in ("target", "model")}
    C = pd.DataFrame(crow)
    C.to_csv(RESULTS / "alert_metrics.csv", index=False)
    out["matched_alert_budget"] = matched_budget(P, thr)

    # twin identifiability: does the calibrated twin recover the hidden physiology?
    truth = pd.read_parquet(PROCESSED / "truth.parquet").set_index("pt")
    par = pd.read_parquet(PROCESSED / "twin_params.parquet")
    onb = par[par.day == 7].set_index("pt")
    last = par[par.day == par.day.max()].set_index("pt")
    true_si = truth.SI           # SI already includes the calibration scale
    pri = pd.read_parquet(PROCESSED / "twin_priors.parquet").set_index("pt")
    out["twin_identifiability"] = {
        "spearman_SI_ehr_prior_only": round(float(spearmanr(pri.prior_SI, true_si.reindex(pri.index)).statistic), 3),
        "spearman_Gb_ehr_prior_only": round(float(spearmanr(pri.prior_Gb, truth.Gb.reindex(pri.index)).statistic), 3),
        "spearman_SI_onboarding": round(float(spearmanr(onb.SI, true_si.reindex(onb.index)).statistic), 3),
        "spearman_SI_day21": round(float(spearmanr(last.SI, true_si.reindex(last.index)).statistic), 3),
        "spearman_Gb_onboarding": round(float(spearmanr(onb.Gb, truth.Gb.reindex(onb.index)).statistic), 3),
        "spearman_Gb_day21": round(float(spearmanr(last.Gb, truth.Gb.reindex(last.index)).statistic), 3),
    }
    out["living_twin"] = living_twin_gain(te)
    (RESULTS / "metrics.json").write_text(json.dumps(out, indent=1, default=float))
    figures(te, R, C, thr, onb, truth)
    if verbose:
        print(R[R.horizon.isin([30, 60, 120])].pivot(index="method", columns="horizon", values="rmse").round(1).to_string())
        print(C[["target", "model", "auroc", "auprc", "sensitivity", "median_lead_min", "false_alerts_per_patient_day",
                 "alert_precision"]].round(3).to_string())
        print(json.dumps({k: out[k] for k in ("matched_alert_budget", "living_twin", "band80_coverage", "bootstrap_rmse_gain_twin", "bootstrap_rmse_gain_vs_cgm",
                                               "twin_identifiability", "regression_vs_true_glucose")}, indent=1, default=float))
    return out


def matched_budget(P, thr):
    """Fair comparison of alert models: each model's threshold is set on validation patients so it
    sends the same number of notifications per patient-day as Prahari; then compared on test."""
    res = {}
    for target in ("spike", "spike250"):
        el = P[P[f"{target}_eligible"] == 1]
        va, te = el[el.set == "val"], el[el.set == "test"]
        full = f"p_{target}_full (with twin)"
        budget = alert_metrics(va, full, thr[f"{target}|full (with twin)"], target)["alerts_per_patient_day"]
        res[target] = {"budget_alerts_per_patient_day": round(budget, 3)}
        for name in ("cgm", "cgm+life", "cgm+life+ehr", "full (with twin)", "twin-only"):
            col = f"p_{target}_{name}"
            lo, hi = float(np.nanmin(va[col])), float(np.nanmax(va[col]))
            for _ in range(22):                       # alerts/day fall as the threshold rises
                mid = 0.5 * (lo + hi)
                if alert_metrics(va, col, mid, target)["alerts_per_patient_day"] > budget:
                    lo = mid
                else:
                    hi = mid
            m = alert_metrics(te, col, hi, target)
            res[target][name] = {k: round(v, 3) if isinstance(v, float) else v for k, v in m.items()}
    return res


def living_twin_gain(te):
    """Twin-alone forecast error with nightly re-calibration vs. a twin frozen after onboarding."""
    fs = PROCESSED / "twin_forecasts_static.parquet"
    if not fs.exists():
        return {}
    keys = te[["pt", "minute"] + [f"y_{h}" for h in HORIZONS]]
    res = {}
    for tag, f in (("nightly", PROCESSED / "twin_forecasts.parquet"), ("frozen_after_week1", fs)):
        d = keys.merge(pd.read_parquet(f), on=["pt", "minute"])
        res[tag] = {h: round(reg_metrics(d[f"y_{h}"].values, d[f"twin_{h}"].values)["rmse"], 2) for h in HORIZONS}
    return res


def figures(te, R, C, thr, onb, truth):
    colors = {"persist": "#b8c0cc", "linear": "#8a94a3", "twin": ACCENT2, "cgm": "#6b9bd1", "cgm+life": "#3b6fb6",
              "cgm+life+ehr": "#1f4e8c", "full (with twin)": ACCENT}
    # 1. RMSE by horizon
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for m in METHODS:
        r = R[R.key == m]
        ax.plot(r.horizon, r.rmse, marker="o", lw=2.6 if m.startswith("full") else 1.6, color=colors[m], label=LABEL[m])
    ax.set_xlabel("Forecast horizon (minutes)")
    ax.set_ylabel("RMSE (mg/dL), lower is better")
    ax.set_xticks(HORIZONS)
    ax.set_title("Forecast error on held-out patients, days 8-21", loc="left", fontsize=11, color=INK)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "rmse_by_horizon.png")
    plt.close(fig)

    # 2. Clarke error grid, 60 min
    d = te[["y_60", "full (with twin)_60"]].dropna().sample(6000, random_state=SEED)
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    z = clarke_zones(d.y_60, d["full (with twin)_60"])
    for zone, col in (("A", ACCENT), ("B", "#3b6fb6"), ("C", "#e0a100"), ("D", ACCENT2), ("E", "#7f1d1d")):
        k = z == zone
        ax.scatter(d.y_60[k], d["full (with twin)_60"][k], s=3, alpha=0.35, color=col, label=f"{zone}: {k.mean() * 100:.1f}%")
    for xs, ys in (([0, 400], [0, 400]), ([0, 175 / 3], [70, 70]), ([175 / 3, 400 / 1.2], [70, 400]), ([70, 70], [84, 400]),
                   ([0, 70], [180, 180]), ([70, 290], [180, 400]), ([70, 70], [0, 56]), ([70, 400], [56, 320]),
                   ([180, 180], [0, 70]), ([180, 400], [70, 70]), ([240, 240], [70, 180]), ([240, 400], [180, 180]),
                   ([130, 180], [0, 70])):
        ax.plot(xs, ys, color=INK, lw=0.7)
    ax.set_xlim(0, 400)
    ax.set_ylim(0, 400)
    ax.set_xlabel("Measured CGM at +60 min (mg/dL)")
    ax.set_ylabel("Prahari forecast (mg/dL)")
    ax.set_title("Clarke error grid, 60-minute forecast", loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=8, markerscale=4, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURES / "clarke_60.png")
    plt.close(fig)

    # 3. ROC + PR
    el = te[te.spike_eligible == 1]
    fig, axs = plt.subplots(1, 2, figsize=(9, 4))
    for name in list(GROUPS) + ["twin-only"]:
        col = colors.get(name, ACCENT2) if name != "twin-only" else ACCENT2
        s = el[f"p_spike_{name}"]
        fpr, tpr, _ = roc_curve(el.spike, s)
        pr, rc, _ = precision_recall_curve(el.spike, s)
        lab = (LABEL.get(name, "Twin peak alone") if name != "twin-only" else "Twin peak alone")
        axs[0].plot(fpr, tpr, color=col, lw=2.4 if name.startswith("full") else 1.4, label=f"{lab} ({roc_auc_score(el.spike, s):.3f})")
        axs[1].plot(rc, pr, color=col, lw=2.4 if name.startswith("full") else 1.4,
                    label=f"{lab} ({average_precision_score(el.spike, s):.3f})")
    axs[0].plot([0, 1], [0, 1], color=GRID)
    axs[0].set_xlabel("False positive rate")
    axs[0].set_ylabel("True positive rate")
    axs[0].set_title("ROC: spike in next 2 h (AUROC)", loc="left", fontsize=10)
    axs[1].set_xlabel("Recall")
    axs[1].set_ylabel("Precision")
    axs[1].set_title("Precision-recall (AUPRC)", loc="left", fontsize=10)
    for a in axs:
        a.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES / "spike_roc_pr.png")
    plt.close(fig)

    # 4. SHAP importance
    imp = pd.read_csv(RESULTS / "shap_importance.csv").head(15)[::-1]
    from .features import READABLE
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.barh([READABLE.get(f, f) for f in imp.feature], imp.mean_abs_shap,
            color=[ACCENT if f.startswith(("twin", "tw_")) else "#3b6fb6" for f in imp.feature])
    ax.set_xlabel("Mean |SHAP| (log-odds), spike classifier")
    ax.set_title("What drives a spike alert (teal = from the twin)", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGURES / "shap_importance.png")
    plt.close(fig)

    # 5. twin identifiability
    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.8))
    t_si = truth.SI.reindex(onb.index)
    axs[0].scatter(t_si * 1e4, onb.SI * 1e4, s=12, color=ACCENT, alpha=0.7)
    axs[0].set_xscale("log")
    axs[0].set_yscale("log")
    axs[0].set_xlabel("Hidden true insulin sensitivity (x1e-4)")
    axs[0].set_ylabel("Twin estimate after onboarding")
    axs[0].set_title(f"Insulin sensitivity, Spearman {spearmanr(onb.SI, t_si).statistic:.2f}", loc="left", fontsize=10)
    t_gb = truth.Gb.reindex(onb.index)
    axs[1].scatter(t_gb, onb.Gb, s=12, color="#3b6fb6", alpha=0.7)
    axs[1].plot([80, 220], [80, 220], color=GRID)
    axs[1].set_xlabel("Hidden true basal glucose (mg/dL)")
    axs[1].set_ylabel("Twin estimate after onboarding")
    axs[1].set_title(f"Basal glucose, Spearman {spearmanr(onb.Gb, t_gb).statistic:.2f}", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURES / "twin_identifiability.png")
    plt.close(fig)


if __name__ == "__main__":
    run()

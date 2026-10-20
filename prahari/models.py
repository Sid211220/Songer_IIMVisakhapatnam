"""Hybrid forecasting layer: twin features + LightGBM.

    python -m prahari.models

* Patient-level split (no patient appears in two sets), stratified by diagnosis: 60/20/20.
* Regression: glucose at +30/60/90/120 min (LightGBM on the change from the last reading),
  plus 10th/90th percentile models for an 80% prediction band.
* Classification: probability of a spike (CGM > 180 mg/dL sustained >= 15 min) in the next 2 h.
  The alert threshold is set on the validation patients (precision >= TARGET_PRECISION),
  then frozen and applied to the test patients.
* Ablation: the same learner with growing feature groups (CGM -> + lifestyle -> + EHR -> + twin),
  plus three non-learned baselines (persistence, linear autoregression, twin alone).
* Explanations: SHAP values (Lundberg & Lee, 2017) give the top reasons behind each alert.
"""
from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score, roc_auc_score

from .config import HORIZONS, MODELS, PROCESSED, RESULTS, SEED, TARGET_PRECISION
from .features import CGM_FEATURES, GROUPS, READABLE

REG_PARAMS = dict(n_estimators=500, learning_rate=0.04, num_leaves=31, min_child_samples=80, subsample=0.8,
                  subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, random_state=SEED, verbose=-1, n_jobs=2)
CLF_PARAMS = dict(REG_PARAMS, n_estimators=400, is_unbalance=False)


def split_patients(X: pd.DataFrame) -> dict:
    pts = X.groupby("pt").t2d.first()
    rng = np.random.default_rng(SEED)
    sets = {"train": [], "val": [], "test": []}
    for _, grp in pts.groupby(pts):
        ids = list(grp.index)
        rng.shuffle(ids)
        a, b = int(0.6 * len(ids)), int(0.8 * len(ids))
        sets["train"] += ids[:a]
        sets["val"] += ids[a:b]
        sets["test"] += ids[b:]
    return {k: sorted(v) for k, v in sets.items()}


def _fit_reg(Xtr, ytr, cols, **kw):
    m = lgb.LGBMRegressor(**{**REG_PARAMS, **kw})
    m.fit(Xtr[cols], ytr)
    return m


def train_all(X: pd.DataFrame | None = None, verbose: bool = True) -> dict:
    if X is None:
        X = pd.read_parquet(PROCESSED / "features.parquet")
    sp = split_patients(X)
    X["set"] = np.select([X.pt.isin(sp["train"]), X.pt.isin(sp["val"])], ["train", "val"], "test")
    (MODELS / "split.json").write_text(json.dumps(sp, indent=1))
    preds = X[["pt", "minute", "day", "set", "g0", "hour", "min_since_meal", "t2d", "spike", "spike_eligible",
               "spike_lead", "spike250", "spike250_eligible", "spike250_lead"] +
              [f"y_{h}" for h in HORIZONS] + [f"ytrue_{h}" for h in HORIZONS] + [f"twin_{h}" for h in HORIZONS]].copy()
    tr = X[X.set == "train"]

    # ---------------- regression
    for h in HORIZONS:
        ok = tr[f"y_{h}"].notna() & tr.g0.notna()
        y = tr.loc[ok, f"y_{h}"] - tr.loc[ok, "g0"]
        preds[f"persist_{h}"] = X.g0
        lin = Ridge(alpha=1.0).fit(tr.loc[ok, CGM_FEATURES].fillna(0), y)
        preds[f"linear_{h}"] = X.g0 + lin.predict(X[CGM_FEATURES].fillna(0))
        for name, cols in GROUPS.items():
            m = _fit_reg(tr[ok], y, cols)
            preds[f"{name}_{h}"] = X.g0 + m.predict(X[cols])
            if name.startswith("full"):
                m.booster_.save_model(str(MODELS / f"reg_{h}.txt"))
                for q in (0.1, 0.9):
                    mq = _fit_reg(tr[ok], y, cols, objective="quantile", alpha=q, n_estimators=300)
                    preds[f"q{int(q * 100)}_{h}"] = X.g0 + mq.predict(X[cols])
                    mq.booster_.save_model(str(MODELS / f"reg_{h}_q{int(q * 100)}.txt"))
        if verbose:
            print(f"  regression +{h} min done")

    # ---------------- spike classifier
    thresholds = {}
    for target in ("spike", "spike250"):
        el = X[f"{target}_eligible"] == 1
        trc = X[el & (X.set == "train")]
        for name, cols in GROUPS.items():
            m = lgb.LGBMClassifier(**CLF_PARAMS)
            m.fit(trc[cols], trc[target])
            p = np.full(len(X), np.nan)
            p[el.values] = m.predict_proba(X.loc[el, cols])[:, 1]
            preds[f"p_{target}_{name}"] = p
            if name.startswith("full"):
                m.booster_.save_model(str(MODELS / f"clf_{target}.txt"))
                full_clf = m if target == "spike" else None
                if target == "spike":
                    clf_model, clf_cols = m, cols
        # twin-only rule as a non-learned baseline score
        preds[f"p_{target}_twin-only"] = np.where(el, X.twin_peak120, np.nan)
        # thresholds on validation patients
        for name in list(GROUPS) + ["twin-only"]:
            v = preds[(preds.set == "val") & el]
            thresholds[f"{target}|{name}"] = pick_threshold(v[target].values, v[f"p_{target}_{name}"].values)
        if verbose:
            print(f"  classifier {target} done")
    (MODELS / "thresholds.json").write_text(json.dumps(thresholds, indent=1))
    feat_cols = GROUPS["full (with twin)"]
    (MODELS / "features.json").write_text(json.dumps(feat_cols))

    explain(X)
    preds.to_parquet(PROCESSED / "predictions.parquet", index=False, compression="zstd")
    if verbose:
        print(f"models: train {len(sp['train'])} / val {len(sp['val'])} / test {len(sp['test'])} patients")
    return dict(preds=preds, split=sp, thresholds=thresholds)


def explain(X: pd.DataFrame | None = None, n_reasons: int = 3) -> pd.DataFrame:
    """SHAP reasons for the spike classifier on test patients (Lundberg & Lee, 2017).

    For each anchor: the features pushing risk UP the most, mapped to plain words and de-duplicated
    (e.g. three time-of-day encodings count as one reason)."""
    import shap
    if X is None:
        X = pd.read_parquet(PROCESSED / "features.parquet")
    sp = json.loads((MODELS / "split.json").read_text())
    cols = json.loads((MODELS / "features.json").read_text())
    booster = lgb.Booster(model_file=str(MODELS / "clf_spike.txt"))
    te = X[X.pt.isin(sp["test"]) & (X.spike_eligible == 1)]
    sv = np.asarray(shap.TreeExplainer(booster).shap_values(te[cols]))
    sv = sv[1] if sv.ndim == 3 else sv
    names = [READABLE.get(c, c) for c in cols]
    order = np.argsort(-sv, axis=1)
    reasons = []
    for row, o in zip(sv, order):
        out = []
        for k in o:
            if row[k] <= 0 or len(out) == n_reasons:
                break
            if names[k] not in out:
                out.append(names[k])
        reasons.append(" | ".join(out))
    R = te[["pt", "minute"]].copy()
    R["reasons"] = reasons
    R.to_parquet(PROCESSED / "alert_reasons.parquet", index=False)
    imp = pd.DataFrame({"feature": cols, "mean_abs_shap": np.abs(sv).mean(axis=0)}).sort_values("mean_abs_shap", ascending=False)
    imp.to_csv(RESULTS / "shap_importance.csv", index=False)
    return R


def pick_threshold(y, p, target=TARGET_PRECISION):
    """Lowest threshold whose precision on validation is >= target (max recall at that precision)."""
    ok = ~np.isnan(p)
    y, p = y[ok], p[ok]
    order = np.argsort(-p)
    ys, ps = y[order], p[order]
    tp = np.cumsum(ys)
    prec = tp / np.arange(1, len(ys) + 1)
    good = np.where((prec >= target) & (np.arange(1, len(ys) + 1) >= 20))[0]
    if len(good) == 0:
        return float(np.quantile(p, 0.99))
    return float(ps[good[-1]])


if __name__ == "__main__":
    train_all()

"""Simulate the whole cohort and save the processed tables.

    python -m prahari.cohort

Writes to data/processed/:
    profiles.parquet   one row per patient: EHR summary + synthetic genetic markers
    streams.parquet    5-minute CGM + smartwatch streams (HR, RMSSD, steps, sleep stage)
    meals.parquet      every meal eaten, and what the patient logged in the app
    doses.parquet      insulin injections (insulin-treated patients only)
    days.parquet       per-day context: weekend, stress day, sleep hours
    truth.parquet      hidden simulator parameters (never shown to the twin or the models)
    personas.parquet   lifestyle persona used to generate each patient's routine
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from .config import PROCESSED
from .ehr import load_profiles
from .simulate import simulate_patient


def build(limit: int | None = None, verbose: bool = True) -> dict:
    prof = load_profiles()
    if limit:
        prof = prof.head(limit)
    out = {k: [] for k in ("streams", "meals", "doses", "days", "truth", "persona")}
    t0 = time.time()
    for i, p in enumerate(prof.to_dict("records")):
        r = simulate_patient(p)
        for k in out:
            out[k].append(pd.DataFrame([r[k]]) if isinstance(r[k], dict) else r[k])
        if verbose and (i + 1) % 25 == 0:
            print(f"  simulated {i + 1}/{len(prof)} patients ({time.time() - t0:.0f}s)")
    tables = {k: pd.concat(v, ignore_index=True) for k, v in out.items()}
    s = tables["streams"]
    for c in ("cgm", "glucose_true", "hr", "rmssd"):
        s[c] = s[c].astype("float32")
    s["steps"] = s["steps"].round().astype("int16")
    s["stage"] = s["stage"].astype("int8")
    s["minute"] = s["minute"].astype("int32")
    tables["profiles"] = prof
    names = dict(streams="streams", meals="meals", doses="doses", days="days", truth="truth",
                 persona="personas", profiles="profiles")
    for k, name in names.items():
        tables[k].to_parquet(PROCESSED / f"{name}.parquet", index=False, compression="zstd")
    if verbose:
        print(f"cohort: {len(prof)} patients, {len(s):,} stream rows, {len(tables['meals']):,} meals "
              f"-> {PROCESSED} ({time.time() - t0:.0f}s)")
    return tables


def load() -> dict:
    names = ("profiles", "streams", "meals", "doses", "days", "truth", "personas")
    return {n: pd.read_parquet(PROCESSED / f"{n}.parquet") for n in names}


if __name__ == "__main__":
    build()

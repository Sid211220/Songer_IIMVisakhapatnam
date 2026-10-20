"""Collect every number the presentation quotes into docs/src/facts.json, so slides never drift
from the results.   python scripts/make_facts.py"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prahari.config import PROCESSED, RESULTS  # noqa: E402

prof = pd.read_parquet(PROCESSED / "profiles.parquet")
meals = pd.read_parquet(PROCESSED / "meals.parquet")
streams = pd.read_parquet(PROCESSED / "streams.parquet", columns=["cgm", "glucose_true"])
sv = pd.read_csv(RESULTS / "simulator_validation.csv")
split = json.loads((ROOT / "models" / "split.json").read_text())
facts = dict(
    n=int(len(prof)), t2d=int((prof.status == "T2D").sum()), pre=int((prof.status != "T2D").sum()),
    women=int((prof.sex == "F").sum()), insulin_users=int(prof.insulin.sum()),
    meals=int(len(meals)), logged_pct=round(float(meals.logged.mean() * 100)),
    readings_m=round(len(streams) / 1e6, 2),
    mard=round(float((abs(streams.cgm - streams.glucose_true) / streams.glucose_true).mean() * 100), 1),
    hypo_true_pct=round(float((streams.glucose_true < 70).mean() * 100), 3),
    split=[len(split["train"]), len(split["val"]), len(split["test"])],
    sim_validation=sv[["check", "short", "simulated", "published"]].values.tolist(),
)
demo = ROOT / "docs" / "src" / "demo_facts.json"
if demo.exists():
    facts["demo"] = json.loads(demo.read_text())
(ROOT / "docs" / "src" / "facts.json").write_text(json.dumps(facts, indent=1))
print(json.dumps({k: v for k, v in facts.items() if k not in ("sim_validation", "demo")}))

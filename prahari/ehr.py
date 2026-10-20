"""EHR layer: Synthea CSV -> minimised patient profiles -> FHIR R4 bundle.

Synthea (Walonoski et al., 2018, JAMIA; Apache-2.0) generates the static,
historical record: demographics, diagnoses, labs, vitals and medications.
We keep only the fields the twin needs (data minimisation, in the spirit of
India's DPDP Act 2023): no names, addresses, SSNs or identifiers leave this module.

Genetic markers: Synthea has none. We add a SYNTHETIC family history flag and a
SYNTHETIC type 2 diabetes polygenic risk percentile, generated from a seeded
random draw. They are clearly labelled and are not real genetic data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SYNTHEA_DIR, SEED

T2D = 44054006
PREDIABETES = 714628002
OBS_CODES = {
    "4548-4": "hba1c",          # %
    "2339-0": "glucose_lab",    # mg/dL
    "2345-7": "glucose_lab",
    "39156-5": "bmi",
    "29463-7": "weight_kg",
    "8302-2": "height_cm",
    "8867-4": "heart_rate",
    "8480-6": "sbp",
    "8462-4": "dbp",
    "33914-3": "egfr",
    "2093-3": "chol_total",
    "18262-6": "ldl",
    "2085-9": "hdl",
    "2571-8": "triglycerides",
    "14959-1": "uacr",
}
COMORB = {
    59621000: "hypertension",
    162864005: "obesity",
    408512008: "obesity",
    431855005: "ckd", 431856006: "ckd", 433144002: "ckd", 431857002: "ckd",
    368581000119106: "neuropathy",
    1551000119108: "retinopathy", 1501000119109: "retinopathy", 97331000119101: "retinopathy",
    127013003: "nephropathy", 90781000119102: "nephropathy", 157141000119108: "nephropathy",
}
MEDS = {"metformin": "metformin", "insulin": "insulin", "liraglutide": "glp1"}


def extract_cohort(src: Path, out: Path = SYNTHEA_DIR, n_pre: int = 110, min_age: int = 25, max_age: int = 80) -> list[str]:
    """Pick adults with active type 2 diabetes (all) plus a sample with prediabetes,
    and write minimised CSVs for just those patients."""
    src = Path(src)
    pats = pd.read_csv(src / "patients.csv", parse_dates=["BIRTHDATE", "DEATHDATE"])
    cond = pd.read_csv(src / "conditions.csv", parse_dates=["START", "STOP"])
    ref = pd.Timestamp(cond["START"].max()).normalize()
    alive = pats[pats.DEATHDATE.isna()].copy()
    alive["age"] = ((ref - alive.BIRTHDATE).dt.days / 365.25).astype(int)
    alive = alive[(alive.age >= min_age) & (alive.age <= max_age)]
    active = cond[cond.STOP.isna()]
    t2d_ids = set(active[active.CODE == T2D].PATIENT) & set(alive.Id)
    pre_ids = sorted((set(active[active.CODE == PREDIABETES].PATIENT) & set(alive.Id)) - t2d_ids)
    rng = np.random.default_rng(SEED)
    pre_pick = list(rng.choice(pre_ids, size=min(n_pre, len(pre_ids)), replace=False))
    ids = sorted(t2d_ids) + sorted(pre_pick)

    out.mkdir(parents=True, exist_ok=True)
    keep = alive[alive.Id.isin(ids)][["Id", "BIRTHDATE", "GENDER"]]
    keep.to_csv(out / "patients.csv", index=False)
    cond[cond.PATIENT.isin(ids)][["START", "STOP", "PATIENT", "CODE", "DESCRIPTION"]].to_csv(out / "conditions.csv", index=False)
    meds = pd.read_csv(src / "medications.csv", usecols=["START", "STOP", "PATIENT", "CODE", "DESCRIPTION"])
    meds[meds.PATIENT.isin(ids)].to_csv(out / "medications.csv", index=False)
    obs_iter = pd.read_csv(src / "observations.csv", usecols=["DATE", "PATIENT", "CODE", "DESCRIPTION", "VALUE", "UNITS"],
                           chunksize=500_000, dtype={"CODE": str, "VALUE": str})
    parts = [ch[ch.PATIENT.isin(ids) & ch.CODE.isin(OBS_CODES.keys())] for ch in obs_iter]
    pd.concat(parts).to_csv(out / "observations.csv", index=False)
    (out / "README.txt").write_text(
        "Filtered output of Synthea (https://github.com/synthetichealth/synthea, Apache-2.0), run with\n"
        f"seed 20261020, population 1500 (Massachusetts default), CSV exporter. Reference date {ref.date()}.\n"
        "Only the columns the twin needs are kept; names, addresses and identifiers were dropped.\n"
        "Synthea patients are entirely synthetic. They follow Synthea's default US demographics; Prahari\n"
        "adds an India-calibrated lifestyle (diet, routine) in the simulation layer.\n")
    return ids


def _seed_for(pid: str) -> int:
    return int(hashlib.sha256((pid + str(SEED)).encode()).hexdigest()[:8], 16)


def load_profiles(src: Path = SYNTHEA_DIR) -> pd.DataFrame:
    """One row per patient with the latest value of each lab/vital and flags."""
    src = Path(src)
    pats = pd.read_csv(src / "patients.csv", parse_dates=["BIRTHDATE"])
    cond = pd.read_csv(src / "conditions.csv", parse_dates=["START", "STOP"])
    meds = pd.read_csv(src / "medications.csv", parse_dates=["START", "STOP"])
    obs = pd.read_csv(src / "observations.csv", parse_dates=["DATE"], dtype={"CODE": str})
    ref = pd.Timestamp(cond["START"].max()).normalize()

    obs["field"] = obs.CODE.map(OBS_CODES)
    obs["value"] = pd.to_numeric(obs.VALUE, errors="coerce")
    latest = (obs.dropna(subset=["value"]).sort_values("DATE")
              .groupby(["PATIENT", "field"]).value.last().unstack())
    n_hba1c = obs[obs.field == "hba1c"].groupby("PATIENT").size()

    rows = []
    for _, p in pats.iterrows():
        pid = p.Id
        c = cond[(cond.PATIENT == pid)]
        active = c[c.STOP.isna()]
        status = "T2D" if (active.CODE == T2D).any() else "prediabetes"
        t2d_start = c[c.CODE == T2D].START.min()
        m = meds[(meds.PATIENT == pid) & meds.STOP.isna()]
        r = dict(patient_id=pid, sex=p.GENDER, age=int((ref - p.BIRTHDATE).days / 365.25), status=status,
                 diabetes_years=float((ref - t2d_start).days / 365.25) if pd.notna(t2d_start) else 0.0)
        for f in sorted(set(OBS_CODES.values())):
            r[f] = float(latest.loc[pid, f]) if (pid in latest.index and f in latest.columns and pd.notna(latest.loc[pid, f])) else np.nan
        r["n_hba1c_tests"] = int(n_hba1c.get(pid, 0))
        for code, name in COMORB.items():
            r[name] = int(r.get(name, 0) or (active.CODE == code).any())
        for key, name in MEDS.items():
            r[name] = int(m.DESCRIPTION.str.contains(key, case=False).any())
        # SYNTHETIC genetic markers (not from Synthea; clearly labelled)
        g = np.random.default_rng(_seed_for(pid))
        r["syn_family_history"] = int(g.random() < (0.55 if status == "T2D" else 0.35))
        r["syn_prs_percentile"] = float(np.clip(g.beta(2.6, 1.8) * 100 if status == "T2D" else g.beta(2.0, 2.0) * 100, 1, 99))
        rows.append(r)
    df = pd.DataFrame(rows)

    # --- Clinical plausibility repair (documented, flagged) -------------------
    # Synthea's diabetes module emits some HbA1c values that are physiologically
    # implausible (< 4%) or inconsistent with the coded diagnosis. We keep the
    # Synthea value when it fits the diagnosis (T2D >= 6.0%; prediabetes 5.7-6.4%,
    # ADA definition) and otherwise re-draw it, seeded, inside that range.
    df["hba1c_synthea"] = df.hba1c
    med3 = (obs[obs.field == "hba1c"].dropna(subset=["value"]).sort_values("DATE")
            .groupby("PATIENT").value.apply(lambda v: float(np.median(v.tail(3)))))
    df["hba1c"] = df.patient_id.map(med3).astype(float)
    rep = []
    for i, r in df.iterrows():
        g = np.random.default_rng(_seed_for(r.patient_id) + 7)
        v = r.hba1c
        if r.status == "T2D":
            ok = pd.notna(v) and 6.0 <= v <= 12.0
            new = v if ok else float(np.round(g.uniform(6.5, 9.5), 1))
        else:
            ok = pd.notna(v) and 5.7 <= v <= 6.4
            new = v if ok else float(np.round(g.uniform(5.7, 6.4), 1))
        df.at[i, "hba1c"] = new
        rep.append(int(not ok))
    df["hba1c_repaired"] = rep
    # Synthea occasionally keeps insulin on a prediabetes record; not clinically coherent.
    df["insulin_repaired"] = ((df.status != "T2D") & (df.insulin == 1)).astype(int)
    df.loc[df.status != "T2D", ["insulin", "metformin", "glp1"]] = 0
    for f, v in dict(bmi=27.0, weight_kg=75.0, heart_rate=74.0, sbp=128.0, dbp=80.0, egfr=85.0,
                     ldl=110.0, hdl=45.0, triglycerides=150.0, chol_total=190.0).items():
        df[f] = df[f].fillna(v)
    df = df.sort_values(["status", "patient_id"], ascending=[False, True]).reset_index(drop=True)
    df.insert(0, "pt", [f"PT-{i + 1:03d}" for i in range(len(df))])
    return df


def to_fhir_bundle(profile: dict) -> dict:
    """Minimal FHIR R4 collection bundle for one patient (the format ABDM uses)."""
    pid = profile["pt"]
    def obs(code, display, value, unit):
        return {"resource": {"resourceType": "Observation", "status": "final",
                             "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
                             "subject": {"reference": f"Patient/{pid}"},
                             "valueQuantity": {"value": round(float(value), 2), "unit": unit}}}
    entries = [{"resource": {"resourceType": "Patient", "id": pid,
                             "gender": "male" if profile["sex"] == "M" else "female"}}]
    entries.append({"resource": {"resourceType": "Condition", "subject": {"reference": f"Patient/{pid}"},
                                 "code": {"coding": [{"system": "http://snomed.info/sct",
                                                      "code": str(T2D if profile["status"] == "T2D" else PREDIABETES),
                                                      "display": "Diabetes mellitus type 2" if profile["status"] == "T2D" else "Prediabetes"}]}}})
    for code, field, disp, unit in [("4548-4", "hba1c", "Hemoglobin A1c", "%"), ("39156-5", "bmi", "BMI", "kg/m2"),
                                    ("33914-3", "egfr", "eGFR", "mL/min/1.73m2"), ("8480-6", "sbp", "Systolic BP", "mm[Hg]")]:
        entries.append(obs(code, disp, profile[field], unit))
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}


if __name__ == "__main__":
    import sys
    ids = extract_cohort(Path(sys.argv[1]))
    prof = load_profiles()
    print(len(ids), "patients;", prof.status.value_counts().to_dict())
    print(json.dumps(to_fhir_bundle(prof.iloc[0].to_dict()), indent=1)[:600])

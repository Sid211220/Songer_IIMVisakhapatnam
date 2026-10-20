"""Fast checks of the building blocks (run: python -m pytest -q)."""
import numpy as np
import pandas as pd
import pytest

from prahari import foods
from prahari.evaluate import clarke_zones
from prahari.features import _spike_onsets
from prahari.simulate import sleep_multiplier, simulate_patient
from prahari.twin import NSTATE, _step, prior

PATIENT = dict(patient_id="test-patient", pt="PT-T", sex="M", age=52, status="T2D", diabetes_years=4.0, hba1c=7.4,
               bmi=27.5, weight_kg=78.0, heart_rate=76.0, egfr=82.0, insulin=0, metformin=1, glp1=0,
               neuropathy=0, syn_prs_percentile=60.0)


def test_meal_totals():
    c, gi = foods.meal_totals([("white_rice_katori", 2), ("dal_katori", 1)])
    assert c == pytest.approx(108)
    assert 35 < gi < 79


def test_sleep_multiplier_bounds():
    assert sleep_multiplier(8.0) == pytest.approx(1.0)
    assert sleep_multiplier(4.0) == pytest.approx(0.75)


@pytest.fixture(scope="module")
def sim():
    return simulate_patient(PATIENT)


def test_simulator_hits_hba1c_target(sim):
    s = sim["streams"]
    eag = 28.7 * PATIENT["hba1c"] - 46.7
    assert abs(s.glucose_true.mean() - sim["truth"]["target_mean"]) < 3
    assert abs(sim["truth"]["target_mean"] / eag - 1) < 0.2


def test_simulator_streams_shape(sim):
    s = sim["streams"]
    assert len(s) == 21 * 288
    assert s.cgm.between(40, 400).all() or s.cgm.isna().any()
    assert set(s.stage.unique()) <= {0, 1, 2, 3}
    assert sim["meals"].carbs.gt(0).all()


def test_cgm_noise_is_realistic(sim):
    s = sim["streams"].dropna(subset=["cgm"])
    mard = (abs(s.cgm - s.glucose_true) / s.glucose_true).mean() * 100
    assert 4 < mard < 16


def test_twin_step_is_stable():
    pr = prior(PATIENT)
    th = pr["theta"]
    s = np.zeros(NSTATE)
    s[0] = s[10] = th["Gb"]
    for m in range(600):
        _step(s, th["SI"], th["Gb"], 1.0, th["kabs"], 0.0, pr["gamma"], pr["BW"], pr["Vi_ml"],
              60000.0 if m == 10 else 0.0, 0.0, 1.0, 0.0, 12.0)
    assert np.isfinite(s).all()
    assert abs(s[0] - th["Gb"]) < 25          # returns towards baseline after the meal


def test_twin_walk_lowers_peak():
    pr = prior(PATIENT)
    th = pr["theta"]

    def run(walk):
        s = np.zeros(NSTATE)
        s[0] = s[10] = th["Gb"]
        peak = 0
        for m in range(240):
            a = 1.0 if (walk and 15 <= m < 30) else 0.0
            _step(s, th["SI"], th["Gb"], 1.0, th["kabs"], 0.0, pr["gamma"], pr["BW"], pr["Vi_ml"],
                  60000.0 if m == 0 else 0.0, a, 1.0, 0.0, 13.0)
            peak = max(peak, s[10])
        return peak
    assert run(True) < run(False)


def test_spike_onset_needs_sustain_and_quiet():
    x = np.array([150] * 8 + [190, 195, 200, 170] + [150] * 8 + [185, 186] + [150] * 4, dtype=float)
    on = _spike_onsets(x, 180)
    assert on[8] and on.sum() == 1          # second excursion lasts only 10 minutes


def test_clarke_zone_a():
    assert (clarke_zones([100, 200], [105, 190]) == "A").all()
    assert clarke_zones([50], [250])[0] == "E"

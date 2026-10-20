"""Single place for paths, seeds and clinical thresholds."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SYNTHEA_DIR = DATA / "synthea"            # filtered Synthea CSVs (EHR layer)
PROCESSED = DATA / "processed"            # simulated streams + features
MODELS = ROOT / "models"
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"

SEED = 20261020

# Study design
DAYS = 21                 # simulated days per patient
ONBOARD_DAYS = 7          # days 1-7: the twin is calibrated ("onboarding week")
STEP_MIN = 5              # CGM / wearable sample interval (minutes)
HORIZONS = [30, 60, 90, 120]   # forecast horizons (minutes)
ANCHOR_EVERY_MIN = 15     # one forecast anchor every 15 minutes

# Clinical thresholds (mg/dL)
# Battelino et al. (2019) International Consensus on Time in Range;
# ADA Standards of Care: peak postprandial glucose < 180 mg/dL.
HYPER_L1 = 180.0
HYPER_L2 = 250.0
HYPO_L1 = 70.0
SPIKE_SUSTAIN_MIN = 15    # an event = glucose above threshold for >= 15 minutes

# Alert operating point: the lowest threshold reaching 70% precision on the validation patients
# (see models.py). A notification is followed by a 120-minute cooldown.
ALERT_COOLDOWN_MIN = 120
TARGET_PRECISION = 0.70

for p in (DATA, SYNTHEA_DIR, PROCESSED, MODELS, RESULTS, FIGURES):
    p.mkdir(parents=True, exist_ok=True)

"""Rebuild everything from the filtered Synthea CSVs: cohort -> twins -> features -> models -> evaluation.

    python scripts/run_all.py            # full run, about 20 minutes on a 2-core laptop
    python scripts/run_all.py --quick    # skip the static-twin ablation
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prahari import cohort, evaluate, features, models, twin, validate_sim  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    print("1/6 simulating the cohort (EHR + lifestyle + physiology + sensors)")
    cohort.build()
    print("2/6 building a digital twin per patient (onboarding + nightly re-calibration)")
    twin.run_cohort(nightly=True)
    if "--quick" not in sys.argv:
        twin.run_cohort(nightly=False)          # ablation: twin frozen after onboarding
    print("3/6 feature table")
    features.build()
    print("4/6 training models")
    models.train_all()
    print("5/6 evaluation")
    evaluate.run()
    print("6/6 simulator face-validity checks")
    validate_sim.run()
    print(f"done in {(time.time() - t0) / 60:.1f} min")

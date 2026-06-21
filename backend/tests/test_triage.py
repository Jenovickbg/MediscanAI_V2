import tempfile
from pathlib import Path

import numpy as np

from app.services.pipeline_service import pipeline_service
from app.services.triage_config import TriageThresholds, classifier_triage, load_triage_thresholds


def test_classifier_triage_three_levels():
    thresholds = TriageThresholds(seuil_bas=0.03, seuil_haut=0.10)

    assert classifier_triage(0.02, thresholds) == "normal"
    assert classifier_triage(0.03, thresholds) == "incertain"
    assert classifier_triage(0.05, thresholds) == "incertain"
    assert classifier_triage(0.10, thresholds) == "eleve"
    assert classifier_triage(0.97, thresholds) == "eleve"


def test_load_triage_thresholds_from_json():
    thresholds = load_triage_thresholds()
    assert thresholds.seuil_bas == 0.03
    assert thresholds.seuil_haut == 0.10


def test_load_triage_thresholds_fallback_on_missing_file():
    missing = Path(tempfile.gettempdir()) / "missing_triage_config.json"
    thresholds = load_triage_thresholds(missing)
    assert thresholds.seuil_bas == 0.03
    assert thresholds.seuil_haut == 0.10


def test_run_model_1_triage_mock_all_slices():
    volume = np.zeros((12, 64, 64), dtype=np.int16)
    triage = pipeline_service.run_model_1_triage(volume, study_id="TEST-TRIAGE")

    assert len(triage) == 12
    assert all("slice" in entry and "score" in entry and "categorie" in entry for entry in triage)
    assert all(entry["categorie"] in ("normal", "incertain", "eleve") for entry in triage)


def test_predict_volume_includes_triage_fields():
    volume = np.zeros((12, 64, 64), dtype=np.int16)
    prediction = pipeline_service.predict_volume(volume, study_id="TEST-PRED")

    assert "triage_par_coupe" in prediction
    assert "coupes_flaguees" in prediction
    assert len(prediction["triage_par_coupe"]) == 12
    assert prediction["coupes_flaguees"] == pipeline_service.coupes_flaguees_from_triage(
        prediction["triage_par_coupe"]
    )
    assert prediction["fracture_detectee"] is True


def test_coupes_flaguees_excludes_normal():
    triage = [
        {"slice": 0, "score": 0.01, "categorie": "normal"},
        {"slice": 1, "score": 0.05, "categorie": "incertain"},
        {"slice": 2, "score": 0.15, "categorie": "eleve"},
    ]
    flagged = pipeline_service.coupes_flaguees_from_triage(triage)
    assert flagged == [1, 2]

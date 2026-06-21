import numpy as np

from app.models.resultat import VERTEBRES
from app.services.pipeline_service import pipeline_service
from app.services.triage_config import classifier_triage, load_triage_thresholds


def test_analyser_examen_contract_with_flagged_slices():
    volume = np.zeros((24, 64, 64), dtype=np.int16)
    result = pipeline_service.analyser_examen(volume, study_id="ORCH-FLAG")

    assert result["study_id"] == "ORCH-FLAG"
    assert isinstance(result["fracture_detectee"], bool)
    assert isinstance(result["scores_par_vertebre"], dict)
    assert isinstance(result["rapport_clinique"], str)
    assert result["rapport_clinique"]
    assert "triage_par_coupe" in result
    assert len(result["coupes_flaguees"]) > 0

    for label, entry in result["scores_par_vertebre"].items():
        assert label in VERTEBRES
        assert 0.0 <= entry["probabilite"] <= 1.0
        assert entry["niveau_risque"] in ("normal", "incertain", "eleve")
        assert isinstance(entry["coupe_reference"], int)
        bbox = entry.get("bounding_box")
        if bbox is not None:
            assert set(bbox.keys()) == {"x", "y", "w", "h"}


def test_analyser_examen_early_exit_when_no_flagged_slices(monkeypatch):
    volume = np.zeros((8, 64, 64), dtype=np.int16)
    normal_triage = [{"slice": i, "score": 0.01, "categorie": "normal"} for i in range(8)]

    monkeypatch.setattr(
        pipeline_service,
        "run_model_1_triage",
        lambda _volume, study_id="": normal_triage,
    )
    model2_called = False
    model3_called = False

    def _no_model2(*_args, **_kwargs):
        nonlocal model2_called
        model2_called = True
        return {}

    def _no_model3(*_args, **_kwargs):
        nonlocal model3_called
        model3_called = True
        return {}

    monkeypatch.setattr(pipeline_service, "run_model_2_localization", _no_model2)
    monkeypatch.setattr(pipeline_service, "run_model_3_vertebra", _no_model3)

    result = pipeline_service.analyser_examen(volume, study_id="ORCH-NORMAL")

    assert result["fracture_detectee"] is False
    assert result["scores_par_vertebre"] == {}
    assert "Aucune anomalie" in result["rapport_clinique"]
    assert result["coupes_flaguees"] == []
    assert model2_called is False
    assert model3_called is False


def test_agreger_par_vertebre_skips_hors_zone():
    triage = [
        {"slice": 10, "score": 0.85, "categorie": "eleve"},
        {"slice": 11, "score": 0.42, "categorie": "incertain"},
    ]
    bbox = {
        10: {"bbox": [100, 120, 30, 28], "confidence": 0.9},
        11: {"bbox": [200, 180, 25, 22], "confidence": 0.7},
    }
    vertebre = {10: "C5", 11: "hors_zone"}

    aggregated = pipeline_service._agreger_par_vertebre(triage, bbox, vertebre)

    assert "C5" in aggregated
    assert "hors_zone" not in aggregated
    assert aggregated["C5"]["probabilite"] == 0.85
    assert aggregated["C5"]["bounding_box"] == {"x": 100, "y": 120, "w": 30, "h": 28}
    assert aggregated["C5"]["coupe_reference"] == 10
    assert aggregated["C5"]["niveau_risque"] == classifier_triage(0.85, load_triage_thresholds())


def test_agreger_par_vertebre_keeps_highest_score_per_vertebra():
    triage = [
        {"slice": 5, "score": 0.55, "categorie": "incertain"},
        {"slice": 6, "score": 0.92, "categorie": "eleve"},
    ]
    bbox = {
        5: {"bbox": [10, 10, 20, 20], "confidence": 0.6},
        6: {"bbox": [30, 30, 25, 25], "confidence": 0.95},
    }
    vertebre = {5: "C4", 6: "C4"}

    aggregated = pipeline_service._agreger_par_vertebre(triage, bbox, vertebre)

    assert aggregated["C4"]["probabilite"] == 0.92
    assert aggregated["C4"]["coupe_reference"] == 6


def test_build_vertebra_details_from_analyse_returns_seven_rows():
    analyse = {
        "scores_par_vertebre": {
            "C5": {
                "probabilite": 0.97,
                "bounding_box": {"x": 245, "y": 180, "w": 32, "h": 28},
                "coupe_reference": 187,
                "niveau_risque": "eleve",
            }
        }
    }
    details = pipeline_service.build_vertebra_details_from_analyse(analyse, n_slices=352)

    assert len(details) == 7
    c5 = next(d for d in details if d["vertebre"] == "C5")
    assert c5["probabilite"] == 0.97
    assert c5["coupe_reference"] == 187
    assert c5["niveau_risque"] == "eleve"
    assert 0.0 < c5["bounding_box_x"] < 1.0


def test_score_global_from_analyse_uses_aggregated_scores():
    analyse = {
        "scores_par_vertebre": {
            "C3": {"probabilite": 0.4},
            "C5": {"probabilite": 0.97},
        }
    }
    assert pipeline_service.score_global_from_analyse(analyse) == 0.97


def test_analyser_examen_mock_c5_detection():
    volume = np.zeros((24, 64, 64), dtype=np.int16)
    result = pipeline_service.analyser_examen(volume, study_id="TEST-MOCK")

    assert result["mode_mock"] is True
    assert result["fracture_detectee"] is True
    assert "C5" in result["scores_par_vertebre"]
    assert result["scores_par_vertebre"]["C5"]["niveau_risque"] == "eleve"

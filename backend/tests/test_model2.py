import numpy as np

from app.services.model2_localization import Model2LocalizationService
from app.services.pipeline_service import pipeline_service


def test_model2_runs_only_on_flagged_slices():
    volume = np.zeros((20, 64, 64), dtype=np.int16)
    coupes_flaguees = [3, 8, 14]

    resultats = pipeline_service.run_model_2_localization(
        volume,
        coupes_flaguees,
        study_id="M2-FLAGGED",
    )

    assert set(resultats.keys()) == {3, 8, 14}
    assert len(resultats) == 3
    assert len(resultats) < volume.shape[0]
    for slice_idx, entry in resultats.items():
        assert "bbox" in entry and "confidence" in entry
        assert len(entry["bbox"]) == 4
        assert 0.0 < entry["confidence"] <= 1.0
        x, y, w, h = entry["bbox"]
        assert x >= 0 and y >= 0 and w > 0 and h > 0


def test_model2_empty_when_no_flagged_slices():
    volume = np.zeros((10, 64, 64), dtype=np.int16)
    resultats = pipeline_service.run_model_2_localization(volume, [], study_id="M2-EMPTY")
    assert resultats == {}


def test_model2_never_processes_all_slices_on_large_volume():
    volume = np.zeros((352, 128, 128), dtype=np.int16)
    triage = pipeline_service.run_model_1_triage(volume, study_id="M2-LARGE")
    coupes_flaguees = pipeline_service.coupes_flaguees_from_triage(triage)

    resultats = pipeline_service.run_model_2_localization(
        volume,
        coupes_flaguees,
        study_id="M2-LARGE",
        triage_par_coupe=triage,
    )

    assert len(resultats) == len(coupes_flaguees)
    assert len(resultats) < volume.shape[0]


def test_predict_volume_includes_model2_localisation():
    volume = np.zeros((12, 64, 64), dtype=np.int16)
    prediction = pipeline_service.predict_volume(volume, study_id="M2-PRED")

    assert "resultats_localisation" in prediction
    assert prediction["mode_mock_model_2"] is True
    flagged = prediction["coupes_flaguees"]
    assert set(prediction["resultats_localisation"].keys()) == set(flagged)


def test_model2_mock_deterministic():
    volume = np.zeros((12, 64, 64), dtype=np.int16)
    service = Model2LocalizationService()
    coupes = [5, 7]

    first = service.run(volume, coupes, study_id="DET")
    second = service.run(volume, coupes, study_id="DET")
    assert first == second

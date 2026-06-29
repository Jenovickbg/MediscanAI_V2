import numpy as np
import pytest

from app.models.resultat import VERTEBRES
from app.services.model3_vertebra import VERTEBRA_CLASSES, VERTEBRA_CLASSES_7, Model3VertebraService
from app.services.pipeline_service import pipeline_service


def test_vertebra_classes_order():
    assert list(VERTEBRA_CLASSES) == list(VERTEBRES)
    assert VERTEBRA_CLASSES == VERTEBRA_CLASSES_7


def test_model3_runs_only_on_flagged_slices():
    volume = np.zeros((20, 64, 64), dtype=np.int16)
    coupes_flaguees = [2, 9, 15]

    resultats = pipeline_service.run_model_3_vertebra(
        volume,
        coupes_flaguees,
        study_id="M3-FLAGGED",
    )

    assert set(resultats.keys()) == {2, 9, 15}
    assert len(resultats) == 3
    assert len(resultats) < volume.shape[0]
    for entry in resultats.values():
        assert "vertebre" in entry and "confiance" in entry
        assert entry["vertebre"] in VERTEBRA_CLASSES


def test_model3_empty_when_no_flagged_slices():
    volume = np.zeros((10, 64, 64), dtype=np.int16)
    resultats = pipeline_service.run_model_3_vertebra(volume, [], study_id="M3-EMPTY")
    assert resultats == {}


def test_model3_never_processes_all_slices_on_large_volume():
    volume = np.zeros((352, 128, 128), dtype=np.int16)
    triage = pipeline_service.run_model_1_triage(volume, study_id="M3-LARGE")
    coupes_flaguees = pipeline_service.coupes_flaguees_from_triage(triage)

    resultats = pipeline_service.run_model_3_vertebra(
        volume,
        coupes_flaguees,
        study_id="M3-LARGE",
    )

    assert len(resultats) == len(coupes_flaguees)
    assert len(resultats) < volume.shape[0]


def test_predict_volume_includes_model3_vertebra():
    volume = np.zeros((12, 64, 64), dtype=np.int16)
    prediction = pipeline_service.predict_volume(volume, study_id="M3-PRED")

    assert "resultats_vertebre" in prediction
    assert prediction["mode_mock_model_3"] is True
    flagged = prediction["coupes_flaguees"]
    assert set(prediction["resultats_vertebre"].keys()) == set(flagged)


def test_model3_mock_deterministic():
    volume = np.zeros((12, 64, 64), dtype=np.int16)
    service = Model3VertebraService()
    coupes = [4, 6]

    def stack_builder(vol: np.ndarray, idx: int) -> np.ndarray:
        return pipeline_service.build_25d_stack(vol, idx)

    first = service.run(volume, coupes, study_id="DET3", stack_builder=stack_builder)
    second = service.run(volume, coupes, study_id="DET3", stack_builder=stack_builder)
    assert first == second


def test_model3_requires_stack_builder():
    volume = np.zeros((8, 64, 64), dtype=np.int16)
    service = Model3VertebraService()
    with pytest.raises(ValueError, match="stack_builder"):
        service.run(volume, [1], study_id="NO-BUILDER")

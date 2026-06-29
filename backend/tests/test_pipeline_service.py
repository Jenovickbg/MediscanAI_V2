import numpy as np

from app.models.resultat import VERTEBRES
from app.services.pipeline_service import PipelineAIService, pipeline_service


def test_predict_volume_mock_returns_seven_vertebrae():
    volume = np.random.default_rng(42).integers(-200, 800, size=(24, 256, 256), dtype=np.int16)

    prediction = pipeline_service.predict_volume(volume, study_id="TEST-MOCK")

    assert prediction["mode_mock"] is True
    assert len(prediction["scores_par_vertebre"]) == 7
    assert all(v in prediction["scores_par_vertebre"] for v in VERTEBRES)
    assert 0.0 <= prediction["score_global"] <= 1.0
    assert isinstance(prediction["fracture_detectee"], bool)


def test_build_vertebra_details_structure():
    volume = np.random.default_rng(7).integers(-100, 600, size=(14, 128, 128), dtype=np.int16)
    prediction = pipeline_service.predict_volume(volume)

    details = pipeline_service.build_vertebra_details(prediction, volume.shape[0])

    assert len(details) == 7
    for detail in details:
        assert detail["vertebre"] in VERTEBRES
        assert 0.0 <= detail["probabilite"] <= 1.0
        assert detail["localisation"]
        assert 0 <= detail["coupe_reference"] < volume.shape[0]


def test_generate_gradcam_mock_shape():
    volume = np.random.default_rng(3).integers(0, 400, size=(10, 64, 64), dtype=np.int16)

    rgb = pipeline_service.generate_gradcam(volume, slice_idx=5, vertebra_id="C5")

    assert rgb.shape == (64, 64, 3)
    assert rgb.dtype == np.uint8


def test_render_gradcam_png_returns_bytes():
    volume = np.random.default_rng(9).integers(0, 400, size=(10, 64, 64), dtype=np.int16)

    png_bytes = pipeline_service.render_gradcam_png(
        volume, slice_idx=4, vertebra_id="C4", overlay=True
    )

    assert isinstance(png_bytes, bytes)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_clinical_report_contains_sections():
    scores = {f"C{i}": 0.1 * i for i in range(1, 8)}
    scores["C5"] = 0.85

    report = pipeline_service.generate_clinical_report(scores, fracture_detectee=True)

    assert "RÉSUMÉ" in report
    assert "C5" in report
    assert "RECOMMANDATION" in report


def test_mock_mode_when_model_missing():
    service = pipeline_service
    assert service.use_mock is True
    assert service.thresholds.seuil_bas == 0.15
    assert service.thresholds.seuil_haut == 0.30

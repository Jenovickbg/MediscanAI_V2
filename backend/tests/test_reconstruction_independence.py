import numpy as np

from app.services.reconstruction_service import ReconstructionService


def test_reconstruction_service_has_no_pipeline_import():
    import app.services.reconstruction_service as recon_module

    assert "pipeline_service" not in recon_module.__dict__
    assert "PipelineAIService" not in recon_module.__dict__


def test_build_mesh_does_not_require_ai_scores():
    service = ReconstructionService()
    volume = np.random.default_rng(1).integers(-200, 800, size=(12, 64, 64), dtype=np.int16)
    spacing = {
        "pixel_spacing": [1.0, 1.0],
        "slice_thickness": 1.0,
        "slice_positions": list(range(12)),
        "volume_kind": "dicom_hu",
        "hu_rescale_applied": True,
        "sort_method": "ImagePositionPatient[2]",
    }

    mesh = service.build_mesh(volume, spacing)

    assert "vertices" in mesh
    assert "faces" in mesh
    assert len(mesh["vertices"]) > 0
    assert len(mesh["faces"]) <= 120_000


def test_png_preview_uses_procedural_mesh():
    service = ReconstructionService()
    volume = np.random.default_rng(2).uniform(0, 255, size=(12, 128, 128)).astype(np.float32)
    spacing = {
        "pixel_spacing": [0.5, 0.5],
        "slice_thickness": 1.0,
        "volume_kind": "png_preview",
        "hu_rescale_applied": False,
        "sort_method": "nom_fichier_png (apercu demo)",
    }

    mesh = service.build_mesh(volume, spacing)

    assert len(mesh["faces"]) < 10_000
    assert len(mesh["vertices"]) < 10_000


def test_is_hounsfield_volume():
    service = ReconstructionService()
    ct = np.random.default_rng(3).integers(-1000, 1200, size=(8, 32, 32))
    png_like = np.random.default_rng(4).integers(0, 255, size=(8, 32, 32))

    assert service._is_hounsfield_volume(ct) is True
    assert service._is_hounsfield_volume(png_like) is False


def test_colorize_mesh_uses_niveau_risque():
    service = ReconstructionService()
    indices = [4, 4, 5, 5]
    colors = service.colorize_mesh(
        indices,
        scores={"C5": 0.1},
        niveaux_risque={"C5": "eleve", "C6": "incertain"},
    )

    assert colors[0] == "#FF4757"
    assert colors[2] == "#FFA048"


def test_dicom_get_mpr_slice_views():
    from app.services.dicom_service import DicomService

    volume = np.arange(4 * 3 * 5, dtype=np.int16).reshape(4, 3, 5)
    service = DicomService()

    axial = service.get_mpr_slice(volume, "axial", 2)
    assert axial.shape == (3, 5)

    sagittal = service.get_mpr_slice(volume, "sagittal", 1)
    assert sagittal.shape == (4, 3)

    coronal = service.get_mpr_slice(volume, "coronal", 0)
    assert coronal.shape == (4, 5)

import numpy as np
import pytest

from app.services.reconstruction_service import (
    ReconstructionService,
    Z_CROP_END_RATIO,
    Z_CROP_START_RATIO,
)


def test_reconstruction_service_has_no_pipeline_import():
    import app.services.reconstruction_service as recon_module

    assert "pipeline_service" not in recon_module.__dict__
    assert "PipelineAIService" not in recon_module.__dict__


def test_cervical_crop_ratios():
    service = ReconstructionService()
    volume = np.arange(100 * 4 * 4, dtype=np.float32).reshape(100, 4, 4)
    total = volume.shape[0]
    debut = int(total * Z_CROP_START_RATIO)
    fin = int(total * Z_CROP_END_RATIO)
    cropped = volume[debut:fin, :, :]

    assert debut == 20
    assert fin == 65
    assert cropped.shape[0] == 45
    assert cropped[0, 0, 0] == volume[20, 0, 0]


def test_build_mesh_png_preview_uses_procedural(tmp_path):
    service = ReconstructionService()
    for i in range(3):
        from PIL import Image

        img = Image.new("L", (64, 64), color=128)
        img.save(tmp_path / f"slice_{i:03d}.png")

    mesh = service.build_mesh(str(tmp_path))

    assert "vertices" in mesh
    assert len(mesh["faces"]) < 10_000
    assert len(mesh["vertices"]) < 10_000


def test_build_mesh_dicom_study(tmp_path):
    pytest.importorskip("pydicom")
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    service = ReconstructionService()
    for z in range(8):
        ds = Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        ds.SOPClassUID = generate_uid()
        ds.SOPInstanceUID = generate_uid()
        ds.ImagePositionPatient = [0.0, 0.0, float(z)]
        ds.PixelSpacing = [1.0, 1.0]
        ds.SliceThickness = 1.0
        ds.RescaleSlope = 1
        ds.RescaleIntercept = -1000
        arr = np.full((32, 32), -900, dtype=np.int16)
        arr[10:22, 10:22] = 400
        ds.PixelData = arr.tobytes()
        ds.Rows, ds.Columns = 32, 32
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        pydicom.dcmwrite(str(tmp_path / f"slice_{z:03d}.dcm"), ds)

    mesh = service.build_mesh(str(tmp_path))

    assert len(mesh["vertices"]) > 0
    assert len(mesh["faces"]) > 0
    assert len(mesh["faces"]) <= 120_000
    assert "stats" in mesh


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

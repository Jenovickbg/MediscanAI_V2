from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
from PIL import Image

from app.utils.dicom_utils import is_dicom_file


class DicomService:
    def load_and_sort_slices(self, study_path: str) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Charge et trie les fichiers DICOM par position Z (ImagePositionPatient[2]).
        Retourne un volume (n_slices, H, W) en int16 Hounsfield et les espacements.
        """
        path = Path(study_path)
        slices: list[tuple[float, np.ndarray, tuple[float, float] | None]] = []

        for file_path in path.iterdir():
            if not file_path.is_file() or not is_dicom_file(file_path.name):
                continue
            try:
                ds = pydicom.dcmread(str(file_path), force=True)
                if not hasattr(ds, "pixel_array"):
                    continue
                pixel_array = ds.pixel_array.astype(np.float32)
                slope = float(getattr(ds, "RescaleSlope", 1))
                intercept = float(getattr(ds, "RescaleIntercept", 0))
                hu = pixel_array * slope + intercept

                z_pos = 0.0
                if hasattr(ds, "ImagePositionPatient") and ds.ImagePositionPatient is not None:
                    z_pos = float(ds.ImagePositionPatient[2])

                spacing = None
                if hasattr(ds, "PixelSpacing") and ds.PixelSpacing is not None:
                    spacing = (float(ds.PixelSpacing[0]), float(ds.PixelSpacing[1]))

                slices.append((z_pos, hu.astype(np.int16), spacing))
            except Exception:
                continue

        if not slices:
            raise ValueError("Impossible de charger les coupes DICOM")

        slices.sort(key=lambda item: item[0])
        volume = np.stack([item[1] for item in slices], axis=0)
        pixel_spacing = slices[0][2] or (1.0, 1.0)

        spacing_dict = {
            "pixel_spacing": list(pixel_spacing),
            "slice_thickness": 1.0,
            "slice_positions": [item[0] for item in slices],
        }

        return volume, spacing_dict

    def load_volume_from_study(self, study_path: str) -> tuple[np.ndarray, dict[str, Any]]:
        """Charge un volume DICOM ou, à défaut, une pile PNG (examens démo)."""
        path = Path(study_path)
        dicom_files = [p for p in path.iterdir() if p.is_file() and is_dicom_file(p.name)]

        if dicom_files:
            return self.load_and_sort_slices(study_path)

        png_files = sorted(path.glob("*.png"))
        if not png_files:
            raise ValueError("Aucune donnée d'imagerie trouvée pour cet examen")

        slices: list[np.ndarray] = []
        for png in png_files:
            with Image.open(png) as img:
                arr = np.array(img.convert("L"), dtype=np.int16)
                slices.append(arr)

        volume = np.stack(slices, axis=0)
        spacing_dict = {
            "pixel_spacing": [0.5, 0.5],
            "slice_thickness": 1.0,
            "slice_positions": list(range(volume.shape[0])),
        }
        return volume, spacing_dict

    def extract_study_metadata(self, study_path: Path) -> dict[str, Any]:
        path = Path(study_path)
        dicom_files = [p for p in path.iterdir() if p.is_file() and is_dicom_file(p.name)]

        study_uid: str | None = None
        date_examen: datetime | None = None
        dimensions: list[int] | None = None
        pixel_spacing: list[float] | None = None
        slice_thickness: float | None = None

        if dicom_files:
            try:
                ds = pydicom.dcmread(str(dicom_files[0]), stop_before_pixels=True, force=True)
                study_uid = str(getattr(ds, "StudyInstanceUID", "") or "") or None
                study_date = getattr(ds, "StudyDate", None)
                study_time = getattr(ds, "StudyTime", None)
                if study_date:
                    time_part = "000000"
                    if study_time:
                        time_part = str(study_time).split(".")[0][:6].ljust(6, "0")
                    date_examen = datetime.strptime(f"{study_date}{time_part}", "%Y%m%d%H%M%S")
                if hasattr(ds, "PixelSpacing") and ds.PixelSpacing is not None:
                    pixel_spacing = [float(ds.PixelSpacing[0]), float(ds.PixelSpacing[1])]
                slice_thickness = float(getattr(ds, "SliceThickness", 1.0))
            except Exception:
                pass

            try:
                volume, spacing = self.load_and_sort_slices(str(path))
                dimensions = [int(volume.shape[2]), int(volume.shape[1]), int(volume.shape[0])]
                pixel_spacing = spacing.get("pixel_spacing", pixel_spacing)
                slice_thickness = spacing.get("slice_thickness", slice_thickness)
            except Exception:
                dimensions = [512, 512, len(dicom_files)]

        return {
            "study_instance_uid": study_uid,
            "date_examen": date_examen,
            "dimensions": dimensions,
            "pixel_spacing": pixel_spacing,
            "slice_thickness": slice_thickness,
        }

    def apply_windowing(
        self,
        volume: np.ndarray,
        wc: float = 300,
        ww: float = 1500,
    ) -> np.ndarray:
        lower = wc - ww / 2
        upper = wc + ww / 2
        windowed = np.clip(volume, lower, upper)
        return (windowed - lower) / (upper - lower)

    def render_slice_to_image(
        self,
        volume: np.ndarray,
        slice_idx: int,
        view: str = "axial",
        wc: float = 300,
        ww: float = 1500,
    ) -> bytes:
        idx = max(0, min(slice_idx, volume.shape[0] - 1))
        slice_data = volume[idx]

        if view == "sagittal":
            x = max(0, min(slice_idx, volume.shape[2] - 1))
            slice_data = volume[:, :, x]
        elif view == "coronal":
            y = max(0, min(slice_idx, volume.shape[1] - 1))
            slice_data = volume[:, y, :]

        normalized = self.apply_windowing(slice_data.astype(np.float32), wc, ww)
        image_array = (normalized * 255).astype(np.uint8)
        image = Image.fromarray(image_array, mode="L")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

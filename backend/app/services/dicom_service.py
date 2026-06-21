from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
from PIL import Image

from app.utils.dicom_utils import is_dicom_file

_volume_cache: dict[str, tuple[np.ndarray, dict[str, Any]]] = {}


class DicomService:
    def load_and_sort_slices(self, study_path: str) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Charge et trie les fichiers DICOM par position Z (ImagePositionPatient[2]).
        Retourne un volume (n_slices, H, W) en int16 Hounsfield et les espacements.
        """
        path = Path(study_path)
        slices: list[tuple[float, int, np.ndarray, tuple[float, float] | None, float]] = []

        for file_path in path.iterdir():
            if not file_path.is_file() or not is_dicom_file(file_path.name):
                continue
            try:
                ds = pydicom.dcmread(str(file_path), force=True)
                if not hasattr(ds, "pixel_array"):
                    continue

                hu = self._pixel_array_to_hounseld(ds)

                z_pos = 0.0
                if hasattr(ds, "ImagePositionPatient") and ds.ImagePositionPatient is not None:
                    z_pos = float(ds.ImagePositionPatient[2])

                instance_number = int(getattr(ds, "InstanceNumber", 0) or 0)

                spacing = None
                if hasattr(ds, "PixelSpacing") and ds.PixelSpacing is not None:
                    spacing = (float(ds.PixelSpacing[0]), float(ds.PixelSpacing[1]))

                slice_thickness = float(getattr(ds, "SliceThickness", 1.0) or 1.0)

                slices.append((z_pos, instance_number, hu, spacing, slice_thickness))
            except Exception:
                continue

        if not slices:
            raise ValueError("Impossible de charger les coupes DICOM")

        unique_z = len({round(item[0], 4) for item in slices})
        if unique_z > 1:
            sort_method = "ImagePositionPatient[2]"
            slices.sort(key=lambda item: (item[0], item[1]))
        else:
            sort_method = "InstanceNumber (IPP[2] absent ou identique)"
            slices.sort(key=lambda item: item[1])

        volume = np.stack([item[2] for item in slices], axis=0).astype(np.float32)
        pixel_spacing = slices[0][3] or (1.0, 1.0)
        slice_thickness = float(np.median([item[4] for item in slices]))

        spacing_dict = {
            "pixel_spacing": list(pixel_spacing),
            "slice_thickness": slice_thickness,
            "slice_positions": [item[0] for item in slices],
            "volume_kind": "dicom_hu",
            "hu_rescale_applied": True,
            "sort_method": sort_method,
            "n_slices": volume.shape[0],
        }

        print(
            "[DicomService][DIAG] Volume chargé — "
            f"tri={sort_method}, n={volume.shape[0]}, "
            f"HU min={float(volume.min()):.1f}, max={float(volume.max()):.1f}, "
            f"mean={float(volume.mean()):.2f}, "
            f"RescaleSlope/Intercept appliqués=True"
        )

        return volume, spacing_dict

    @staticmethod
    def _pixel_array_to_hounseld(ds: pydicom.Dataset) -> np.ndarray:
        """Convertit les pixels bruts en Unités Hounsfield via RescaleSlope / RescaleIntercept."""
        pixel_array = ds.pixel_array.astype(np.float32)
        slope = float(getattr(ds, "RescaleSlope", 1) or 1)
        intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
        return pixel_array * slope + intercept

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
                arr = np.array(img.convert("L"), dtype=np.float32)
                slices.append(arr)

        volume = np.stack(slices, axis=0)
        spacing_dict = {
            "pixel_spacing": [0.5, 0.5],
            "slice_thickness": 1.0,
            "slice_positions": list(range(volume.shape[0])),
            "volume_kind": "png_preview",
            "hu_rescale_applied": False,
            "sort_method": "nom_fichier_png (apercu demo)",
            "n_slices": volume.shape[0],
        }

        print(
            "[DicomService][DIAG] Volume PNG demo — "
            f"HU non applicable, min={float(volume.min()):.1f}, max={float(volume.max()):.1f}, "
            f"mean={float(volume.mean()):.2f}, tri={spacing_dict['sort_method']}"
        )

        return volume, spacing_dict

    def get_cached_volume(self, study_path: str) -> tuple[np.ndarray, dict[str, Any]]:
        """Retourne le volume en cache ou le charge une seule fois par chemin d'examen."""
        key = str(Path(study_path).resolve())
        if key not in _volume_cache:
            _volume_cache[key] = self.load_volume_from_study(study_path)
        return _volume_cache[key]

    @staticmethod
    def clear_volume_cache() -> None:
        _volume_cache.clear()

    @staticmethod
    def get_mpr_slice(volume: np.ndarray, view: str, index: int) -> np.ndarray:
        """Extrait une coupe MPR (axiale, sagittale ou coronale) — ré-échantillonnage pur."""
        if view == "axial":
            idx = max(0, min(index, volume.shape[0] - 1))
            return volume[idx, :, :]
        if view == "sagittal":
            idx = max(0, min(index, volume.shape[2] - 1))
            return volume[:, :, idx]
        if view == "coronal":
            idx = max(0, min(index, volume.shape[1] - 1))
            return volume[:, idx, :]
        raise ValueError(f"Vue inconnue : {view}")

    def render_mpr_png(
        self,
        volume: np.ndarray,
        view: str,
        index: int,
        wc: float = 300,
        ww: float = 1500,
    ) -> bytes:
        slice_data = self.get_mpr_slice(volume, view, index)
        normalized = self.apply_windowing(slice_data.astype(np.float32), wc, ww)
        image_array = (normalized * 255).astype(np.uint8)
        image = Image.fromarray(image_array, mode="L")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

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

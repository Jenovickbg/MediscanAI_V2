from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
from scipy.ndimage import gaussian_filter, zoom
from skimage.measure import label as sklabel, marching_cubes

from app.core.config import settings
from app.models.resultat import VERTEBRES
from app.utils.dicom_utils import is_dicom_file

logger = logging.getLogger(__name__)

MAX_TRIANGLES = 120_000
MESH_CACHE_VERSION = "v5_largest_component"
BONE_THRESHOLD_HU = 200.0
GAUSSIAN_SIGMA = 1.5
CLEAN_VOLUME_LEVEL = 100.0
CLEAN_VOLUME_HU = 200.0
CLEAN_GAUSSIAN_SIGMA = 1.0
Z_CROP_START_RATIO = 0.20
Z_CROP_END_RATIO = 0.65
VERTS_DISPLAY_SCALE = 10.0


class ReconstructionService:
    """Reconstruction 3D geometrique — independante du pipeline IA."""

    def get_or_build_mesh(
        self,
        study_id: str,
        study_path: str,
        scores: dict[str, float] | None = None,
        niveaux_risque: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        cache_path = settings.CACHE_DIR / f"mesh_{MESH_CACHE_VERSION}_{study_id}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        mesh = self.build_mesh(study_path, study_id=study_id)
        scores = scores or {v: 0.1 for v in VERTEBRES}
        vertebra_indices = self.map_vertebrae_to_mesh(
            np.array(mesh["vertices"]),
            mesh.get("stats", {}).get("slice_positions", []),
        )
        mesh["vertex_colors"] = self.colorize_mesh(
            vertebra_indices,
            scores,
            niveaux_risque=niveaux_risque,
        )
        mesh["vertebrae_bounds"] = self._compute_vertebrae_bounds(
            np.array(mesh["vertices"]),
            vertebra_indices,
        )
        mesh["fracture_markers"] = self._fracture_markers(
            mesh["vertebrae_bounds"],
            scores,
            niveaux_risque=niveaux_risque,
        )

        cache_path.write_text(json.dumps(mesh), encoding="utf-8")
        return mesh

    @staticmethod
    def clear_study_cache(study_id: str) -> None:
        cache_path = settings.CACHE_DIR / f"mesh_{MESH_CACHE_VERSION}_{study_id}.json"
        cache_path.unlink(missing_ok=True)
        cache_key = hashlib.md5(f"{study_id}_{int(BONE_THRESHOLD_HU)}".encode()).hexdigest()
        geom_path = settings.CACHE_DIR / f"mesh_geom_{cache_key}.json"
        geom_path.unlink(missing_ok=True)

    def build_mesh(
        self,
        study_path: str,
        threshold_hu: float = BONE_THRESHOLD_HU,
        study_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Reconstruction 3D avec espacement physique DICOM reel.
        Charge les coupes depuis study_path, resampling isotropique, marching cubes.
        """
        cache_key_src = study_id or study_path
        cache_key = hashlib.md5(f"{cache_key_src}_{int(threshold_hu)}".encode()).hexdigest()
        cache_path = settings.CACHE_DIR / f"mesh_geom_{cache_key}.json"

        if cache_path.exists():
            logger.info("[Reconstruction] Cache trouvé pour %s", cache_key_src)
            print(f"[Reconstruction] Cache trouvé pour {cache_key_src}")
            return json.loads(cache_path.read_text(encoding="utf-8"))

        result = self._build_mesh_uncached(study_path, threshold_hu)
        cache_path.write_text(json.dumps(result), encoding="utf-8")
        return result

    def _build_mesh_uncached(
        self,
        study_path: str,
        threshold_hu: float = BONE_THRESHOLD_HU,
    ) -> dict[str, Any]:
        path = Path(study_path)
        dcm_files = [p for p in path.iterdir() if p.is_file() and is_dicom_file(p.name)]

        if not dcm_files:
            from app.services.dicom_service import DicomService

            volume, spacing = DicomService().load_volume_from_study(str(path))
            print("[Reconstruction][DIAG] Pas de DICOM - maillage procedural")
            return self._procedural_spine_mesh(volume, spacing)

        try:
            return self._build_mesh_from_dicom(path, int(threshold_hu))
        except Exception as exc:
            logger.warning("Marching cubes echoue (%s) - maillage procedural", exc)
            print(f"[Reconstruction][DIAG] Marching cubes echoue: {exc}")
            from app.services.dicom_service import DicomService

            volume, spacing = DicomService().load_volume_from_study(str(path))
            return self._procedural_spine_mesh(volume, spacing)

    def _build_mesh_from_dicom(self, study_path: Path, threshold_hu: int = 200) -> dict[str, Any]:
        slices: list[pydicom.Dataset] = []
        for file_path in study_path.iterdir():
            if not file_path.is_file() or not is_dicom_file(file_path.name):
                continue
            dcm = pydicom.dcmread(str(file_path), force=True)
            if not hasattr(dcm, "pixel_array"):
                continue
            slices.append(dcm)

        if not slices:
            raise ValueError("Aucune coupe DICOM avec pixels dans cet examen")

        slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))

        pixel_spacing = float(slices[0].PixelSpacing[0])
        if len(slices) >= 2:
            slice_thickness = abs(
                float(slices[1].ImagePositionPatient[2]) - float(slices[0].ImagePositionPatient[2])
            )
        else:
            slice_thickness = float(getattr(slices[0], "SliceThickness", 1.0) or 1.0)

        if slice_thickness <= 0:
            slice_thickness = float(getattr(slices[0], "SliceThickness", 1.0) or 1.0)

        print(f"[Reconstruction][DIAG] PixelSpacing XY : {pixel_spacing:.3f} mm")
        print(f"[Reconstruction][DIAG] SliceThickness Z : {slice_thickness:.3f} mm")
        print(f"[Reconstruction][DIAG] Nombre de coupes : {len(slices)}")

        volume_layers: list[np.ndarray] = []
        for dcm in slices:
            img = dcm.pixel_array.astype(np.float32)
            slope = float(getattr(dcm, "RescaleSlope", 1) or 1)
            intercept = float(getattr(dcm, "RescaleIntercept", 0) or 0)
            volume_layers.append(img * slope + intercept)

        volume = np.stack(volume_layers, axis=0)
        print(f"[Reconstruction][DIAG] Volume shape avant resampling : {volume.shape}")
        print(
            f"[Reconstruction][DIAG] HU min: {float(volume.min()):.0f}, "
            f"max: {float(volume.max()):.0f}"
        )

        total = volume.shape[0]
        debut = int(total * Z_CROP_START_RATIO)
        fin = int(total * Z_CROP_END_RATIO)
        fin = max(fin, debut + 1)
        volume = volume[debut:fin, :, :]
        print(f"[Reconstruction][DIAG] Volume apres rognage cervical : {volume.shape}")

        zoom_z = slice_thickness / pixel_spacing
        zoom_factors = (zoom_z / 2, 0.5, 0.5)
        volume_resampled = zoom(volume, zoom_factors, order=1)
        print(f"[Reconstruction][DIAG] Volume apres resampling : {volume_resampled.shape}")
        print(f"[Reconstruction][DIAG] zoom_factors Z/2/2 : {zoom_factors}")

        volume_smooth = gaussian_filter(volume_resampled, sigma=GAUSSIAN_SIGMA)

        binary_volume = (volume_smooth > float(threshold_hu)).astype(np.uint8)
        labeled = sklabel(binary_volume, connectivity=2)
        component_sizes = np.bincount(labeled.ravel())
        component_sizes[0] = 0

        if component_sizes.max() == 0:
            raise ValueError("Aucun voxel osseux apres seuillage")

        largest_component = int(np.argmax(component_sizes))
        removed_voxels = int(np.sum(binary_volume) - component_sizes[largest_component])
        print(
            f"[Reconstruction][DIAG] Composante connexe max (label={largest_component}) - "
            f"supprimes={removed_voxels} voxels parasites"
        )

        clean_volume = (labeled == largest_component).astype(np.float32) * CLEAN_VOLUME_HU + 1.0
        volume_for_mc = gaussian_filter(clean_volume, sigma=CLEAN_GAUSSIAN_SIGMA)

        step_size = 2
        verts, faces, normals, _values = marching_cubes(
            volume_for_mc,
            level=CLEAN_VOLUME_LEVEL,
            step_size=step_size,
            allow_degenerate=False,
        )

        while len(faces) > MAX_TRIANGLES and step_size < 6:
            step_size += 1
            print(
                f"[Reconstruction][DIAG] Trop de faces ({len(faces)}) - step_size={step_size}"
            )
            verts, faces, normals, _values = marching_cubes(
                volume_for_mc,
                level=CLEAN_VOLUME_LEVEL,
                step_size=step_size,
                allow_degenerate=False,
            )

        center = verts.mean(axis=0)
        verts_centered = verts - center
        max_abs = float(np.abs(verts_centered).max())
        scale = VERTS_DISPLAY_SCALE / max_abs if max_abs > 0 else 1.0
        verts_normalized = verts_centered * scale

        print(
            f"[Reconstruction][DIAG] Mesh final : {len(verts_normalized)} sommets, "
            f"{len(faces)} faces, step_size={step_size}"
        )

        return {
            "vertices": verts_normalized.tolist(),
            "faces": faces.tolist(),
            "normals": normals.tolist(),
            "stats": {
                "nb_sommets": len(verts_normalized),
                "nb_faces": len(faces),
                "spacing_xy_mm": pixel_spacing,
                "spacing_z_mm": slice_thickness,
                "z_crop_start": debut,
                "z_crop_end": fin,
            },
        }

    def _procedural_spine_mesh(
        self,
        volume: np.ndarray,
        spacing: dict[str, Any],
    ) -> dict[str, Any]:
        """Maillage cervical simplifie pour examens demo ou volumes non-DICOM."""
        pixel_spacing = spacing.get("pixel_spacing", [0.5, 0.5])
        slice_thickness = float(spacing.get("slice_thickness", 1.0))
        z_extent = volume.shape[0] * slice_thickness
        y_center = volume.shape[1] * pixel_spacing[0] * 0.5
        x_center = volume.shape[2] * pixel_spacing[1] * 0.5

        all_vertices: list[list[float]] = []
        all_faces: list[list[int]] = []
        all_normals: list[list[float]] = []
        vertex_offset = 0

        for i, _vertebra in enumerate(VERTEBRES):
            z_center = (i + 0.5) / len(VERTEBRES) * z_extent
            rx = pixel_spacing[1] * 18
            ry = pixel_spacing[0] * 14
            rz = slice_thickness * max(volume.shape[0] / len(VERTEBRES) * 0.35, 1.5)

            verts, faces, norms = self._ellipsoid_mesh(
                center=(x_center, y_center, z_center),
                radii=(rx, ry, rz),
                segments=16,
            )
            shifted_faces = [
                [f[0] + vertex_offset, f[1] + vertex_offset, f[2] + vertex_offset]
                for f in faces
            ]
            all_vertices.extend(verts)
            all_faces.extend(shifted_faces)
            all_normals.extend(norms)
            vertex_offset += len(verts)

        verts_arr = np.array(all_vertices, dtype=np.float32)
        center = verts_arr.mean(axis=0)
        verts_centered = verts_arr - center
        max_abs = float(np.abs(verts_centered).max())
        scale = VERTS_DISPLAY_SCALE / max_abs if max_abs > 0 else 1.0
        verts_normalized = (verts_centered * scale).tolist()

        print(
            f"[Reconstruction][DIAG] Maillage procedural - "
            f"vertices={len(verts_normalized)}, faces={len(all_faces)}"
        )

        return {
            "vertices": verts_normalized,
            "faces": all_faces,
            "normals": all_normals,
            "stats": {"nb_sommets": len(verts_normalized), "nb_faces": len(all_faces)},
        }

    @staticmethod
    def _ellipsoid_mesh(
        center: tuple[float, float, float],
        radii: tuple[float, float, float],
        segments: int = 16,
    ) -> tuple[list[list[float]], list[list[int]], list[list[float]]]:
        cx, cy, cz = center
        rx, ry, rz = radii
        vertices: list[list[float]] = []
        faces: list[list[int]] = []

        for lat in range(segments + 1):
            theta = lat * np.pi / segments
            for lon in range(segments):
                phi = lon * 2 * np.pi / segments
                x = cx + rx * np.sin(theta) * np.cos(phi)
                y = cy + ry * np.sin(theta) * np.sin(phi)
                z = cz + rz * np.cos(theta)
                vertices.append([float(x), float(y), float(z)])

        for lat in range(segments):
            for lon in range(segments):
                first = lat * segments + lon
                second = first + segments
                faces.append([first, second, first + 1])
                faces.append([second, second + 1, first + 1])

        normals = [[0.0, 0.0, 1.0] for _ in vertices]
        return vertices, faces, normals

    def map_vertebrae_to_mesh(
        self,
        vertices: np.ndarray,
        z_positions: list[float],
    ) -> list[int]:
        if len(vertices) == 0:
            return []

        z_coords = vertices[:, 2]
        z_min, z_max = float(z_coords.min()), float(z_coords.max())
        if z_max - z_min < 1e-6:
            return [0] * len(vertices)

        indices: list[int] = []
        for z in z_coords:
            ratio = (z - z_min) / (z_max - z_min)
            segment = min(int(ratio * len(VERTEBRES)), len(VERTEBRES) - 1)
            indices.append(segment)
        return indices

    def colorize_mesh(
        self,
        vertebra_indices: list[int],
        scores: dict[str, float],
        niveaux_risque: dict[str, str] | None = None,
    ) -> list[str]:
        colors: list[str] = []
        for idx in vertebra_indices:
            vertebre = VERTEBRES[idx]
            if niveaux_risque and vertebre in niveaux_risque:
                niveau = niveaux_risque[vertebre]
                if niveau == "eleve":
                    colors.append("#FF4757")
                elif niveau == "incertain":
                    colors.append("#FFA048")
                else:
                    colors.append("#00E5A0")
                continue

            score = float(scores.get(vertebre, 0.0))
            if score < 0.30:
                colors.append("#00E5A0")
            elif score < 0.60:
                colors.append("#FFA048")
            else:
                colors.append("#FF4757")
        return colors

    def _compute_vertebrae_bounds(
        self,
        vertices: np.ndarray,
        vertebra_indices: list[int],
    ) -> dict[str, dict[str, Any]]:
        bounds: dict[str, dict[str, Any]] = {}
        if len(vertices) == 0:
            return bounds

        for i, vertebre in enumerate(VERTEBRES):
            mask = [idx == i for idx in vertebra_indices]
            if not any(mask):
                continue
            verts = vertices[mask]
            bounds[vertebre] = {
                "min_z": float(verts[:, 2].min()),
                "max_z": float(verts[:, 2].max()),
                "center": [float(c) for c in verts.mean(axis=0)],
            }
        return bounds

    @staticmethod
    def _fracture_markers(
        vertebrae_bounds: dict[str, dict[str, Any]],
        scores: dict[str, float],
        niveaux_risque: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        markers: list[dict[str, Any]] = []
        for vertebre, bound in vertebrae_bounds.items():
            is_fracture = False
            if niveaux_risque:
                is_fracture = niveaux_risque.get(vertebre) == "eleve"
            else:
                is_fracture = scores.get(vertebre, 0.0) > 0.60

            if is_fracture:
                markers.append(
                    {
                        "vertebre": vertebre,
                        "position": bound["center"],
                        "score": scores.get(vertebre, 0.0),
                    }
                )
        return markers

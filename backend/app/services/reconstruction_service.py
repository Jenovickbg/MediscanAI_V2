from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes

from app.core.config import settings
from app.models.resultat import VERTEBRES

logger = logging.getLogger(__name__)

MAX_TRIANGLES = 120_000
MESH_CACHE_VERSION = "v2_hu"
BONE_THRESHOLD_HU = 200.0
GAUSSIAN_SIGMA = 1.0


class ReconstructionService:
    """Reconstruction 3D géométrique — indépendante du pipeline IA."""

    def get_or_build_mesh(
        self,
        study_id: str,
        volume: np.ndarray,
        spacing: dict[str, Any],
        scores: dict[str, float] | None = None,
        niveaux_risque: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        cache_path = settings.CACHE_DIR / f"mesh_{MESH_CACHE_VERSION}_{study_id}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        mesh = self.build_mesh(volume, spacing)
        scores = scores or {v: 0.1 for v in VERTEBRES}
        vertebra_indices = self.map_vertebrae_to_mesh(
            np.array(mesh["vertices"]),
            spacing.get("slice_positions", []),
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

    def build_mesh(
        self,
        volume: np.ndarray,
        spacing: dict[str, Any],
        threshold_hu: float = BONE_THRESHOLD_HU,
    ) -> dict[str, Any]:
        self._print_volume_diagnostics(volume, spacing)

        if spacing.get("volume_kind") == "png_preview" or not self._is_hounsfield_volume(volume):
            print(
                "[Reconstruction][DIAG] Volume non-HU ou aperçu PNG — "
                "maillage procédural cervical (pas de marching cubes sur bruit)"
            )
            return self._procedural_spine_mesh(volume, spacing)

        try:
            return self._marching_cubes_mesh(volume, spacing, threshold_hu)
        except Exception as exc:
            logger.warning("Marching cubes échoué (%s) — maillage procédural", exc)
            print(f"[Reconstruction][DIAG] Marching cubes échoué: {exc}")
            return self._procedural_spine_mesh(volume, spacing)

    @staticmethod
    def _print_volume_diagnostics(volume: np.ndarray, spacing: dict[str, Any]) -> None:
        hu = volume.astype(np.float32)
        print("[Reconstruction][DIAG] --- Volume avant reconstruction ---")
        print(f"  shape={hu.shape}, dtype={volume.dtype}")
        print(
            f"  min={float(hu.min()):.1f}, max={float(hu.max()):.1f}, "
            f"mean={float(hu.mean()):.2f}"
        )
        print(
            f"  p05={float(np.percentile(hu, 5)):.1f}, "
            f"p50={float(np.percentile(hu, 50)):.1f}, "
            f"p95={float(np.percentile(hu, 95)):.1f}"
        )
        print(f"  tri coupes: {spacing.get('sort_method', 'inconnu')}")
        print(
            f"  RescaleSlope/Intercept appliqués: "
            f"{spacing.get('hu_rescale_applied', False)}"
        )
        print(
            f"  spacing z/y/x=({spacing.get('slice_thickness')}, "
            f"{spacing.get('pixel_spacing', [1, 1])[0]}, "
            f"{spacing.get('pixel_spacing', [1, 1])[1]})"
        )

    @staticmethod
    def _is_hounsfield_volume(volume: np.ndarray) -> bool:
        """CT valide : air ~ -1000 HU, os > +200 HU."""
        hu = volume.astype(np.float32)
        return float(hu.min()) < -100.0 and float(hu.max()) > 250.0

    def _marching_cubes_mesh(
        self,
        volume: np.ndarray,
        spacing: dict[str, Any],
        threshold_hu: float,
    ) -> dict[str, Any]:
        hu_volume = volume.astype(np.float32)
        smoothed = gaussian_filter(hu_volume, sigma=GAUSSIAN_SIGMA)

        print(
            "[Reconstruction][DIAG] Après Gaussien sigma=1.0 — "
            f"min={float(smoothed.min()):.1f}, max={float(smoothed.max()):.1f}, "
            f"mean={float(smoothed.mean()):.2f}"
        )

        pixel_spacing = spacing.get("pixel_spacing", [1.0, 1.0])
        slice_thickness = float(spacing.get("slice_thickness", 1.0))
        voxel_spacing = (slice_thickness, float(pixel_spacing[0]), float(pixel_spacing[1]))

        level = float(threshold_hu)
        bone_voxels = int(np.sum(smoothed >= level))
        total_voxels = smoothed.size
        print(
            f"[Reconstruction][DIAG] Seuil osseux fixe={level:.0f} HU — "
            f"voxels >= seuil: {bone_voxels}/{total_voxels} "
            f"({100.0 * bone_voxels / max(total_voxels, 1):.2f}%)"
        )

        step_size = 2
        verts, faces, normals = self._run_marching_cubes(
            smoothed, level, voxel_spacing, step_size
        )

        while len(faces) > MAX_TRIANGLES and step_size < 6:
            step_size += 1
            print(
                f"[Reconstruction][DIAG] Trop de faces ({len(faces)}) — "
                f"step_size={step_size}"
            )
            verts, faces, normals = self._run_marching_cubes(
                smoothed, level, voxel_spacing, step_size
            )

        print(
            f"[Reconstruction][DIAG] Maillage final — "
            f"vertices={len(verts)}, faces={len(faces)}, step_size={step_size}"
        )

        return {
            "vertices": verts.tolist(),
            "faces": faces.tolist(),
            "normals": normals.tolist(),
        }

    @staticmethod
    def _run_marching_cubes(
        smoothed: np.ndarray,
        level: float,
        voxel_spacing: tuple[float, float, float],
        step_size: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        verts, faces, normals, _values = marching_cubes(
            smoothed,
            level=level,
            spacing=voxel_spacing,
            step_size=step_size,
        )
        return verts, faces, normals

    def _procedural_spine_mesh(
        self,
        volume: np.ndarray,
        spacing: dict[str, Any],
    ) -> dict[str, Any]:
        """Maillage cervical simplifié pour examens démo ou volumes non-DICOM."""
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

        print(
            f"[Reconstruction][DIAG] Maillage procédural — "
            f"vertices={len(all_vertices)}, faces={len(all_faces)}"
        )

        return {
            "vertices": all_vertices,
            "faces": all_faces,
            "normals": all_normals,
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

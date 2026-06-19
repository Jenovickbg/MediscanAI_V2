from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes

from app.core.config import settings
from app.models.resultat import VERTEBRES

logger = logging.getLogger(__name__)

MAX_TRIANGLES = 500_000


class ReconstructionService:
    def get_or_build_mesh(
        self,
        study_id: str,
        volume: np.ndarray,
        spacing: dict[str, Any],
        scores: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        cache_path = settings.CACHE_DIR / f"mesh_{study_id}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        mesh = self.build_mesh(volume, spacing)
        scores = scores or {v: 0.1 for v in VERTEBRES}
        vertebra_indices = self.map_vertebrae_to_mesh(
            np.array(mesh["vertices"]),
            spacing.get("slice_positions", []),
        )
        mesh["vertex_colors"] = self.colorize_mesh(vertebra_indices, scores)
        mesh["vertebrae_bounds"] = self._compute_vertebrae_bounds(
            np.array(mesh["vertices"]),
            vertebra_indices,
        )
        mesh["fracture_markers"] = self._fracture_markers(mesh["vertebrae_bounds"], scores)

        cache_path.write_text(json.dumps(mesh), encoding="utf-8")
        return mesh

    def build_mesh(
        self,
        volume: np.ndarray,
        spacing: dict[str, Any],
        threshold_hu: int = 200,
    ) -> dict[str, Any]:
        try:
            return self._marching_cubes_mesh(volume, spacing, threshold_hu)
        except Exception as exc:
            logger.warning("Marching cubes échoué (%s) — maillage procédural", exc)
            return self._procedural_spine_mesh(volume, spacing)

    def _marching_cubes_mesh(
        self,
        volume: np.ndarray,
        spacing: dict[str, Any],
        threshold_hu: int,
    ) -> dict[str, Any]:
        smoothed = gaussian_filter(volume.astype(np.float32), sigma=0.6)

        pixel_spacing = spacing.get("pixel_spacing", [1.0, 1.0])
        slice_thickness = float(spacing.get("slice_thickness", 1.0))
        voxel_spacing = (slice_thickness, float(pixel_spacing[0]), float(pixel_spacing[1]))

        level = float(threshold_hu)
        if smoothed.max() < 500:
            level = float(np.percentile(smoothed, 75))

        step_size = 2
        verts, faces, normals, _values = marching_cubes(
            smoothed,
            level=level,
            spacing=voxel_spacing,
            step_size=step_size,
        )

        if len(faces) > MAX_TRIANGLES:
            step_size = 3
            verts, faces, normals, _values = marching_cubes(
                smoothed,
                level=level,
                spacing=voxel_spacing,
                step_size=step_size,
            )

        return {
            "vertices": verts.tolist(),
            "faces": faces.tolist(),
            "normals": normals.tolist(),
        }

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
            shifted_faces = [[f[0] + vertex_offset, f[1] + vertex_offset, f[2] + vertex_offset] for f in faces]
            all_vertices.extend(verts)
            all_faces.extend(shifted_faces)
            all_normals.extend(norms)
            vertex_offset += len(verts)

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
    ) -> list[str]:
        colors: list[str] = []
        for idx in vertebra_indices:
            vertebre = VERTEBRES[idx]
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
    ) -> list[dict[str, Any]]:
        markers: list[dict[str, Any]] = []
        for vertebre, bound in vertebrae_bounds.items():
            if scores.get(vertebre, 0.0) > 0.60:
                markers.append(
                    {
                        "vertebre": vertebre,
                        "position": bound["center"],
                        "score": scores[vertebre],
                    }
                )
        return markers

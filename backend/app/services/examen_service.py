from __future__ import annotations

import io
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import numpy as np
from PIL import Image
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.examen import Examen, Patient
from app.models.resultat import ResultatAnalyse, ScoreVertebre, VERTEBRES
from app.services.dicom_service import DicomService
from app.services.triage_config import is_vertebra_at_risk, resolve_niveau_risque
from app.services.upload_task_store import UploadTask, upload_task_store
from app.utils.dicom_utils import is_dicom_file

ResultFilter = Literal["all", "fracture", "normal"]
PeriodFilter = Literal["all", "week", "month"]


class ExamenService:
    def __init__(self) -> None:
        self.dicom_service = DicomService()

    def save_upload_files(self, task: UploadTask, files: list[tuple[str, bytes]]) -> int:
        task.temp_dir.mkdir(parents=True, exist_ok=True)
        saved = 0

        for filename, content in files:
            if not is_dicom_file(filename):
                continue
            safe_name = Path(filename).name
            target = task.temp_dir / safe_name
            if target.exists():
                target = task.temp_dir / f"{uuid4().hex}_{safe_name}"
            target.write_bytes(content)
            saved += 1

        task.files_received += saved
        upload_task_store.update_progress(task.task_id, task.files_received)
        return saved

    def finalize_upload(
        self,
        task: UploadTask,
        db: Session,
        uploaded_by: int,
    ) -> dict[str, Any]:
        dicom_files = sorted(
            [p for p in task.temp_dir.iterdir() if p.is_file() and is_dicom_file(p.name)],
            key=lambda p: p.name,
        )

        if not dicom_files:
            raise ValueError("Aucun fichier DICOM valide trouvé dans l'upload")

        metadata = self.dicom_service.extract_study_metadata(task.temp_dir)
        study_uid = metadata.get("study_instance_uid") or str(uuid4())

        final_dir = settings.UPLOAD_DIR / study_uid
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.move(str(task.temp_dir), str(final_dir))

        patient = db.query(Patient).filter(Patient.patient_id == task.patient_id).first()
        if patient is None:
            patient = Patient(patient_id=task.patient_id)
            db.add(patient)
            db.flush()

        existing = (
            db.query(Examen)
            .filter(Examen.study_instance_uid == study_uid)
            .first()
        )
        if existing is not None:
            db.delete(existing)
            db.flush()

        date_examen = metadata.get("date_examen")
        examen = Examen(
            study_instance_uid=study_uid,
            patient_id=task.patient_id,
            date_examen=date_examen,
            nb_coupes=len(dicom_files),
            dicom_path=str(final_dir),
            uploaded_by=uploaded_by,
        )
        db.add(examen)
        db.commit()
        db.refresh(examen)

        preview_slices = self._preview_slice_indices(len(dicom_files))

        return {
            "study_id": study_uid,
            "nb_coupes": len(dicom_files),
            "metadata": {
                "patient_id": task.patient_id,
                "study_instance_uid": study_uid,
                "date_examen": date_examen.isoformat() if date_examen else None,
                "nb_coupes": len(dicom_files),
                "dimensions": metadata.get("dimensions"),
                "pixel_spacing": metadata.get("pixel_spacing"),
                "slice_thickness": metadata.get("slice_thickness"),
            },
            "preview_slices": preview_slices,
        }

    def create_demo_examen(
        self,
        db: Session,
        uploaded_by: int,
        patient_id: str = "DEMO-001",
    ) -> dict[str, Any]:
        """Génère un examen d'exemple à partir de coupes PNG synthétiques."""
        sample_dir = settings.SAMPLE_DIR
        sample_dir.mkdir(parents=True, exist_ok=True)

        png_files = sorted(sample_dir.glob("*.png"))
        if not png_files:
            self._generate_sample_pngs(sample_dir, count=12)

        study_uid = f"DEMO-{uuid4().hex[:12].upper()}"
        final_dir = settings.UPLOAD_DIR / study_uid
        final_dir.mkdir(parents=True, exist_ok=True)

        png_files = sorted(sample_dir.glob("*.png"))
        for idx, png in enumerate(png_files):
            shutil.copy(png, final_dir / f"slice_{idx:04d}.png")

        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if patient is None:
            patient = Patient(patient_id=patient_id)
            db.add(patient)
            db.flush()

        examen = Examen(
            study_instance_uid=study_uid,
            patient_id=patient_id,
            date_examen=datetime.now(),
            nb_coupes=len(png_files),
            dicom_path=str(final_dir),
            uploaded_by=uploaded_by,
        )
        db.add(examen)
        db.commit()

        return {
            "study_id": study_uid,
            "nb_coupes": len(png_files),
            "metadata": {
                "patient_id": patient_id,
                "study_instance_uid": study_uid,
                "date_examen": datetime.now().isoformat(),
                "nb_coupes": len(png_files),
                "dimensions": [512, 512, len(png_files)],
                "pixel_spacing": [0.5, 0.5],
                "slice_thickness": 1.0,
                "demo": True,
            },
            "preview_slices": self._preview_slice_indices(len(png_files)),
        }

    def get_examen_by_study_id(self, db: Session, study_id: str) -> Examen | None:
        return db.query(Examen).filter(Examen.study_instance_uid == study_id).first()

    def list_examens(
        self,
        db: Session,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
        result_filter: ResultFilter = "all",
        period: PeriodFilter = "all",
    ) -> dict[str, Any]:
        query = db.query(Examen).outerjoin(
            ResultatAnalyse,
            Examen.study_instance_uid == ResultatAnalyse.study_instance_uid,
        )

        if search and search.strip():
            term = search.strip().lower()
            query = query.filter(
                or_(
                    func.lower(Examen.patient_id).contains(term),
                    func.lower(Examen.study_instance_uid).contains(term),
                )
            )

        if result_filter == "fracture":
            query = query.filter(ResultatAnalyse.fracture_detectee.is_(True))
        elif result_filter == "normal":
            query = query.filter(ResultatAnalyse.fracture_detectee.is_(False))

        if period == "week":
            start = datetime.now(timezone.utc) - timedelta(days=7)
            query = query.filter(Examen.uploaded_at >= start)
        elif period == "month":
            now = datetime.now(timezone.utc)
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(Examen.uploaded_at >= start)

        total = query.count()
        examens = (
            query.order_by(Examen.uploaded_at.desc())
            .offset(max(page - 1, 0) * limit)
            .limit(limit)
            .all()
        )

        study_ids = [ex.study_instance_uid for ex in examens]
        resultats_by_study: dict[str, ResultatAnalyse] = {}
        if study_ids:
            resultats = (
                db.query(ResultatAnalyse)
                .options(joinedload(ResultatAnalyse.scores_vertebres))
                .filter(ResultatAnalyse.study_instance_uid.in_(study_ids))
                .all()
            )
            resultats_by_study = {r.study_instance_uid: r for r in resultats}

        items: list[dict[str, Any]] = []
        for examen in examens:
            resultat = resultats_by_study.get(examen.study_instance_uid)
            display_date = examen.date_examen or examen.uploaded_at

            vertebres: list[str] = []
            score_global: float | None = None
            fracture_detectee: bool | None = None
            analysed = resultat is not None

            if resultat is not None:
                score_global = resultat.score_global
                fracture_detectee = resultat.fracture_detectee
                vertebres = self._affected_vertebrae(resultat.scores_vertebres)

            items.append(
                {
                    "id": examen.id,
                    "study_id": examen.study_instance_uid,
                    "patient_id": examen.patient_id,
                    "date": display_date,
                    "nb_coupes": examen.nb_coupes,
                    "uploaded_at": examen.uploaded_at,
                    "vertebres": vertebres,
                    "score_global": score_global,
                    "fracture_detectee": fracture_detectee,
                    "analysed": analysed,
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
        }

    @staticmethod
    def _affected_vertebrae(scores: list[ScoreVertebre]) -> list[str]:
        at_risk = [
            score.vertebre
            for score in scores
            if is_vertebra_at_risk(score.probabilite, score.niveau_risque)
        ]
        if at_risk:
            return sorted(at_risk, key=lambda v: VERTEBRES.index(v) if v in VERTEBRES else 99)

        if not scores:
            return []

        top = max(scores, key=lambda s: s.probabilite)
        if top.probabilite > 0:
            return [top.vertebre]
        return []

    @staticmethod
    def _preview_slice_indices(nb_coupes: int) -> list[int]:
        if nb_coupes <= 0:
            return []
        if nb_coupes == 1:
            return [0]
        middle = nb_coupes // 2
        return [0, middle, nb_coupes - 1]

    @staticmethod
    def _generate_sample_pngs(sample_dir: Path, count: int = 12) -> None:
        for i in range(count):
            gradient = np.linspace(40, 200, 512, dtype=np.uint8)
            tile = np.tile(gradient, (512, 1))
            noise = np.random.default_rng(i).integers(0, 30, (512, 512), dtype=np.uint8)
            image_array = np.clip(tile + noise, 0, 255).astype(np.uint8)
            image = Image.fromarray(image_array, mode="L")
            image.save(sample_dir / f"slice_{i:03d}.png")

    def render_preview_png(self, study_path: Path, slice_idx: int) -> bytes:
        dicom_files = sorted(
            [p for p in study_path.iterdir() if p.is_file() and is_dicom_file(p.name)],
            key=lambda p: p.name,
        )
        png_files = sorted(study_path.glob("*.png"))

        if dicom_files:
            volume, _ = self.dicom_service.load_and_sort_slices(str(study_path))
            return self.dicom_service.render_slice_to_image(volume, slice_idx, "axial")

        if png_files:
            idx = min(slice_idx, len(png_files) - 1)
            with Image.open(png_files[idx]) as img:
                buffer = io.BytesIO()
                img.convert("L").save(buffer, format="PNG")
                return buffer.getvalue()

        raise FileNotFoundError("Aucune image disponible pour cet examen")

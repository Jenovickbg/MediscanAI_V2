from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.resultat import ResultatAnalyse, ScoreVertebre
from app.services.analyse_task_store import AnalyseStatus, analyse_task_store
from app.services.dicom_service import DicomService
from app.services.examen_service import ExamenService
from app.services.pipeline_service import pipeline_service


class AnalyseService:
    def __init__(self) -> None:
        self.examen_service = ExamenService()
        self.dicom_service = DicomService()

    def run_analysis(self, study_id: str, db: Session) -> ResultatAnalyse:
        examen = self.examen_service.get_examen_by_study_id(db, study_id)
        if examen is None:
            raise ValueError("Examen introuvable")

        task = analyse_task_store.get_by_study(study_id)
        if task is None:
            task = analyse_task_store.create(study_id)

        analyse_task_store.update(study_id, status=AnalyseStatus.RUNNING, progress=5)
        start = time.perf_counter()

        try:
            volume, _ = self.dicom_service.load_volume_from_study(examen.dicom_path)
            analyse_task_store.update(study_id, progress=35)

            prediction = pipeline_service.predict_volume(volume, study_id=study_id)
            analyse_task_store.update(study_id, progress=75)

            details = pipeline_service.build_vertebra_details(prediction, volume.shape[0])
            rapport = pipeline_service.generate_clinical_report(
                prediction["scores_par_vertebre"],
                prediction["fracture_detectee"],
            )

            existing = (
                db.query(ResultatAnalyse)
                .filter(ResultatAnalyse.study_instance_uid == study_id)
                .first()
            )
            if existing is not None:
                db.delete(existing)
                db.flush()

            duree = time.perf_counter() - start
            resultat = ResultatAnalyse(
                study_instance_uid=study_id,
                fracture_detectee=prediction["fracture_detectee"],
                score_global=prediction["score_global"],
                rapport_clinique=rapport,
                date_analyse=datetime.now(timezone.utc),
                duree_analyse_sec=duree,
                seuil_utilise=pipeline_service.threshold,
                mode_mock=prediction.get("mode_mock", False),
            )
            db.add(resultat)
            db.flush()

            for detail in details:
                db.add(
                    ScoreVertebre(
                        resultat_id=resultat.id,
                        vertebre=detail["vertebre"],
                        probabilite=detail["probabilite"],
                        localisation=detail["localisation"],
                        bounding_box_x=detail["bounding_box_x"],
                        bounding_box_y=detail["bounding_box_y"],
                        bounding_box_w=detail["bounding_box_w"],
                        bounding_box_h=detail["bounding_box_h"],
                        coupe_reference=detail["coupe_reference"],
                    )
                )

            db.commit()
            db.refresh(resultat)

            analyse_task_store.update(study_id, status=AnalyseStatus.DONE, progress=100)
            return resultat

        except Exception as exc:
            analyse_task_store.update(
                study_id,
                status=AnalyseStatus.ERROR,
                progress=0,
                error=str(exc),
            )
            raise

    def get_resultat(self, db: Session, study_id: str) -> ResultatAnalyse | None:
        return (
            db.query(ResultatAnalyse)
            .filter(ResultatAnalyse.study_instance_uid == study_id)
            .first()
        )


analyse_service = AnalyseService()

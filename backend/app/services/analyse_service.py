from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.resultat import ResultatAnalyse, ScoreVertebre
from app.services.analyse_task_store import AnalyseStatus, analyse_task_store
from app.services.dicom_service import DicomService
from app.services.examen_service import ExamenService
from app.services.pipeline_service import pipeline_service

logger = logging.getLogger(__name__)
_inference_lock = threading.Lock()
_study_generation: dict[str, int] = {}
_generation_lock = threading.Lock()


class AnalysisCancelledError(Exception):
    pass


def _finite_float(value: float) -> float:
    if value != value or value in (float("inf"), float("-inf")):
        return 0.0
    return float(value)


class AnalyseService:
    def __init__(self) -> None:
        self.examen_service = ExamenService()
        self.dicom_service = DicomService()

    def bump_generation(self, study_id: str) -> int:
        with _generation_lock:
            generation = _study_generation.get(study_id, 0) + 1
            _study_generation[study_id] = generation
            return generation

    def _check_cancelled(self, study_id: str, generation: int) -> None:
        with _generation_lock:
            if _study_generation.get(study_id, generation) != generation:
                raise AnalysisCancelledError("Analyse annulée pour relance")

    def run_analysis(
        self,
        study_id: str,
        generation: int,
        on_progress_notify: Callable[[int], None] | None = None,
    ) -> ResultatAnalyse:
        """Exécute l'analyse — sans garder de session DB ouverte pendant l'inférence CPU."""
        db = SessionLocal()
        try:
            examen = self.examen_service.get_examen_by_study_id(db, study_id)
            if examen is None:
                raise ValueError("Examen introuvable")
            dicom_path = examen.dicom_path
        finally:
            db.close()

        task = analyse_task_store.get_by_study(study_id)
        if task is None:
            task = analyse_task_store.create(study_id)

        analyse_task_store.update(study_id, status=AnalyseStatus.RUNNING, progress=5)
        start = time.perf_counter()
        stop_heartbeat = threading.Event()

        def heartbeat_loop() -> None:
            while not stop_heartbeat.wait(12):
                analyse_task_store.touch(study_id)

        heartbeat = threading.Thread(
            target=heartbeat_loop,
            name=f"analyse-heartbeat-{study_id[:24]}",
            daemon=True,
        )
        heartbeat.start()

        try:
            self._check_cancelled(study_id, generation)
            analyse_task_store.touch(study_id)
            volume, _ = self.dicom_service.get_cached_volume(dicom_path)
            analyse_task_store.update(study_id, progress=35)

            def on_progress(value: int) -> None:
                self._check_cancelled(study_id, generation)
                analyse_task_store.update(study_id, progress=value)
                analyse_task_store.touch(study_id)
                if on_progress_notify is not None:
                    on_progress_notify(value)

            analyse_task_store.update(study_id, progress=38)
            self._check_cancelled(study_id, generation)

            self._wait_for_inference_slot(study_id, generation, on_progress)
            try:
                self._check_cancelled(study_id, generation)
                analyse = pipeline_service.analyser_examen(
                    volume,
                    study_id=study_id,
                    on_progress=on_progress,
                    is_cancelled=lambda: self._is_cancelled(study_id, generation),
                )
            finally:
                _inference_lock.release()
            analyse_task_store.update(study_id, progress=85)

            details = pipeline_service.build_vertebra_details_from_analyse(
                analyse,
                volume.shape[0],
            )
            rapport = analyse["rapport_clinique"]
            score_global = _finite_float(pipeline_service.score_global_from_analyse(analyse))
            duree = time.perf_counter() - start

            save_db = SessionLocal()
            try:
                existing = (
                    save_db.query(ResultatAnalyse)
                    .filter(ResultatAnalyse.study_instance_uid == study_id)
                    .first()
                )
                if existing is not None:
                    save_db.delete(existing)
                    save_db.flush()

                resultat = ResultatAnalyse(
                    study_instance_uid=study_id,
                    fracture_detectee=bool(analyse["fracture_detectee"]),
                    score_global=score_global,
                    rapport_clinique=rapport,
                    date_analyse=datetime.now(timezone.utc),
                    duree_analyse_sec=duree,
                    seuil_utilise=pipeline_service.threshold,
                    mode_mock=analyse.get("mode_mock", False),
                )
                save_db.add(resultat)
                save_db.flush()

                for detail in details:
                    save_db.add(
                        ScoreVertebre(
                            resultat_id=resultat.id,
                            vertebre=detail["vertebre"],
                            probabilite=_finite_float(detail["probabilite"]),
                            localisation=detail["localisation"],
                            bounding_box_x=_finite_float(detail["bounding_box_x"]),
                            bounding_box_y=_finite_float(detail["bounding_box_y"]),
                            bounding_box_w=_finite_float(detail["bounding_box_w"]),
                            bounding_box_h=_finite_float(detail["bounding_box_h"]),
                            coupe_reference=int(detail["coupe_reference"]),
                            niveau_risque=detail.get("niveau_risque"),
                            confiance_vertebre=(
                                _finite_float(detail["confiance_vertebre"])
                                if detail.get("confiance_vertebre") is not None
                                else None
                            ),
                        )
                    )

                save_db.commit()
                save_db.refresh(resultat)
            finally:
                save_db.close()

            analyse_task_store.update(study_id, status=AnalyseStatus.DONE, progress=100)
            return resultat

        except AnalysisCancelledError:
            logger.info("Analyse annulée pour %s (relance)", study_id)
            analyse_task_store.update(
                study_id,
                status=AnalyseStatus.ERROR,
                progress=0,
                error="Analyse annulée pour relance",
            )
            raise
        except Exception as exc:
            logger.exception("Analyse échouée pour %s", study_id)
            analyse_task_store.update(
                study_id,
                status=AnalyseStatus.ERROR,
                progress=0,
                error=str(exc),
            )
            raise
        finally:
            stop_heartbeat.set()

    def _wait_for_inference_slot(
        self,
        study_id: str,
        generation: int,
        on_progress: Callable[[int], None],
    ) -> None:
        """Attend le verrou CPU sans faire expirer la tâche côté API."""
        waited = 0
        while True:
            self._check_cancelled(study_id, generation)
            if _inference_lock.acquire(blocking=False):
                return
            analyse_task_store.touch(study_id)
            on_progress(36 + min(2, waited // 30))
            time.sleep(3)
            waited += 3

    def _is_cancelled(self, study_id: str, generation: int) -> bool:
        with _generation_lock:
            return _study_generation.get(study_id, generation) != generation

    def get_resultat(self, db: Session, study_id: str) -> ResultatAnalyse | None:
        return (
            db.query(ResultatAnalyse)
            .filter(ResultatAnalyse.study_instance_uid == study_id)
            .first()
        )


analyse_service = AnalyseService()

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.resultat import ResultatAnalyse
from app.models.utilisateur import Utilisateur
from app.schemas.analyse import (
    AnalyseStartResponse,
    AnalyseStatusSchema,
    ResultatAnalyseSchema,
    ScoreVertebreSchema,
)
from app.services.analyse_service import analyse_service
from app.services.analyse_task_store import AnalyseStatus, analyse_task_store
from app.services.examen_service import ExamenService

router = APIRouter(prefix="/analyse", tags=["analyse"])
examen_service = ExamenService()


def _to_schema(resultat: ResultatAnalyse) -> ResultatAnalyseSchema:
    return ResultatAnalyseSchema(
        study_id=resultat.study_instance_uid,
        score_global=resultat.score_global,
        fracture_detectee=resultat.fracture_detectee,
        scores_vertebres=[
            ScoreVertebreSchema(
                vertebre=s.vertebre,
                probabilite=s.probabilite,
                localisation=s.localisation,
                bounding_box_x=s.bounding_box_x,
                bounding_box_y=s.bounding_box_y,
                bounding_box_w=s.bounding_box_w,
                bounding_box_h=s.bounding_box_h,
                coupe_reference=s.coupe_reference,
            )
            for s in resultat.scores_vertebres
        ],
        rapport_clinique=resultat.rapport_clinique,
        date_analyse=resultat.date_analyse,
        duree_analyse_sec=resultat.duree_analyse_sec,
        seuil_utilise=resultat.seuil_utilise,
        mode_mock=resultat.mode_mock,
    )


def _run_background_analysis(study_id: str) -> None:
    db = SessionLocal()
    try:
        analyse_service.run_analysis(study_id, db)
    except Exception:
        pass
    finally:
        db.close()


@router.post("/{study_id}", response_model=AnalyseStartResponse)
def start_analysis(
    study_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> AnalyseStartResponse:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")

    existing = analyse_service.get_resultat(db, study_id)
    if existing is not None:
        task = analyse_task_store.get_by_study(study_id)
        if task is None:
            task = analyse_task_store.create(study_id)
            analyse_task_store.update(study_id, status=AnalyseStatus.DONE, progress=100)
        return AnalyseStartResponse(task_id=task.task_id, study_id=study_id)

    current_task = analyse_task_store.get_by_study(study_id)
    if current_task and current_task.status == AnalyseStatus.RUNNING:
        return AnalyseStartResponse(task_id=current_task.task_id, study_id=study_id)

    task = analyse_task_store.create(study_id)
    background_tasks.add_task(_run_background_analysis, study_id)
    return AnalyseStartResponse(task_id=task.task_id, study_id=study_id)


@router.get("/{study_id}/status", response_model=AnalyseStatusSchema)
def get_analysis_status(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> AnalyseStatusSchema:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")

    task = analyse_task_store.get_by_study(study_id)
    if task is None:
        existing = analyse_service.get_resultat(db, study_id)
        if existing is not None:
            return AnalyseStatusSchema(study_id=study_id, status="done", progress=100)
        return AnalyseStatusSchema(study_id=study_id, status="pending", progress=0)

    return AnalyseStatusSchema(
        study_id=study_id,
        status=task.status.value,
        progress=task.progress,
        error=task.error,
    )


@router.get("/{study_id}/resultats", response_model=ResultatAnalyseSchema)
def get_analysis_results(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> ResultatAnalyseSchema:
    resultat = analyse_service.get_resultat(db, study_id)
    if resultat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Résultats d'analyse non disponibles",
        )
    return _to_schema(resultat)

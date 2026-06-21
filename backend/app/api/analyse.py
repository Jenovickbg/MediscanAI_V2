from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.resultat import ResultatAnalyse
from app.models.utilisateur import Utilisateur
from app.schemas.analyse import (
    AnalyseStartResponse,
    AnalyseStatusSchema,
    BoundingBoxSchema,
    ResultatAnalyseSchema,
    VertebreResultatSchema,
)
from app.services.analyse_service import analyse_service
from app.services.analyse_task_store import AnalyseStatus, analyse_task_store
from app.services.examen_service import ExamenService
from app.services.triage_config import classifier_triage, load_triage_thresholds

router = APIRouter(prefix="/analyse", tags=["analyse"])
examen_service = ExamenService()

BBOX_PIXEL_SIZE = 512


def _bbox_to_pixels(score) -> BoundingBoxSchema | None:
    if score.bounding_box_w <= 0 and score.bounding_box_h <= 0:
        return None
    return BoundingBoxSchema(
        x=int(round(score.bounding_box_x * BBOX_PIXEL_SIZE)),
        y=int(round(score.bounding_box_y * BBOX_PIXEL_SIZE)),
        w=int(round(score.bounding_box_w * BBOX_PIXEL_SIZE)),
        h=int(round(score.bounding_box_h * BBOX_PIXEL_SIZE)),
    )


def _to_schema(resultat: ResultatAnalyse) -> ResultatAnalyseSchema:
    thresholds = load_triage_thresholds()
    scores_par_vertebre: dict[str, VertebreResultatSchema] = {}

    for score in resultat.scores_vertebres:
        niveau = score.niveau_risque or classifier_triage(score.probabilite, thresholds)
        if niveau == "normal" and score.probabilite < thresholds.seuil_bas:
            continue

        scores_par_vertebre[score.vertebre] = VertebreResultatSchema(
            probabilite=score.probabilite,
            bounding_box=_bbox_to_pixels(score),
            coupe_reference=score.coupe_reference,
            niveau_risque=niveau,
        )

    return ResultatAnalyseSchema(
        study_id=resultat.study_instance_uid,
        score_global=resultat.score_global,
        fracture_detectee=resultat.fracture_detectee,
        scores_par_vertebre=scores_par_vertebre,
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

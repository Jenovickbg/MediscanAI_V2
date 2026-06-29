import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import assert_examen_access, get_current_user
from app.models.resultat import ResultatAnalyse
from app.models.utilisateur import Utilisateur
from app.schemas.analyse import (
    AnalyseStartResponse,
    AnalyseStatusSchema,
    BoundingBoxSchema,
    ResultatAnalyseSchema,
    VertebreResultatSchema,
)
from app.services.analyse_service import AnalysisCancelledError, analyse_service
from app.services.analyse_task_store import AnalyseStatus, analyse_task_store, stale_timeout_for_exam
from app.services.examen_service import ExamenService
from app.services.triage_config import classifier_triage, load_triage_thresholds
from app.utils.datetime_utils import ensure_utc

router = APIRouter(prefix="/analyse", tags=["analyse"])
examen_service = ExamenService()
logger = logging.getLogger(__name__)

BBOX_PIXEL_SIZE = 512


def _safe_float(value: float | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return number


def _safe_pixel_coord(value: float) -> int:
    number = _safe_float(value)
    return int(round(number))


def _bbox_to_pixels(score) -> BoundingBoxSchema | None:
    raw = (
        score.bounding_box_x,
        score.bounding_box_y,
        score.bounding_box_w,
        score.bounding_box_h,
    )
    if not all(_is_finite_number(v) for v in raw):
        return None
    w = _safe_float(score.bounding_box_w)
    h = _safe_float(score.bounding_box_h)
    if w <= 0 and h <= 0:
        return None
    return BoundingBoxSchema(
        x=_safe_pixel_coord(score.bounding_box_x * BBOX_PIXEL_SIZE),
        y=_safe_pixel_coord(score.bounding_box_y * BBOX_PIXEL_SIZE),
        w=_safe_pixel_coord(w * BBOX_PIXEL_SIZE),
        h=_safe_pixel_coord(h * BBOX_PIXEL_SIZE),
    )


def _is_finite_number(value: object) -> bool:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf"))


def _to_schema(resultat: ResultatAnalyse) -> ResultatAnalyseSchema:
    thresholds = load_triage_thresholds()
    scores_par_vertebre: dict[str, VertebreResultatSchema] = {}

    for score in resultat.scores_vertebres:
        niveau = score.niveau_risque or classifier_triage(score.probabilite, thresholds)
        if niveau == "normal" and score.probabilite < thresholds.seuil_bas:
            continue

        scores_par_vertebre[score.vertebre] = VertebreResultatSchema(
            probabilite=_safe_float(score.probabilite),
            bounding_box=_bbox_to_pixels(score),
            coupe_reference=int(score.coupe_reference or 0),
            niveau_risque=niveau,
            confiance_vertebre=(
                _safe_float(score.confiance_vertebre)
                if score.confiance_vertebre is not None
                else None
            ),
        )

    return ResultatAnalyseSchema(
        study_id=resultat.study_instance_uid,
        score_global=_safe_float(resultat.score_global),
        fracture_detectee=resultat.fracture_detectee,
        scores_par_vertebre=scores_par_vertebre,
        rapport_clinique=resultat.rapport_clinique,
        date_analyse=resultat.date_analyse,
        duree_analyse_sec=resultat.duree_analyse_sec,
        seuil_utilise=resultat.seuil_utilise,
        mode_mock=resultat.mode_mock,
    )


def _run_background_analysis(study_id: str, generation: int) -> None:
    """Analyse synchrone — exécutée dans un thread pour ne pas bloquer l'API."""
    try:
        analyse_service.run_analysis(study_id, generation)
    except AnalysisCancelledError:
        logger.info("Analyse annulée pour %s", study_id)
    except Exception:
        logger.exception("Erreur thread analyse pour %s", study_id)


async def _run_background_analysis_async(study_id: str, generation: int) -> None:
    await asyncio.to_thread(_run_background_analysis, study_id, generation)


def _result_is_fresh(examen, resultat: ResultatAnalyse) -> bool:
    """False when the exam was re-imported after the last analysis."""
    uploaded = ensure_utc(examen.uploaded_at)
    analysed = ensure_utc(resultat.date_analyse)
    if uploaded is None or analysed is None:
        return True
    return uploaded <= analysed


@router.post("/{study_id}", response_model=AnalyseStartResponse)
def start_analysis(
    study_id: str,
    background_tasks: BackgroundTasks,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> AnalyseStartResponse:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")
    assert_examen_access(examen, current_user)

    existing = analyse_service.get_resultat(db, study_id)
    if existing is not None and not force and _result_is_fresh(examen, existing):
        task = analyse_task_store.get_by_study(study_id)
        if task is None:
            task = analyse_task_store.create(study_id)
            analyse_task_store.update(study_id, status=AnalyseStatus.DONE, progress=100)
        return AnalyseStartResponse(task_id=task.task_id, study_id=study_id)

    stale_limit = stale_timeout_for_exam(examen.nb_coupes)
    current_task = analyse_task_store.get_by_study(study_id)
    if (
        current_task
        and current_task.status == AnalyseStatus.RUNNING
        and not force
        and not analyse_task_store.is_stale_running(study_id, stale_limit)
    ):
        return AnalyseStartResponse(task_id=current_task.task_id, study_id=study_id)

    if current_task and current_task.status == AnalyseStatus.PENDING and not force:
        if not analyse_task_store.is_stale_pending(study_id):
            return AnalyseStartResponse(task_id=current_task.task_id, study_id=study_id)

    generation = analyse_service.bump_generation(study_id)
    task = analyse_task_store.create(study_id)
    background_tasks.add_task(_run_background_analysis_async, study_id, generation)
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
    assert_examen_access(examen, current_user)

    task = analyse_task_store.get_by_study(study_id)
    if task is None:
        existing = analyse_service.get_resultat(db, study_id)
        if existing is not None:
            return AnalyseStatusSchema(study_id=study_id, status="done", progress=100)
        return AnalyseStatusSchema(
            study_id=study_id,
            status="error",
            progress=0,
            error="Aucune analyse en cours. Cliquez sur Réessayer.",
        )

    if task.status == AnalyseStatus.PENDING and analyse_task_store.is_stale_pending(study_id):
        return AnalyseStatusSchema(
            study_id=study_id,
            status="error",
            progress=task.progress,
            error=(
                "L'analyse ne s'est pas lancée correctement. "
                "Cliquez sur Réessayer (ou Relancer)."
            ),
        )

    # Pas de coupure « stale » sur GET : l'analyse CPU peut rester longtemps à même %.

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
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")
    assert_examen_access(examen, current_user)

    resultat = analyse_service.get_resultat(db, study_id)
    if resultat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Résultats d'analyse non disponibles",
        )
    return _to_schema(resultat)

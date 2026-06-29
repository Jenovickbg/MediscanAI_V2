from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.api.analyse import _result_is_fresh, _to_schema
from app.core.database import SessionLocal
from app.core.deps import assert_examen_access
from app.core.security import decode_access_token
from app.models.utilisateur import Utilisateur
from app.services.analyse_service import AnalysisCancelledError, analyse_service
from app.services.analyse_task_store import AnalyseStatus, analyse_task_store
from app.services.examen_service import ExamenService

router = APIRouter(tags=["analyse-ws"])
examen_service = ExamenService()
logger = logging.getLogger(__name__)


def _authenticate_ws(token: str, db: Session) -> Utilisateur:
    payload = decode_access_token(token)
    if payload is None:
        raise ValueError("Token invalide ou expiré")

    email = payload.get("sub")
    if not email or not isinstance(email, str):
        raise ValueError("Token invalide")

    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if user is None:
        raise ValueError("Utilisateur introuvable")
    if not user.actif:
        raise ValueError("Compte désactivé")
    return user


def _progress_message(progress: int, nb_coupes: int) -> tuple[str, str]:
    if progress <= 10:
        return "chargement", "Chargement des fichiers DICOM..."
    if progress < 62:
        return "classification", f"Analyse de {nb_coupes} coupes en cours..."
    if progress < 80:
        return "localisation", "Localisation des zones suspectes..."
    if progress < 95:
        return "rapport", "Génération du rapport clinique..."
    return "termine", "Analyse terminée."


@router.websocket("/ws/{study_id}")
async def analyse_avec_progression(
    websocket: WebSocket,
    study_id: str,
    token: str = Query(...),
    force: bool = Query(default=False),
) -> None:
    await websocket.accept()
    db = SessionLocal()
    loop = asyncio.get_running_loop()

    try:
        user = _authenticate_ws(token, db)
    except ValueError as exc:
        await websocket.send_json(
            {"step": "erreur", "progress": 0, "message": str(exc)}
        )
        return

    try:
        examen = examen_service.get_examen_by_study_id(db, study_id)
        if examen is None:
            await websocket.send_json(
                {"step": "erreur", "progress": 0, "message": "Examen introuvable"}
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            assert_examen_access(examen, user)
        except HTTPException as exc:
            await websocket.send_json(
                {"step": "erreur", "progress": 0, "message": str(exc.detail)}
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        existing = analyse_service.get_resultat(db, study_id)
        if existing is not None and not force and _result_is_fresh(examen, existing):
            schema = _to_schema(existing)
            await websocket.send_json(
                {
                    "step": "termine",
                    "progress": 100,
                    "message": "Analyse terminée.",
                    "resultat": schema.model_dump(mode="json"),
                }
            )
            return

        generation = analyse_service.bump_generation(study_id)
        analyse_task_store.create(study_id)
        nb_coupes = examen.nb_coupes or 0

        def notify_progress(progress: int) -> None:
            step, message = _progress_message(progress, nb_coupes)
            payload = {"step": step, "progress": progress, "message": message}
            future = asyncio.run_coroutine_threadsafe(websocket.send_json(payload), loop)
            try:
                future.result(timeout=5)
            except Exception:
                logger.debug("Envoi progression WS ignoré pour %s", study_id)

        def run_in_thread() -> None:
            try:
                analyse_service.run_analysis(
                    study_id,
                    generation,
                    notify_progress,
                )
            except AnalysisCancelledError:
                logger.info("[WebSocket] Analyse annulée : %s", study_id)
            except Exception:
                logger.exception("[WebSocket] Erreur analyse %s", study_id)

        await asyncio.to_thread(run_in_thread)

        resultat = analyse_service.get_resultat(db, study_id)
        if resultat is None:
            await websocket.send_json(
                {
                    "step": "erreur",
                    "progress": 0,
                    "message": "Résultats d'analyse non disponibles",
                }
            )
            return

        schema = _to_schema(resultat)
        await websocket.send_json(
            {
                "step": "termine",
                "progress": 100,
                "message": "Analyse terminée.",
                "resultat": schema.model_dump(mode="json"),
            }
        )

    except WebSocketDisconnect:
        logger.info("[WebSocket] Client déconnecté : %s", study_id)
    except AnalysisCancelledError:
        logger.info("[WebSocket] Analyse annulée : %s", study_id)
    except Exception as exc:
        logger.exception("[WebSocket] Erreur analyse %s", study_id)
        task = analyse_task_store.get_by_study(study_id)
        if task and task.status == AnalyseStatus.ERROR and task.error:
            message = task.error
        else:
            message = str(exc)
        try:
            await websocket.send_json(
                {"step": "erreur", "progress": 0, "message": f"Erreur : {message}"}
            )
        except Exception:
            pass
    finally:
        db.close()

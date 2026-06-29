from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import BACKEND_DIR, settings
from app.core.deps import get_admin_user, get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.settings import AppSettingsSchema, ModelStatusSchema, TriageThresholdsSchema
from app.services.pipeline_service import pipeline_service
from app.services.triage_config import TriageThresholds, load_triage_thresholds, save_triage_thresholds
from app.utils.model_paths import resolve_model_path

router = APIRouter()


def _thresholds_schema() -> TriageThresholdsSchema:
    import json

    config_path = BACKEND_DIR / settings.TRIAGE_THRESHOLDS_PATH
    extra: dict = {}
    if config_path.exists():
        try:
            extra = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            extra = {}

    thresholds = load_triage_thresholds()
    return TriageThresholdsSchema(
        seuil_bas=thresholds.seuil_bas,
        seuil_haut=thresholds.seuil_haut,
        score_thresh_rcnn=thresholds.score_thresh_rcnn,
        nms_thresh_rcnn=thresholds.nms_thresh_rcnn,
        max_detections=thresholds.max_detections,
        derniere_maj=thresholds.derniere_maj,
        recall_garanti=extra.get("recall_garanti"),
        auc_modele1=extra.get("auc_modele1"),
        accuracy_modele3=extra.get("accuracy_modele3"),
    )


def build_app_settings() -> AppSettingsSchema:
    model_files = {
        "model1": resolve_model_path(settings.MODEL_1_PATH),
        "model2": resolve_model_path(settings.MODEL_2_PATH),
        "model3": resolve_model_path(
            settings.MODEL_3_PATH,
            "model/model3_vertebre_densenet121.pth",
        ),
    }

    return AppSettingsSchema(
        version=settings.APP_VERSION,
        device=str(pipeline_service.device) if pipeline_service.device else None,
        modeles={
            "model1": ModelStatusSchema(
                fichier_present=model_files["model1"] is not None,
                charge=pipeline_service.model_loaded,
                mock=pipeline_service.use_mock,
            ),
            "model2": ModelStatusSchema(
                fichier_present=model_files["model2"] is not None,
                charge=pipeline_service.model_2.model_loaded,
                mock=pipeline_service.model_2.use_mock,
            ),
            "model3": ModelStatusSchema(
                fichier_present=model_files["model3"] is not None,
                charge=pipeline_service.model_3.model_loaded,
                mock=pipeline_service.model_3.use_mock,
            ),
        },
        seuils=_thresholds_schema(),
    )


@router.get("/health")
def health_check() -> dict:
    """Vérifie l'API et le chargement des 3 modèles IA."""
    payload = build_app_settings()
    return {
        "status": "ok",
        "version": payload.version,
        "device": payload.device,
        "model_loaded": pipeline_service.model_loaded,
        "mock_mode": pipeline_service.use_mock,
        "modeles": {key: model.model_dump() for key, model in payload.modeles.items()},
        "seuils": payload.seuils.model_dump(),
        "model_dir": str(BACKEND_DIR / "model"),
    }


@router.get("/settings", response_model=AppSettingsSchema)
def get_settings(
    _current_user: Utilisateur = Depends(get_current_user),
) -> AppSettingsSchema:
    """Paramètres applicatifs et état des modèles IA."""
    return build_app_settings()


@router.put("/settings/thresholds", response_model=TriageThresholdsSchema)
def update_thresholds(
    payload: TriageThresholdsSchema,
    _admin: Utilisateur = Depends(get_admin_user),
) -> TriageThresholdsSchema:
    """Met à jour les seuils de triage (administrateur uniquement)."""
    if payload.seuil_bas >= payload.seuil_haut:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le seuil bas doit être inférieur au seuil haut",
        )

    updated = save_triage_thresholds(
        TriageThresholds(
            seuil_bas=payload.seuil_bas,
            seuil_haut=payload.seuil_haut,
            score_thresh_rcnn=payload.score_thresh_rcnn,
            nms_thresh_rcnn=payload.nms_thresh_rcnn,
            max_detections=payload.max_detections,
            derniere_maj=payload.derniere_maj,
        )
    )

    pipeline_service.reload_thresholds()
    pipeline_service.model_2.thresholds = load_triage_thresholds()

    return TriageThresholdsSchema(
        seuil_bas=updated.seuil_bas,
        seuil_haut=updated.seuil_haut,
        score_thresh_rcnn=updated.score_thresh_rcnn,
        nms_thresh_rcnn=updated.nms_thresh_rcnn,
        max_detections=updated.max_detections,
        derniere_maj=updated.derniere_maj,
        recall_garanti=payload.recall_garanti,
        auc_modele1=payload.auc_modele1,
        accuracy_modele3=payload.accuracy_modele3,
    )

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.examen import ExamenMetadataSchema, UploadResponseSchema
from app.services.examen_service import ExamenService

router = APIRouter(prefix="/demo", tags=["demo"])
examen_service = ExamenService()


@router.get("/load-sample", response_model=UploadResponseSchema)
def load_sample_examen(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> UploadResponseSchema:
    """Charge un examen d'exemple pour tester l'interface sans DICOM réels."""
    result = examen_service.create_demo_examen(db, current_user.id)
    return UploadResponseSchema(
        study_id=result["study_id"],
        nb_coupes=result["nb_coupes"],
        metadata=ExamenMetadataSchema.model_validate(result["metadata"]),
        preview_slices=result.get("preview_slices", []),
        files_received=result["nb_coupes"],
        total_files=result["nb_coupes"],
        finalized=True,
    )

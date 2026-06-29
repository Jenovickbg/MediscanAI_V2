from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import assert_examen_access, get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.examen import (
    ExamenListItemSchema,
    ExamenListResponse,
    ExamenMetadataSchema,
    ExamenSchema,
    UploadResponseSchema,
    UploadStatusSchema,
)
from app.services.examen_service import ExamenService
from app.services.upload_task_store import UploadStatus, upload_task_store

router = APIRouter(prefix="/examens", tags=["examens"])
examen_service = ExamenService()


def _build_upload_response(result: dict, task_id: str | None = None) -> UploadResponseSchema:
    return UploadResponseSchema(
        task_id=task_id,
        study_id=result["study_id"],
        nb_coupes=result["nb_coupes"],
        metadata=ExamenMetadataSchema.model_validate(result["metadata"]),
        preview_slices=result.get("preview_slices", []),
        files_received=result["nb_coupes"],
        total_files=result["nb_coupes"],
        finalized=True,
    )


@router.post("/upload", response_model=UploadResponseSchema)
async def upload_examen(
    patient_id: str = Form(...),
    files: list[UploadFile] = File(...),
    task_id: str | None = Form(None),
    finalize: bool = Form(False),
    total_files: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> UploadResponseSchema:
    if not patient_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id requis")

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun fichier reçu")

    if task_id:
        task = upload_task_store.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable")
        if task.patient_id != patient_id.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id incohérent")
    else:
        placeholder_dir = settings.TEMP_UPLOAD_DIR / "pending"
        task = upload_task_store.create(
            patient_id=patient_id.strip(),
            temp_dir=placeholder_dir,
            total_files=total_files,
        )
        task.temp_dir = settings.TEMP_UPLOAD_DIR / task.task_id
        task.temp_dir.mkdir(parents=True, exist_ok=True)

    file_payload: list[tuple[str, bytes]] = []
    for upload in files:
        content = await upload.read()
        filename = upload.filename or "unknown.dcm"
        file_payload.append((filename, content))

    examen_service.save_upload_files(task, file_payload)

    is_single_batch = task_id is None and (total_files is None or total_files <= len(files))
    auto_finalize = finalize or is_single_batch

    if not auto_finalize:
        return UploadResponseSchema(
            task_id=task.task_id,
            files_received=task.files_received,
            total_files=task.total_files,
            finalized=False,
        )

    try:
        result = examen_service.finalize_upload(task, db, current_user.id)
        upload_task_store.complete(task.task_id, result)
        return _build_upload_response(result, task.task_id)
    except Exception as exc:
        upload_task_store.fail(task.task_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/upload/status/{task_id}", response_model=UploadStatusSchema)
def get_upload_status(task_id: str) -> UploadStatusSchema:
    task = upload_task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable")

    result = None
    if task.status == UploadStatus.DONE and task.result:
        result = _build_upload_response(task.result, task.task_id)

    return UploadStatusSchema(
        task_id=task.task_id,
        status=task.status.value,
        progress=task.progress,
        files_received=task.files_received,
        total_files=task.total_files,
        error=task.error,
        result=result,
    )


@router.get("", response_model=ExamenListResponse)
def list_examens(
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
    result: str | None = Query(default=None, pattern="^(all|fracture|normal)$"),
    period: str | None = Query(default=None, pattern="^(all|week|month)$"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> ExamenListResponse:
    uploaded_by = current_user.id if current_user.role == "medecin" else None
    include_uploader = current_user.role == "admin"

    data = examen_service.list_examens(
        db,
        page=page,
        limit=limit,
        search=search,
        result_filter=result or "all",  # type: ignore[arg-type]
        period=period or "all",  # type: ignore[arg-type]
        uploaded_by=uploaded_by,
        include_uploader=include_uploader,
    )
    return ExamenListResponse(
        items=[ExamenListItemSchema.model_validate(item) for item in data["items"]],
        total=data["total"],
        page=data["page"],
        limit=data["limit"],
    )


@router.get("/{study_id}", response_model=ExamenSchema)
def get_examen(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> ExamenSchema:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")
    assert_examen_access(examen, current_user)
    return ExamenSchema.model_validate(examen)


@router.delete("/{study_id}")
def delete_examen(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> dict[str, bool]:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")
    assert_examen_access(examen, current_user)

    examen_service.delete_examen(db, examen)
    return {"success": True}

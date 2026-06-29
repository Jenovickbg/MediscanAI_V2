from datetime import datetime

from pydantic import BaseModel, Field


class ExamenMetadataSchema(BaseModel):
    patient_id: str
    study_instance_uid: str
    date_examen: str | None = None
    nb_coupes: int
    dimensions: list[int] | None = None
    pixel_spacing: list[float] | None = None
    slice_thickness: float | None = None
    demo: bool = False


class UploadResponseSchema(BaseModel):
    task_id: str | None = None
    study_id: str | None = None
    nb_coupes: int | None = None
    metadata: ExamenMetadataSchema | None = None
    preview_slices: list[int] = Field(default_factory=list)
    files_received: int = 0
    total_files: int | None = None
    finalized: bool = False


class UploadStatusSchema(BaseModel):
    task_id: str
    status: str
    progress: int
    files_received: int
    total_files: int | None = None
    error: str | None = None
    result: UploadResponseSchema | None = None


class ExamenSchema(BaseModel):
    id: int
    study_instance_uid: str
    patient_id: str
    date_examen: datetime | None
    nb_coupes: int
    dicom_path: str
    uploaded_at: datetime
    uploaded_by: int

    model_config = {"from_attributes": True}


class ExamenListItemSchema(BaseModel):
    id: int
    study_id: str
    patient_id: str
    date: datetime
    nb_coupes: int
    uploaded_at: datetime
    vertebres: list[str] = Field(default_factory=list)
    score_global: float | None = None
    fracture_detectee: bool | None = None
    analysed: bool = False
    uploaded_by: int | None = None
    medecin_nom: str | None = None


class ExamenListResponse(BaseModel):
    items: list[ExamenListItemSchema]
    total: int
    page: int
    limit: int

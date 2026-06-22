from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.utilisateur import Utilisateur
from app.services.examen_service import ExamenService
from app.services.pipeline_service import pipeline_service

router = APIRouter(prefix="/images", tags=["images"])
examen_service = ExamenService()


@router.get("/{study_id}/coupes")
def get_coupe_info(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> dict[str, int]:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")

    try:
        volume, _ = examen_service.dicom_service.get_cached_volume(examen.dicom_path)
        depth, height, width = volume.shape
        middle = depth // 2 if depth > 0 else 0
        return {
            "nb_coupes": depth,
            "coupe_centrale": middle,
            "width": width,
            "height": height,
        }
    except Exception:
        middle = examen.nb_coupes // 2 if examen.nb_coupes > 0 else 0
        return {
            "nb_coupes": examen.nb_coupes,
            "coupe_centrale": middle,
            "width": 512,
            "height": 512,
        }


@router.get("/{study_id}/coupe/{numero}")
def get_coupe_image(
    study_id: str,
    numero: int,
    view: str = Query(default="axial", pattern="^(axial|sagittal|coronal)$"),
    window_center: float = Query(default=300, alias="window_center"),
    window_width: float = Query(default=1500, alias="window_width"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> Response:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")

    try:
        volume, _ = examen_service.dicom_service.get_cached_volume(examen.dicom_path)
        png_bytes = examen_service.dicom_service.render_slice_to_image(
            volume,
            numero,
            view,
            wc=window_center,
            ww=window_width,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupe indisponible: {exc}",
        ) from exc

    return Response(content=png_bytes, media_type="image/png")


@router.get("/{study_id}/mpr/{view}/{index}")
def get_mpr_image(
    study_id: str,
    view: str,
    index: int,
    window_center: float = Query(default=300, alias="window_center"),
    window_width: float = Query(default=1500, alias="window_width"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> Response:
    if view not in ("axial", "sagittal", "coronal"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vue invalide")

    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")

    try:
        volume, _ = examen_service.dicom_service.get_cached_volume(examen.dicom_path)
        png_bytes = examen_service.dicom_service.render_mpr_png(
            volume,
            view,
            index,
            wc=window_center,
            ww=window_width,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupe MPR indisponible: {exc}",
        ) from exc

    return Response(content=png_bytes, media_type="image/png")


@router.get("/{study_id}/gradcam/{numero}")
def get_gradcam_image(
    study_id: str,
    numero: int,
    vertebra: str | None = Query(default=None, pattern="^C[1-7]$"),
    overlay: bool = Query(default=False, description="Heatmap transparente pour superposition UI"),
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> Response:
    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")

    try:
        volume, _ = examen_service.dicom_service.load_volume_from_study(examen.dicom_path)
        png_bytes = pipeline_service.render_gradcam_png(volume, numero, vertebra, overlay=overlay)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grad-CAM indisponible: {exc}",
        ) from exc

    return Response(content=png_bytes, media_type="image/png")


@router.get("/{study_id}/reconstruction-3d")
def get_reconstruction_3d(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> dict:
    from app.schemas.reconstruction import Reconstruction3DSchema
    from app.services.analyse_service import analyse_service
    from app.services.reconstruction_service import ReconstructionService

    examen = examen_service.get_examen_by_study_id(db, study_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable")

    resultat = analyse_service.get_resultat(db, study_id)
    scores: dict[str, float] = {}
    niveaux_risque: dict[str, str] = {}
    if resultat is not None:
        scores = {s.vertebre: s.probabilite for s in resultat.scores_vertebres}
        niveaux_risque = {
            s.vertebre: s.niveau_risque
            for s in resultat.scores_vertebres
            if s.niveau_risque
        }
    else:
        scores = {f"C{i}": 0.1 for i in range(1, 8)}

    try:
        volume, spacing = examen_service.dicom_service.get_cached_volume(examen.dicom_path)
        recon_service = ReconstructionService()
        mesh = recon_service.get_or_build_mesh(
            study_id,
            volume,
            spacing,
            scores,
            niveaux_risque=niveaux_risque or None,
        )
        return Reconstruction3DSchema.model_validate(mesh).model_dump()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconstruction 3D échouée: {exc}",
        ) from exc


@router.get("/{study_id}/export-pdf")
def export_report_pdf(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
) -> Response:
    from app.services.report_service import report_service

    try:
        pdf_bytes = report_service.generate_pdf(db, study_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Génération PDF échouée: {exc}",
        ) from exc

    filename = f"mediscanai-rapport-{study_id[:16]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

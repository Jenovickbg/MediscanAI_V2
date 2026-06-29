from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.models.utilisateur import Utilisateur
from app.schemas.medecin import MedecinCreateSchema, MedecinSchema, MedecinUpdateSchema
from app.services.medecin_service import medecin_service

router = APIRouter(prefix="/medecins", tags=["medecins"])


def _to_schema(user: Utilisateur, nb_examens: int = 0) -> MedecinSchema:
    return MedecinSchema(
        id=user.id,
        email=user.email,
        nom=user.nom,
        actif=user.actif,
        created_at=user.created_at,
        nb_examens=nb_examens,
    )


@router.get("", response_model=list[MedecinSchema])
def list_medecins(
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(get_admin_user),
) -> list[MedecinSchema]:
    return [MedecinSchema.model_validate(row) for row in medecin_service.list_medecins(db)]


@router.post("", response_model=MedecinSchema, status_code=status.HTTP_201_CREATED)
def create_medecin(
    body: MedecinCreateSchema,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(get_admin_user),
) -> MedecinSchema:
    try:
        user = medecin_service.create_medecin(db, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_schema(user, 0)


@router.put("/{medecin_id}", response_model=MedecinSchema)
def update_medecin(
    medecin_id: int,
    body: MedecinUpdateSchema,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(get_admin_user),
) -> MedecinSchema:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucune donnée à mettre à jour")

    try:
        user = medecin_service.update_medecin(db, medecin_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    from app.models.examen import Examen

    nb_examens = (
        db.query(func.count(Examen.id)).filter(Examen.uploaded_by == medecin_id).scalar() or 0
    )
    return _to_schema(user, int(nb_examens))


@router.delete("/{medecin_id}")
def delete_medecin(
    medecin_id: int,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(get_admin_user),
) -> dict[str, bool]:
    try:
        medecin_service.delete_medecin(db, medecin_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True}

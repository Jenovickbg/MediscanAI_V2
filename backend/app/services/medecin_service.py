from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.examen import Examen
from app.models.utilisateur import Utilisateur


class MedecinService:
    def list_medecins(self, db: Session) -> list[dict]:
        rows = (
            db.query(
                Utilisateur,
                func.count(Examen.id).label("nb_examens"),
            )
            .outerjoin(Examen, Examen.uploaded_by == Utilisateur.id)
            .filter(Utilisateur.role == "medecin")
            .group_by(Utilisateur.id)
            .order_by(Utilisateur.nom.asc())
            .all()
        )
        return [
            {
                "id": user.id,
                "email": user.email,
                "nom": user.nom,
                "actif": user.actif,
                "created_at": user.created_at,
                "nb_examens": int(nb_examens or 0),
            }
            for user, nb_examens in rows
        ]

    def get_medecin(self, db: Session, medecin_id: int) -> Utilisateur | None:
        return (
            db.query(Utilisateur)
            .filter(Utilisateur.id == medecin_id, Utilisateur.role == "medecin")
            .first()
        )

    def create_medecin(self, db: Session, data: dict) -> Utilisateur:
        existing = db.query(Utilisateur).filter(Utilisateur.email == data["email"]).first()
        if existing is not None:
            raise ValueError("Un compte existe déjà avec cet email")

        user = Utilisateur(
            email=data["email"],
            nom=data["nom"],
            hashed_password=get_password_hash(data["password"]),
            role="medecin",
            actif=data.get("actif", True),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_medecin(self, db: Session, medecin_id: int, data: dict) -> Utilisateur:
        user = self.get_medecin(db, medecin_id)
        if user is None:
            raise LookupError("Médecin introuvable")

        if data.get("email") and data["email"] != user.email:
            conflict = (
                db.query(Utilisateur)
                .filter(Utilisateur.email == data["email"], Utilisateur.id != medecin_id)
                .first()
            )
            if conflict is not None:
                raise ValueError("Un compte existe déjà avec cet email")
            user.email = data["email"]

        if data.get("nom"):
            user.nom = data["nom"]
        if data.get("password"):
            user.hashed_password = get_password_hash(data["password"])
        if data.get("actif") is not None:
            user.actif = data["actif"]

        db.commit()
        db.refresh(user)
        return user

    def delete_medecin(self, db: Session, medecin_id: int) -> None:
        user = self.get_medecin(db, medecin_id)
        if user is None:
            raise LookupError("Médecin introuvable")

        nb_examens = db.query(func.count(Examen.id)).filter(Examen.uploaded_by == medecin_id).scalar() or 0
        if nb_examens > 0:
            raise ValueError(
                f"Impossible de supprimer ce médecin : {nb_examens} examen(s) lui sont attribués. "
                "Désactivez-le plutôt."
            )

        db.delete(user)
        db.commit()


medecin_service = MedecinService()

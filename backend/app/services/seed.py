"""Création des comptes par défaut au premier démarrage."""

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.utilisateur import Utilisateur

DEFAULT_USERS: list[dict[str, str]] = [
    {
        "email": "admin@mediscanai.cd",
        "password": "Admin2025!",
        "nom": "Administrateur",
        "role": "admin",
    },
    {
        "email": "dr.kabila@mediscanai.cd",
        "password": "Medecin2025!",
        "nom": "Dr. Kabila",
        "role": "medecin",
    },
]


def seed_default_users(db: Session) -> None:
    for user_data in DEFAULT_USERS:
        existing = db.query(Utilisateur).filter(Utilisateur.email == user_data["email"]).first()
        if existing is not None:
            continue

        db.add(
            Utilisateur(
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                nom=user_data["nom"],
                role=user_data["role"],
            )
        )

    db.commit()

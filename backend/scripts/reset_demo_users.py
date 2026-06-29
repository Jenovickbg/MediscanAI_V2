"""Réinitialise les mots de passe des comptes démo."""

from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.models.utilisateur import Utilisateur
from app.services.seed import DEFAULT_USERS


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        for user_data in DEFAULT_USERS:
            user = db.query(Utilisateur).filter(Utilisateur.email == user_data["email"]).first()
            if user is None:
                db.add(
                    Utilisateur(
                        email=user_data["email"],
                        hashed_password=get_password_hash(user_data["password"]),
                        nom=user_data["nom"],
                        role=user_data["role"],
                    )
                )
                print(f"Créé : {user_data['email']}")
            else:
                user.hashed_password = get_password_hash(user_data["password"])
                user.nom = user_data["nom"]
                user.role = user_data["role"]
                print(f"Mot de passe réinitialisé : {user_data['email']}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()

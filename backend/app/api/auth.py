from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models.utilisateur import Utilisateur
from app.schemas.auth import LoginRequest, TokenResponse, UserSchema

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(Utilisateur).filter(Utilisateur.email == body.email).first()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not user.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé. Contactez l'administrateur.",
        )

    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(
        access_token=access_token,
        user=UserSchema.model_validate(user),
    )


@router.get("/me", response_model=UserSchema)
def get_me(current_user: Utilisateur = Depends(get_current_user)) -> UserSchema:
    return UserSchema.model_validate(current_user)

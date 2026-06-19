from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class RoleUtilisateur(str, Enum):
    MEDECIN = "medecin"
    ADMIN = "admin"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserSchema(BaseModel):
    id: int
    email: EmailStr
    nom: str
    role: RoleUtilisateur
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSchema

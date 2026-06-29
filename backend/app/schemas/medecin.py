from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class MedecinSchema(BaseModel):
    id: int
    email: EmailStr
    nom: str
    actif: bool
    created_at: datetime
    nb_examens: int = 0

    model_config = {"from_attributes": True}


class MedecinCreateSchema(BaseModel):
    email: EmailStr
    nom: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    actif: bool = True


class MedecinUpdateSchema(BaseModel):
    email: EmailStr | None = None
    nom: str | None = Field(default=None, min_length=2, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    actif: bool | None = None

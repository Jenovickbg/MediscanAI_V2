from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    examens: Mapped[list["Examen"]] = relationship(back_populates="patient")


class Examen(Base):
    __tablename__ = "examens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    study_instance_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(128), ForeignKey("patients.patient_id"))
    date_examen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nb_coupes: Mapped[int] = mapped_column(Integer, default=0)
    dicom_path: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id"))

    patient: Mapped["Patient"] = relationship(back_populates="examens")

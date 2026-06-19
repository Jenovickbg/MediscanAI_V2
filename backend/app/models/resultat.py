from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

VERTEBRES = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")


class ResultatAnalyse(Base):
    __tablename__ = "resultats_analyse"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    study_instance_uid: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("examens.study_instance_uid"),
        unique=True,
        index=True,
    )
    fracture_detectee: Mapped[bool] = mapped_column(Boolean, default=False)
    score_global: Mapped[float] = mapped_column(Float, default=0.0)
    rapport_clinique: Mapped[str] = mapped_column(Text, default="")
    date_analyse: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    duree_analyse_sec: Mapped[float] = mapped_column(Float, default=0.0)
    seuil_utilise: Mapped[float] = mapped_column(Float, default=0.03)
    mode_mock: Mapped[bool] = mapped_column(Boolean, default=False)

    scores_vertebres: Mapped[list["ScoreVertebre"]] = relationship(
        back_populates="resultat",
        cascade="all, delete-orphan",
    )


class ScoreVertebre(Base):
    __tablename__ = "scores_vertebres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resultat_id: Mapped[int] = mapped_column(ForeignKey("resultats_analyse.id"))
    vertebre: Mapped[str] = mapped_column(String(3))
    probabilite: Mapped[float] = mapped_column(Float, default=0.0)
    localisation: Mapped[str] = mapped_column(String(255), default="")
    bounding_box_x: Mapped[float] = mapped_column(Float, default=0.0)
    bounding_box_y: Mapped[float] = mapped_column(Float, default=0.0)
    bounding_box_w: Mapped[float] = mapped_column(Float, default=0.0)
    bounding_box_h: Mapped[float] = mapped_column(Float, default=0.0)
    coupe_reference: Mapped[int] = mapped_column(Integer, default=0)

    resultat: Mapped["ResultatAnalyse"] = relationship(back_populates="scores_vertebres")

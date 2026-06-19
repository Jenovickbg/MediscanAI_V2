from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.examen import Examen
from app.models.resultat import ResultatAnalyse, ScoreVertebre, VERTEBRES

SUSPICION_THRESHOLD = 0.30
FRACTURE_THRESHOLD = 0.60
PeriodKey = Literal["7d", "30d", "90d"]
PERIOD_DAYS: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}

MODEL_METRICS = {
    "recall": 0.942,
    "auc": 0.971,
    "f1": 0.913,
    "model_name": "DenseNet-121 2.5D",
}


class StatsService:
    def get_dashboard(self, db: Session, recent_limit: int = 10) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        today_exams = (
            db.query(func.count(ResultatAnalyse.id))
            .filter(ResultatAnalyse.date_analyse >= today_start)
            .scalar()
            or 0
        )

        month_fractures = (
            db.query(func.count(ResultatAnalyse.id))
            .filter(
                ResultatAnalyse.date_analyse >= month_start,
                ResultatAnalyse.fracture_detectee.is_(True),
            )
            .scalar()
            or 0
        )

        avg_score = (
            db.query(func.avg(ResultatAnalyse.score_global))
            .scalar()
        )
        avg_time = (
            db.query(func.avg(ResultatAnalyse.duree_analyse_sec))
            .scalar()
        )

        examens = (
            db.query(Examen)
            .options(joinedload(Examen.patient))
            .order_by(Examen.uploaded_at.desc())
            .limit(recent_limit)
            .all()
        )

        study_ids = [ex.study_instance_uid for ex in examens]
        resultats_by_study: dict[str, ResultatAnalyse] = {}
        if study_ids:
            resultats = (
                db.query(ResultatAnalyse)
                .options(joinedload(ResultatAnalyse.scores_vertebres))
                .filter(ResultatAnalyse.study_instance_uid.in_(study_ids))
                .all()
            )
            resultats_by_study = {r.study_instance_uid: r for r in resultats}

        recent_exams: list[dict] = []
        for examen in examens:
            resultat = resultats_by_study.get(examen.study_instance_uid)
            display_date = examen.date_examen or examen.uploaded_at

            vertebres: list[str] = []
            score_global: float | None = None
            fracture_detectee: bool | None = None
            analysed = resultat is not None

            if resultat is not None:
                score_global = resultat.score_global
                fracture_detectee = resultat.fracture_detectee
                vertebres = self._affected_vertebrae(resultat.scores_vertebres)

            recent_exams.append(
                {
                    "study_id": examen.study_instance_uid,
                    "patient_id": examen.patient_id,
                    "date": display_date,
                    "vertebres": vertebres,
                    "score_global": score_global,
                    "fracture_detectee": fracture_detectee,
                    "analysed": analysed,
                }
            )

        return {
            "today_exams": today_exams,
            "month_fractures": month_fractures,
            "avg_score": float(avg_score or 0.0),
            "avg_time": float(avg_time or 0.0),
            "recent_exams": recent_exams,
        }

    def get_historique(self, db: Session, period: PeriodKey = "30d") -> dict:
        days = PERIOD_DAYS.get(period, 30)
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        resultats = (
            db.query(ResultatAnalyse)
            .options(joinedload(ResultatAnalyse.scores_vertebres))
            .filter(ResultatAnalyse.date_analyse >= start)
            .all()
        )

        daily_map: dict[date, int] = {}
        for offset in range(days):
            day = (start + timedelta(days=offset)).date()
            daily_map[day] = 0

        fracture_count = 0
        normal_count = 0
        vertebra_fracture_counts = {v: 0 for v in VERTEBRES}
        vertebra_score_sums = {v: 0.0 for v in VERTEBRES}
        vertebra_score_counts = {v: 0 for v in VERTEBRES}

        for resultat in resultats:
            day_key = resultat.date_analyse.date()
            if day_key in daily_map:
                daily_map[day_key] += 1

            if resultat.fracture_detectee:
                fracture_count += 1
            else:
                normal_count += 1

            for score in resultat.scores_vertebres:
                if score.vertebre not in vertebra_fracture_counts:
                    continue
                if score.probabilite >= FRACTURE_THRESHOLD:
                    vertebra_fracture_counts[score.vertebre] += 1
                vertebra_score_sums[score.vertebre] += score.probabilite
                vertebra_score_counts[score.vertebre] += 1

        daily_counts = [
            {"date": day, "count": daily_map[day]}
            for day in sorted(daily_map.keys())
        ]

        result_distribution = [
            {"label": "Fracture", "value": fracture_count},
            {"label": "Normal", "value": normal_count},
        ]

        vertebrae_distribution = [
            {
                "vertebre": vertebre,
                "fracture_count": vertebra_fracture_counts[vertebre],
                "avg_score": (
                    vertebra_score_sums[vertebre] / vertebra_score_counts[vertebre]
                    if vertebra_score_counts[vertebre] > 0
                    else 0.0
                ),
            }
            for vertebre in VERTEBRES
        ]

        return {
            "period": period,
            "daily_counts": daily_counts,
            "result_distribution": result_distribution,
            "vertebrae_distribution": vertebrae_distribution,
            "recall_metrics": MODEL_METRICS,
        }

    def _affected_vertebrae(self, scores: list[ScoreVertebre]) -> list[str]:
        at_risk = [
            score.vertebre
            for score in scores
            if score.probabilite >= SUSPICION_THRESHOLD
        ]
        if at_risk:
            return sorted(at_risk, key=lambda v: VERTEBRES.index(v) if v in VERTEBRES else 99)

        if not scores:
            return []

        top = max(scores, key=lambda s: s.probabilite)
        if top.probabilite > 0:
            return [top.vertebre]
        return []


stats_service = StatsService()

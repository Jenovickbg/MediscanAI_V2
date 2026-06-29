from __future__ import annotations

from datetime import datetime, timedelta, timezone


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_plausible_study_date(
    study_date: datetime,
    reference: datetime,
    *,
    max_years_before: int = 5,
    max_days_after: int = 1,
) -> bool:
    """Ignore DICOM StudyDate values that are clearly wrong vs import time."""
    ref = ensure_utc(reference) or datetime.now(timezone.utc)
    study = ensure_utc(study_date)
    if study is None:
        return False

    earliest = ref - timedelta(days=max_years_before * 365)
    latest = ref + timedelta(days=max_days_after)
    return earliest <= study <= latest


def examen_display_datetime(examen) -> datetime:
    """Date shown in dashboard/history: import time, or DICOM date if trustworthy."""
    uploaded = ensure_utc(examen.uploaded_at) or datetime.now(timezone.utc)
    study = ensure_utc(examen.date_examen)
    if study and is_plausible_study_date(study, uploaded):
        return study
    return uploaded

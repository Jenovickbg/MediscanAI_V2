from datetime import datetime, timezone

from app.utils.datetime_utils import examen_display_datetime, is_plausible_study_date


def test_ignores_invalid_dicom_study_date() -> None:
    class FakeExamen:
        date_examen = datetime(2005, 1, 1, 1, 1, tzinfo=timezone.utc)
        uploaded_at = datetime(2026, 6, 19, 13, 46, 45, tzinfo=timezone.utc)

    assert examen_display_datetime(FakeExamen()) == FakeExamen.uploaded_at


def test_keeps_plausible_dicom_study_date() -> None:
    uploaded = datetime(2026, 6, 19, 13, 46, 45, tzinfo=timezone.utc)
    study = datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc)

    class FakeExamen:
        date_examen = study
        uploaded_at = uploaded

    assert examen_display_datetime(FakeExamen()) == study


def test_is_plausible_study_date_rejects_ancient() -> None:
    ref = datetime(2026, 6, 19, tzinfo=timezone.utc)
    old = datetime(2005, 1, 1, tzinfo=timezone.utc)
    assert is_plausible_study_date(old, ref) is False

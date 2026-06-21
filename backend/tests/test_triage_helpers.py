from app.services.triage_config import (
    is_vertebra_at_risk,
    niveau_risque_label,
    resolve_niveau_risque,
)


def test_resolve_niveau_risque_from_db():
    assert resolve_niveau_risque(0.05, "eleve") == "eleve"
    assert resolve_niveau_risque(0.05, "normal") == "normal"


def test_is_vertebra_at_risk():
    assert is_vertebra_at_risk(0.01, "eleve") is True
    assert is_vertebra_at_risk(0.01, "incertain") is True
    assert is_vertebra_at_risk(0.97, "normal") is False
    assert is_vertebra_at_risk(0.01, None) is False
    assert is_vertebra_at_risk(0.15, None) is True


def test_niveau_risque_label():
    assert niveau_risque_label("eleve") == "Fracture suspectée"
    assert niveau_risque_label("incertain") == "Surveillance"
    assert niveau_risque_label("normal") == "Normal"

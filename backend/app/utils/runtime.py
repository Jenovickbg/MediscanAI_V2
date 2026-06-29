"""Indicateurs d'environnement d'exécution (tests, mock forcé, etc.)."""

from __future__ import annotations

import os


def is_ia_mock_forced() -> bool:
    """True si les tests ou le dev doivent ignorer le chargement PyTorch."""
    return os.getenv("MEDISCANAI_FORCE_MOCK", "").lower() in ("1", "true", "yes")

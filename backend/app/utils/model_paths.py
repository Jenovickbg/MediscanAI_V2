"""Résolution des chemins de poids PyTorch (noms de fichiers alternatifs)."""

from __future__ import annotations

from pathlib import Path

from app.core.config import BACKEND_DIR


def resolve_model_path(*candidates: str) -> Path | None:
    """Retourne le premier fichier existant parmi les candidats."""
    for relative in candidates:
        path = BACKEND_DIR / relative
        if path.is_file():
            return path
    return None

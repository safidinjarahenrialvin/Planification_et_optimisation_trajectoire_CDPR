"""Libellés de présentation partagés par les vues et les exports."""
from __future__ import annotations

from collections.abc import Iterable


KIND_LABELS = {
    "baseline_zigzag": "Baseline : zigzag",
    "baseline_nn": "Baseline de repli historique : plus proche voisin",
    "time_opt": "Trajectoire temps optimal",
    "energy_opt": "Trajectoire énergie optimale",
    "compromise": "Trajectoire compromis",
}


def kind_label(kind: object) -> str:
    """Retourne un libellé utilisateur tout en conservant les kinds inconnus."""
    value = str(kind)
    return KIND_LABELS.get(value, value)


def baseline_kind(kinds: Iterable[object]) -> str | None:
    """Retourne le kind baseline réellement présent dans une collection."""
    values = [str(kind) for kind in kinds]
    for preferred in ("baseline_zigzag", "baseline_nn"):
        if preferred in values:
            return preferred
    return next((value for value in values if value.startswith("baseline_")), None)


def baseline_label(kinds: Iterable[object]) -> str:
    """Retourne le libellé de la baseline présente, ou un libellé neutre."""
    kind = baseline_kind(kinds)
    return kind_label(kind) if kind is not None else "Baseline de référence"

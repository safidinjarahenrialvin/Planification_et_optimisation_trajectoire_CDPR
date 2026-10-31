"""
BLOC 4 — Générateur de points (PointGenerator)
================================================

Portée    : produire la liste des points de prise de vue à partir des seuls
            paramètres de Config. Aucune géométrie n'est dupliquée ici.

La taille de grille dépend de Config : la configuration par défaut est 9×9
(81 points), tandis que `Config.with_n()` fournit les modes rapides.

Sorties :
    - DataFrame (id, x, y, z, ligne, colonne) — N lignes selon Config
  - CSV `data/outputs/points_generes.csv`
  - Rapport JSON `data/outputs/points_generes_report.json` (FOV, alertes)
  - Alerte géométrique dans le rapport si l'étendue dépasse les limites

Convention d'ordre (importante pour la cohérence inter-blocs)
--------------------------------------------------------------
  - `ligne`  = index selon Y (0 à n_rangs-1)
  - `colonne`= index selon X (0 à n_colonnes-1)
  - `id`     = ligne * n_colonnes + colonne
  - Ordre d'écriture : ligne 0 d'abord (y minimal), colonne 0 d'abord.
    Cette convention est partagée par le filtre, le comparateur et les tests.

Convention FOV
--------------
  FOV_h (62.2°) est alignée sur l'axe X → empreinte W_h vs esp_x.
  FOV_v (48.8°) est alignée sur l'axe Y → empreinte W_v vs esp_y.
  Si la caméra est physiquement tournée de 90°, les rôles s'inversent.
  Cette convention est documentée ici et pourra être paramétrée si
  nécessaire ; elle n'a aucun impact numérique tant que esp_x == esp_y.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)

# Nom de colonnes figés (contrat d'interface §6).
_CSV_COLUMNS = ["id", "x", "y", "z", "ligne", "colonne"]


class PointGenerator:
    """
    Génère la grille de points de vue à partir de la Config validée.

    Aucune constante n'est codée en dur : toutes les valeurs proviennent
    de `self.config`.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Génération
    # ------------------------------------------------------------------
    def generate(
        self,
        origin: str | tuple = "centre",
    ) -> pd.DataFrame:
        """
        Retourne la grille sous forme de DataFrame.

        Paramètres
        ----------
        origin : 'centre' (défaut) ou tuple (cx, cy)
            Centre de la grille. 'centre' équivaut à (0.0, 0.0), ce qui
            correspond au point de départ/retour obligatoire du cahier
            des charges. Un tuple permet un décalage futur de la grille
            sans changer sa forme.

        Retour
        ------
        DataFrame avec colonnes : id, x, y, z, ligne, colonne
        """
        xs, ys = self._grid_coordinates(origin)
        z_value = float(self.config.z_absolu_r0)

        rows = []
        pid = 0
        for i, y in enumerate(ys):
            for j, x in enumerate(xs):
                rows.append({
                    "id": pid,
                    "x": float(x),
                    "y": float(y),
                    "z": z_value,
                    "ligne": i,
                    "colonne": j,
                })
                pid += 1

        df = pd.DataFrame(rows, columns=_CSV_COLUMNS)

        # Contrôle défensif : Config R4 garantit déjà que l'étendue tient
        # dans les limites opérationnelles. On vérifie une seconde fois
        # pour produire un message explicite si jamais la logique évolue.
        self._verify_extent(df)

        logger.info(
            "PointGenerator : %d points générés (grille %d×%d, espacement %.3f m).",
            len(df), self.config.n_rangs, self.config.n_colonnes,
            self.config.esp_x,
        )
        return df

    # ------------------------------------------------------------------
    # Rapport FOV
    # ------------------------------------------------------------------
    def fov_report(self) -> dict[str, Any]:
        """
        Construit le rapport JSON complet :
          - résumé Config (immutable, pour reproductibilité)
          - étendue de la grille
          - empreinte FOV sur le sol et recouvrement avec les voisins
          - liste d'alertes géométriques (normalement vide avec v3.1)
        """
        cfg = self.config
        xs, ys = self._grid_coordinates("centre")

        # Étendue de la grille
        half_x = float((xs.max() - xs.min()) / 2.0)
        half_y = float((ys.max() - ys.min()) / 2.0)

        # Empreinte FOV au sol (à z = z_vol au-dessus des plants)
        W_h, W_v = self._fov_footprint_m()
        overlap_x_cm = (W_h - cfg.esp_x) * 100.0
        overlap_y_cm = (W_v - cfg.esp_y) * 100.0

        # Alertes géométriques calculées à partir de la configuration active.
        alerts = self._collect_alerts(xs, ys, W_h, W_v)

        report: dict[str, Any] = {
            "config_summary": {
                "N": int(cfg.N),
                "n_rangs": int(cfg.n_rangs),
                "n_colonnes": int(cfg.n_colonnes),
                "esp_x_m": float(cfg.esp_x),
                "esp_y_m": float(cfg.esp_y),
                "z_absolu_r0_m": float(cfg.z_absolu_r0),
                "z_vol_m": float(cfg.z_vol),
                "fov_camera_deg": [float(cfg.fov_camera[0]), float(cfg.fov_camera[1])],
            },
            "grid_extent": {
                "x_min": float(xs.min()),
                "x_max": float(xs.max()),
                "y_min": float(ys.min()),
                "y_max": float(ys.max()),
                "half_x_m": half_x,
                "half_y_m": half_y,
            },
            "fov_footprint": {
                "W_h_m": W_h,
                "W_v_m": W_v,
                "W_h_cm": W_h * 100.0,
                "W_v_cm": W_v * 100.0,
            },
            "overlap": {
                "x_cm": overlap_x_cm,
                "y_cm": overlap_y_cm,
                "covers_fully_x": bool(overlap_x_cm >= 0.0),
                "covers_fully_y": bool(overlap_y_cm >= 0.0),
            },
            "alerts": alerts,
        }
        return report

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------
    def save_csv(self, df: pd.DataFrame, path: Path | str) -> Path:
        """Écrit le DataFrame des points au format CSV figé."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, float_format="%.6f")
        logger.info("CSV points écrit : %s", path)
        return path

    def save_json(self, report: dict, path: Path | str) -> Path:
        """Écrit le rapport JSON (FOV + alertes)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("Rapport JSON écrit : %s", path)
        return path

    # ------------------------------------------------------------------
    # Pipeline complet
    # ------------------------------------------------------------------
    def run(
        self,
        output_dir: Path | str = "data/outputs",
    ) -> dict[str, Path]:
        """
        Pipeline complet : génération → CSV + JSON.
        Retourne un dict avec les chemins des deux fichiers écrits.
        """
        output_dir = Path(output_dir)
        df = self.generate()
        report = self.fov_report()
        csv_path = self.save_csv(df, output_dir / "points_generes.csv")
        json_path = self.save_json(report, output_dir / "points_generes_report.json")
        return {"csv": csv_path, "json": json_path}

    # ------------------------------------------------------------------
    # Utilitaires privés
    # ------------------------------------------------------------------
    def _grid_coordinates(
        self, origin: str | tuple
    ) -> tuple[np.ndarray, np.ndarray]:
        """Retourne les tableaux xs (n_colonnes) et ys (n_rangs)."""
        if origin == "centre":
            cx, cy = 0.0, 0.0
        elif isinstance(origin, tuple) and len(origin) == 2:
            cx, cy = float(origin[0]), float(origin[1])
        else:
            raise ValueError(
                f"origin doit être 'centre' ou un tuple (cx, cy), "
                f"reçu {origin!r}."
            )

        # Demi-étendues dérivées : (n - 1)/2 × espacement
        half_x = (self.config.n_colonnes - 1) / 2.0 * self.config.esp_x
        half_y = (self.config.n_rangs - 1) / 2.0 * self.config.esp_y

        xs = np.linspace(cx - half_x, cx + half_x, self.config.n_colonnes)
        ys = np.linspace(cy - half_y, cy + half_y, self.config.n_rangs)
        return xs, ys

    def _fov_footprint_m(self) -> tuple[float, float]:
        """
        Empreinte FOV de la caméra sur un plan horizontal situé à z_vol
        au-dessus des plants.
            W_h = 2 · z_vol · tan(FOV_h / 2)
            W_v = 2 · z_vol · tan(FOV_v / 2)
        """
        fov_h_deg, fov_v_deg = self.config.fov_camera
        z = self.config.z_vol
        W_h = 2.0 * z * math.tan(math.radians(fov_h_deg / 2.0))
        W_v = 2.0 * z * math.tan(math.radians(fov_v_deg / 2.0))
        return W_h, W_v

    def _verify_extent(self, df: pd.DataFrame) -> None:
        """
        Vérification défensive : l'étendue de la grille doit rester dans
        les limites opérationnelles. Config R4 garantit déjà ceci, mais
        on produit une erreur explicite si la logique évolue.
        """
        cfg = self.config
        x_max_abs = df["x"].abs().max()
        y_max_abs = df["y"].abs().max()
        lim_x = max(abs(cfg.x_min), abs(cfg.x_max))
        lim_y = max(abs(cfg.y_min), abs(cfg.y_max))
        if x_max_abs > lim_x + 1e-9:
            raise ValueError(
                f"Étendue X de la grille ({x_max_abs:.4f} m) dépasse la "
                f"limite X ({lim_x:.4f} m). Vérifier Config R4."
            )
        if y_max_abs > lim_y + 1e-9:
            raise ValueError(
                f"Étendue Y de la grille ({y_max_abs:.4f} m) dépasse la "
                f"limite Y ({lim_y:.4f} m). Vérifier Config R4."
            )

    def _collect_alerts(
        self,
        xs: np.ndarray,
        ys: np.ndarray,
        W_h: float,
        W_v: float,
    ) -> list[str]:
        """Rassemble les alertes géométriques (vides en nominal v3.1)."""
        alerts: list[str] = []
        cfg = self.config

        lim_x = max(abs(cfg.x_min), abs(cfg.x_max))
        lim_y = max(abs(cfg.y_min), abs(cfg.y_max))
        if max(abs(xs.min()), abs(xs.max())) > lim_x + 1e-9:
            alerts.append(f"Grille hors limite X (lim={lim_x:.3f} m).")
        if max(abs(ys.min()), abs(ys.max())) > lim_y + 1e-9:
            alerts.append(f"Grille hors limite Y (lim={lim_y:.3f} m).")

        if W_h < cfg.esp_x - 1e-9:
            alerts.append(
                f"Empreinte FOV X ({W_h*100:.2f} cm) < espacement X "
                f"({cfg.esp_x*100:.2f} cm) : trou de couverture possible."
            )
        if W_v < cfg.esp_y - 1e-9:
            alerts.append(
                f"Empreinte FOV Y ({W_v*100:.2f} cm) < espacement Y "
                f"({cfg.esp_y*100:.2f} cm) : trou de couverture possible."
            )
        return alerts

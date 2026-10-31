"""
BLOC 0 — Configuration centrale (Config)
=========================================

Source unique de vérité du projet SP2 (Projet Tandem).

Référence : configuration opérationnelle du pipeline SP2.
Cette classe est la source unique des paramètres géométriques, mécaniques,
cinématiques et NSGA-II. Les décisions historiques et les variantes legacy
sont conservées dans `docs/DECISIONS.md` et dans les constructeurs dédiés.

Configuration courante par défaut :
    - grille 9×9 (81 points), espacement 0.20 m ;
    - bornes opérationnelles ±0.80 m en X/Y et z_max = 0.86 m ;
    - plateforme 300×240 mm, avec bornes zero-loss calibrées par plateforme ;
    - NSGA-II : population 500, 1500 générations.

Mécanisme quick mode — Config.with_n(n) :
  Dérive l'espacement et les paramètres NSGA-II pour n'importe quelle
  taille de grille impaire ≥ 3, en gardant les mêmes bornes ±0.80 m.
  Table recommandée :
      3 → pop= 30, gen= 100   (smoke test, ~8 s)
      5 → pop=100, gen= 300   (rapide,     ~25 s)
      7 → pop=200, gen= 500   (intermédiaire, ~1 min 15 s)
      9 → pop=500, gen=1500   (référence, ~2 min 30 s)
     11 → pop=800, gen=2000   (haute résolution, ~6 min)

Classes legacy conservées pour A/B testing :
  - Config.legacy_v3_0() : 9×9 @ 0.25, ±1.00, plateforme 200×160
  - Config.legacy_v3_1() : 7×7 @ 0.25, ±0.75, plateforme 700×560
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ===========================================================================
# Tables géométriques et variantes historiques
# ===========================================================================
ANCRAGES_A_M: np.ndarray = np.array(
    [
        [-1.250, +1.250, +1.000],
        [+1.250, +1.250, +1.000],
        [-1.250, -1.250, +1.000],
        [+1.250, -1.250, +1.000],
        [-1.250, +1.250, +0.000],
        [+1.250, +1.250, +0.000],
        [-1.250, -1.250, +0.000],
        [+1.250, -1.250, +0.000],
    ],
    dtype=float,
).T

ATTACHES_B_M_V3_1: np.ndarray = np.array(
    [
        [-0.350, +0.280, +0.025],
        [+0.350, +0.280, +0.025],
        [-0.350, -0.280, +0.025],
        [+0.350, -0.280, +0.025],
        [-0.350, +0.280, -0.025],
        [+0.350, +0.280, -0.025],
        [-0.350, -0.280, -0.025],
        [+0.350, -0.280, -0.025],
    ],
    dtype=float,
).T

ATTACHES_B_M_V3_0: np.ndarray = np.array(
    [
        [-0.100, +0.080, +0.025],
        [+0.100, +0.080, +0.025],
        [-0.100, -0.080, +0.025],
        [+0.100, -0.080, +0.025],
        [-0.100, +0.080, -0.025],
        [+0.100, +0.080, -0.025],
        [-0.100, -0.080, -0.025],
        [+0.100, -0.080, -0.025],
    ],
    dtype=float,
).T


_EPS: float = 1e-9

# Bornes opérationnelles par défaut, dérivées du sweep WFW.
_OP_BOUND_XY: float = 0.80
_OP_Z_MAX: float = 0.86

# Fallback historique pour une plateforme non référencée. Les plateformes
# connues utilisent plutôt _ZERO_LOSS_BY_PLATFORM ci-dessous.
_OP_BOUND_ZERO_LOSS: float = 0.545

# ---------------------------------------------------------------------------
# Bornes zero-loss calibrées par plateforme.
# ---------------------------------------------------------------------------
# Valeurs dérivées du sweep WFW à la paire (T_min=1 N, T_max=58 N) :
#   - On cherche le plus grand rectangle ±(x,y) dont le coin reste dans
#     l'ellipse WFW (a, b) : (x/a)² + (y/b)² ≤ 1.
#   - Marge de sécurité : ~10 % sur chaque axe pour absorber le bruit
#     dû à l'échantillonnage discret du sweep (12×12×8).
#
# Format : {nom_plateforme: (x_bound, y_bound)}
_ZERO_LOSS_BY_PLATFORM: dict[str, tuple[float, float]] = {
    # WFW mesuré (±a X, ±b Y) → rectangle zéro-perte
    "700x560": (0.545, 0.545),   # WFW ±0.724 / ±0.855 — valeur historique
    "300x240": (0.400, 0.240),   # WFW ±0.568 / ±0.341
    "250x200": (0.280, 0.280),   # WFW ±0.341 / ±0.341
    "200x160": (0.090, 0.090),   # WFW ±0.114 / ±0.114
}

# Nom de la plateforme par défaut.
# Source unique de vérité utilisée par :
#   - Config.with_n() comme valeur par défaut de `platform`
#   - les scripts CLI (run_pipeline, run_wfw_3d, sweep_wfw, view_robot_3d)
#     pour aligner leur `--platform` default
#   - le suffixage conditionnel des fichiers de sortie
# Toute modification doit passer par ici — jamais dupliquée.
DEFAULT_PLATFORM: str = "300x240"

# ---------------------------------------------------------------------------
# Tailles de plateforme mobile (D-CONFIG-06).
# Format : (demi-étendue X, demi-étendue Y) en mètres.
# ---------------------------------------------------------------------------
_PLATFORM_MAP: dict[str, tuple[float, float]] = {
    "300x240": (0.150, 0.120),   # configuration prototype courante
    "250x200": (0.125, 0.100),   # variante compacte
    "700x560": (0.350, 0.280),   # plateforme de référence historique
    "560x560": (0.280, 0.280),   # carré compact (⚠ rang 5)
    "630x630": (0.315, 0.315),   # carré aire-équivalent (⚠ rang 5)
}

# Modèle de masse calibré sur les estimations historiques v3.0/v3.1 :
#   200×160 mm (0.032 m²) → 385 g
#   500×400 mm (0.200 m²) → 397 g
#   700×560 mm (0.392 m²) → 417 g
# Fit linéaire : masse = offset + pente × surface
# (interprétation : offset = overhead fixe, pente = masse surfacique)
_MASS_OFFSET_KG: float = 0.3765
_MASS_PER_M2_KG: float = 0.104


def _estimate_mass_kg(half_x: float, half_y: float) -> float:
    """
    Estime la masse de la plateforme à partir de ses demi-étendues.
    Approximation linéaire calibrée sur les données historiques.

    Limite : cette formule suppose une conception en treillis ouvert
    (overhead fixe dominant). Pour une plaque pleine, la masse serait
    proportionnelle à la surface et bien plus élevée.
    """
    surface_m2 = (2.0 * half_x) * (2.0 * half_y)
    return _MASS_OFFSET_KG + _MASS_PER_M2_KG * surface_m2

# Masse par défaut pour la plateforme de référence (DEFAULT_PLATFORM).
# Doit être défini APRÈS _estimate_mass_kg et DEFAULT_PLATFORM.
_DEFAULT_MASS_KG: float = _estimate_mass_kg(*_PLATFORM_MAP[DEFAULT_PLATFORM])


def _parse_platform_string(s: str) -> tuple[float, float]:
    """
    Parse une chaîne de plateforme vers (half_x, half_y) en mètres.

    Formats acceptés :
      - Nom connu : "560x560", "700x560", "630x630" (dans _PLATFORM_MAP)
      - Dimension libre : "WxH" en millimètres, avec séparateur
        'x', 'X' ou '×'. Ex. "400x300", "600X500", "560×560".

    Lève ValueError si la chaîne n'est pas reconnue ou si une
    dimension est ≤ 0.
    """
    if s in _PLATFORM_MAP:
        return _PLATFORM_MAP[s]
    for sep in ("x", "X", "×"):
        if sep in s:
            parts = s.split(sep)
            if len(parts) != 2:
                break
            try:
                w_mm = float(parts[0].strip())
                h_mm = float(parts[1].strip())
            except ValueError:
                break
            if w_mm <= 0 or h_mm <= 0:
                raise ValueError(
                    f"Dimensions de plateforme doivent être strictement "
                    f"positives, reçu {s!r}."
                )
            return (w_mm / 2000.0, h_mm / 2000.0)  # mm → m, demi-étendue
    raise ValueError(
        f"Format de plateforme invalide : {s!r}. Attendu un nom connu "
        f"{sorted(_PLATFORM_MAP.keys())} ou 'WxH' en mm (ex. '400x300')."
    )

# Table NSGA-II recommandée par taille de grille (D-CONFIG-02).
_NSGA_TABLE: dict[int, tuple[int, int]] = {
    3:  (30, 100),
    5:  (100, 300),
    7:  (200, 500),
    9:  (500, 1500),
    11: (800, 2000),
}


def _build_attaches(half_x: float, half_y: float) -> np.ndarray:
    """
    Construit la matrice attaches_B (3, 8) pour une plateforme donnée.

    Ordre des 8 attaches (identique à ANCRAGES_A_M) :
      1-4 : niveau z = +0.025 (haut)
      5-8 : niveau z = -0.025 (bas)
    """
    thickness_half = 0.025
    return np.array([
        [-half_x, +half_y, +thickness_half],
        [+half_x, +half_y, +thickness_half],
        [-half_x, -half_y, +thickness_half],
        [+half_x, -half_y, +thickness_half],
        [-half_x, +half_y, -thickness_half],
        [+half_x, +half_y, -thickness_half],
        [-half_x, -half_y, -thickness_half],
        [+half_x, -half_y, -thickness_half],
    ], dtype=float).T

# ===========================================================================
# Structure principale
# ===========================================================================
@dataclass(frozen=True)
class Config:
    """Conteneur immuable de tous les paramètres SP2 (v3.2)."""

    # --- Zone d'étude (SP1, gelée) ----------------------------------------
    parcelle_x: float = 2.5
    parcelle_y: float = 2.5

    # --- Grille par défaut (9×9, N=81, espacement 0.20 m) ----------------
    n_rangs: int = 9
    n_colonnes: int = 9
    esp_x: float = 0.20
    esp_y: float = 0.20

    # --- Géométrie robot --------------------------------------------------
    ancrages_A: np.ndarray = field(
        default_factory=lambda: ANCRAGES_A_M.copy(),
        compare=False,
    )
    attaches_B: np.ndarray = field(
        default_factory=lambda: _build_attaches(
            *_PLATFORM_MAP[DEFAULT_PLATFORM]
        ),
        compare=False,
    )

    # --- Mécanique / tensions --------------------------------------------
    masse_kg: float = _DEFAULT_MASS_KG
    T_min: float = 1.0
    T_max: float = 58.0

    # --- Limites opérationnelles -----------------------------------------
    x_min: float = -_OP_BOUND_XY
    x_max: float = +_OP_BOUND_XY
    y_min: float = -_OP_BOUND_XY
    y_max: float = +_OP_BOUND_XY
    z_min: float = 0.00
    z_max: float = _OP_Z_MAX

    # --- Orientation ------------------------------------------------------
    orientation_plateforme: str = "fixe"

    # --- Cinématique ------------------------------------------------------
    v_max: float = 0.045
    a_max: float = 0.03
    T_acc: float = 1.5
    T_dec: float = 1.5
    T_stabilisation: float = 2.0

    # --- Agronomie & vision -----------------------------------------------
    z_vol: float = 0.30
    hauteur_plants: float = 0.35
    offset_r0_sol: float = 0.20
    fov_camera: Tuple[float, float] = (62.2, 48.8)

    # --- Override optionnel de la hauteur caméra --------------------------
    z_absolu_r0_override: Optional[float] = None

    # --- NSGA-II (valeurs par défaut pour N=81) ---------------------------
    nsga_pop_size: int = 500
    nsga_n_gen: int = 1500
    nsga_seed: int = 42

    # ==================================================================
    # Propriétés dérivées
    # ==================================================================
    @property
    def N(self) -> int:
        return self.n_rangs * self.n_colonnes

    @property
    def z_absolu_sol(self) -> float:
        return self.hauteur_plants + self.z_vol

    @property
    def z_absolu_r0(self) -> float:
        if self.z_absolu_r0_override is not None:
            return float(self.z_absolu_r0_override)
        return self.z_absolu_sol - self.offset_r0_sol

    # ==================================================================
    # Validation — 8 règles
    # ==================================================================
    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        """
        Applique les 8 règles de validation dans l'ordre du cahier
        d'architecture. Lève `ValueError` avec un message préfixé [Rn]
        dès qu'une règle échoue. Ne retourne rien si tout est cohérent.

        Règles implémentées :
          R1 — T_min < T_max
          R2 — bornes op. ⊂ enveloppe des ancrages (XY)
          R3 — n_rangs, n_colonnes > 0
          R4 — étendue de la grille ⊆ limites opérationnelles
          R5 — orientation_plateforme == "fixe"
          R6 — z_absolu_r0 ∈ [z_min, z_max]
          R7 — fov_camera = tuple (float, float)
          R8 — v_max > 0 et a_max > 0 (ajoutée D-CONFIG-15)
        """
        if not (self.T_min < self.T_max):
            raise ValueError(
                f"[R1] T_min ({self.T_min}) doit être strictement inférieur "
                f"à T_max ({self.T_max})."
            )
        ax = self.ancrages_A[0, :]
        ay = self.ancrages_A[1, :]
        if not (ax.min() - _EPS <= self.x_min and self.x_max <= ax.max() + _EPS):
            raise ValueError(
                f"[R2] Limites X [{self.x_min}, {self.x_max}] hors enveloppe "
                f"des ancrages X [{ax.min()}, {ax.max()}]."
            )
        if not (ay.min() - _EPS <= self.y_min and self.y_max <= ay.max() + _EPS):
            raise ValueError(
                f"[R2] Limites Y [{self.y_min}, {self.y_max}] hors enveloppe "
                f"des ancrages Y [{ay.min()}, {ay.max()}]."
            )
        if self.n_rangs <= 0 or self.n_colonnes <= 0:
            raise ValueError(
                f"[R3] n_rangs ({self.n_rangs}) et n_colonnes "
                f"({self.n_colonnes}) doivent être strictement positifs."
            )
        half_x = (self.n_colonnes - 1) / 2.0 * self.esp_x
        half_y = (self.n_rangs - 1) / 2.0 * self.esp_y
        lim_x = max(abs(self.x_min), abs(self.x_max))
        lim_y = max(abs(self.y_min), abs(self.y_max))
        if half_x > lim_x + _EPS:
            raise ValueError(
                f"[R4] Étendue X de la grille (±{half_x:.3f} m) dépasse la "
                f"limite X (±{lim_x:.3f} m)."
            )
        if half_y > lim_y + _EPS:
            raise ValueError(
                f"[R4] Étendue Y de la grille (±{half_y:.3f} m) dépasse la "
                f"limite Y (±{lim_y:.3f} m)."
            )
        if self.orientation_plateforme != "fixe":
            raise ValueError(
                f"[R5] orientation_plateforme doit valoir 'fixe', "
                f"reçu '{self.orientation_plateforme}'."
            )
        z = self.z_absolu_r0
        if not (self.z_min - _EPS <= z <= self.z_max + _EPS):
            raise ValueError(
                f"[R6] z_absolu(R0) = {z:.3f} m hors de "
                f"[{self.z_min}, {self.z_max}] m. Référence : B2."
            )
        if not (
            isinstance(self.fov_camera, tuple)
            and len(self.fov_camera) == 2
            and all(isinstance(v, (int, float)) for v in self.fov_camera)
        ):
            raise ValueError(
                f"[R7] fov_camera doit être un tuple (FOV_h, FOV_v), "
                f"reçu {self.fov_camera!r}."
            )

        # --- R8 — Cinématique strictement positive (D-CONFIG-15) ---
        # a_max = 0 provoque une division par zéro dans le profil LSPB
        # (BLOC 6 et BLOC 9). v_max = 0 rend tout mouvement impossible.
        if self.v_max <= 0:
            raise ValueError(
                f"[R8] v_max doit être strictement positif, "
                f"reçu {self.v_max}."
            )
        if self.a_max <= 0:
            raise ValueError(
                f"[R8] a_max doit être strictement positif, "
                f"reçu {self.a_max}."
            )


    # ==================================================================
    # Journal d'hypothèses
    # ==================================================================
    def log_hypotheses(self) -> None:
        entries = [
            ("B1", f"masse = {self.masse_kg} kg",
             "GELÉE (v3.1)", "pesage prototype ; recalibrer si écart > 5 %"),
            ("B2", f"hauteur_plants = {self.hauteur_plants} m",
             "GELÉE (estimation)",
             "mesure JAS 20/30/40 ; recalcul si écart > 0.10 m"),
            ("B3", f"fov_camera = {self.fov_camera} deg",
             "GELÉE", "RGB seul"),
            ("B4", f"N = {self.N} (grille {self.n_rangs}×{self.n_colonnes}, "
                   f"esp = {self.esp_x:.3f} m)",
             "GELÉE (v3.2, dérivée sweep)",
             "sweep_wfw.py + D-CONFIG-01"),
            ("B5", f"offset R0/sol = {self.offset_r0_sol} m",
             "GELÉE", "schéma coté recommandé"),
        ]
        logger.info("Journal d'hypothèses Config (v3.2) :")
        for code, val, statut, correction in entries:
            logger.info("  [%s] %-50s statut=%s | plan=%s",
                        code, val, statut, correction)

    # ==================================================================
    # Classmethods — variantes
    # ==================================================================
    @classmethod
    def with_n(
        cls,
        n: int,
        zero_loss: bool = False,
        xy_bound: Optional[float] = None,
        x_bound: Optional[float] = None,
        y_bound: Optional[float] = None,
        platform: str = DEFAULT_PLATFORM,
        platform_size: Optional[tuple[float, float]] = None,
        platform_mass: Optional[float] = None,
        **overrides,
    ) -> "Config":
        """
        Config avec grille n×n couvrant une zone carrée ou rectangulaire.

        Bornes — ordre de priorité :
          1. x_bound ET y_bound → zone asymétrique
          2. x_bound seul       → zone symétrique (X = Y = x_bound)
          3. y_bound seul       → zone symétrique (X = Y = y_bound)
          4. xy_bound           → zone symétrique explicite
          5. défaut (zero_loss ou standard)

        Espacement dérivé par axe :
          esp_x = 2 × x_bound / (n − 1)
          esp_y = 2 × y_bound / (n − 1)

        Les paramètres NSGA-II sont tirés de la table _NSGA_TABLE.

        Exemples :
          Config.with_n(9)                          → ±0.80 m, esp=0.20 m
          Config.with_n(9, zero_loss=True)          → ±0.545 m, esp=0.136 m
          Config.with_n(9, xy_bound=0.30)           → ±0.30 m, esp=0.075 m
          Config.with_n(9, x_bound=0.30, y_bound=0.40) → rectangulaire

        zero_loss : bool
            Si True, utilise des bornes resserrées garantissant zéro
            rejet Cause B. Les bornes exactes dépendent de la plateforme
            (cf. _ZERO_LOSS_BY_PLATFORM) :
              700x560 : ±0.545 m
              300x240 : ±0.400 / ±0.240 m
              250x200 : ±0.280 m
              200x160 : ±0.090 m
            Plateforme inconnue → fallback sur ±0.545 m avec warning.

        platform : str
            Taille de la plateforme mobile. Formats acceptés :

        platform : str
            Taille de la plateforme mobile. Formats acceptés :
              - nom connu : "300x240" (défaut), "700x560" (référence v3.4),
                "250x200", "630x630"
                - dimension libre : "WxH" en mm, ex. "400x300", "350x280"
            ATTENTION : éviter les plateformes carrées (ratio ~1) avec
            des ancrages carrés — elles rendent W singulière (D-CONFIG-09).
        platform_size : tuple (half_x, half_y) en mètres, optionnel
            Override direct des demi-étendues. Priorité sur `platform`.
        platform_mass : float (kg), optionnel
            Override de la masse. Priorité sur l'estimation automatique.
        """
        if n < 3 or n % 2 == 0:
            raise ValueError(f"n doit être impair et ≥ 3, reçu {n}.")

        # --- Bornes par défaut selon mode + plateforme (D-CONFIG-12) ---
        if zero_loss:
            if platform in _ZERO_LOSS_BY_PLATFORM:
                default_xb, default_yb = _ZERO_LOSS_BY_PLATFORM[platform]
            else:
                logger.warning(
                    "Plateforme %s absente de _ZERO_LOSS_BY_PLATFORM. "
                    "Fallback sur la valeur générique ±%.3f m (calibrée "
                    "pour 700x560). Des rejets en Cause B sont possibles "
                    "sur les autres plateformes.",
                    platform, _OP_BOUND_ZERO_LOSS,
                )
                default_xb = default_yb = _OP_BOUND_ZERO_LOSS
        else:
            default_xb = default_yb = _OP_BOUND_XY


        # --- Résolution de la taille de plateforme (par priorité) ---
        # Priorité 1 : platform_size explicite (demi-étendues en m)
        # Priorité 2 : platform (nom connu OU "WxH" en mm)
        if platform_size is not None:
            half_x = float(platform_size[0])
            half_y = float(platform_size[1])
            if half_x <= 0 or half_y <= 0:
                raise ValueError(
                    f"platform_size doit être strictement positif, "
                    f"reçu {platform_size!r}."
                )
            platform_label = f"custom({half_x * 2000:.0f}x{half_y * 2000:.0f}mm)"
        else:
            half_x, half_y = _parse_platform_string(platform)
            platform_label = platform

        thickness_half = 0.025   # 50 mm / 2, constant

        # --- Garde-fou singularité (D-CONFIG-09) ---
        # Une plateforme carrée avec ancrages carrés rend W singulière
        # (rang 5 < 6) : le robot ne peut pas contrôler le moment de lacet.
        # Avertissement non bloquant — l'utilisateur peut toujours tester,
        # mais le pipeline échouera au BLOC 3 (WFW) ou BLOC 6 (coûts).
        if abs(half_x - half_y) < 1e-6 * max(half_x, half_y):
            logger.warning(
                "Plateforme carrée détectée (%.0f × %.0f mm). Avec des "
                "ancrages carrés, cette géométrie rend la matrice de "
                "structure W singulière (rang 5 < 6). Le robot ne peut "
                "pas contrôler le moment de lacet. Voir D-CONFIG-09. "
                "Utiliser un ratio d'aspect ≥ 1.20.",
                half_x * 2000, half_y * 2000,
            )

        # Reconstruire la matrice attaches_B (8, 3) → transpose (3, 8)
        new_attaches = np.array([
            [-half_x, +half_y, +thickness_half],
            [+half_x, +half_y, +thickness_half],
            [-half_x, -half_y, +thickness_half],
            [+half_x, -half_y, +thickness_half],
            [-half_x, +half_y, -thickness_half],
            [+half_x, +half_y, -thickness_half],
            [-half_x, -half_y, -thickness_half],
            [+half_x, -half_y, -thickness_half],
        ], dtype=float).T

        # --- Résolution de la masse ---
        # Priorité 1 : platform_mass explicite (kg)
        # Priorité 2 : estimation depuis les dimensions
        if platform_mass is not None:
            if platform_mass <= 0:
                raise ValueError(
                    f"platform_mass doit être strictement positif, "
                    f"reçu {platform_mass!r}."
                )
            new_mass = float(platform_mass)
            mass_label = "custom"
        else:
            new_mass = _estimate_mass_kg(half_x, half_y)
            mass_label = "estimée"

        logger.info(
            "Plateforme %s : demi-étendues (%.3f, %.3f) m, "
            "masse %s %.1f g.",
            platform_label, half_x, half_y, mass_label, new_mass * 1000,
        )

        # Résolution des bornes par priorité :
        #   1. x_bound ET y_bound → zone asymétrique explicite
        #   2. x_bound seul       → fallback symétrique (X = Y = x_bound)
        #   3. y_bound seul       → fallback symétrique (X = Y = y_bound)
        #   4. xy_bound           → zone symétrique explicite
        #   5. défaut             → standard OU zero_loss (par plateforme)
        if x_bound is not None and y_bound is not None:
            xb, yb = float(x_bound), float(y_bound)
        elif x_bound is not None:
            xb = yb = float(x_bound)
        elif y_bound is not None:
            xb = yb = float(y_bound)
        elif xy_bound is not None:
            xb = yb = float(xy_bound)
        else:
            xb, yb = default_xb, default_yb

        if xb <= 0 or yb <= 0:
            raise ValueError(
                f"Bornes doivent être strictement positives : "
                f"x_bound={xb}, y_bound={yb}."
            )

        esp_x = 2.0 * xb / (n - 1)
        esp_y = 2.0 * yb / (n - 1)

        pop_size, n_gen = _NSGA_TABLE.get(
            n, (max(30, n * n * 6), max(100, n * n * 18)),
        )
        defaults: dict = {
            "n_rangs": n, "n_colonnes": n,
            "esp_x": esp_x, "esp_y": esp_y,
            "x_min": -xb, "x_max": +xb,
            "y_min": -yb, "y_max": +yb,
            "z_min": 0.00, "z_max": _OP_Z_MAX,
            "nsga_pop_size": pop_size,
            "nsga_n_gen": n_gen,
            "attaches_B": new_attaches,
            "masse_kg": new_mass,
        }
        defaults.update(overrides)
        return cls(**defaults)

    @classmethod
    def legacy_v3_0(cls) -> "Config":
        """Config v3.0 — pour A/B testing historique."""
        return cls(
            n_rangs=9, n_colonnes=9,
            esp_x=0.25, esp_y=0.25,
            attaches_B=ATTACHES_B_M_V3_0.copy(),
            masse_kg=0.385,
            T_min=1.0, T_max=4.395,
            x_min=-1.00, x_max=+1.00,
            y_min=-1.00, y_max=+1.00,
            z_max=0.80,
            nsga_pop_size=100, nsga_n_gen=200,
        )


    @classmethod
    def legacy_v3_1(cls) -> "Config":
        """Config v3.1 — pour A/B testing vs v3.2."""
        return cls(
            n_rangs=7, n_colonnes=7,
            esp_x=0.25, esp_y=0.25,
            attaches_B=ATTACHES_B_M_V3_1.copy(),
            masse_kg=0.417,
            x_min=-0.75, x_max=+0.75,
            y_min=-0.75, y_max=+0.75,
            z_max=0.80,
            nsga_pop_size=400, nsga_n_gen=1000,
        )

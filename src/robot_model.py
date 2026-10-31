"""
BLOC 1 — Modèle du robot (RobotModel)
======================================

Référence : modèle géométrique du pipeline SP2 (BLOC 1) et Annexe B.1.
Portée    : primitives géométriques du CDPR 8 câbles pour une pose p,
            orientation plateforme FIXE (R = I).

Convention de signe (décision D-BLOC1-01, voir docs/DECISIONS.md)
-------------------------------------------------------------------
    U_i = (A_i − B_i) / ‖A_i − B_i‖

U_i pointe de l'attache mobile B_i vers l'ancrage fixe A_i, c'est-à-dire
DANS LE SENS DE LA FORCE exercée par le câble sur la plateforme (le câble
tire la plateforme vers son ancrage). C'est la seule convention compatible
avec T_i > 0 pour un câble réel.

Le torseur de la colonne i est :
    W[:, i] = [ U_i ; B_i(p) × U_i ]   (6 composantes)
où B_i(p) est le vecteur position de l'attache i dans R0, mesuré depuis
l'origine du repère fixe. Le moment B_i × U_i est donc le moment de la
force T_i·U_i appliquée en B_i, pris par rapport à l'origine de R0.

Équilibre statique :
    W(p)·T + W_ext = 0   ⇔   W(p)·T = −W_ext
avec W_ext = [F_ext ; M_ext], F_ext = (0, 0, −m·g), M_ext = (0, 0, 0).

Comparaison avec tension.pdf (Annexe B.1)
------------------------------------------
Le document SP1 utilise la formule `m_i = B_i × U_i`, reprise ici. En
revanche, la formule du §5 BLOC 1 pour le signe de U_i (`B_i − A_i`) a
été écartée : elle rend la tension compressive. La formulation alternative
`U_i' = −U_i` (i.e. B_i − A_i) produit `W' = −W` ; les deux formulations
sont donc équivalentes à un changement de signe global de T près. Le test
`test_alternative_formulation_is_negative` vérifie cette relation.
"""
from __future__ import annotations

import numpy as np

from src.config import Config

# Tolérance numérique globale pour la détection de singularité.
_NORM_EPS: float = 1e-9


class RobotModel:
    """
    Modèle géométrique du robot à câbles parallèle (8 câbles, 6 DOF statique).

    La classe est instanciée une fois par session de calcul avec la Config
    gelée. Chaque méthode publique prend une pose p dans R0 et retourne
    une ou plusieurs primitives géométriques.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        # Copies défensives : la Config est gelée mais les tableaux numpy
        # ne sont pas profondément immuables. On garde des copies privées
        # pour empêcher toute mutation accidentelle côté appelant.
        self.A = np.asarray(config.ancrages_A, dtype=float).copy()  # (3, 8)
        self.b = np.asarray(config.attaches_B, dtype=float).copy()  # (3, 8)

        # Vérifications de forme — échouent tôt si la Config est corrompue.
        # (if/raise plutôt que assert : les assert sont désactivés sous -O)
        if self.A.shape != (3, 8):
            raise ValueError(
                f"ancrages_A doit être (3, 8), reçu {self.A.shape}"
            )
        if self.b.shape != (3, 8):
            raise ValueError(
                f"attaches_B doit être (3, 8), reçu {self.b.shape}"
            )

    # ------------------------------------------------------------------
    # Primitives bas niveau
    # ------------------------------------------------------------------
    def attach_positions(self, p: np.ndarray) -> np.ndarray:
        """
        Calcule B_i(p) = p + b_i pour les 8 câbles (R = I ⇒ translation pure).

        Paramètres
        ----------
        p : ndarray (3,)
            Position de la plateforme dans R0, en mètres.

        Retour
        ------
        B : ndarray (3, 8)
            Colonne i = B_i(p).
        """
        p = np.asarray(p, dtype=float)
        if p.shape != (3,):
            raise ValueError(f"p doit être de shape (3,), reçu {p.shape}.")
        return p[:, None] + self.b

    def _raw_cable_vectors(self, p: np.ndarray) -> np.ndarray:
        """
        Vecteurs bruts v_i = A_i − B_i (non normalisés), shape (3, 8).
        Méthode privée : sert de brique commune à `cable_vectors` et
        `cable_lengths`, pour éviter deux appels redondants.
        """
        return self.A - self.attach_positions(p)

    def cable_lengths(self, p: np.ndarray) -> np.ndarray:
        """
        Longueurs de câble L_i = ‖A_i − B_i‖, shape (8,).
        """
        v = self._raw_cable_vectors(p)
        L = np.linalg.norm(v, axis=0)
        if np.any(L < _NORM_EPS):
            raise ValueError(
                "Longueur de câble nulle détectée — pose singulière. "
                "Le point de fonctionnement est confondu avec un ancrage."
            )
        return L

    def cable_vectors(self, p: np.ndarray) -> np.ndarray:
        """
        Vecteurs unitaires U_i = (A_i − B_i) / ‖A_i − B_i‖, shape (8, 3).

        Chaque ligne U[i, :] est le vecteur unitaire pointant de l'attache
        vers l'ancrage. C'est la direction de la force exercée par le
        câble sur la plateforme lorsque T_i > 0.
        """
        v = self._raw_cable_vectors(p)         # (3, 8)
        L = np.linalg.norm(v, axis=0)          # (8,)
        if np.any(L < _NORM_EPS):
            raise ValueError("Longueur de câble nulle détectée — pose singulière.")
        # Normalisation par colonne puis transposition : (3,8) → (8,3)
        return (v / L).T

    def structure_matrix(self, p: np.ndarray) -> np.ndarray:
        """
        Matrice de structure W (6, 8).

        Colonne i :
            W[:, i] = [ U_i (3) ; B_i(p) × U_i (3) ]

        où B_i(p) est exprimé dans R0 (origine = centre bas du cadre).

        Retour
        ------
        W : ndarray (6, 8)
        """
        B = self.attach_positions(p)           # (3, 8)
        U = self.cable_vectors(p)              # (8, 3)

        # Produit vectoriel B_i × U_i pour chaque câble.
        # np.cross(B.T, U) opère ligne à ligne : B.T est (8, 3), U est (8, 3),
        # le résultat est (8, 3) — ligne i = B_i × U_i.
        moments = np.cross(B.T, U)             # (8, 3)

        # Assemblage vertical : lignes 0-2 = forces, lignes 3-5 = moments.
        # On transpose U et moments pour passer de (8, 3) à (3, 8) et les
        # empiler par lignes.
        W = np.vstack([U.T, moments.T])        # (6, 8)
        return W

    # ------------------------------------------------------------------
    # Entrée principale
    # ------------------------------------------------------------------
    def evaluate(self, p: np.ndarray) -> dict:
        """
        Évalue toutes les primitives en une seule passe (évite 3 appels
        redondants à `attach_positions`).

        Retour
        ------
        dict avec clés :
            'U' : (8, 3) — vecteurs unitaires
            'L' : (8,)   — longueurs de câble
            'W' : (6, 8) — matrice de structure
            'B' : (3, 8) — positions des attaches (utile pour debug/tests)
        """
        B = self.attach_positions(p)           # (3, 8)
        v = self.A - B                         # (3, 8)
        L = np.linalg.norm(v, axis=0)          # (8,)
        if np.any(L < _NORM_EPS):
            raise ValueError("Longueur de câble nulle détectée — pose singulière.")
        U = (v / L).T                          # (8, 3)
        moments = np.cross(B.T, U)             # (8, 3)
        W = np.vstack([U.T, moments.T])        # (6, 8)
        return {"U": U, "L": L, "W": W, "B": B}

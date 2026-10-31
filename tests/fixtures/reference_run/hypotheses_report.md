# Rapport d'hypothèses — Projet Tandem SP2

**Version** : v3.2
**Statut de la configuration** : gelée

---

## Synthèse

| Code | Hypothèse | Valeur | Statut |
|---|---|---|---|
| B1 | Masse opérationnelle de la plateforme | 0.383988 kg | GELÉE (v3.1) |
| B2 | Hauteur des plants (fenêtre de service) | 0.35 m | GELÉE (estimation externe) |
| B3 | FOV caméra (paire unique) | (62.2, 48.8)° (RGB uniquement) | GELÉE (simplifiée v3.0) |
| B4 | Grille et effectif N | N = 9 (grille 3×3, marge 0.375 m/bord) | GELÉE (validée WFW v3.1) |
| B5 | Offset R0 / sol (pied de support) | 0.2 m | GELÉE |

---

## B1 — Masse opérationnelle de la plateforme

**Valeur retenue** : 0.383988 kg
**Statut** : GELÉE (v3.1)
**Source** : Recalibration masse surfacique (treillis ouvert, tube carbone Ø6.1 mm)

**Historique** :
- v3.0 : 0.385 kg (estimation grossière, sur-estimée)
- v3.1 : 0.417 kg (calibrée sur charge réelle)

**Plan de correction** :

> Peser la plateforme assemblée dès que le prototype est disponible ; si écart > 5 %, recalculer T_max et rejouer BLOC 3 et BLOC 6.

---

## B2 — Hauteur des plants (fenêtre de service)

**Valeur retenue** : 0.35 m
**Statut** : GELÉE (estimation externe)
**Source** : Fiches variétales haricot nain (Phaseolus vulgaris var. nana), médiane 30–50 cm

**Historique** :
- v3.0 : 0.30 m (implicite tomate, invalide)
- v3.1 : 0.35 m (haricot nain, estimation médiane)

**Plan de correction** :

> Mesurer à JAS 20, 30 et 40 dès que des plants réels sont disponibles. Si écart > 0.10 m, recalculer z_absolu_r0 et vérifier la marge vs z_max = 0.80 m.

---

## B3 — FOV caméra (paire unique)

**Valeur retenue** : (62.2, 48.8)° (RGB uniquement)
**Statut** : GELÉE (simplifiée v3.0)
**Source** : Raspberry Pi Camera v2 — fiche technique

**Historique** :
- v2.0 : anticipation d'un canal thermique (non retenu)
- v3.0 : canal thermique abandonné, RGB seul

**Plan de correction** :

> Aucune action prévue : FOV intrinsèque au capteur, vérifiable à réception.

---

## B4 — Grille et effectif N

**Valeur retenue** : N = 9 (grille 3×3, marge 0.375 m/bord)
**Statut** : GELÉE (validée WFW v3.1)
**Source** : Dérivation Annexe D de la Base d'architecture

**Historique** :
- v3.0 : N=81 (9×9, marge 0.25 m) — WFW rejetait 98.8 %
- v3.1 : N=49 (7×7, marge 0.375 m) — WFW 100 % via BLOC 10

**Plan de correction** :

> La validité de B4 a été confirmée par le test WFW exhaustif du BLOC 10 (re-vérification indépendante des 49 points). Aucune correction prévue.

---

## B5 — Offset R0 / sol (pied de support)

**Valeur retenue** : 0.2 m
**Statut** : GELÉE
**Source** : Confirmation physique : pied de 20 cm sous les 4 barres

**Historique** :
- v3.0 : 0.20 m, hypothèse de clairance non sourcée
- v3.0 : 0.20 m, confirmée par le montage réel

**Plan de correction** :

> Confirmation par schéma coté recommandée, non bloquante : le paramètre est isolé dans Config, toute correction reste localisée.

---

*Rapport généré automatiquement par BLOC 10 (src/validator.py).*

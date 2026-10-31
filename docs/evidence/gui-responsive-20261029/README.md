# Audit responsive de l’interface GUI — 2026-10-29

## Périmètre et protocole

L’application Streamlit a été vérifiée dans Chromium avec Playwright aux viewports **1024 × 1000 px** et **768 × 1000 px**. Les parcours couverts sont Accueil, Paramètres, Résultats (onglets Scène 3D et Pareto) et Historique. Les captures et métriques JSON sont dans ce répertoire.

Les vues Résultats et Historique ont utilisé une copie temporaire de `tests/fixtures/reference_run`, chargée comme `data/runs/audit_responsive_reference`. Cette fixture a été supprimée après l’audit. Aucun calcul scientifique n’a été lancé et ces captures ne sont pas de nouveaux résultats expérimentaux.

## Résultats observés

- À **1024 px**, la barre latérale reste ouverte et la zone principale mesure 724 px. À **768 px**, `initial_sidebar_state="auto"` replie la barre latérale et la zone principale mesure 767 px.
- Pour les dix états page/viewport mesurés, `documentScrollWidth` et `bodyScrollWidth` correspondent à la largeur du viewport ; `mainScrollWidth` correspond à `mainClientWidth` (724 px à 1024 px, 767 px à 768 px). Aucun défilement horizontal global n’est apparu.
- Les sept onglets Résultats nécessitent un défilement horizontal **interne à 1024 px** (`667 px` de contenu pour `564 px` visibles). Ils tiennent tous dans la largeur de l’onglet à **768 px** après repli de la barre latérale.
- Le tableau dense d’Historique conserve son défilement horizontal interne. Il ne fait pas déborder la page.
- Aucune erreur JavaScript de page ou de console n’a été relevée.

## Corrections apportées

1. La barre latérale passe de l’état forcé `expanded` à `auto` : elle reste ouverte à 1024 px et est repliée à 768 px, libérant l’espace principal.
2. Les métriques de prévisualisation Paramètres passent de quatre colonnes à deux ; l’empreinte occupe toute la largeur et la métrique d’altitude porte le libellé compact **Altitude absolue R0**, avec le libellé complet dans son aide contextuelle.
3. Les options de la scène 3D passent de trois colonnes à deux afin que **Baseline : zigzag** reste entièrement lisible.
4. La section de prévisualisation, qui répétait le numéro d’étape 3, est numérotée **4**.

## Captures

| Page | 1024 px | 768 px |
|---|---|---|
| Accueil | [Capture](1024-accueil.png) | [Capture](768-accueil.png) |
| Paramètres | [Capture](1024-parametres.png) | [Capture](768-parametres.png) |
| Résultats — Scène 3D | [Capture](1024-resultats-3d.png) | [Capture](768-resultats-3d.png) |
| Résultats — Pareto | [Capture](1024-resultats-pareto.png) | [Capture](768-resultats-pareto.png) |
| Historique | [Capture](1024-historique.png) | [Capture](768-historique.png) |

Les mesures détaillées, dont l’état du sidebar et la largeur du bandeau d’onglets, sont conservées dans [measurements.json](measurements.json).

## Limites de la vérification

Cette tranche qualifie les largeurs **1024 et 768 px** pour les quatre pages du parcours et ne constitue pas une certification de compatibilité pour les téléphones plus étroits. Elle ne remplace pas l’audit clavier/lecteur d’écran/impression, ni une qualification scientifique des données de référence.

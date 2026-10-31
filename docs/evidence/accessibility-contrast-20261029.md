# Preuve — contraste de la palette GUI

**Date :** 2026-10-29  
**Branche :** `feature/gui-improvement`  
**Périmètre :** tranche technique 21.4a — contraste de la présentation.

## Méthode

La luminance relative est calculée selon la formule WCAG 2.x, puis le ratio est
calculé entre la couleur la plus claire et la plus sombre. Le seuil retenu pour
le texte normal est `4.5:1` (WCAG AA).

## Défaut identifié

La couleur primaire précédente `#635BFF` produisait :

```text
#635BFF sur #F8FAFC : 4.49:1
```

Cette valeur était juste sous le seuil AA pour les liens et textes utilisant
l’accent sur le fond principal.

## Correction appliquée

La couleur `accent-primary` est maintenant `#5B52E8` :

```text
#5B52E8 sur #F8FAFC : 5.26:1
#5B52E8 sur #FFFFFF : 5.50:1
#FFFFFF sur #5B52E8 : 5.50:1
```

La correction concerne `app/theme.py` et ne modifie ni les calculs
scientifiques ni les artefacts de pipeline.

## Vérifications

Le test automatisé `test_primary_accent_meets_wcag_aa_for_text_on_light_surfaces`
contrôle les trois usages : accent sur le fond principal, accent sur une surface
blanche et texte blanc sur bouton primaire.

```text
20 passed
Ruff : All checks passed
Compilation Python : OK
```

Une vérification navigateur a également confirmé le démarrage de Streamlit et
le rendu de la navigation principale après la modification.

## Limite

Cette mesure couvre les tokens de palette explicitement utilisés par le thème.
Elle ne constitue pas encore un audit exhaustif du contraste de tous les
composants générés par Streamlit, Plotly et les tableaux interactifs.

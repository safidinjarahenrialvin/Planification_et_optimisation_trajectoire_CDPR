# Charte de présentation GUI — Tandem SP2

## Intention

L’interface doit ressembler à un projet final d’étudiant ingénieur : claire, technique, sobre et capable d’expliquer ses limites. Elle ne doit ni ressembler à un tableau de bord commercial, ni cacher la complexité scientifique derrière des formulations vagues.

## Principes visuels

- **Hiérarchie simple :** un titre, une question à laquelle la page répond, puis les preuves.
- **Couleurs sobres :** bleu nuit pour la structure, bleu technique pour les données, vert pour les éléments validés et orange/rouge uniquement pour les alertes.
- **KPI lisibles :** une unité dans chaque indicateur et aucune comparaison de grandeurs incompatibles sur un même axe.
- **Figures réelles :** les graphiques sont construits depuis les artefacts du run, jamais depuis des images décoratives qui pourraient diverger des tableaux.
- **Espace et regroupement :** les contrôles sont placés près de la visualisation qu’ils modifient.

## Principes éditoriaux

- Employer « exécution » ou « run » selon le contexte, mais ne pas alterner sans raison dans un même écran.
- Préférer « ce qu’il faut retenir », « couverture de la grille » et « vérification » aux titres purement internes comme « sortie du BLOC ».
- Toujours préciser la baseline, l’unité et le statut de validation.
- Expliquer un WARN au lieu de le transformer en résultat positif.
- Distinguer une preuve scientifique d’une illustration pédagogique.
- Utiliser des phrases courtes, naturelles et prononçables à l’oral.

## Structure recommandée d’une page

1. **Contexte :** pourquoi cette page existe.
2. **Résultat :** métriques principales et statut.
3. **Preuves :** figures, tableaux et artefacts.
4. **Interprétation :** ce que l’étudiant peut dire au jury.
5. **Limites :** ce qui reste à mesurer ou à confirmer.

## Critère d’acceptation

Une personne extérieure doit pouvoir comprendre l’objectif de la page en moins de trente secondes, retrouver l’unité des chiffres et savoir où vérifier la conclusion dans les artefacts du run.

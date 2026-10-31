# Scénario de soutenance — Tandem SP2

## Objectif

Ce scénario propose une démonstration de 7 minutes fondée sur un run explicitement
sélectionné. Lancez d’abord une exécution depuis **Paramètres**, ou copiez un run
complet produit par le terminal dans `data/runs/`, puis chargez-le depuis l’Accueil.
Les pages, figures et exports utilisent alors le même jeu d’artefacts.

Les chiffres sont affichés dynamiquement par l’application. Ils ne doivent pas être recopiés dans des diapositives sans vérifier le run présenté.

## Déroulé recommandé

| Temps | Page | Action | Message à faire passer |
|---:|---|---|---|
| 0:00–0:45 | Accueil | Présenter le problème et la synthèse | Le système arbitre entre temps et énergie, avec une baseline explicite. |
| 0:45–1:30 | Accueil | Lire les KPI et le tableau des stratégies | Les valeurs viennent des artefacts scientifiques, pas d’images préfabriquées. |
| 1:30–2:15 | Résultats / Validation | Montrer PASS, WARN et FAIL | Un WARN est expliqué ; il n’est pas masqué ni présenté comme un PASS. |
| 2:15–3:05 | Résultats / Pareto | Montrer le front de Pareto | Il n’existe pas une solution optimale unique sans préciser le critère. |
| 3:05–3:55 | Résultats / Trajectoire | Choisir `time_opt` puis `energy_opt` | La sélection de stratégie est synchronisée entre les vues. |
| 3:55–4:55 | Résultats / Trajectoire | Manipuler la scène 3D et activer l’animation pédagogique | L’animation illustre un profil réel ; elle ne constitue pas une nouvelle simulation. |
| 4:55–5:40 | Historique | Montrer les runs disponibles | Deux runs ne sont comparables que si leurs configurations sont identifiées. |
| 5:40–7:00 | Résultats / Validation > Preuves techniques | Télécharger le rapport (`rapport.md`) | Chaque conclusion est traçable vers des CSV, JSON et la configuration du run. |

## Formulation de conclusion

> La plateforme fournit une chaîne complète entre configuration, génération des points, filtrage WFW/FOV, optimisation, validation et présentation. La décision finale est formulée comme un compromis temps-énergie et reste accompagnée de ses hypothèses et limites.

## Questions probables du jury

### Pourquoi ne pas choisir uniquement la trajectoire la plus rapide ?

Parce que le problème est multiobjectif. La trajectoire la plus rapide peut consommer davantage d’énergie. Le front de Pareto permet de présenter les solutions non dominées et de rendre le compromis explicite.

### Les résultats sont-ils reproductibles ?

Oui, dans le périmètre du run présenté : la configuration effective, l’empreinte, la graine et les artefacts CSV/JSON sont conservés. Le rapport jury est généré à partir de ces fichiers.

### Que signifie le statut WARN ?

Il faut lire le détail du contrôle. Un front Pareto contenant moins de trois
compromis temps-énergie distincts produit un WARN. À partir de trois compromis
distincts, un front sans solution dominée est PASS. Une solution dominée reste
un FAIL, quelle que soit la cardinalité du front.

### L’animation prouve-t-elle la faisabilité mécanique ?

Non. Elle est une visualisation pédagogique des positions du profil validé. Les preuves restent les contrôles scientifiques, la matrice des coûts, les profils et les rapports de validation.

### Que faudrait-il faire pour une étude de production ?

Augmenter les paramètres d’optimisation, confirmer les hypothèses physiques par des mesures et rejouer le pipeline avec une configuration documentée. Les résultats du mode rapide sont une démonstration reproductible, pas une qualification industrielle.

## Règles de présentation

- Ne pas annoncer un gain sans préciser la baseline et l’unité.
- Ne pas masquer un WARN ou une alerte FOV.
- Ne pas présenter l’animation comme une preuve indépendante.
- Toujours identifier explicitement le run présenté, sa configuration et sa graine.
- En cas de question, ouvrir le rapport jury et remonter à l’artefact source.

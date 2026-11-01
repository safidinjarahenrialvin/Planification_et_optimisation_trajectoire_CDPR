# Organigrammes de la chaîne logicielle — Partie 3

Ces organigrammes représentent l’architecture logicielle du projet Tandem SP2 au niveau des quatre blocs fonctionnels retenus pour la partie 3 du mémoire. Ils sont dérivés de l’orchestration de `PipelineService` et des modules scientifiques de `src/`.

## Chaîne globale

- `chaine_logicielle_4_blocs.mmd` / `.png` : vue synthétique de la chaîne complète.
- Entrée : paramètres physiques du robot et mission d’acquisition.
- Sortie : trajectoires validées, indicateurs de performance, rapports et figures.

## Correspondance avec le mémoire

| Figure | Section | Fonction | Principaux modules |
|---|---:|---|---|
| `bloc_1_preparation_donnees` | 3.4 | Valider la configuration et construire les objets scientifiques partagés | `Config`, `ConfigurationService`, `RobotModel`, `WFW` |
| `bloc_2_espace_travail` | 3.5 | Générer les points et conserver ceux qui sont géométriquement et mécaniquement faisables | `PointGenerator`, `PointFilter`, `WFW` |
| `bloc_3_optimisation_trajectoires` | 3.6 | Construire la matrice des coûts et rechercher les compromis temps–énergie | `CostCalculator`, `Optimizer`, NSGA-II |
| `bloc_4_validation_profilage_comparaison` | 3.7 | Profiler, contrôler, comparer à la référence et produire les résultats | `TrajectoryExtractor`, `TrajectoryProfiler`, `Validator`, `Comparator` |

## Légendes proposées

- **Figure 3.x — Vue synthétique de la chaîne logicielle de planification des trajectoires du robot Tandem.**
- **Figure 3.x — Organigramme du bloc 1 : préparation des données et construction du modèle de calcul.**
- **Figure 3.x — Organigramme du bloc 2 : génération des points de vue et filtrage par l’espace de travail faisable.**
- **Figure 3.x — Organigramme du bloc 3 : calcul des coûts de transition et optimisation multiobjectif par NSGA-II.**
- **Figure 3.x — Organigramme du bloc 4 : profilage temporel, validation numérique et comparaison avec la baseline.**

## Logique de lecture à utiliser dans le rapport

Chaque bloc doit être présenté selon la même structure : **objectif → entrées → traitements → décisions de contrôle → sorties → transition vers le bloc suivant**. Cette régularité permet de distinguer clairement la méthode logicielle des résultats numériques présentés dans les sections suivantes.

Les fichiers `.mmd` constituent les sources modifiables. Les fichiers `.png` sont les rendus prêts à être insérés dans le rapport. Les décisions `PASS`, `WARN` et `FAIL` du bloc 4 correspondent au comportement effectivement implémenté par `Validator`; elles ne représentent pas une appréciation subjective des résultats.

## Exemple d’insertion LaTeX

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=\textwidth]{figures/chaine_logicielle_4_blocs.png}
    \caption{Vue synthétique de la chaîne logicielle de planification des trajectoires du robot Tandem.}
    \label{fig:chaine_logicielle_4_blocs}
\end{figure}
```

Pour les quatre organigrammes détaillés, utiliser une largeur comprise entre `0.70\textwidth` et `0.90\textwidth`, ou les placer en annexe si la hauteur rend la lecture difficile dans le corps du chapitre.

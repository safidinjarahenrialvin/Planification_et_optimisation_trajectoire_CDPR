# Plan directeur d’amélioration de Tandem SP2
## Ajout d’une interface graphique, visualisation 3D et analyse interactive

**Projet concerné :** `tandem_sp2`
**Version de départ :** pipeline scientifique actuel, blocs 0 à 11
**Objectif :** améliorer le projet existant sans réécrire ni dégrader les algorithmes validés
**Interface retenue pour la première version :** application Web locale Python avec Streamlit et Plotly
**Public visé :** étudiant, encadrant, ingénieur, futur repreneur et utilisateur non spécialiste du terminal

---

## 1. Décision principale

Le projet existant sera conservé comme base scientifique. Nous n’allons pas créer une deuxième implémentation indépendante des blocs 0 à 11.

Nous ajouterons progressivement une couche d’application au-dessus du code actuel :

```text
Interface graphique
        ↓
Services d’application
        ↓
Orchestration du pipeline
        ↓
Algorithmes scientifiques existants
        ↓
CSV, JSON, figures et rapports
```

La règle fondamentale sera :

> L’interface peut appeler les algorithmes, mais les algorithmes ne doivent pas dépendre de l’interface.

Ainsi, le même moteur pourra continuer à être utilisé depuis :

- le terminal ;
- l’interface graphique ;
- les tests automatisés ;
- de futurs scripts ;
- une éventuelle API ultérieure.

---

## 2. Pourquoi cette stratégie est la plus sûre

Le projet actuel contient déjà les éléments scientifiques essentiels :

- configuration ;
- modèle géométrique ;
- cinématique ;
- calcul WFW ;
- génération et filtrage des points ;
- calcul des coûts ;
- optimisation NSGA-II ;
- extraction des trajectoires ;
- profilage cinématique ;
- validation ;
- comparaison avec une baseline.

Ces blocs ont déjà été testés, exécutés et documentés dans les rapports des BLOCs 0 à 11.

Une réécriture simultanée du moteur et de l’interface augmenterait le risque de modifier involontairement les résultats scientifiques. La méthode retenue est donc une migration contrôlée :

```text
stabiliser
    ↓
extraire les services
    ↓
tester la non-régression
    ↓
ajouter l’interface
    ↓
étendre les visualisations
```

---

## 3. Sources techniques retenues

Le choix des technologies et des pratiques de réalisation doit être fondé sur les sources suivantes.

### Streamlit

La documentation officielle indique que Streamlit réexécute le script lors des interactions. Les variables ordinaires ne sont donc pas suffisantes pour conserver une configuration ou un résultat entre deux interactions. `st.session_state` est prévu pour conserver l’état d’une session et persiste également entre les pages d’une application multipage [1].

La documentation officielle recommande `st.Page` et `st.navigation` pour organiser une application multipage et exécuter ses pages depuis un point d’entrée commun [2].

Les formulaires Streamlit regroupent les widgets et transmettent leurs valeurs lors de la soumission. Ils sont donc adaptés à la saisie groupée des paramètres de configuration [3].

Streamlit distingue `st.cache_data`, adapté aux données sérialisables comme les DataFrames, et `st.cache_resource`, adapté aux ressources partagées. Cette distinction impose de ne pas mettre aveuglément l’exécution complète du pipeline dans un cache [4].

Streamlit fournit également `AppTest` pour tester une application comme un utilisateur simulé avec pytest [5].

### Plotly

Plotly fournit des graphiques 3D interactifs en Python [6]. Streamlit sait afficher directement un objet Plotly avec `st.plotly_chart` et peut gérer des sélections interactives de points [7]. Ces capacités correspondent directement au visualiseur 3D déjà présent dans `src/robot_3d_viewer.py`.

### Packaging Python

Le guide officiel PyPA recommande d’utiliser `pyproject.toml` pour déclarer le système de construction, les métadonnées du projet et les dépendances. Il permet également de séparer des dépendances facultatives, par exemple une dépendance GUI [8].

### Tests

La documentation pytest décrit les fixtures comme des mécanismes réutilisables de préparation des tests et permet de paramétrer les tests pour couvrir plusieurs configurations [9].

---

## 4. Invariants à protéger avant toute modification

Avant d’ajouter une interface, nous devons définir ce qui ne doit pas changer sans décision scientifique explicite.

### Invariants numériques

Pour une même configuration, une même graine et les mêmes options, nous devons préserver :

- `N = n_rangs × n_colonnes` ;
- les coordonnées des points générés ;
- la classification WFW des points ;
- la structure de la matrice des coûts ;
- les unités de temps, distance, tension et énergie ;
- les bornes `T_min`, `T_max`, `v_max` et `a_max` ;
- les règles de dominance Pareto ;
- la structure des trajectoires ;
- les contrôles du BLOC 10 ;
- la convention de la baseline du BLOC 11.

### Invariants de fichiers

Les noms et colonnes des fichiers existants doivent rester compatibles tant qu’une migration documentée n’est pas décidée :

```text
points_generes.csv
points_filtres.csv
cost_matrix.csv
solutions_pareto.csv
trajectories.csv
trajectories_summary.csv
profiles.csv
validation_report.json
comparison.csv
```

### Invariants d’architecture

Les modules scientifiques de `src/` ne doivent pas importer Streamlit.

Un import comme celui-ci sera interdit dans les algorithmes :

```python
import streamlit as st
```

La GUI pourra importer `src`, mais l’inverse ne sera pas autorisé.

---

## 5. Architecture cible

La première version peut conserver la majorité des fichiers actuels, puis ajouter les couches suivantes :

```text
tandem_sp2/
├── src/
│   ├── config.py
│   ├── robot_model.py
│   ├── kinematics.py
│   ├── wfw.py
│   ├── point_generator.py
│   ├── point_filter.py
│   ├── cost_calculator.py
│   ├── optimizer.py
│   ├── extractor.py
│   ├── profiler.py
│   ├── validator.py
│   ├── comparator.py
│   └── robot_3d_viewer.py
│
├── app/
│   ├── streamlit_app.py
│   ├── pages/
│   │   ├── home.py
│   │   ├── parameters.py
│   │   ├── pipeline.py
│   │   ├── robot_3d.py
│   │   ├── statistics.py
│   │   ├── pareto.py
│   │   ├── trajectories.py
│   │   ├── validation.py
│   │   ├── comparison.py
│   │   ├── assumptions.py
│   │   └── exports.py
│   ├── components/
│   │   ├── status.py
│   │   ├── metrics.py
│   │   ├── tables.py
│   │   └── errors.py
│   └── state.py
│
├── services/
│   ├── pipeline_service.py
│   ├── configuration_service.py
│   ├── result_service.py
│   ├── run_registry.py
│   └── progress.py
│
├── visualization/
│   ├── robot_scene.py
│   ├── plant_scene.py
│   ├── pareto_plots.py
│   ├── trajectory_plots.py
│   └── statistics_plots.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── gui/
│
├── data/
│   └── runs/
│
└── docs/
```

Cette organisation est une cible progressive. Il ne faut pas déplacer tous les fichiers en une seule opération sans tests intermédiaires.

---

## 6. Rôles des nouvelles couches

### `PipelineService`

Le service orchestre les BLOCs 4 à 11 et expose une fonction appelable par le terminal comme par la GUI.

Il ne doit pas contenir de widget Streamlit.

Interface conceptuelle :

```python
class PipelineService:
    def run(self, request: PipelineRequest) -> PipelineResult:
        ...
```

### `ConfigurationService`

Il transforme les valeurs saisies par l’utilisateur en un objet `Config` validé.

Il doit :

- vérifier les types ;
- vérifier les bornes ;
- expliquer les erreurs ;
- produire une empreinte stable ;
- refuser une configuration incohérente avant les calculs longs.

### `ResultService`

Il charge les CSV, JSON et figures d’un run donné et fournit des objets prêts à afficher.

La GUI ne doit pas reconstruire les résultats directement à partir de fichiers dispersés dans plusieurs dossiers.

### `RunRegistry`

Il enregistre les exécutions et associe :

```text
run_id
configuration
empreinte
date
statut
répertoire de sortie
```

### Couche `visualization`

Elle construit les figures Plotly ou les données de figures sans connaître les widgets de la GUI.

Cela permet de tester une figure sans lancer Streamlit.

---

## 7. Organisation des exécutions

Les résultats ne doivent plus être mélangés dans un seul répertoire lorsqu’un utilisateur lance plusieurs configurations.

La cible est :

```text
data/runs/
└── run_YYYYMMDD_HHMMSS_<hash>/
    ├── config.json
    ├── metadata.json
    ├── .config_hash
    ├── points_generes.csv
    ├── points_filtres.csv
    ├── cost_matrix.csv
    ├── solutions_pareto.csv
    ├── trajectories.csv
    ├── profiles.csv
    ├── validation_report.json
    ├── comparison.csv
    └── figures/
```

La configuration effective doit être sauvegardée avec les résultats. Un résultat sans sa configuration est scientifiquement incomplet.

Le mécanisme existant `.config_hash` doit être conservé et intégré au registre des runs.

---

# Plan de réalisation par phases

## Phase 0 — Geler la version scientifique de référence

### Objectif

Créer une référence incontestable avant de modifier l’architecture.

### Actions

1. Vérifier l’état du dépôt.
2. Exécuter les tests rapides.
3. Exécuter le smoke test du pipeline.
4. Conserver les rapports et les métriques de référence.
5. Créer un tag Git de référence, par exemple :

```text
v1.0-scientific-stable
```

6. Documenter la version de Python et les dépendances.

### Livrables

```text
docs/baseline_reference.md
data/reference_run/
```

### Critères d’acceptation

- les tests rapides réussissent ;
- le pipeline rapide produit tous les fichiers attendus ;
- `validation_report.json` est lisible ;
- le diagnostic du comparateur est conservé ;
- le tag Git est créé ;
- aucune modification GUI n’est encore mélangée à cette référence.

### Règle d’arrêt

Si la référence n’est pas reproductible, aucune interface ne doit être développée. Il faut d’abord corriger ou documenter le problème scientifique.

---

## Phase 1 — Cartographier les points d’entrée

### Objectif

Identifier précisément ce qui doit être réutilisé et ce qui doit être extrait de `scripts/run_pipeline.py`.

### Actions

1. Lister les fonctions d’orchestration.
2. Identifier les paramètres réellement utilisés.
3. Identifier les sorties de chaque bloc.
4. Repérer les appels qui écrivent directement dans le terminal.
5. Repérer les dépendances au répertoire courant.
6. Repérer les fonctions qui appellent `sys.exit` ou lèvent des exceptions destinées à la CLI.

### Livrable

```text
docs/architecture_current.md
```

Ce document doit contenir un tableau :

```text
étape | entrée | traitement | sortie | exception | fichier producteur
```

### Critères d’acceptation

Un développeur qui ne connaît pas le projet doit pouvoir répondre :

- comment créer une configuration ;
- comment lancer chaque bloc ;
- quels fichiers sont nécessaires ;
- quels fichiers sont produits ;
- quelle exception signifie quelle erreur.

---

## Phase 2 — Créer les objets de requête et de résultat

### Objectif

Remplacer les paramètres dispersés par des structures explicites.

### Objets recommandés

```python
@dataclass(frozen=True)
class PipelineOptions:
    fast: bool = False
    K: int = 10
    pop_size: int = 100
    n_gen: int = 200
    seed: int = 42
    resume: bool = False
```

```python
@dataclass(frozen=True)
class PipelineRequest:
    config: Config
    options: PipelineOptions
    output_dir: Path
```

```python
@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    output_dir: Path
    validation_status: str
    files: dict[str, Path]
    metrics: dict[str, object]
```

Les noms et types exacts pourront être adaptés au code existant. L’important est que les entrées et sorties soient explicites.

### Critères d’acceptation

- le service peut être appelé sans Streamlit ;
- les tests peuvent construire une requête directement ;
- les options ne dépendent pas d’un objet `argparse.Namespace` ;
- les résultats ne dépendent pas d’un affichage terminal.

---

## Phase 3 — Extraire `PipelineService` sans modifier les algorithmes

### Objectif

Faire appeler les mêmes classes scientifiques par un service commun.

### Ordre de réalisation

1. extraire le BLOC 4 ;
2. vérifier ses sorties ;
3. extraire le BLOC 5 ;
4. vérifier ses sorties ;
5. continuer jusqu’au BLOC 11 ;
6. conserver le script CLI comme adaptateur du service.

Architecture intermédiaire :

```text
scripts/run_pipeline.py
        ↓
PipelineService
        ↓
BLOCs scientifiques
```

### Règle importante

Pendant cette phase, il ne faut pas modifier les formules, les tolérances ou les décisions de l’algorithme sauf si une anomalie documentée est découverte.

Une correction scientifique doit avoir :

- une justification ;
- un test avant/après ;
- une mise à jour de la documentation ;
- une comparaison à la référence.

### Critères d’acceptation

Pour le même run de référence :

- les fichiers existent aux mêmes étapes ;
- les colonnes sont identiques ;
- les statuts de validation sont identiques ou expliqués ;
- les métriques sont identiques à la tolérance numérique documentée ;
- le CLI utilise le service au lieu de dupliquer la logique.

---

## Phase 4 — Renforcer la configuration et sa validation

### Objectif

Permettre à la GUI de modifier les paramètres sans créer de configuration invalide.

### Actions

1. Séparer les paramètres géométriques, mécaniques, cinématiques et optimisation.
2. Ajouter une validation avant construction de `Config`.
3. Définir les unités dans les libellés et les noms de variables.
4. Produire un message lisible pour chaque erreur.
5. Sérialiser la configuration effective en JSON.
6. Calculer son empreinte.

### Exemples de contrôles

```text
n_rangs > 0
n_colonnes > 0
T_min < T_max
v_max > 0
a_max > 0
masse_kg > 0
K > 0
pop_size > 0
n_gen > 0
```

Il faut aussi reprendre les contraintes métier déjà présentes dans `Config`.

### Critères d’acceptation

Une configuration incorrecte est refusée avant le BLOC 4 et explique précisément :

```text
paramètre
valeur reçue
contrainte attendue
correction proposée
```

---

## Phase 5 — Construire le squelette Streamlit

### Objectif

Créer une interface minimale sans encore exposer tout le pipeline.

### Structure

```text
app/streamlit_app.py
app/pages/home.py
app/pages/parameters.py
app/state.py
```

La navigation multipage utilisera `st.Page` et `st.navigation`, conformément à la documentation Streamlit [2].

### Pages initiales

- Accueil ;
- Paramètres ;
- Résultats.

### Gestion de l’état

`st.session_state` conservera uniquement l’état utile à la session :

```text
run_id courant
configuration saisie
statut du dernier run
sélection de trajectoire
filtres d’affichage
```

Il ne faut pas y stocker aveuglément tous les objets lourds du pipeline.

### Critères d’acceptation

- l’application démarre avec `streamlit run app/streamlit_app.py` ;
- les pages sont accessibles ;
- un changement de page ne perd pas la configuration saisie ;
- un rafraîchissement ne déclenche pas automatiquement un nouveau calcul scientifique.

---

## Phase 6 — Ajouter le formulaire de paramètres

### Objectif

Remplacer la saisie des options dans le terminal par un formulaire contrôlé.

Les widgets seront regroupés dans des formulaires Streamlit afin que les valeurs soient validées et appliquées lors d’une soumission explicite [3].

### Sections du formulaire

#### Géométrie

- rangs ;
- colonnes ;
- espacements ;
- bornes spatiales ;
- hauteur de référence ;
- offset R0-sol.

#### Mécanique

- masse ;
- tension minimale ;
- tension maximale ;
- géométrie de la plateforme ;
- géométrie des ancrages.

#### Cinématique

- vitesse maximale ;
- accélération maximale ;
- fréquence ou pas d’échantillonnage ;
- stabilisation.

#### Optimisation

- population ;
- générations ;
- graine ;
- nombre de sous-pas ;
- mode rapide.

### Critères d’acceptation

- les unités sont visibles ;
- les valeurs par défaut viennent de la configuration actuelle ;
- une valeur invalide est bloquée ;
- le bouton « Appliquer » ne lance pas encore le pipeline complet ;
- le bouton « Lancer l’analyse » lance explicitement le calcul.

---

## Phase 7 — Brancher l’exécution du pipeline

### Objectif

Lancer `PipelineService` depuis la GUI tout en gardant une interface utilisable.

### Règles

1. Chaque exécution reçoit un `run_id`.
2. Les résultats vont dans un nouveau répertoire.
3. Les erreurs sont capturées et traduites en messages compréhensibles.
4. Les logs détaillés sont conservés dans le répertoire du run.
5. Le dernier run n’est jamais écrasé silencieusement.

### Exécution longue

Le pipeline peut durer longtemps. L’interface ne doit pas paraître bloquée.

La première version peut utiliser une exécution séparée et un fichier ou une structure de progression. Une solution plus simple peut d’abord afficher un état « calcul en cours », puis être améliorée avec une progression par bloc.

La progression minimale doit indiquer :

```text
BLOC courant
état
temps écoulé
message d’erreur éventuel
```

### À ne pas faire

Ne pas décorer l’exécution complète avec `st.cache_data` comme si elle était une simple lecture de DataFrame. Le pipeline écrit des fichiers et possède des effets de bord. Le cache doit être réservé aux lectures ou transformations déterministes contrôlées [4].

### Critères d’acceptation

- le bouton lance une exécution complète ;
- la GUI récupère le statut final ;
- un échec affiche le bloc et l’erreur ;
- un run terminé peut être rechargé sans relancer le calcul ;
- les résultats sont isolés par run.

---

## Phase 8 — Intégrer les résultats existants

### Objectif

Afficher les fichiers du pipeline sans recalcul inutile.

### Pages

#### Accueil

Afficher :

- run courant ;
- statut global ;
- nombre de points ;
- nombre de solutions Pareto ;
- trajectoire sélectionnée ;
- dernière erreur ou avertissement.

#### Statistiques

Afficher :

- points générés ;
- points retenus ;
- points rejetés ;
- taux de faisabilité ;
- tailles et plages des coûts ;
- temps d’exécution par bloc si disponible.

#### Pareto

Afficher `solutions_pareto.csv` sous forme de graphique interactif temps/énergie.

#### Trajectoires

Afficher les trois trajectoires et leurs résumés.

#### Profils

Afficher les profils de vitesse, position et composantes de vitesse.

#### Validation

Afficher les checks `PASS`, `WARN`, `FAIL` provenant de `validation_report.json`.

#### Comparaison

Afficher `comparison.csv`, la baseline et le diagnostic du BLOC 11.

#### Hypothèses

Afficher B1 à B5 à partir du rapport JSON ou Markdown.

### Critères d’acceptation

Chaque page doit fonctionner en rechargeant un run existant, sans lancer de nouveau calcul.

---

## Phase 9 — Intégrer la visualisation 3D du robot

### Objectif

Transformer le visualiseur Plotly actuel en composant réutilisable.

Le module existant `src/robot_3d_viewer.py` représente déjà :

- le bâti ;
- les pieds ;
- les câbles ;
- la plateforme ;
- les points de vue ;
- une trajectoire optionnelle.

Il doit être conservé comme base et progressivement découplé de l’écriture HTML si nécessaire.

### Couches d’affichage

L’interface doit pouvoir activer ou désactiver :

- bâti ;
- pieds ;
- câbles ;
- plateforme ;
- points de vue ;
- plants ;
- points rejetés ;
- trajectoire ;
- centre.

### Plants

La première version des plants doit rester légère :

- tige simplifiée ;
- feuilles simplifiées ;
- hauteur provenant de la configuration ;
- position provenant des points de la grille.

Il ne faut pas commencer par un modèle 3D détaillé qui ralentirait l’interface et détournerait l’attention du modèle scientifique.

### Interaction

La figure Plotly doit permettre :

- rotation ;
- zoom ;
- déplacement ;
- affichage des coordonnées au survol ;
- sélection de la trajectoire.

`st.plotly_chart` permet d’afficher la figure et de gérer les sélections interactives lorsque cela est nécessaire [7].

### Critères d’acceptation

- la scène 3D s’affiche sans calcul de pipeline ;
- la plateforme respecte les coordonnées du modèle ;
- les câbles utilisent les mêmes attaches et ancrages que `RobotModel` ;
- la caméra est manipulable ;
- les plants sont visuellement distincts de la plateforme ;
- une trajectoire sélectionnée peut être affichée.

---

## Phase 10 — Animation et inspection d’une trajectoire

### Objectif

Ajouter une visualisation temporelle après stabilisation de la version statique.

### Étapes

1. sélectionner `time_opt`, `energy_opt` ou `compromise` ;
2. charger le profil correspondant ;
3. choisir un instant ;
4. calculer la pose affichée ;
5. afficher la plateforme et les câbles ;
6. afficher le waypoint courant ;
7. afficher `t`, `|v|` et le segment.

### Décision importante

L’animation doit utiliser les résultats du BLOC 9 et non inventer une nouvelle loi de mouvement dans l’interface.

La GUI visualise le profil ; elle ne remplace pas `TrajectoryProfiler`.

### Critères d’acceptation

- l’animation ne modifie aucun CSV ;
- elle respecte le temps global du profil ;
- elle affiche une alerte si une donnée est manquante ;
- elle conserve une option d’affichage statique pour les ordinateurs moins puissants.

---

## Phase 11 — Ajouter les analyses statistiques

### Objectif

Rendre les résultats compréhensibles sans obliger l’utilisateur à ouvrir les CSV.

### Analyses prévues

#### Points

- nombre total ;
- nombre retenu ;
- nombre rejeté par cause ;
- répartition par ligne et colonne ;
- étendue spatiale ;
- taux de couverture.

#### Coûts

- minimum, maximum, moyenne et médiane ;
- histogramme des temps ;
- histogramme des énergies ;
- taux de paires infaisables ;
- asymétrie maximale ;
- distribution des distances.

#### Pareto

- nombre de solutions ;
- plages temps/énergie ;
- solutions sélectionnées ;
- densité du front ;
- compromis relatif.

#### Trajectoires

- temps mouvement ;
- temps stabilisation ;
- temps total ;
- énergie ;
- distance ;
- nombre de waypoints ;
- gain par rapport à la baseline.

### Règle scientifique

Les statistiques descriptives ne doivent pas modifier la décision du solveur. Elles servent à analyser et expliquer les résultats.

### Critères d’acceptation

Chaque statistique doit indiquer son unité et sa source de données.

---

## Phase 12 — Tests de non-régression du moteur

### Objectif

Prouver que l’ajout de la GUI n’a pas dégradé les résultats scientifiques.

### Tests unitaires

Tester séparément :

- validation de configuration ;
- génération de points ;
- cinématique ;
- WFW ;
- calcul d’un coût ;
- dominance ;
- extraction ;
- profilage ;
- validation ;
- construction de la baseline.

### Tests d’intégration

Tester le pipeline rapide avec une sortie temporaire.

### Tests de régression

Comparer un nouveau run à la référence selon des tolérances documentées :

```text
colonnes identiques
nombre de lignes attendu
faisabilité identique
écart numérique maximal
statut de validation
```

### Fixtures pytest

Les fixtures pytest doivent fournir :

- une configuration minimale ;
- un robot ;
- un WFW ;
- des DataFrames synthétiques ;
- un répertoire temporaire ;
- une référence de petits résultats.

Les fixtures sont adaptées à cette organisation car pytest les rend réutilisables entre plusieurs tests [9].

### Paramétrisation

Paramétrer au minimum :

- petite grille et grille standard ;
- mode rapide et mode nominal ;
- direction `rows` et `cols` ;
- configuration valide et invalide ;
- présence ou absence de points filtrés.

---

## Phase 13 — Tests de l’interface

### Objectif

Vérifier que la GUI répond correctement aux actions principales.

Streamlit fournit `AppTest`, qui permet d’exécuter une page simulée, de manipuler des widgets et de vérifier les éléments affichés [5].

### Scénarios minimaux

1. démarrage de la page d’accueil ;
2. affichage des valeurs par défaut ;
3. saisie d’une configuration valide ;
4. rejet d’une configuration invalide ;
5. lancement d’un petit run ;
6. affichage du statut `PASS` ou `WARN` attendu ;
7. navigation vers la page 3D ;
8. sélection d’une trajectoire ;
9. navigation vers la page Pareto ;
10. téléchargement d’un résultat ;
11. chargement d’un run existant.

### Critères d’acceptation

Un changement de widget ne doit pas lancer involontairement un pipeline coûteux.

Les tests doivent sélectionner les widgets par `key` stable plutôt que de dépendre uniquement de leur position dans la page.

---

## Phase 14 — Documentation utilisateur et développeur

### Documentation utilisateur

Créer :

```text
docs/GUI_GUIDE_UTILISATEUR.md
```

Ce guide expliquera :

- comment démarrer l’application ;
- comment modifier les paramètres ;
- comment lancer un run ;
- comment lire les statuts ;
- comment manipuler la vue 3D ;
- comment interpréter Pareto ;
- comment exporter les résultats.

### Documentation développeur

Créer :

```text
docs/GUI_GUIDE_DEVELOPPEUR.md
```

Ce guide expliquera :

- la séparation GUI/moteur ;
- l’état Streamlit ;
- le cycle de vie d’un run ;
- le registre des résultats ;
- les règles d’import ;
- les tests ;
- les règles de non-régression.

### Mise à jour du README

Ajouter :

```text
pip install -e ".[gui]"
streamlit run app/streamlit_app.py
```

La dépendance GUI pourra être déclarée comme extra dans `pyproject.toml`, conformément aux possibilités documentées par PyPA [8].

---

## Phase 15 — Packaging et installation

### Objectif

Permettre à une autre personne d’installer et d’exécuter le projet sans échange oral.

### Actions

1. déplacer les métadonnées et dépendances principales vers `pyproject.toml` si nécessaire ;
2. définir une extra `gui` ;
3. définir une extra `dev` pour les tests et outils ;
4. documenter la version minimale de Python ;
5. ajouter une commande de démarrage ;
6. vérifier une installation dans un environnement virtuel propre.

Exemple conceptuel :

```toml
[project.optional-dependencies]
gui = [
    "streamlit",
    "plotly",
]

dev = [
    "pytest",
    "ruff",
]
```

Les versions exactes devront être déterminées après vérification de compatibilité avec les versions déjà utilisées.

### Critères d’acceptation

Sur un environnement vierge :

```text
installation réussie
application démarrable
smoke test réussi
interface accessible
```

---

## Phase 16 — Sécurité et fiabilité des données

Streamlit documente que certains mécanismes de cache utilisent la sérialisation et que les données non fiables ne doivent pas être chargées sans contrôle [4].

Dans notre projet :

- les résultats CSV et JSON doivent provenir de runs locaux de confiance ;
- les fichiers téléchargés par un utilisateur doivent être validés ;
- les chemins doivent être contrôlés pour éviter une écriture hors du répertoire des runs ;
- aucune donnée arbitraire ne doit être désérialisée sans justification ;
- les paramètres utilisateur doivent passer par le validateur de configuration.

La première version ne doit pas inclure d’authentification complexe ou d’accès public Internet. Elle doit fonctionner localement.

---

## Phase 17 — Critères de fin du projet

La version améliorée sera considérée comme acceptable lorsque toutes les conditions suivantes seront remplies.

### Moteur

- le pipeline CLI fonctionne toujours ;
- les tests existants réussissent ;
- les nouveaux tests du service réussissent ;
- aucune importation de Streamlit n’existe dans les algorithmes ;
- la configuration est enregistrée avec chaque run.

### Interface

- l’application démarre avec une commande documentée ;
- les pages sont accessibles ;
- les paramètres peuvent être saisis ;
- les erreurs sont compréhensibles ;
- un run peut être lancé et rechargé ;
- l’interface n’écrase pas silencieusement un run existant.

### Visualisation

- le robot est visible en 3D ;
- la plateforme, les câbles et les points sont cohérents avec le modèle ;
- les plants sont visibles ;
- les trajectoires peuvent être sélectionnées ;
- le Pareto est interactif ;
- les profils sont consultables.

### Validation

- les contrôles du BLOC 10 sont visibles ;
- les résultats du BLOC 11 sont visibles ;
- les avertissements sont distingués des erreurs ;
- les fichiers peuvent être exportés.

### Reproductibilité

- deux exécutions avec la même configuration et la même graine sont identifiables ;
- chaque run contient sa configuration ;
- la version du code et les options sont connues ;
- un futur repreneur peut comprendre le fonctionnement sans échange oral.

---

## 18. Ordre pratique exact pour l’IA qui réalisera le code

Une IA chargée de coder devra respecter cet ordre et ne pas sauter directement à la GUI complète.

### Étape A — Inspection

Lire avant toute modification :

```text
README.md
docs/RUNBOOK.md
docs/DECISIONS.md
pyproject.toml
requirements.txt
scripts/run_pipeline.py
src/config.py
src/validator.py
src/comparator.py
```

Puis établir la carte des entrées et sorties.

### Étape B — Référence

Exécuter les tests et le smoke test. Enregistrer le résultat.

### Étape C — Service

Créer `PipelineService` sans modifier les équations.

### Étape D — Non-régression

Faire appeler le CLI par le service et comparer les sorties.

### Étape E — Configuration

Créer la validation des paramètres et la sérialisation.

### Étape F — GUI minimale

Créer l’application, la navigation et l’état.

### Étape G — Paramètres

Ajouter le formulaire sans lancer automatiquement le pipeline.

### Étape H — Exécution

Ajouter le bouton de lancement, les runs isolés et le diagnostic d’erreur.

### Étape I — Résultats

Afficher d’abord les CSV et JSON déjà produits.

### Étape J — 3D

Réutiliser `Robot3DViewer`, puis ajouter les plants et les options de visibilité.

### Étape K — Statistiques

Ajouter les agrégations et les graphiques interactifs.

### Étape L — Tests GUI

Ajouter les scénarios `AppTest` et les tests d’intégration.

### Étape M — Documentation et installation

Finaliser les guides, `pyproject.toml`, le README et le test d’installation propre.

À chaque étape, l’IA doit fournir :

1. les fichiers modifiés ;
2. la justification ;
3. les tests exécutés ;
4. les résultats ;
5. les limites restantes ;
6. la décision de poursuivre ou non.

---

## 19. Règles strictes pour les futures modifications

1. Ne jamais modifier les équations scientifiques uniquement pour faciliter l’interface.
2. Ne jamais copier la logique du pipeline dans une page Streamlit.
3. Ne jamais lancer un calcul coûteux sur chaque rerun de page.
4. Ne jamais écraser un run sans confirmation explicite ou nouvel identifiant.
5. Ne jamais cacher un `FAIL` derrière un simple message graphique.
6. Ne jamais transformer automatiquement un `WARN` en `PASS`.
7. Toujours afficher les unités.
8. Toujours enregistrer la configuration qui a produit un résultat.
9. Toujours ajouter un test pour une correction de bug.
10. Toujours conserver le CLI jusqu’à la validation finale de la GUI.
11. Toujours utiliser la même source de vérité pour les coordonnées du robot.
12. Toujours comparer une nouvelle version aux résultats de référence.

---

## 20. Première livraison recommandée

La première livraison ne doit pas chercher à tout faire.

Elle doit contenir uniquement :

- `PipelineService` ;
- formulaire de paramètres ;
- lancement du mode rapide ;
- affichage du statut de validation ;
- tableau des métriques principales ;
- graphique Pareto ;
- visualisation 3D statique du robot ;
- téléchargement du rapport de validation.

Cette version constituera un MVP scientifique. Les plants détaillés, l’animation, les tensions par câble et les analyses avancées viendront ensuite.

### Pourquoi commencer par ce périmètre ?

Il couvre le cycle complet :

```text
paramétrer
    ↓
calculer
    ↓
valider
    ↓
visualiser
    ↓
exporter
```

Il permet aussi de tester l’architecture avant d’ajouter des fonctionnalités qui pourraient complexifier la scène 3D ou ralentir l’application.

---

## Conclusion

L’amélioration doit être réalisée comme une évolution contrôlée du projet scientifique existant.

La stratégie retenue est :

```text
version scientifique stable
        ↓
service d’orchestration commun
        ↓
configuration validée
        ↓
interface multipage Streamlit
        ↓
visualisation Plotly
        ↓
tests de non-régression
        ↓
version interactive documentée
```

Le premier objectif n’est pas de créer beaucoup d’écrans. Le premier objectif est de garantir que l’écran affiche exactement les résultats du moteur scientifique validé.

La GUI sera donc considérée comme une couche de présentation et de pilotage, tandis que `src/` restera la source de vérité des calculs.

Cette organisation permet d’obtenir une version plus accessible et plus visuelle sans sacrifier la rigueur du modèle mécanique, la reproductibilité des résultats ou la possibilité d’utiliser encore le terminal.

---

## 21. Feuille de route après livraison GUI — mise à jour 2026-10-29

Les tranches d’harmonisation des graphiques, de filtrage WFW et de téléchargements
ciblés sont maintenant fusionnées dans `main`. La suite doit conserver la chaîne :

```text
Paramètres GUI → ConfigurationService → Config → pipeline scientifique
```

### 21.1 Priorité immédiate — altitude absolue de la plateforme R0

Le moteur possède `Config.z_absolu_r0_override`, sa validation et son support CLI
via `--z-absolu`. La GUI expose maintenant ce contrat dans Paramètres au lieu de
créer un champ ambigu nommé simplement `z`.

Libellé recommandé : **Altitude absolue de la plateforme R0 (m)**.

Comportement attendu :

- mode **Automatique** sélectionné par défaut ;
- affichage de la valeur calculée `z_absolu_r0` ;
- mode **Valeur imposée** activant un nombre en mètres ;
- précision de saisie de `0,001 m` ;
- bornes contrôlées par `z_min` et `z_max` ;
- valeur manuelle visible dans l’aperçu et `config.json` ;
- modification invalidant l’aperçu confirmé ;
- empreinte différente entre mode automatique et override manuel ;
- tests de bornes, sérialisation et non-régression GUI.

**État : livré dans `main` le 2026-10-29.** Le mode automatique conserve ses
empreintes historiques afin de ne pas invalider les reprises existantes ; un
marqueur de mode est ajouté uniquement pour un override manuel, ce qui distingue
les deux modes même lorsque leur altitude effective est identique. Le contrôle
GUI transmet le champ jusqu’à `Config`, affiche la valeur effective dans
l’aperçu et enregistre l’override ainsi que la valeur dérivée dans `config.json`.
Les tests couvrent les bornes R6, l’invalidation de l’aperçu, la compatibilité
d’empreinte automatique et la propagation jusqu’aux points générés. Cette option
reste une hypothèse de configuration, non une validation expérimentale.

La valeur automatique actuelle est calculée par :

```text
z_absolu_r0 = hauteur_plants + z_vol - offset_r0_sol
```

Pour la configuration de référence, elle vaut `0,450 m`. Un override est une
hypothèse de configuration et non une validation de la sécurité mécanique ou de
la qualité agronomique.

### 21.2 Ordre des améliorations suivantes

1. [x] implémenter et tester le contrôle `z_absolu_r0_override` dans Paramètres ;
2. [x] auditer Accueil, Paramètres, Résultats et Historique à 1024/768 px ([rapport](evidence/gui-responsive-20261029/README.md)) ;
3. terminer l’accessibilité clavier, focus, tableaux, graphiques et impression ;
4. rendre la sélection des sources plus lisible dans Accueil ;
5. ajouter des filtres opérationnels à Historique ;
6. stabiliser un mode présentation fidèle aux statuts et aux unités ;
7. ajouter la sélection d’un point dans le front de Pareto ;
8. construire la comparaison multi-seeds avec dispersion et limites explicites ;
9. mesurer puis calibrer les durées d’exécution ;
10. envisager le chargement différé et le cache seulement après mesure du coût réel ;
11. nettoyer les fixtures et données versionnées après preuve de reproductibilité.

Chaque item doit rester dans un commit fonctionnel, être accompagné de tests et
faire l’objet d’une mise à jour du registre. Les résultats scientifiques, les
seuils mécaniques et les décisions expérimentales ne doivent pas être inférés de
l’apparence de l’interface.

---

## Références

[1]: https://docs.streamlit.io/develop/concepts/architecture/session-state "Streamlit — Add statefulness to apps"

[2]: https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation "Streamlit — Define multipage apps with st.Page and st.navigation"

[3]: https://docs.streamlit.io/develop/api-reference/execution-flow/st.form "Streamlit — st.form API reference"

[4]: https://docs.streamlit.io/develop/concepts/architecture/caching "Streamlit — Caching overview"

[5]: https://docs.streamlit.io/develop/concepts/app-testing/get-started "Streamlit — Get started with app testing"

[6]: https://plotly.com/python/3d-charts/ "Plotly Python — 3D charts"

[7]: https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart "Streamlit — st.plotly_chart API reference"

[8]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ "Python Packaging User Guide — Writing pyproject.toml"

[9]: https://docs.pytest.org/en/stable/how-to/fixtures.html "pytest — How to use fixtures"

# Cartographie historique de l’architecture de Tandem SP2

## Objet et statut du document

Ce document conserve la cartographie du pipeline scientifique **avant** l’extraction de `PipelineService` et l’ajout de l’interface GUI. Il décrit un état historique du dépôt et ne doit pas être utilisé comme description de l’architecture courante de `feature/gui-improvement`.

Pour l’architecture actuelle, se reporter à `docs/GUIDE_DEVELOPPEUR_GUI.md` et aux modules `app/`, `services/`, `src/` et `visualization/`. Le CLI appelle maintenant `PipelineService`; l’ancienne description de `scripts/run_pipeline.py` ci-dessous sert à comprendre l’état antérieur et les choix de migration.

La cartographie historique répond aux questions suivantes :

- où le programme commence-t-il ?
- quels paramètres sont nécessaires ?
- dans quel ordre les blocs sont-ils exécutés ?
- quelles données entrent et sortent de chaque bloc ?
- quels fichiers sont écrits ?
- quelles erreurs peuvent interrompre le pipeline ?
- quelles parties devront être séparées pour créer la nouvelle application ?

Ce document décrit l’existant. Il ne modifie pas le comportement scientifique du projet.

---

## 1. Points d’entrée actuels

### 1.1 Pipeline principal

Le point d’entrée de production est :

```text
scripts/run_pipeline.py
```

Il est exécuté depuis le terminal :

```bash
python scripts/run_pipeline.py
```

Le mode rapide est :

```bash
python scripts/run_pipeline.py --fast
```

Le module ajoute la racine du projet à `sys.path` afin de pouvoir importer les modules `src` lorsque le script est lancé depuis différents répertoires.

### 1.2 Entrée Python réutilisable

Le script expose également :

```python
run_pipeline(
    config,
    output_dir,
    K,
    pop_size,
    n_gen,
    seed,
    resume,
)
```

Cette fonction est déjà un embryon de service réutilisable, mais elle retourne encore un dictionnaire générique et reste définie dans un script qui contient aussi la logique CLI.

### 1.3 Autres scripts

Le dépôt contient aussi :

```text
scripts/run_wfw_3d.py
scripts/sweep_wfw.py
scripts/view_robot_3d.py
```

Ils servent respectivement à :

- produire une exploration ou visualisation WFW 3D ;
- balayer des configurations WFW ;
- lancer la visualisation interactive du robot.

La première GUI utilisera principalement le pipeline principal et `src/robot_3d_viewer.py`. Ces scripts secondaires resteront disponibles jusqu’à décision contraire.

---

## 2. Couches actuellement présentes

L’organisation actuelle est principalement :

```text
scripts/
    orchestration et interface terminal

src/
    modèles, algorithmes et visualisations

tests/
    tests unitaires et d’intégration

data/
    sorties régénérables ou snapshots
```

La séparation scientifique est déjà bonne : les calculs sont majoritairement dans `src` et le script principal les enchaîne.

La séparation applicative n’est toutefois pas encore complète, car `run_pipeline.py` contient simultanément :

- la construction de la configuration ;
- la validation des options CLI ;
- la gestion du mode `--resume` ;
- la gestion du hash de configuration ;
- l’orchestration des blocs ;
- la lecture et l’écriture des fichiers ;
- les logs ;
- la production du rapport final ;
- la conversion des exceptions en codes retour.

C’est la principale raison de créer `PipelineService` avant de construire la GUI.

---

## 3. Paramètres d’entrée du pipeline

### 3.1 Paramètres de configuration

La classe principale est :

```python
src.config.Config
```

Elle contient notamment :

- la taille de la grille ;
- les espacements ;
- les bornes spatiales ;
- la masse ;
- les ancrages ;
- les attaches ;
- les bornes de tension ;
- la hauteur de travail ;
- le FOV de la caméra ;
- la vitesse maximale ;
- l’accélération maximale ;
- le temps de stabilisation ;
- les paramètres NSGA-II.

La configuration est validée dans `Config.__post_init__` puis dans `Config._validate`.

### 3.2 Options CLI

Les arguments définis par `_build_parser` sont :

```text
--fast
--n
--output-dir
--K
--pop-size
--n-gen
--seed
--z-absolu
--resume
--verbose
--zero-loss
--platform
--platform-mass
--xy-bound
--x-bound
--y-bound
```

### 3.3 Résolution des paramètres

`_resolve_config_and_params` transforme les arguments CLI en :

```text
Config
K
pop_size
n_gen
seed
```

Le mode `--fast` force actuellement :

```text
grille 3 × 3
zero-loss activé
K = 5 par défaut
pop_size = 30 par défaut
n_gen = 100 par défaut
```

Le mode normal utilise par défaut une grille `9 × 9`, avec les valeurs d’optimisation de `Config` et `K = 10`.

Les contrôles explicites sont :

```text
K >= 1
pop_size >= 2
n_gen >= 1
```

---

## 4. Empreinte et reprise

### 4.1 Construction de l’empreinte

La fonction `_config_fingerprint` calcule un hash court à partir de paramètres tels que :

- `N` ;
- rangs et colonnes ;
- espacements ;
- bornes ;
- masse ;
- attaches ;
- tensions ;
- hauteurs ;
- FOV ;
- vitesse et accélération ;
- stabilisation ;
- `K` ;
- population ;
- générations ;
- graine.

Le résultat est un hash SHA-256 tronqué à 16 caractères.

### 4.2 Fichier `.config_hash`

`_check_config_fingerprint` écrit :

```text
output_dir/.config_hash
```

En mode normal, le hash est réécrit.

En mode `--resume` :

1. le fichier doit exister ;
2. le hash stocké doit être identique ;
3. sinon le pipeline s’arrête avec une `RuntimeError`.

### Pourquoi cette fonction est importante

Elle empêche de mélanger silencieusement des CSV produits avec deux configurations différentes.

### Limite actuelle

L’empreinte est enregistrée, mais la configuration complète n’est pas encore écrite dans un fichier JSON dédié par run. Cette amélioration appartient à la future couche de gestion des exécutions.

---

## 5. Contrat général des sorties

Les sorties sont écrites dans `output_dir`.

Le répertoire `figures/` est créé automatiquement.

Les étapes déclarent leurs fichiers attendus dans `_STEP_OUTPUTS` afin de permettre le mode `--resume`.

```text
4_point_generator
5_point_filter
6_cost_calculator
7_optimizer
8_extractor
9_profiler
10_validator
11_comparator
```

Le pipeline relit ensuite plusieurs fichiers depuis le disque entre deux étapes. Cette caractéristique sera conservée dans la première version du service pour préserver la traçabilité.

---

## 6. Vue globale du flux

```text
arguments CLI
    ↓
Config + options
    ↓
empreinte de configuration
    ↓
RobotModel + WFW partagés
    ↓
BLOC 4 — génération des points
    ↓
BLOC 5 — filtrage WFW
    ↓
BLOC 6 — matrice des coûts
    ↓
BLOC 7 — optimisation NSGA-II
    ↓
BLOC 8 — extraction des trajectoires
    ↓
BLOC 9 — profilage temporel
    ↓
BLOC 10 — validation et figures
    ↓
BLOC 11 — comparaison baseline
    ↓
rapport final CLI
```

Les BLOCs 0 à 3 fournissent les fondations appelées par les blocs de production :

```text
BLOC 0 : configuration
BLOC 1 : modèle robotique
BLOC 2 : cinématique
BLOC 3 : WFW
```

---

## 7. Instances partagées

Au début de `run_pipeline`, le code crée :

```python
robot = RobotModel(config)
wfw = WFW(robot, config)
```

Ces objets sont réutilisés par :

- le BLOC 5 pour vérifier la faisabilité ;
- le BLOC 6 pour calculer les coûts ;
- le BLOC 10 pour refaire les validations.

### Conséquence architecturale

Le futur `PipelineService` devra construire ces objets une seule fois par exécution et les transmettre aux composants qui en ont besoin.

Ils ne doivent pas être stockés comme état global mutable de Streamlit.

---

# 8. Cartographie détaillée des BLOCs

## BLOC 4 — Génération des points

### Classe

```python
PointGenerator(config)
```

### Entrée

```text
Config
```

### Traitement

`PointGenerator.generate` construit la grille de positions à partir de la configuration.

Il calcule également les informations liées au FOV avec `fov_report`.

### Écriture

`PointGenerator.run(output_dir=...)` produit :

```text
points_generes.csv
points_generes_report.json
```

### Relecture dans le pipeline

Après l’exécution, le pipeline utilise le DataFrame retourné par `generate`.

En mode `--resume`, il recharge :

```text
points_generes.csv
```

### Données importantes

Les points contiennent notamment :

```text
id
ligne
colonne
x
y
z
```

### Erreurs possibles

Les erreurs de configuration provenant de `Config` peuvent interrompre le bloc avant la génération.

---

## BLOC 5 — Filtrage des points

### Classe

```python
PointFilter(config, wfw)
```

### Entrées

```text
Config
WFW
DataFrame des points générés
```

### Traitement

`PointFilter.run` évalue les points selon :

- les limites opérationnelles ;
- la faisabilité WFW ;
- la présence d’un centre exploitable ;
- le nombre minimal de points requis.

### Écriture

Le bloc produit :

```text
points_filtres.csv
points_rejetes_cause_a.csv
points_rejetes_cause_b.csv
point_filter_report.json
```

### Sortie utilisée ensuite

Le pipeline recharge ou conserve :

```text
df_filtered
```

### Exceptions métier

```python
CenterNotFeasibleError
InsufficientPointsError
```

Dans la CLI, `InsufficientPointsError` conduit au code retour `3` avec un message proposant des réglages alternatifs.

`CenterNotFeasibleError` est actuellement capturée par le gestionnaire général et conduit au code retour `1`, sauf traitement spécifique ajouté ultérieurement.

---

## BLOC 6 — Calcul de la matrice des coûts

### Classe

```python
CostCalculator(config, robot)
```

### Entrées

```text
Config
RobotModel
points_filtres
K
```

### Traitement

Pour chaque paire de points, le calculateur évalue notamment :

- la faisabilité ;
- la distance ;
- le temps LSPB ;
- les tensions ;
- l’énergie.

### Écriture

```text
cost_matrix.csv
```

### Colonnes attendues

La validation et le comparateur attendent notamment :

```text
i
j
time
energy
distance
feasible
```

### Diagnostic dans l’orchestrateur

Après écriture, `run_pipeline` recharge le CSV et calcule :

```text
n_infeasible_pairs
infeasible_rate
```

Ces valeurs sont écrites dans les métadonnées du rapport final et affichées dans les logs.

### Particularité

Le BLOC 6 est identifié par le script comme le bloc potentiellement le plus lent. Il est donc prioritaire pour une future progression GUI.

---

## BLOC 7 — Optimisation NSGA-II

### Classe

```python
Optimizer(config, df_filtered, df_costs)
```

### Entrées

```text
Config
points filtrés
matrice des coûts
pop_size
n_gen
seed
```

### Traitement

L’optimiseur cherche des ordres de visite non dominés selon les objectifs temps et énergie.

`Optimizer.run_and_save` écrit les résultats directement.

### Écriture

```text
solutions_pareto.csv
solutions_orders.csv
```

### Métadonnée extraite

Le pipeline conserve :

```text
n_pareto_solutions
```

### Exception métier

```python
DegenerateFrontError
```

Elle signifie qu’aucun tour faisable n’a pu être construit.

Dans la CLI, elle conduit au code retour `4`.

---

## BLOC 8 — Extraction des trajectoires

### Classe

```python
TrajectoryExtractor(
    config,
    df_filtered,
    df_costs,
    df_sols,
)
```

### Entrées

```text
Config
points filtrés
matrice des coûts
solutions Pareto
```

### Traitement

Le bloc sélectionne les trajectoires représentatives :

```text
time_opt
energy_opt
compromise
```

Il reconstruit les waypoints et les résumés cumulés.

### Écriture

```text
trajectories.csv
trajectories_summary.csv
```

### Sorties utilisées par la suite

Le BLOC 9 recharge `trajectories.csv`.

Le BLOC 10 recharge les deux fichiers pour vérifier la cohérence.

Le BLOC 11 les utilise pour comparer les trajectoires à la baseline.

---

## BLOC 9 — Profilage cinématique

### Classe

```python
TrajectoryProfiler(config, dt=0.1, min_samples_per_segment=5)
```

### Entrées

```text
Config
trajectories.csv
```

### Traitement

Le profileur transforme les waypoints en séries temporelles LSPB :

- position ;
- vitesse ;
- temps local ;
- temps global ;
- segment.

### Écriture

```text
profiles.csv
profiles_time_opt.csv
profiles_energy_opt.csv
profiles_compromise.csv
```

### Paramètres actuellement fixés par l’orchestrateur

```text
dt = 0.1 s
min_samples_per_segment = 5
```

Ces valeurs devront devenir des options explicites du futur service si la GUI doit les modifier.

---

## BLOC 10 — Validation et production des figures

### Classe

```python
Validator(config, robot, wfw, output_dir, figures_dir)
```

### Entrées sur disque

Le validateur exige :

```text
points_filtres.csv
cost_matrix.csv
solutions_pareto.csv
trajectories.csv
trajectories_summary.csv
profiles.csv
```

### Vérifications

Il contrôle :

1. la cohérence de la configuration ;
2. les points filtrés ;
3. la matrice des coûts ;
4. les solutions Pareto ;
5. les trajectoires ;
6. les profils ;
7. la cohérence croisée.

### Écriture

```text
validation_report.json
hypotheses_report.json
hypotheses_report.md
```

### Figures

Le validateur produit :

```text
figures/wfw_slice.png
figures/pareto_front.png
figures/trajectories_3d_time_opt.png
figures/trajectories_3d_energy_opt.png
figures/trajectories_3d_compromise.png
figures/profiles.png
```

Le pipeline les attend dans `_STEP_OUTPUTS` pour le mode `--resume`.

### Statuts

Le statut global est :

```text
FAIL si au moins un check est FAIL
WARN sinon si au moins un check est WARN
PASS sinon
```

En mode `--fast`, la CLI accepte uniquement le `WARN` connu du check `solutions_pareto`, sans `FAIL`.

---

## BLOC 11 — Comparaison avec la baseline

### Classe

```python
Comparator(config, points, costs, summary, trajectories)
```

### Entrées sur disque

```text
points_filtres.csv
cost_matrix.csv
trajectories_summary.csv
trajectories.csv
```

### Traitement

Le comparateur :

1. construit une baseline zigzag si la grille est complète ;
2. utilise une heuristique de plus proche voisin si la grille est incomplète ;
3. impose le départ et le retour au centre ;
4. additionne les coûts de la matrice ;
5. calcule les gains temps et énergie ;
6. produit un diagnostic de performance.

### Écriture

```text
baseline_zigzag.csv
comparison.csv
comparison_diagnostic.json
figures/comparison.png
figures/trajectories_comparison_grid.png
figures/trajectories_comparison_2d.png
```

### Métadonnées reprises dans le rapport CLI

Lorsque le bloc est exécuté et non sauté, le pipeline lit le diagnostic et ajoute :

```text
optimal_beats_baseline
min_time_gain_pct
min_energy_gain_pct
```

---

# 9. Table synthétique des artefacts

| Bloc | Entrées principales | Sorties principales | Objet réutilisé |
|---|---|---|---|
| 4 | `Config` | points générés, rapport FOV | `PointGenerator` |
| 5 | points, `Config`, `WFW` | points filtrés, rejets, rapport | `PointFilter` |
| 6 | points filtrés, `RobotModel`, `K` | matrice des coûts | `CostCalculator` |
| 7 | points, matrice, options NSGA-II | Pareto, ordres | `Optimizer` |
| 8 | points, matrice, Pareto | trajectoires, résumés | `TrajectoryExtractor` |
| 9 | trajectoires | profils temporels | `TrajectoryProfiler` |
| 10 | CSV des blocs 4–9 | validation, hypothèses, figures | `Validator` |
| 11 | points, coûts, trajectoires | baseline, comparaison, diagnostic, figures | `Comparator` |

---

## 10. Gestion du mode `--resume`

`_run_step` applique la règle suivante :

```text
si resume et tous les fichiers déclarés existent : SKIP
sinon : exécuter l’étape
```

Lorsqu’une étape est sautée :

- le résultat Python de l’étape vaut `None` ;
- le DataFrame nécessaire est relu depuis le CSV lorsque le pipeline le prévoit ;
- le temps de l’étape vaut `0.0` ;
- le rapport final affiche `(skipped)`.

### Risque à traiter dans le futur service

La reprise est actuellement fondée sur la présence et la taille des fichiers. Elle ne valide pas encore le contenu ou le hash de chaque artefact.

Une future version pourra ajouter :

- un manifeste de fichiers ;
- les empreintes des CSV ;
- une version de schéma ;
- un état explicite par bloc.

---

## 11. Effets de bord actuels

Les effets de bord identifiés sont :

- création de répertoires ;
- écriture de CSV ;
- écriture de JSON ;
- écriture de Markdown ;
- écriture de PNG ;
- écriture de `.config_hash` ;
- journalisation ;
- affichage du rapport final dans le terminal ;
- modification ou remplacement des sorties lorsque `resume=False` ;
- réutilisation du contenu existant lorsque `resume=True`.

Ces effets de bord devront être regroupés et exposés explicitement dans `PipelineResult` pour la GUI.

---

## 12. Exceptions et codes retour CLI

### Exceptions métier connues

```text
InsufficientPointsError → code 3
DegenerateFrontError    → code 4
```

### Autres exceptions

Toute autre exception est capturée par `main` :

```text
log d’erreur
code retour 1
```

### Statut de validation

Après exécution :

```text
PASS → code 0
WARN attendu en --fast → code 0
WARN non attendu → code 2
```

La GUI devra conserver la distinction entre :

- erreur de configuration ;
- erreur de calcul ;
- validation `FAIL` ;
- avertissement attendu ;
- avertissement non attendu.

Elle ne doit pas réduire tous ces cas à un simple message « échec ».

---

## 13. Rapport final CLI

`_print_final_report` affiche :

- le répertoire de sortie ;
- les timings par étape ;
- le temps total ;
- les métadonnées clés ;
- la liste des fichiers et leur taille.

Ce rapport est actuellement uniquement destiné au terminal. Le futur service devra produire les mêmes informations sous forme structurée afin que la GUI puisse les présenter dans des cartes et tableaux.

---

## 14. Points à corriger ou à clarifier plus tard

Cette section ne corrige rien dans la Phase 1. Elle liste les sujets à traiter dans les phases suivantes.

### 14.1 Liste incomplète des sorties du BLOC 11

Le BLOC 11 produit :

```text
figures/trajectories_comparison_2d.png
```

mais cette sortie n’apparaît pas dans `_STEP_OUTPUTS["11_comparator"]`.

Conséquence possible : en mode `--resume`, si les autres sorties existent mais que cette figure manque, le bloc peut être considéré comme déjà terminé et être sauté.

Correction à prévoir dans une étape dédiée et testée.

### 14.2 Documentation interne du script

La docstring principale mentionne « BLOC 4 → BLOC 10 », alors que le script exécute aussi le BLOC 11.

Correction documentaire à prévoir.

### 14.3 Résultats du BLOC 11 en mode reprise

Si le BLOC 11 est sauté, le code ne recharge pas systématiquement `comparison_diagnostic.json` pour remplir les métadonnées `optimal_beats_baseline`, `min_time_gain_pct` et `min_energy_gain_pct`.

La GUI devra utiliser `ResultService` pour charger le diagnostic même après reprise.

### 14.4 Types de retour

`run_pipeline` retourne actuellement :

```python
dict[str, object]
```

Un objet `PipelineResult` typé rendrait les résultats plus sûrs pour la GUI.

### 14.5 Progression

Le pipeline logue le début et la fin des blocs, mais ne publie pas encore un flux de progression structuré pour une interface.

### 14.6 Répertoire de sortie

Le mode CLI utilise par défaut `data/outputs`, qui est adapté aux artefacts régénérables mais moins adapté à l’historique de plusieurs runs GUI.

La future GUI devra utiliser un répertoire par `run_id`.

---

## 15. Découpage recommandé du futur `PipelineService`

Le service devra reprendre la logique actuelle en conservant cet ordre :

```text
resolve configuration
    ↓
create run directory
    ↓
write configuration metadata
    ↓
create RobotModel and WFW
    ↓
run BLOC 4
    ↓
run BLOC 5
    ↓
run BLOC 6
    ↓
run BLOC 7
    ↓
run BLOC 8
    ↓
run BLOC 9
    ↓
run BLOC 10
    ↓
run BLOC 11
    ↓
load diagnostics
    ↓
return typed result
```

Le CLI devra ensuite devenir un adaptateur :

```text
arguments argparse
        ↓
PipelineRequest
        ↓
PipelineService.run
        ↓
rapport terminal + code retour
```

La GUI utilisera le même service :

```text
formulaire Streamlit
        ↓
PipelineRequest
        ↓
PipelineService.run
        ↓
cartes, tableaux, figures et téléchargements
```

---

## 16. Critère de sortie de la Phase 1

La Phase 1 est considérée comme terminée lorsque :

- les entrées et sorties des BLOCs 4 à 11 sont documentées ;
- les effets de bord sont connus ;
- les exceptions et codes retour sont documentés ;
- les points d’entrée sont identifiés ;
- les risques de reprise sont listés ;
- le futur contrat de `PipelineService` est défini ;
- aucune modification scientifique n’a été effectuée.

La prochaine phase sera la création contrôlée des objets de requête, d’options et de résultat, puis l’extraction progressive de `PipelineService`.

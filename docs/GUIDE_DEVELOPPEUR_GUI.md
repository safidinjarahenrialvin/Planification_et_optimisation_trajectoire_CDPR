# Guide développeur — GUI Tandem SP2

## 1. Principe d’architecture

Le projet suit une séparation stricte :

```text
Streamlit GUI → services applicatifs → algorithmes scientifiques (`src/`)
```

La GUI collecte et présente les données. Les services valident la configuration,
orchestrent le pipeline, chargent les artefacts et préparent les exports. Les
formules scientifiques restent dans `src/` et ne doivent pas importer Streamlit.

## 2. Répertoires importants

- `src/` : modèles, algorithmes et pipeline scientifique ;
- `services/` : contrats applicatifs indépendants de l’interface ;
- `visualization/` : figures Plotly réutilisables ;
- `visualization/labels.py` : libellés partagés des stratégies et baselines;
- `visualization/chart_style.py` : tokens et layout communs aux graphiques;
- `app/` : pages Streamlit et état de session ;
- `tests/` : tests unitaires, intégration et AppTest ;
- `docs/` : décisions, runbook, guides et suivi de continuité ;
- `data/runs/` : sorties isolées de la GUI, ignorées par Git ;
- `data/snapshots/` : copies runtime créées explicitement, ignorées par Git.

La page Résultats affiche d’abord la source chargée et le choix de stratégie,
puis expose sept onglets spécialisés : **Scène 3D**, **Trajectoires**,
**Profils cinématiques**, **Couverture WFW**, **Pareto**, **Analyse & comparaison**
et **Validation**. La scène 3D, la trajectoire sélectionnée, la baseline, les
profils, la couverture et les graphiques de comparaison sont ainsi séparés sans
changer les services ni les artefacts. Les hypothèses, contrôles et exports
restent dans Validation; cette dernière ne montre que les compteurs de contrôle
et les preuves techniques. Les analyses exhaustives de coûts restent dans
l’expander secondaire **Preuves techniques**. Toute évolution doit conserver ce
principe : une information synthétique en tête, puis une responsabilité claire
par onglet, sans recopier les mêmes explications.

## 3. Contrats des services

`PipelineService` exécute le pipeline avec une requête explicite.
`ConfigurationService` valide et sérialise la configuration effective.
`ResultService` transforme un répertoire d’artefacts en `RunResults`.
`ExportService` lit des fichiers autorisés, produit un rapport Markdown et crée
une archive ZIP en mémoire.
`SnapshotService` valide puis copie un run terminé vers `data/snapshots/`, sans
dépendance Streamlit ni modification de la source.

La création de snapshot exige un run directement sous `data/runs/`, un manifeste
`schema_version=1` au statut `COMPLETED`, les huit étapes du pipeline, l’inventaire
exhaustif des artefacts et une même empreinte dans le manifeste, `config.json` et
`.config_hash`. `ResultService.load` contrôle aussi les schémas et cohérences des
artefacts. Le contenu est copié dans un staging privé sous le même répertoire,
haché avant/après copie puis revalidé; toute évolution du run pendant l’opération
annule la publication. La destination utilise `renameat2(RENAME_NOREPLACE)` sous
Linux pour rendre visible la copie entière en une opération et refuser les
collisions, même concurrentes. Les noms sont un seul composant ASCII de 1 à 64
caractères. Les liens symboliques et fichiers spéciaux sont refusés; les snapshots
runtime ne sont pas commités.

`RunResults.cost_statistics()` est la source unique des statistiques de coûts
présentées par l’interface et le rapport jury. Elle exclut les boucles `i = j`
des taux de faisabilité et des distributions; moyenne, médiane, écart-type,
quartiles et étendue sont calculés sur les seules transitions inter-points
faisables. Les figures de coûts conservent distance (m), temps (s) et énergie (J)
dans des axes séparés.

La page Paramètres sépare deux opérations : `Actualiser l’aperçu` calcule et
stocke la configuration effective dans l’état de session; `Lancer l’exécution
sélectionnée` n’est accepté que si la signature des réglages n’a pas changé
depuis cet aperçu. La signature inclut le mode et la valeur imposée de l’altitude
R0 ; toute modification invalide l’aperçu et bloque le lancement jusqu’à sa
réactualisation. Cette garde évite de lancer un calcul avec une configuration
différente de celle relue par l’utilisateur. Les bornes GUI sont `K ≤ 100`,
`pop_size ≤ 2000` et `n_gen ≤ 5000`; elles limitent le risque opérationnel sans
remplacer une qualification scientifique des budgets NSGA-II.

Un service ne doit pas dépendre de `st.session_state`, afficher une interface ou
lancer implicitement un calcul. Cette règle permet de tester le service avec
pytest et de le réutiliser dans le CLI.

L’altitude est présentée sous le libellé **Altitude absolue de la plateforme R0**,
jamais comme un champ générique `z`. Le mode **Automatique** est le défaut et
utilise `z_absolu_sol - offset_r0_sol`; le mode **Valeur imposée** accepte une
valeur en mètres avec un pas de `0,001 m`, bornée par `z_min`/`z_max` et validée
par la règle R6 de `Config`. La valeur effective est affichée dans l’aperçu et
`config.json` conserve à la fois `z_absolu_r0_override` et la valeur dérivée.
Le marqueur d’override dans l’empreinte différencie une valeur manuelle du mode
automatique même à altitude effective identique; le mode automatique conserve
les empreintes historiques. Les empreintes d’anciens runs ayant un override
manuel changent avec cette distinction et ne sont pas garanties compatibles avec
une reprise `--resume` créée avant ce changement. L’override demeure une hypothèse
de configuration, pas une preuve expérimentale ni une validation de la sécurité
mécanique ou de la qualité agronomique.

## 4. Ajouter un nouvel export

1. Identifier l’artefact produit par le pipeline.
2. Ajouter sa lecture dans `ResultService` si la GUI doit l’analyser.
3. Ajouter l’extension ou le sélecteur dans `app/pages/results.py`, sous **Preuves techniques**.
4. Ajouter un test dans `tests/test_export_service.py`.
5. Vérifier que l’archive ZIP contient le nouveau fichier.
6. Ne jamais modifier le contenu scientifique pendant l’export.

Les chemins sont résolus par `ExportService` et les chemins sortant du run sont
refusés afin d’éviter une lecture involontaire hors du répertoire d’artefacts.
La page Résultats ne construit l’archive ZIP qu’après une demande explicite et
réutilise le contenu préparé pour le run actif.

Les téléchargements ciblés de la stratégie sélectionnée passent également par
`ExportService`. Ils doivent être construits en mémoire, refuser un `kind`
inconnu et ne jamais réécrire les CSV ou JSON du run. Le téléchargement d’une
figure existante doit utiliser `read_artifact()` afin de conserver le contrôle
des chemins.

## 5. Vérifications obligatoires

```bash
.venv/bin/ruff check src services scripts app visualization tests
.venv/bin/pytest -q
streamlit run app/streamlit_app.py
```

La vérification navigateur du worker GUI est documentée dans
`docs/evidence/gui-worker-cancellation-20261029.md`. Elle confirme le clic réel
sur **Annuler l’exécution**, l’état terminal `CANCELLED` et l’exclusion du run
partiel par le manifeste. L’annulation est coopérative : elle est observée aux
points de contrôle sûrs, notamment entre les étapes et à chaque génération de
NSGA-II, et ne force pas l’arrêt au milieu d’une étape scientifique déjà
engagée.

La CI GitHub reproduit les contrôles principaux avec :

```bash
ruff check app services src scripts tests visualization
python -m compileall -q app services src scripts tests visualization
pytest -q -m "not slow"
python scripts/run_pipeline.py --fast --output-dir data/ci-output
```

Elle vérifie ensuite que `/_stcore/health` répond `ok` après le démarrage
headless de Streamlit. Le smoke test est accepté avec le statut attendu du
contrôle Pareto : `WARN` sous trois compromis distincts, `PASS` à partir de
trois, tant qu’aucun contrôle n’est en `FAIL`.

Pour vérifier une installation propre :

```bash
rm -rf /tmp/tandem-sp2-venv
python -m venv /tmp/tandem-sp2-venv
/tmp/tandem-sp2-venv/bin/pip install -e ".[gui,dev]"
/tmp/tandem-sp2-venv/bin/pytest -q
```

Le smoke test du moteur reste indépendant de la GUI :

```bash
python scripts/run_pipeline.py --fast
```

## 6. Règles de modification

- préserver les sorties de référence et les empreintes de configuration ;
- ne pas importer Streamlit dans `src/` ;
- ajouter un test pour chaque correction de bug ;
- faire un commit fonctionnel par phase ;
- mettre à jour `docs/SUIVI_AMELIORATION_GUI.md` après validation ;
- tester le démarrage GUI sans déclencher de calcul.
- afficher les stratégies à partir de leur `kind` réel; ne jamais coder en dur
  « baseline zigzag » lorsqu’un run peut produire `baseline_nn`.
- tester séparément l’aperçu confirmé, la modification qui l’invalide et le
  lancement autorisé après actualisation.

### Qualification responsive

Le point d’entrée conserve `initial_sidebar_state="auto"` : la navigation reste
ouverte à 1024 px et se replie à 768 px. Après une modification de layout, vérifier
Accueil, Paramètres, Résultats et Historique aux deux largeurs sur un artefact
fixture, sans lancer de calcul scientifique. Les KPI et options visibles doivent
rester lisibles; le défilement horizontal interne des onglets ou d’un tableau dense
est acceptable, contrairement à un débordement horizontal de page. Ne pas assimiler
ce contrôle à l’audit clavier, lecteurs d’écran ou impression.

## 7. Conventions communes des graphiques

Les figures Plotly doivent réutiliser `visualization.chart_style` plutôt que
introduire des couleurs locales. `strategy_color()` fixe la couleur d’une
stratégie ou d’une baseline, `POINT_COLORS` fixe les états des points WFW et
`apply_chart_layout()` applique les surfaces, la grille, la typographie, les
marges et la légende communes.

Les statuts automatiques doivent toujours être écrits (`PASS`, `WARN`, `FAIL`)
et accompagnés d’une formulation explicite. Une couleur ou une forme ne doit
jamais être l’unique canal d’information. `WARN` décrit un point à examiner et
ne doit pas être présenté comme un échec ni comme une validation scientifique.

Chaque graphique rendu par une page doit être précédé par
`render_chart_context(...)` avec une description courte de sa sémantique, ses
axes, ses unités et, si nécessaire, la signification des couleurs ou des formes.
Le contexte d’un tableau doit également être rendu avant `st.dataframe(...)` via
`render_table_context(...)`. Ces descriptions complètent les contrôles
interactifs et les téléchargements ; elles ne remplacent pas les données
détaillées ni un audit complet de lecteur d’écran.

Lorsque la légende du graphique, ses axes et ses contrôles suffisent déjà à
expliquer la figure, aucune description textuelle redondante ne doit être ajoutée.
Les phrases conservées dans l’interface commencent par une majuscule et restent
courtes. Dans l’onglet **Validation**, le statut global n’est pas répété sous
forme de message : les compteurs `PASS`, `WARN` et `FAIL` sont affichés sur une
même ligne, tandis que les détails restent disponibles dans **Preuves techniques**.

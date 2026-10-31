# Projet Tandem — SP2 : Planification et optimisation des trajectoires

**Sous-projet 2** du projet Tandem (ESP–ENIM Metz, Diasporeines Africa).
Optimisation des trajectoires d'un robot à câbles suspendu (CDPR 8 câbles)
pour l'acquisition d'images dédiées au suivi du stress hydrique des plants
de haricot nain.

## Démarrage rapide

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest tests/ -v -m "not slow"        # vérifier la base
    python scripts/run_pipeline.py --fast # smoke test zero-loss (~30 s)
    python scripts/run_pipeline.py        # run complet (~2 min)

Les tests marqués `slow` sont séparés de la CI rapide et peuvent être lancés
localement avec :

    pytest tests/ -v -m slow

Le workflow GitHub **Slow tests** est déclenché manuellement depuis l’onglet
Actions. Il conserve les sorties de diagnostic éventuelles comme artefact du
run, sans ralentir les validations exécutées sur chaque push.

## Interface GUI

Installer l’extra graphique puis démarrer l’application :

    pip install -e ".[gui,dev]"
    streamlit run app/streamlit_app.py

La GUI permet de saisir une configuration, lancer un run isolé et consulter les
résultats depuis la source chargée puis sept vues spécialisées : Scène 3D,
Trajectoires, Profils cinématiques, Couverture WFW, Pareto, Analyse & comparaison
et Validation. Les artefacts et statistiques de coûts détaillés restent
accessibles dans **Preuves techniques**; les résultats sont conservés sous `data/runs/<run_id>` pour préserver
la traçabilité. Un run terminé peut être copié à la demande sous
`data/snapshots/<nom>` après validation du manifeste et des artefacts. La copie
reste locale et est ignorée par Git; voir `data/snapshots/README.md` pour le parcours.

## Documentation

- `docs/DECISIONS.md` : journal des décisions techniques (D-BLOCx-yy)
- `docs/RUNBOOK.md`   : comment exécuter, diagnostiquer, reprendre
- `docs/GUIDE_UTILISATEUR_GUI.md` : utiliser l’interface et les exports
- `docs/GUIDE_DEVELOPPEUR_GUI.md` : architecture, tests et reprise du projet
- `docs/SUIVI_AMELIORATION_GUI.md` : registre des phases d’amélioration
- `docs/architecture_current.md` : cartographie historique du pipeline avant l’extraction des services et l’ajout de la GUI

## Structure

    src/          Code source (un module par bloc)
    tests/        Tests unitaires pytest (cas rapides + intégration lente)
    scripts/      Point d'entrée production (run_pipeline.py)
    data/outputs/ Artefacts régénérables (exclus du git)
    data/runs/    Runs GUI isolés (exclus du git)
    data/snapshots/ Snapshots explicites runtime (exclus du git)
    docs/         Documentation technique et schémas

## Résultats de référence

Les résultats numériques dépendent de la plateforme, de la grille et des
paramètres NSGA-II. Le smoke test reproductible est `--fast` : il utilise une
grille 3×3 et les bornes zero-loss adaptées à la plateforme `300x240`.
Les métriques doivent être lues dans `validation_report.json` et
`comparison_diagnostic.json` produits par le run concerné.

## Contact

Henri-Alvin (M1, ESP) — voir `docs/DECISIONS.md` pour l'historique.

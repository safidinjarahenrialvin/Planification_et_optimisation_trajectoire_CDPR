# Référence scientifique du projet Tandem SP2

## Objet

Ce document conserve les mesures historiques du projet avant le début du
développement GUI. Il sert de référence documentaire de non-régression; aucun
snapshot correspondant n’est fourni par défaut dans le dépôt.

## Environnement

- **Branche de référence exécutée :** `feature/gui-improvement`, issue de `main`
- **Commit de code de référence :** `6e8e390` (`docs: add complete Mermaid flowcharts`)
- **Python :** 3.12.3
- **Installation :** environnement virtuel `.venv`
- **Dépendances :** versions exactes de `requirements.txt`
- **Date de référence :** 2026-10-27
- **Mode :** `--fast`
- **Graine NSGA-II :** 42
- **Grille :** 3 × 3, soit 9 points
- **Sous-pas BLOC 6 :** `K=5`
- **Population NSGA-II :** 30
- **Générations NSGA-II :** 100

## Vérifications exécutées

### Tests automatisés

Commande :

```bash
.venv/bin/pytest tests/ -m 'not slow' -q
```

Résultat :

```text
264 passed, 1 deselected in 23.99s
```

Le test exclu est marqué `slow` conformément à la commande de référence.

### Compilation et qualité statique

Commandes :

```bash
.venv/bin/python -m compileall -q src scripts
.venv/bin/ruff check src scripts tests
```

Résultat :

```text
All checks passed!
```

### Smoke test du pipeline

Commande :

```bash
.venv/bin/python scripts/run_pipeline.py \
    --fast \
    --output-dir /tmp/tandem_sp2_reference
```

Le smoke test s’est terminé avec le code retour `0`.

Le statut est `PASS` lorsque le front contient au moins trois compromis
temps-énergie distincts et aucune solution dominée. Le statut `WARN` est
réservé aux fronts de zéro à deux compromis distincts; il ne s’agit pas d’un
`FAIL`.

## Résultats de référence

| Indicateur | Valeur |
|---|---:|
| Points générés | 9 |
| Points filtrés | 9 |
| Entrées de la matrice des coûts | 81 |
| Paires infaisables | 0 |
| Solutions Pareto | 16 |
| Statut validation | `PASS` attendu avec 4 compromis distincts |
| Trajectoires sélectionnées | 3 |
| Baseline | zigzag par lignes |
| Waypoints baseline | 10 |
| Optimisation meilleure que baseline | `True` |
| Gain minimal temps | 6.1535888516327475 % |
| Gain minimal énergie | 12.831856435924854 % |
| Durée totale du smoke test | 7.2 s |

## Statuts du BLOC 10

```text
7 PASS
0 WARN
0 FAIL
```

Le front du mode `--fast` contient 4 compromis temps-énergie distincts : il
franchit donc le nouveau seuil de 3. Le pipeline retourne le code `0`.

## Fichiers produits

Les sorties historiques ont été produites dans un répertoire temporaire lors de
la campagne de référence :

```text
/tmp/tandem_sp2_reference/
```

Ce répertoire comprenait notamment :

- les points générés et filtrés ;
- la matrice des coûts ;
- les solutions Pareto ;
- les trajectoires ;
- les profils cinématiques ;
- le rapport de validation ;
- le rapport d’hypothèses ;
- la baseline et la comparaison ;
- les figures produites par les BLOCs 10 et 11.

## Règle de non-régression

Avant et après chaque étape d’amélioration, il faudra vérifier au minimum :

1. les tests non lents restent réussis ;
2. la compilation et Ruff restent réussis ;
3. le pipeline rapide se termine avec le code `0` ;
4. les colonnes et fichiers attendus restent présents ;
5. le statut ne passe pas de `WARN` attendu à `FAIL` ;
6. les points, coûts et métriques restent compatibles avec un run de référence régénéré, selon les tolérances documentées ;
7. aucune modification de `src/` n’importe Streamlit.

## Limite de cette référence

Cette référence concerne le mode rapide et ne remplace pas une validation de production sur la grille nominale. Elle constitue une base rapide, déterministe et répétable pour détecter les régressions pendant le développement GUI.

La référence de production devra être ajoutée ultérieurement après décision sur le temps de calcul et la taille des artefacts à versionner.

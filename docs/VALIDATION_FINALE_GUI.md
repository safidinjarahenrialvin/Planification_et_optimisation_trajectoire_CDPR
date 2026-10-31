# Validation finale — GUI Tandem SP2

- **Branche :** `feature/gui-improvement`
- **Dernier commit validé :** `8833520` (`test(results): complete CSV and cross-file contracts`)
- **Étapes récentes :** `7618a03` (métriques mouvement/total), `db747e3` (statistiques de gains), `e7f3580` (Historique et runs invalides)
- **Commits fondateurs GUI :** `75901b5` (aperçu Paramètres), `2545512` (CI GUI et santé Streamlit), `6d5f507` (KPI Pareto)
- **Date de validation :** 2026-10-28
- **Portée :** validation locale de reprise et de non-régression; aucun run de production nominal n’a été exécuté.

> **Note de version :** ce rapport est un état historique arrêté au 2026-10-28 et
> au commit indiqué ci-dessus. Depuis, la campagne nominale multi-seeds a été
> exécutée; consulter `docs/RAPPORT_QUALIFICATION_NOMINALE_9X9_2026-10-28.md` et
> le registre `docs/SUIVI_AMELIORATION_GUI.md` pour l’état le plus récent. La
> campagne demeure `NOT_VALIDATED` scientifiquement.

Cette validation décrit l’état actuel de la branche après l’alignement du packaging/CI,
l’harmonisation des métriques temporelles, la traçabilité des gains, l’Historique
autonome et le durcissement des contrats CSV/inter-fichiers.

## Environnement et commandes

L’environnement d’analyse utilise Python 3.12 et les dépendances déclarées par le dépôt.
L’installation reproductible recommandée est :

```bash
python3 -m venv /tmp/tandem-sp2-venv
/tmp/tandem-sp2-venv/bin/python -m pip install -e ".[gui,dev]"
```

Les contrôles exécutés sont :

```bash
pytest -q -m "not slow"
ruff check app services src scripts tests visualization
python -m compileall -q app services src scripts tests visualization
python scripts/run_pipeline.py --fast --output-dir /tmp/tandem-sp2-fast-run
```

Streamlit a également été lancé en mode headless sur le port `18501`; l’endpoint
`/_stcore/health` a retourné `ok`, puis le processus a été arrêté proprement.

## Résultats

| Contrôle | Résultat observé |
|---|---|
| Suite non lente pytest | **335 passed**, 1 test lent exclu |
| Ruff sur toutes les couches | `All checks passed!` |
| Compilation Python | `compileall: OK` |
| Smoke test `--fast` | Code retour `0` |
| Points générés / retenus | `9 / 9` |
| Entrées matrice des coûts / paires infaisables | `81 / 0` |
| Solutions Pareto | `16` solutions brutes, `4` couples temps-énergie distincts |
| Gains minimaux | Temps : `+6,15 %` déterminé par `energy_opt`; énergie : `+12,83 %` déterminé par `time_opt` |
| Flux Paramètres | Aperçu séparé, aperçu obsolète bloqué, bornes `K ≤ 100`, `pop_size ≤ 2000`, `n_gen ≤ 5000` |
| Validation scientifique | `PASS` attendu en mode rapide, `7 PASS`, `0 WARN`, `0 FAIL` |
| Comparaison à la baseline | `optimal_beats_baseline=True` |
| Démarrage GUI | Santé HTTP `ok`; aucun run scientifique implicite observé au démarrage |
| Historique | Sources valides chargeables sans source active; runs invalides isolés et diagnostiqués |
| Contrats de résultats | Types, CSV optionnels, rangs, références, cumuls, `n_waypoints` et baseline contrôlés |
| Libellé baseline nominal à cette révision | `baseline_zigzag` → `Baseline zigzag` |
| Libellé baseline de repli à cette révision | `baseline_nn` → `Baseline plus proche voisin` |
| État Git du checkout | Propre après les contrôles |

Le front du smoke test 3×3 contient 4 compromis temps-énergie distincts et
franchit donc le seuil de 3. Un front de zéro à deux compromis distincts
produirait `WARN`; une solution dominée produirait `FAIL`.

## Packaging et CI

`requirements.txt` contient désormais Streamlit et utilise `pytest==8.4.2`, cohérent
avec la contrainte `pytest>=8,<9` du `pyproject.toml`. La CI GitHub couvre maintenant :

- Ruff sur `app`, `services`, `src`, `scripts`, `tests` et `visualization` ;
- compilation Python de toutes les couches ;
- tests non lents ;
- smoke test scientifique ;
- vérification de la présence des artefacts principaux ;
- démarrage headless de Streamlit et endpoint de santé HTTP.

## Limites de cette validation

- Aucun run complet de production sur la grille nominale n’a été exécuté.
- Le démarrage HTTP confirme que le serveur Streamlit répond, mais ne remplace pas un
  parcours manuel de toutes les pages dans un navigateur.
- Les gains mesurés sont ceux du scénario rapide versionné et ne constituent pas une
  preuve de performance générale.
- La distinction `baseline_zigzag`/`baseline_nn` est couverte par un test ciblé de
  graphique et par les tests de comparaison existants; elle ne constitue pas une
  qualification physique de la baseline.
- Les lignes brutes du front Pareto sont conservées pour la traçabilité des
  permutations co-optimales; l’interface affiche séparément le nombre de compromis
  objectifs distincts.
- La validation des hypothèses physiques B1/B2/B5 reste à réaliser avec les données
  expérimentales ou l’encadrement scientifique approprié.
- L’estimation de durée de la page Paramètres est indicative et n’est pas une
  mesure de performance ni une garantie de délai.
- Les points #2, #9, #11, #18 et #19 du backlog restent ouverts; leur état détaillé,
  ainsi que les points terminés #1 et #6 à #8/#13 à #17, figure dans
  `docs/SUIVI_AMELIORATION_GUI.md`.
- Aucun run nominal 9×9 multi-seeds n’a encore été exécuté; les résultats du smoke
  test 3×3 ne constituent donc pas une qualification scientifique de production.

## Vérifications de référence à relancer

```bash
pytest -q
ruff check app services src scripts tests visualization
python -m compileall -q app services src scripts tests visualization
python scripts/run_pipeline.py --fast --output-dir /tmp/tandem-sp2-fast-run
streamlit run app/streamlit_app.py
```

# Rapport d’exécution — qualification nominale 9×9

**Date :** 2026-10-28
**Branche / révision :** `feature/gui-improvement` / `1f70332`
**Campagne :** `data/qualification/nominal-9x9`
**Protocole :** `docs/QUALIFICATION_NOMINALE_9X9.md`
**Statut scientifique :** `NOT_VALIDATED` — cette campagne collecte des preuves et ne constitue pas une décision d’acceptation des hypothèses.

## Configuration exécutée

La commande exécutée depuis la racine du dépôt était :

```bash
.venv/bin/python -u scripts/qualify_nominal.py \
  --output-dir data/qualification/nominal-9x9 \
  --seeds 42 43 44
```

Paramètres consignés au manifeste : grille 9×9 (`N=81`), plateforme `300x240`, bornes zero-loss activées, `K=10`, `pop_size=500`, `n_gen=1500`, seeds `42`, `43`, `44`. Les configurations effectives sont identiques entre seeds une fois les champs propres au seed exclus ; les empreintes d’exécution diffèrent, comme attendu pour des seeds distinctes. Chaque répertoire de seed conserve son propre jeu complet d’artefacts.

## Résultats synthétiques

| Seed | Run | Validation automatique | Points générés / filtrés | Pareto | Gain temps min. | Gain énergie min. |
|---:|---|---|---:|---:|---:|---:|
| 42 | `COMPLETED` | `WARN` | 81 / 81 | 2 | +20,47 % | +28,06 % |
| 43 | `COMPLETED` | `WARN` | 81 / 81 | 2 | +18,55 % | +26,23 % |
| 44 | `COMPLETED` | `PASS` | 81 / 81 | 4 | +15,26 % | +22,98 % |

Les trois runs indiquent que l’optimisé bat la baseline (`optimal_beats_baseline=true`). Les gains minimaux rapportés restent positifs dans ces trois essais ; leurs amplitudes varient entre seeds. Ces valeurs sont des observations sur ce jeu de données/configuration, pas une généralisation statistique.

Les seeds 42 et 43 rapportent **6 PASS, 1 WARN et 0 FAIL**; la seed 44
rapporte **7 PASS, 0 WARN et 0 FAIL**. Les contrôles automatiques indiquent
pour chaque seed : les 81 points filtrés sont faisables et dans les bornes ; les
6 561 entrées de la matrice de coûts sont cohérentes et faisables ; trois
trajectoires sont valides selon le validateur ; les profils respectent la
vitesse configurée, s’arrêtent aux waypoints et leurs cumuls sont cohérents.

## Écart à examiner

Les fronts Pareto contiennent **2, 2 et 4 compromis distincts**. Avec le seuil
opérationnel actuel, les seeds 42 et 43 restent `WARN`, tandis que la seed 44
est `PASS` sur ce contrôle. La campagne ne démontre donc pas la stabilité du
front ; l’écart de cardinalité observé entre seeds doit être évalué selon le
protocole et les critères scientifiques. Les contrôles de trajectoires sont
des validations internes du pipeline, non une confirmation expérimentale de
leur validité physique sur un prototype.

Le manifeste de campagne conserve explicitement `scientific_status: NOT_VALIDATED`. Aucun changement de statut n’est apporté à B1, B2 ou B5 ; une revue humaine séparée reste requise, incluant la stabilité du Pareto, les trajectoires, les gains, les sources de paramètres et les seuils d’acceptation.

## Analyse de stabilité Pareto ajoutée

Une analyse reproductible a été exécutée après la campagne, sans recalculer les
runs :

```bash
.venv/bin/python scripts/analyze_pareto_stability.py \
  --campaign-dir data/qualification/nominal-9x9
```

Les indicateurs observés sont :

| Indicateur | Résultat |
|---|---:|
| Cardinalité Pareto | 2, 2 et 4 |
| Coefficient de variation de la cardinalité | 0,354 |
| Distance de Hausdorff normalisée moyenne | 0,8792 |
| Distance de Hausdorff normalisée maximale | 1,3184 |
| Recouvrement des enveloppes temporelles | 0 pour chaque paire |
| Recouvrement des enveloppes énergétiques | 0 pour chaque paire |

Les enveloppes temporelles et énergétiques des fronts ne se recouvrent pas entre
les seeds dans cette campagne. Les fronts sont donc numériquement variables dans
les conditions exécutées. Cette observation ne fixe pas automatiquement un seuil
d’acceptation et ne transforme pas le statut scientifique : la campagne reste
`NOT_VALIDATED` et `REVIEW_REQUIRED` pour la stabilité.

Le détail machine-readable et le résumé lisible sont conservés dans
`data/qualification/nominal-9x9/pareto_stability_report.json` et
`data/qualification/nominal-9x9/pareto_stability_report.md`.

## Artefacts archivés

- `data/qualification/nominal-9x9/qualification_manifest.json` — spécification, statut et résultats par seed.
- `data/qualification/nominal-9x9/qualification_summary.csv` — résumé tabulaire.
- `data/qualification/nominal-9x9/seed_{42,43,44}/` — manifestes et artefacts complets indépendants par seed.

La durée de l’exécution observée était d’environ six minutes dans l’environnement sandbox ; elle constitue une observation unique et ne doit pas être considérée comme une estimation garantie pour d’autres environnements.

# Protocole de qualification nominale 9×9

## Objet

Ce protocole décrit une campagne reproductible destinée à qualifier le comportement du pipeline SP2 sur la grille nominale 9×9. La campagne produit des runs séparés par seed, conserve leurs artefacts complets et génère un résumé comparatif.

La campagne ne déclare pas automatiquement les hypothèses physiques validées. Le champ `scientific_status` du manifeste reste donc `NOT_VALIDATED` jusqu’à revue scientifique explicite.

## Configuration par défaut de la campagne

```text
Grille                  : 9×9, N=81
Plateforme              : 300×240
Bornes opérationnelles  : zero-loss activées
Sous-pas BLOC 6         : K=10
Population NSGA-II      : 500
Générations NSGA-II     : 1500
Seeds                   : 42, 43, 44
```

Ces valeurs correspondent au profil nominal actuellement exposé par la GUI. Toute modification doit être documentée dans le manifeste de campagne.

## Exécution

Depuis la racine du dépôt :

```bash
.venv/bin/python scripts/qualify_nominal.py \
  --output-dir data/qualification/nominal-9x9 \
  --seeds 42 43 44
```

La même campagne peut être lancée depuis GitHub Actions avec le workflow
manuel **Nominal 9x9 qualification**. Les paramètres `seeds`, `pop_size` et
`n_gen` sont visibles avant le lancement et les artefacts sont conservés dans
un artefact GitHub nommé `qualification-nominal-9x9-<run_id>`.

Ce workflow ne se déclenche jamais automatiquement et ne transforme pas le
résultat en validation scientifique : le manifeste reste `NOT_VALIDATED` et
la revue des critères ci-dessous doit être effectuée séparément.

La possibilité de le déclencher depuis l’interface ou l’API GitHub dépend aussi
de la présence du fichier de workflow sur la branche par défaut. Tant que ce
workflow reste uniquement sur une branche de fonctionnalité, GitHub peut
répondre `404` au dispatch manuel ; dans ce cas, utiliser l’exécution locale
documentée ci-dessus et ne pas présenter un artefact GitHub comme disponible.

Pour une campagne de validation technique courte, il est possible de réduire le budget explicitement, mais ses résultats ne doivent pas être présentés comme une qualification scientifique :

```bash
.venv/bin/python scripts/qualify_nominal.py \
  --output-dir /tmp/tandem-qualification-smoke \
  --seeds 42 43 \
  --pop-size 10 \
  --n-gen 2
```

## Artefacts produits

```text
<campaign>/
├── qualification_manifest.json
├── qualification_summary.csv
├── seed_42/
│   ├── config.json
│   ├── run_manifest.json
│   ├── validation_report.json
│   ├── comparison_diagnostic.json
│   └── ...
├── seed_43/
└── seed_44/
```

Chaque répertoire `seed_*` est un run indépendant. Aucun fichier scientifique n’est fusionné entre les seeds.

## Analyse de stabilité du front Pareto

Après une campagne existante, lancer l’analyse sans recalculer le pipeline :

```bash
.venv/bin/python scripts/analyze_pareto_stability.py \
  --campaign-dir data/qualification/nominal-9x9
```

Le script produit `pareto_stability_report.json` et
`pareto_stability_report.md`. Il compare les colonnes `time` et `energy` de
`solutions_pareto.csv` pour chaque seed, en conservant le statut scientifique
`NOT_VALIDATED` et le statut de stabilité `REVIEW_REQUIRED` tant qu’aucun seuil
n’a été accepté par l’encadrement.

Les indicateurs sont les suivants :

- cardinalité du front par seed, moyenne, écart-type et coefficient de variation ;
- min, max, moyenne et écart-type de chaque objectif ;
- recouvrement des enveloppes temporelles et énergétiques ;
- distance de Hausdorff et distance de Chamfer dans l’espace des objectifs
  normalisé par l’étendue observée de la campagne ;
- fraction de chaque front faiblement dominée par l’autre front, avec les deux
  directions conservées.

Ces mesures décrivent la variabilité numérique entre seeds. Elles ne constituent
pas à elles seules une validation scientifique : les seuils d’acceptation, la
stabilité des trajectoires et l’interprétation physique doivent être définis
avec l’encadrement.

## Critères à vérifier par la revue scientifique

1. Chaque seed possède un manifeste `COMPLETED` et un statut de validation sans `FAIL`.
2. La configuration effective et l’empreinte sont identiques hors seed.
3. Les points générés et filtrés sont cohérents entre les seeds.
4. Le nombre de solutions Pareto et leur distribution sont suffisamment stables.
5. Les trajectoires sélectionnées restent physiquement valides.
6. Les gains par rapport à la baseline ne changent pas de signe de manière inexpliquée.
7. Les hypothèses B1, B2 et B5 sont confirmées ou réfutées avec les encadrants et les données disponibles.
8. Les seuils d’acceptation sont consignés dans un rapport scientifique séparé.

Le script fournit la collecte des preuves, mais la décision de clôture reste humaine et scientifique.

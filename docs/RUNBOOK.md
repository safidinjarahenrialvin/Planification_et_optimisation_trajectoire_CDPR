# `docs/RUNBOOK.md` — Guide complet d'exécution

```markdown
# RUNBOOK — Exécution du pipeline SP2

**Version** : v3.5 (plateforme 300×240, zero-loss adaptatif)
**Portée** : comment relancer le pipeline après un changement de
`Config`, une modification de code, ou pour regénérer les artefacts
du mémoire.

---

## 1. Prérequis

- Environnement virtuel activé (`.venv`) :
  ```bash
  cd ~/projets/tandem_sp2
  source .venv/bin/activate
  ```
- Toutes les dépendances installées (`pip install -r requirements.txt`)
- Être à la racine du projet (`tandem_sp2/`)

Vérification rapide de l'environnement :
```bash
python --version                    # Python 3.12+ supporté
python -c "import numpy, scipy, pymoo; print('OK')"
ruff check src/ scripts/ tests/     # doit afficher "All checks passed!"
pytest tests/ -m "not slow" -q     # suite rapide verte
```

---

## 2. Référence rapide — les 5 commandes les plus utiles

| Objectif | Commande |
|---|---|
| **Smoke test** (~30 s) | `python scripts/run_pipeline.py --fast` |
| **Run de référence** (~7 min) | `python scripts/run_pipeline.py --zero-loss` |
| **Run rapide** (~1 min) | `python scripts/run_pipeline.py --n 5 --zero-loss` |
| **Vue 3D interactive** | `python scripts/view_robot_3d.py` puis `xdg-open data/outputs/figures/robot_3d_300x240.html` |
| **Comparer plateformes** | `python scripts/sweep_wfw.py --quick --platform 250x200` |

---

## 3. Test rapide (smoke test, ~30 s)

À lancer **avant tout run complet** — valide la chaîne de bout en bout
sur une grille 3×3 avec bornes zero-loss adaptées à la plateforme.

```bash
python scripts/run_pipeline.py --fast
```

**Attendu** :
- `Plateforme 300x240 : demi-étendues (0.150, 0.120) m, masse estimée 384.0 g.`
- `PointFilter : 9/9 retenus` (ou moins si `--xy-bound` est petit)
- `Validation : WARN` uniquement sur `solutions_pareto` (normal sur 3×3)
- Timings : ~10–30 s

Si ce mode échoue, **ne pas lancer le run complet** — corriger d'abord.

---

## 4. Run de référence (production mémoire)

```bash
rm -rf data/outputs/*
python scripts/run_pipeline.py --zero-loss
```

**Configuration effective** :
- Plateforme 300×240 mm (défaut)
- Grille 9×9 (N=81), espacement `(0.10, 0.06) m`
- Bornes X ±0.40, Y ±0.24 (zero-loss adapté à la plateforme)
- NSGA-II : pop=500, gen=1500
- Runtime : **~7 min**

**Attendu** :
- `PointFilter : 81/81 retenus, 0 Cause A, 0 Cause B`
- `Matrice de coûts : 0 paires infaisables`
- `NSGA-II : 2 solutions non dominées après post-filtrage`
- `optimal_beats_baseline : True`
- `min_time_gain_pct : +20.5 %`, `min_energy_gain_pct : +28.1 %`
- `Validation : PASS` si le front contient au moins 3 compromis distincts et aucune solution dominée; `WARN` uniquement sous ce seuil

---

## 5. Options CLI complètes

### `scripts/run_pipeline.py`

| Option | Défaut | Effet |
|---|---|---|
| `--fast` | — | Grille 3×3, NSGA réduit (~30 s) |
| `--n N` | 9 | Taille de grille N×N (impair ≥ 3) |
| `--platform WxH` | `300x240` | Taille de plateforme (nom ou dimension) |
| `--platform-mass M` | auto | Masse en **grammes** (override) |
| `--zero-loss` | désactivé | Bornes resserrées par plateforme |
| `--xy-bound B` | — | Bornes X=Y symétriques (m) |
| `--x-bound B` | — | Borne X uniquement (m) |
| `--y-bound B` | — | Borne Y uniquement (m) |
| `--z-absolu Z` | 0.45 | Hauteur caméra dans R0 (m) |
| `--pop-size N` | table | Population NSGA-II |
| `--n-gen N` | table | Générations NSGA-II |
| `--seed S` | 42 | Graine NSGA-II |
| `--output-dir DIR` | `data/outputs` | Répertoire de sortie |
| `--resume` | désactivé | Skip les étapes déjà effectuées |
| `--verbose` | désactivé | Logs DEBUG |

### Autres scripts

| Script | Usage principal |
|---|---|
| `scripts/run_wfw_3d.py` | Visualisation 3D multi-volumes WFW |
| `scripts/sweep_wfw.py` | Balayage (T_min, T_max) → CSV + heatmap |
| `scripts/view_robot_3d.py` | Vue 3D interactive (HTML) du robot |

Options communes : `--platform`, `--output-dir`, `--verbose`.
Options spécifiques : voir `--help` de chaque script.

---

## 6. Interprétation du rapport de validation

Le `validation_report.json` retourne un `overall_status` :

| Statut | Signification | Action |
|---|---|---|
| **`PASS`** | Les 7 checks passent | Artefacts prêts pour le mémoire |
| **`WARN`** | Au moins un check en avertissement | Artefacts utilisables, à documenter |
| **`FAIL`** | Au moins un check échoue | **NE PAS UTILISER** — voir §9 |

### WARN fréquents et légitimes

| Check | Cause | Interprétation |
|---|---|---|
| `solutions_pareto` | Front < 10 solutions | Corrélation temps/énergie forte (ρ ≈ 0.98) — front intrinsèquement étroit |
| `cost_matrix` | Paires infaisables > 0 | WFW rétréci à haute altitude — comportement physique |
| `points_filtres` | Points rejetés | Bords hors WFW — grille > zone utile |

### FAIL — symptômes typiques

| Symptôme | Cause probable | Solution |
|---|---|---|
| `config_consistency` FAIL | Matrice W singulière | Voir §9 (plateforme carrée) |
| `trajectories` FAIL | Tour sans centre | Vérifier `PointFilter` |
| `profiles` FAIL | v > v_max | Bug profiler — vérifier `cost_matrix` |

---

## 7. Régénérer une étape ciblée

### Principe du `--resume`

Le pipeline détecte les étapes dont **tous les fichiers de sortie non vides
existent** et les skippe. La reprise exige également `.config_hash` ; sans
ce fichier, elle est refusée pour éviter de mélanger des configurations. Pour
forcer la régénération d'une étape,
**supprimer ses sorties** :

```bash
# Exemple : régénérer uniquement BLOC 7 (optimiseur)
rm data/outputs/solutions_pareto.csv
rm data/outputs/solutions_orders.csv
python scripts/run_pipeline.py --zero-loss --resume
```

### Table de correspondance étape ↔ fichiers

| Étape | Fichiers de sortie |
|---|---|
| 4 — PointGenerator | `points_generes.csv`, `points_generes_report.json` |
| 5 — PointFilter | `points_filtres.csv`, `points_rejetes_*.csv`, `point_filter_report.json` |
| 6 — CostCalculator | `cost_matrix.csv` |
| 7 — Optimizer | `solutions_pareto.csv`, `solutions_orders.csv` |
| 8 — Extractor | `trajectories.csv`, `trajectories_summary.csv` |
| 9 — Profiler | `profiles*.csv` (4 fichiers) |
| 10 — Validator | `validation_report.json`, `figures/*.png`, `hypotheses_report.*` |
| 11 — Comparator | `baseline_zigzag.csv`, `comparison*.csv`, `figures/comparison*.png` |

### Régénération **complète** d'un run

```bash
rm -rf data/outputs/*
python scripts/run_pipeline.py --zero-loss
```

---

## 8. Comparer plusieurs configurations

### Scénario A — Comparer deux plateformes

```bash
# Plateforme 300x240 (défaut)
rm -rf /tmp/cmp_300x240
python scripts/run_pipeline.py --zero-loss \
    --n 5 --xy-bound 0.25 --output-dir /tmp/cmp_300x240

# Plateforme 250x200
rm -rf /tmp/cmp_250x200
python scripts/run_pipeline.py --zero-loss --platform 250x200 \
    --n 5 --xy-bound 0.25 --output-dir /tmp/cmp_250x200

# Comparer les rapports
for d in /tmp/cmp_300x240 /tmp/cmp_250x200; do
    echo "=== $d ==="
    python -c "
import json
with open('$d/comparison_diagnostic.json') as f:
    d = json.load(f)
print(f\"  gain_temps  : {d['min_time_gain_pct']:+.2f} %\")
print(f\"  gain_energie: {d['min_energy_gain_pct']:+.2f} %\")
"
done
```

### Scénario B — Sweep WFW multi-plateformes

```bash
python scripts/sweep_wfw.py --quick --platform 300x240
python scripts/sweep_wfw.py --quick --platform 250x200
python scripts/sweep_wfw.py --quick --platform 700x560

# Extraire la paire nominale (T_min=1, T_max=58) de chaque CSV
for f in data/outputs/sweep_*.csv; do
    echo "=== $f ==="
    head -1 "$f"
    awk -F, '$1==1.0 && $2==58.0 {print}' "$f"
done
```

---

## 9. Diagnostic des échecs courants

### Erreur — `InsufficientPointsError`

```
Configuration inviable — Trop peu de points retenus après filtrage : 1 < 4
```

**Cause** : la grille dépasse largement le WFW. Trop de points rejetés.

**Solutions** :
1. Utiliser `--zero-loss` (bornes adaptées à la plateforme)
2. Réduire l'extent : `--xy-bound 0.25`
3. Agrandir la plateforme : `--platform 700x560`

### Erreur — `DegenerateFrontError`

```
Front NSGA-II dégénéré : toutes les solutions sont pénalisées
```

**Cause** : aucun chemin hamiltonien dans le graphe de faisabilité.

**Solutions** :
1. Vérifier `cost_matrix.csv` : combien de paires infaisables ?
2. Si > 50 % infaisables → augmenter `T_max` ou réduire `z_absolu`
3. Vérifier que la plateforme n'est **pas carrée** (voir ci-dessous)

### Erreur — Singularité `rang(W) < 6`

```
Matrice W singulière (rang 5 < 6). Le robot ne peut pas contrôler les 6 DOF.
```

**Cause** : plateforme carrée avec ancrages carrés — perte du degré de
liberté de lacet. Voir D-CONFIG-09.

**Solution** : utiliser une plateforme au **ratio d'aspect ≥ 1.20**
(300×240 = 1.25, 700×560 = 1.25). **Jamais** de carré (560×560, 630×630).

### Erreur — WFW rétréci à haute altitude

```
Taux de rejet 40 % ≥ seuil 15 %
```

**Cause** : `z_absolu` trop élevé → câbles presque horizontaux → tensions saturées.

**Solutions** :
1. Réduire `z_absolu` : `--z-absolu 0.35`
2. Agrandir la plateforme
3. Réduire la hauteur de plants (hypothèse B2)

### Warning — Front de Pareto étroit

```
Front de 2 compromis distincts (< 3)
```

**Cause** : corrélation forte temps/énergie sur cette instance.

**Ce n'est pas un défaut** — c'est un résultat scientifique et un front très
court (cf. D-BLOC10-07). Documenter dans le mémoire, ne pas « corriger ».

---

## 10. Visualisation 3D

### Vue interactive du robot (Plotly HTML)

```bash
# Vue simple (robot au centre, pas de trajectoire)
python scripts/view_robot_3d.py

# Avec une trajectoire en surimpression
python scripts/view_robot_3d.py \
    --trajectory data/outputs/trajectories.csv \
    --kind time_opt \
    --points data/outputs/points_filtres.csv \
    --output data/outputs/figures/robot_3d_time_opt.html

# Ouvrir dans le navigateur
xdg-open data/outputs/figures/robot_3d_time_opt.html
```

**Contrôles souris** :
- Clic gauche = rotation
- Molette = zoom
- Clic droit = pan
- Bouton "Télécharger PNG" en haut à droite

### Volumes WFW imbriqués (matplotlib PNG)

```bash
python scripts/run_wfw_3d.py --n-xy 25 --n-z 15 --platform 300x240
```

**Sortie** : `data/outputs/figures/wfw_3d_combined.png` — volumes WCW et
WFW calculés avec les limites de tension de la configuration active.

---

## 11. Régénérer après un changement de `Config`

**Procédure complète** :

1. Modifier `src/config.py` (avec justification)
2. **Documenter** la modification dans `docs/DECISIONS.md`
3. Lancer un smoke test : `python scripts/run_pipeline.py --fast`
4. Si OK, lancer le run complet :
   ```bash
   rm -rf data/outputs/*
   python scripts/run_pipeline.py --zero-loss
   ```
5. Vérifier `PASS` ou `WARN` justifié dans le rapport final
6. Régénérer la vue 3D :
   ```bash
   python scripts/view_robot_3d.py
   ```
7. Committer **d'abord** `docs/DECISIONS.md` puis `git add src/ scripts/ tests/`

---

## 12. Ce qu'il ne faut PAS faire

- ❌ **Modifier un CSV à la main** dans `data/outputs/` — il sera
  écrasé au prochain run.
- ❌ **Relancer un run complet sans raison** — utiliser `--resume`.
- ❌ **Utiliser une plateforme carrée** avec ancrages carrés
  (560×560, 630×630) — singularité W (D-CONFIG-09).
- ❌ **Changer un paramètre de `Config` sans le documenter** dans
  `docs/DECISIONS.md`.
- ❌ **Ignorer un `WARN`** — le comprendre et le documenter.
- ❌ **Commiter `data/outputs/*.csv`** — ce sont des artefacts
  régénérables (déjà dans `.gitignore`).
- ❌ **Utiliser `--resume` après un changement de `Config`** — les
  fichiers de sortie ne sont plus valides. Supprimer `data/outputs/*`
  d'abord.

---

## 13. Temps de calcul de référence

| Configuration | Étape 6 | Étape 7 | Total |
|---|---|---|---|
| `--fast` (3×3) | 1 s | 1 s | **~10 s** |
| `--n 5 --zero-loss` | 15 s | 11 s | **~1 min** |
| `--n 7 --zero-loss` | 30 s | 30 s | **~2 min** |
| `--n 9 --zero-loss` | 2 min 30 s | 4 min | **~7 min** |
| `--n 11 --zero-loss` | 6 min | 15 min | **~25 min** |

BLOC 6 (coût matrice) et BLOC 7 (NSGA-II) dominent. Pour itérer, préférer
`--n 5` ou `--n 7`.

---

## 14. Reprise par un tiers

Le projet est conçu pour être **repris sans échange oral** :

1. **Lire `README.md`** — vue d'ensemble.
2. **Lire `docs/DECISIONS.md`** — historique des choix techniques (D-xxx-yy).
3. **Lire ce document** (RUNBOOK) — exécution.
4. **Lancer les tests** :
   ```bash
  pytest tests/ -v -m "not slow"     # suite rapide verte
   ```
5. **Smoke test** :
   ```bash
   python scripts/run_pipeline.py --fast
   ```
6. **Run de référence** :
   ```bash
   python scripts/run_pipeline.py --zero-loss
   ```

---

## 15. Historique des versions

| Version | Date | Changement majeur |
|---|---|---|
| v3.0 | 2026-09-12 | Base — grille 9×9, plateforme 200×160 (v3.0 original) |
| v3.1 | 2026-09-13 | Plateforme 700×560, grille 7×7, T_max 58 N |
| v3.2 | 2026-09-15 | Grille 9×9, bornes ±0.80 m, N=81 |
| v3.3 | 2026-09-16 | WFW 3D multi-volumes, sweep (T_min, T_max) |
| v3.4 | 2026-09-17 | Fix rang(W), tests de non-singularité |
| **v3.5** | **2026-09-17** | **Plateforme 300×240 par défaut, zero-loss adaptatif, DEFAULT_PLATFORM** |

---

## 16. Contact / ressources

- **Code source** : `src/` (un module par bloc, 12 blocs)
- **Tests** : `tests/` (264 tests rapides, 1 test slow)
- **Scripts CLI** : `scripts/` (4 scripts, tous documentés `--help`)
- **Documentation** :
  - `docs/DECISIONS.md` — journal des choix techniques
  - `docs/RUNBOOK.md` — ce document
  - `docs/figures/` — organigrammes des blocs (à venir)
- **Artefacts produits** : `data/outputs/` (régénérables, hors git)
```

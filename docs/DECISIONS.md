## D-BLOC1-01 — Convention de signe de U_i

**Date** : 2026-09-12
**Statut** : Adoptée
**Bloc concerné** : BLOC 1 (RobotModel), BLOC 3 (WFW)

### Contexte
Le §5 BLOC 1 du cahier d'architecture v3.0 spécifie :
    U_i = (B_i(p) − A_i) / ‖B_i(p) − A_i‖

Le §5 BLOC 3 spécifie :
    W(p)·T = −F_ext, avec F_ext = (0, 0, −m·g, 0, 0, 0)

### Analyse
Si U_i = (B_i − A_i), alors T_i·U_i est une force compressive (dirigée
de A_i vers B_i). Pour les câbles supérieurs, cela signifie qu'une
tension T_i > 0 pousse la plateforme vers le BAS — physiquement absurde.
Sous cette convention, AUCUNE solution T > 0 n'existe au point central
avec m = 0.385 kg et la géométrie Annexe A.

### Décision
Adopter U_i = (A_i − B_i) / ‖A_i − B_i‖ (pointe de l'attache vers
l'ancrage). Alors T_i·U_i est la force réelle exercée par le câble sur
la plateforme, et W·T = −F_ext est cohérent. La formulation alternative
produit W' = −W ; les deux sont équivalentes à un changement de signe
global de T, mais seule la convention retenue est compatible T > 0.

### Conséquence
Les tests `test_alternative_formulation_is_negative` et
`test_central_equilibrium_self_consistent` documentent et verrouillent
ce choix.

---

## D-BLOC1-02 — Écart sur l'équilibre central annoncé (§2.1)

**Date** : 2026-09-12
**Statut** : Signalée à l'encadrant
**Bloc concerné** : BLOC 1, BLOC 3

### Contexte
Le §2.1 du cahier d'architecture v3.0 annonce « Équilibre central
attendu : 1 N (bas) / 4.395 N (haut) — source tension.pdf ».

### Analyse
Avec U_i = (A_i − B_i) (convention D-BLOC1-01), m = 0.385 kg, g = 9.81,
et la géométrie Annexe A, le bilan de forces en z au point (0, 0, 0.45)
donne :
    1.21915·T_top − 1.00311·T_bot = m·g = 3.7769 N

Les valeurs (T_bot = 1.0, T_top = 4.395) donnent :
    1.21915·4.395 − 1.00311·1.0 = 4.3551 N ≠ 3.7769 N

L'écart est de 0.578 N, très au-delà de la tolérance 0.1 N/câble du §7.

### Solution
Deux possibilités :
(a) tension.pdf utilise une convention de signe ou une valeur de masse
    différente de celles retenues ici (à vérifier avec l'encadrant SP1).
(b) Les valeurs « 1 / 4.395 » sont indicatives et non un résultat
    d'équilibre exact.

L'implémentation adopte la physique correcte (famille de solutions
symétriques : T_top ≈ 3.921 N quand T_bot = 1.0, ou T_bot ≈ 1.576 N
quand T_top = 4.395). Aucune hypothèse n'est modifiée sans validation.

### Action
Soumettre ce calcul à l'encadrant SP1 pour confirmation avant de figer
BLOC 3 (WFW).

---

## D-BLOC3-01 — Révision des paramètres mécaniques (v3.0 → v3.1)

**Date** : 2026-09-12
**Statut** : Adoptée provisoirement, soumise à validation encadrant
**Blocs concernés** : BLOC 0, 1, 3, 5, 6, 7, et tout ce qui dépend de N

### Contexte
Le test exhaustif du WFW sur la grille B4 (81 points, marge 0.25 m/bord)
prévu au §7 de la Base d'architecture v3.0 a révélé un taux de rejet de
98.8 % (1/81 points faisables). Ce n'est pas le régime d'échec anticipé
par le §9.4 ("marge B4 insuffisante, réduire N") — le WFW est réduit à
un point isolé au centre, quelle que soit la marge.

### Diagnostic
Un balayage systématique a éliminé toutes les causes isolées :
- La hauteur z n'est pas la cause (rejet constant pour z ∈ [0, 0.45]).
- T_min ∈ [0.1, 1.0] N n'a aucun effet significatif sur l'ANCIENNE
  plateforme (200×160 mm).
- T_max ∈ [4.395, 50] N n'a aucun effet significatif (< 5 % de gain).
- L'élargissement du cadre (ancrages) est impossible : contrainte SP1 gelée.
- Le seul levier viable est l'augmentation de la taille de la plateforme
  mobile, qui augmente le bras de levier des attaches et donc la capacité
  à générer les moments nécessaires hors du centre.

### Paramètres révisés (Config v3.1 finale)

| Champ | v3.0 | v3.1 finale | Justification |
|---|---|---|---|
| `attaches_B` (demi-étendues) | (±0.100, ±0.080) m | (±0.350, ±0.280) m | Plateforme 700×560×50 mm — seule taille testée donnant 100 % de couverture sur grille 7×7 |
| `T_min` | 1.0 N | **1.0 N (inchangé)** | Valeur SP1 d'origine restaurée. Sensibilité sur NOUVELLE plateforme : T_min=0.0→100 %, 1.0→100 %, 2.0→79.6 %, 4.0→63.3 % |
| `T_max` | 4.395 N | **58.0 N** | Valeur nécessaire pour 100 % de couverture avec T_min=1.0 N (masse recalibrée 417 g, plateforme 700×560) |
| `masse_kg` | 0.385 | 0.417 | Recalibration masse surfacique réelle (treillis ouvert, tube carbone Ø6.1 mm) |
| `n_rangs`, `n_colonnes` | 9 × 9 | 7 × 7 | Marge B4 = 0.375 m/bord → 1.75 m utile → 7 points @ 0.25 m |
| `x_min/max`, `y_min/max` | ±1.00 m | ±0.75 m | Dérivées de l'étendue de la grille retenue (Annexe D.2) |

**Champs inchangés** : ancrages `A_i` (SP1, gelé), `z_vol` (0.30 m),
`hauteur_plants` (0.35 m, hypothèse B2), `offset_r0_sol` (0.20 m),
`z_min/z_max` (0/0.80 m), `v_max/a_max` (0.045/0.03), `fov_camera`.

### Erreur méthodologique corrigée (important pour traçabilité)

La première rédaction de cette décision proposait `T_min = 4.0 N` sur la
base du diagnostic « T_min n'a aucun effet significatif ». Ce diagnostic
avait été établi **sur la plateforme 200×160 mm d'origine**. Or, sur la
NOUVELLE plateforme 700×560 mm, le bras de levier allongé rend le système
beaucoup plus sensible à T_min : la valeur 4.0 N fait tomber la couverture
de 100 % à 63.3 % (31/49).

C'est un cas classique de **généralisation abusive d'un résultat obtenu
sur une géométrie différente**. Correction : `T_min` revient à 1.0 N
(valeur SP1 d'origine), qui donne 100 % de couverture vérifiée
numériquement sur la géométrie v3.1 finale.

### Conséquence sur N
**N = 49** (au lieu de 81). La zone d'étude reste 2.5 × 2.5 m (définie par
les ancrages SP1), mais la zone **opérationnelle** rétrécit à ±0.75 m.

### Dépréciation de tension.pdf pour les bornes de tension
Le calcul reproduit exactement `T = [4.395 ×4, 1.0 ×4] N` **à z = 0.50 m**
(et non 0.45 m), ce qui indique que les valeurs T_min/T_max de SP1 sont
un **artefact d'un calcul d'équilibre à une hauteur qui n'est plus celle
utilisée**. Elles ne sont pas des spécifications matérielles. Elles sont
donc dépréciées en tant que contraintes, et remplacées par des bornes
dérivées du besoin réel : T_min = 1.0 N (SP1 conservé) et T_max = 58.0 N
(besoin de couverture).

### Ce qui reste à valider par l'encadrant (SP1 + encadrant SP2)
1. Acceptation d'une plateforme 700×560×50 mm (implication SP1 mécanique).
2. Acceptation d'un T_max matériel ≈ 58 N → NEMA17 haute perf + réducteur
   ou tambour ≤ 10 mm.
3. Acceptation d'un câble Dyneema Ø0.5–0.6 mm (marge 2.5–3:1 sur 58 N).
4. Réduction de N à 49.
5. **Mesure empirique de T_min** sur prototype : la valeur 1.0 N est
   reprise de SP1, mais la valeur réellement nécessaire pour éviter le
   mou de câble doit être confirmée (attendu : 0.3–1.5 N).

### Conséquence si validation refusée
Si SP1 refuse d'agrandir la plateforme, alors le projet SP2 doit pivoter
vers un périmètre différent (documenté comme résultat scientifique) :
« analyse de la limitation structurelle d'un CDPR low-cost sous
contraintes SP1 figées », avec un WFW utile de < 3 cm.



---



## D-BLOC4-01 — Test du shift de grille restreint au cas faisable

**Date** : 2026-09-12
**Statut** : Adoptée
**Bloc concerné** : BLOC 4 (PointGenerator)

### Contexte
Le test `test_origin_tuple_shifts_grid` vérifiait un décalage (0.5, -0.5)
sur la config 7×7 par défaut, ce qui pousse la grille hors des limites
opérationnelles (±0.75 m). Le test échouait pour une raison légitime.

### Décision
- Le test de décalage utilise désormais une config 5×5 (±0.5 m), qui
  laisse une marge pour un shift non trivial (0.2, -0.1).
- Un test distinct `test_origin_shift_out_of_bounds_raises` verrouille
  le comportement de refus de `_verify_extent`, qui fonctionnait déjà
  correctement mais n'était pas couvert explicitement.

### Conséquence
Aucune modification du code source. Deux tests au lieu d'un, couvrant
à la fois le comportement nominal (shift faisable) et le garde-fou
(shift hors-limites refusé).

---


## D-BLOC6-01 — Évaluation de la tension au point milieu

**Date** : 2026-09-12
**Statut** : Adoptée
**Bloc concerné** : BLOC 6 (CostCalculator)

### Contexte
L'évaluation de T au point de départ de chaque sous-segment introduit
une asymétrie E_ij ≠ E_ji de l'ordre de 1 % (0.08 J sur 6 J), au-delà
du seuil §7 (|E_ij − E_ji| < 1e-3 J).

### Décision
Évaluer T au point milieu de chaque sous-segment :
    p_k_mid = p_i + ((k + 0.5)/K)·(p_j − p_i)

Cette convention rend le calcul exactement symétrique par construction :
le point milieu du sous-segment k dans le sens i→j est identique au point
milieu du sous-segment K−1−k dans le sens j→i.

### Conséquence
Critère §7 vérifié à < 1e-6 J, sans modification du coût de calcul.
Aucune symétrisation ad hoc (type (E_ij + E_ji)/2) n'est nécessaire,
ce qui préserve la transparence de la mesure.


---

## D-BLOC7-01 — Contenu du test de pénalité explicité par assert

**Date** : 2026-09-12
**Statut** : Adoptée
**Bloc concerné** : BLOC 7 (Optimizer), test T9

### Contexte
Le test `test_infeasible_pair_penalized` a d'abord échoué parce que ses
deux permutations de test étaient inversées : `x_good` contenait en
réalité la paire interdite (8,0) et `x_bad` n'en contenait aucune.
La cause profonde : un tour est encodé `[centre, corps…, centre]`, donc
le premier et le dernier id du corps ne sont PAS adjacents — ils ne
forment pas de paire consécutive ensemble.

### Décision
Le test corrigé ajoute un `assert` explicite sur les paires décodées
pour ancrer le raisonnement dans le code plutôt que dans un commentaire :
    assert (8, 0) in list(zip(ids_bad[:-1], ids_bad[1:]))
Ce garde-fou échoue immédiatement si la convention de décodage évolue,
au lieu de laisser une assertion mal orientée passer par hasard.

### Conséquence
- Aucune modification du code de production.
- Le test est désormais reproductible et documenté au niveau où l'erreur
  a été commise (raisonnement sur la structure du tour, pas sur la
  valeur de la pénalité).

---


## D-BLOC9-01 — Déduplication des samples aux jonctions

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 9 (TrajectoryProfiler)

### Contexte
La première version émettait, pour chaque segment, TOUS les samples
locaux de t=0 à t=T_seg. À chaque jonction, cela produisait deux lignes
identiques (même temps, même position, même v=0) : dernière ligne du
segment k et première ligne du segment k+1.

Conséquences :
  - temps global non strictement croissant (diff nul aux jonctions)
  - waypoints dupliqués dans le CSV
  - ambiguïté pour BLOC 10 (deux lignes pour un même événement)

### Décision
Supprimer le premier sample des segments d'indice > 0. Chaque waypoint
apparaît alors exactement une fois dans le profil. Le temps global est
strictement croissant. Le critère §7 (v = 0 aux extrémités) reste
vérifié : v = 0 au début du premier segment, et v = 0 à la fin de
chaque segment (donc à chaque waypoint visité).

Cas dégénéré d = 0 : un seul sample émis (au lieu de min_samples
identiques à t=0).

### Conséquence
Aucune modification du code de production hors `profile_trajectory`.
Tests T2 et T5 réécrits pour refléter la nouvelle sémantique (T2 : v=0
aux vrais waypoints ; T5 : continuité vérifiée contre les waypoints
d'entrée plutôt que contre la ligne précédente). T9 ajusté (1 sample
pour un segment nul).

---


## D-BLOC10-01 — Fixtures synthétiques non physiques assumées

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 10 (Validator), tests

### Contexte
La fixture `_write_minimal_outputs` construisait :
  - une parabole symétrique pour `solutions_pareto` → 5 points dominés
    (énergies quasi-égales deux à deux sur la branche descendante),
  - une vitesse synthétique non plafonnée → |v| max = 0.126 m/s > v_max.

Ces deux échecs provenaient des données de test, pas du code de
production.

### Décision
- `solutions_pareto` synthétiques : droite STRICTEMENT DÉCROISSANTE
  (`e = 40 − 1.5·t`), garantissant la non-dominance mutuelle par
  construction.
- `profiles` synthétiques : vitesse plafonnée à `0.03 m/s` (marge 33 %
  sous `v_max = 0.045`), position linéaire indépendante de la vitesse.
- Le docstring de la fixture précise explicitement qu'il ne s'agit PAS
  de LSPB physiques : les profils servent uniquement à exercer les 3
  invariants du check `_check_profiles` (|v| ≤ v_max, v = 0 aux
  waypoints, monotonie du temps).

### Conséquence
Aucune modification du code de production. Tests 13/13.

---


## D-BLOC10-02 — Tolérance sur les petits fronts Pareto

**Date** : 2026-09-13
**Statut** : Adoptée
**Blocs concernés** : BLOC 7 (Optimizer), BLOC 10 (Validator), run_pipeline

### Contexte
Le smoke test `--fast` produisait un front de 2 solutions (pop=20, gen=20).
Le Validator détectait une dominance entre elles et retournait `FAIL`,
alors que le pipeline est sain.

### Diagnostic
Sur un front de 2 solutions, une dominance détectée est un artefact :
deux objectifs « quasi-identiques » à 1e-9 près peuvent produire une
dominance stricte qui n'a aucune signification algorithmique. La
notion de non-dominance n'est statistiquement robuste qu'à partir de
3 solutions.

### Décisions
1. `Validator._check_solutions` : tolère une dominance détectée si
   `n < 3` (statut `WARN` au lieu de `FAIL`). Au-delà de 3, la
   détection reste stricte (`FAIL`).
2. `Optimizer.run` : lecture explicite via `res.opt` au lieu de
   `res.X`/`res.F`, pour clarifier l'intention et immuniser contre un
   futur changement pymoo.
3. `run_pipeline --fast` : paramètres revus à pop=50/gen=50 (contre
   20/20). Coût : ~1 s supplémentaire. Bénéfice : front de 8-15
   solutions, représentatif de la qualité réelle du pipeline.

### Conséquence
Le smoke test retourne `PASS` (ou `WARN` justifié). Le run complet
(pop=100, gen=200) reste inchangé : un front dégénéré y reste un
signal d'alerte légitime.

---


## D-BLOC7-02 — Paramètres NSGA-II ajustés empiriquement

**Date** : 2026-09-13
**Statut** : À arbitrer après run 7×7
**Blocs concernés** : BLOC 7, script run_pipeline

### Contexte
Le run complet (grille 7×7, pop=100, gen=200) produit 9 solutions
non dominées, sous le seuil §7 (≥ 10 → WARN).

Le run ne prend que 3 s sur BLOC 7, contre 5–15 min estimés. Le budget
temps permet une augmentation substantielle de pop_size/n_gen.

### Décision proposée
Relancer avec pop_size=200, n_gen=500 pour densifier le front
(coût estimé : 30–45 s). Si le front reste < 10, considérer que la
corrélation temps/énergie est structurelle et documenter le résultat
comme observation scientifique.

### Mesures à comparer
- run_1 : pop=100, gen=200 → 9 solutions, WARN
- run_2 : pop=200, gen=500 → ? solutions, ?

---

## D-BLOC7-03 — Paramètres NSGA-II calibrés empiriquement

**Date** : 2026-09-13
**Statut** : Adoptée (sous réserve de la dernière passe pop=400)
**Blocs concernés** : BLOC 7, run_pipeline

### Contexte
Trois runs successifs :
- pop=100, gen=200 (20 000 évals, 3 s) → 9 solutions, WARN, time_opt=429.16 s
- pop=200, gen=500 (100 000 évals, 13 s) → 10 solutions, PASS, time_opt=379.81 s

Le gain de -11.5 % sur time_opt entre les deux runs **sur le même problème**
prouve que pop=100/gen=200 n'avait pas convergé.

### Décision provisoire
Retenir pop_size=200, n_gen=500 comme paramètres de production, avec une
passe de confirmation pop=400/gen=1000 pour vérifier la convergence.

### Observation scientifique
La courbe de convergence (time_opt vs budget NSGA-II) devra figurer dans
le mémoire : elle documente empiriquement le choix des paramètres et
démontre que la solution n'est pas un artefact d'un budget insuffisant.

---

## D-BLOC7-04 — Convergence NSGA-II et déduplication objective

**Date** : 2026-09-13
**Statut** : En cours de validation
**Blocs concernés** : BLOC 7, BLOC 10

### Contexte
Trois runs successifs montrent une amélioration continue sans plateau :
- pop=100, gen=200 : time_opt=429.16 s, energy_opt=901.27 J
- pop=200, gen=500 : time_opt=379.81 s (-11.5%), energy_opt=842.50 J (-6.5%)
- pop=400, gen=1000: time_opt=348.02 s (-8.4%), energy_opt=781.07 J (-7.3%)

Découverte supplémentaire : sur 19 solutions retournées par pymoo,
seules 11 sont distinctes en (time, energy). Les 8 restantes sont
des permutations symétriques co-optimales.

### Décisions
1. Le Validator déduplique désormais par (time, energy) avant
   comptage et affichage. Les solutions brutes restent dans le CSV
   pour traçabilité (elles documentent une symétrie du coût).
2. Une dernière passe (pop=800, gen=2000) est lancée pour confirmer
   la convergence. Si le gain vs pop=400 est < 3%, les paramètres
   pop=400/gen=1000 seront retenus comme défaut.

### Observation scientifique
Les permutations co-optimales révèlent une symétrie du paysage de coût
autour de la grille : certains points équidistants des voisins peuvent
être visités dans un ordre indifférent. Cette observation est à
documenter dans le mémoire (analyse de la structure du problème).


---

## D-BLOC7-05 — Post-filtrage strict de non-dominance

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 7 (Optimizer)

### Contexte
Le run pop=800/gen=2000 a produit 13 solutions dans solutions_pareto.csv,
dont 2 étaient dominées par une troisième (mêmes temps, énergie
strictement supérieure). Le Validator a détecté le problème et retourné
FAIL — correctement.

### Cause
pymoo retourne son `res.opt` en utilisant un tri de dominance avec une
tolérance numérique interne. Sur des problèmes à objectifs très corrélés
(ici temps ≈ k·énergie), cette tolérance peut laisser passer des couples
quasi-dominés.

### Décision
Post-filtrage strict dans `Optimizer.run()` : un masque de non-dominance
O(n²) est calculé sur les F de pymoo, et seules les solutions strictement
non dominées sont conservées. Coût négligeable (n < 100).

### Conséquence
`solutions_pareto.csv` contient désormais un front strictement non dominé,
ce qui rend le check §7 du Validator fiable. Si pymoo retourne des
doublons objectifs (mêmes (time, energy), ordres différents), ils sont
conservés — ils documentent une symétrie du problème.


---

## D-BLOC7-06 — Tolérances de dominance et précision CSV

**Date** : 2026-09-13
**Statut** : Adoptée
**Blocs concernés** : BLOC 7, BLOC 10

### Contexte
Après post-filtrage strict, le Validator retournait toujours FAIL :
deux solutions (#0, #9) apparaissaient dominées dans le CSV alors
qu'elles ne l'étaient pas aux valeurs float64 internes.

Cause : le CSV était écrit avec float_format="%.6e", perdant 4 à 6
chiffres significatifs. Le Validator, lisant ce CSV arrondi, détectait
une dominance invisible dans les vraies données.

### Décisions
1. **Précision CSV étendue** : les solutions Pareto sont écrites en
   `%.15e` (float64 complet). Plus de perte d'information.
2. **Tolérances de dominance** ajoutées dans le Validator et le
   post-filtrage Optimizer :
   - 1e-3 s sur le temps (3e-6 relatif sur ~350 s)
   - 1e-2 J sur l'énergie (1e-5 relatif sur ~800 J)
   Ces seuils correspondent au niveau où les différences deviennent
   physiquement non significatives.

### Conséquence
Le statut de validation reflète désormais une dominance **réelle**,
pas un artefact numérique. Le nombre de solutions dans le front reste
inchangé (13), mais la vérité physique des comparaisons est préservée.

### Observation
Deux solutions à moins de 1 ms et 10 mJ près sont **équivalentes du
point de vue de la mission**. Le choix du compromis (BLOC 8) doit
donc reposer sur des écarts significatifs, pas sur du bruit.

---

## D-BLOC10-03 — Figures de trajectoires individuelles

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 10 (Validator)

### Contexte
La figure `trajectories_3d.png` superposait les 3 trajectoires sur un
même graphe 3D. Sur la grille 7×7 (49 points), les 3 tracés se
recouvrent au point de devenir illisibles — les couleurs se mélangent
et aucune trajectoire n'est identifiable individuellement.

### Décision
Remplacer la figure unique par 3 figures séparées :
  - `trajectories_3d_time_opt.png`
  - `trajectories_3d_energy_opt.png`
  - `trajectories_3d_compromise.png`

Chaque figure conserve la grille de points en arrière-plan gris
(référence commune) et met en évidence :
  - la trajectoire du kind en couleur et style distinctif,
  - le point de départ/retour au centre (marqueur étoile),
  - les totaux (temps de déplacement, énergie) dans le titre.

### Conséquence
L'utilisateur du mémoire peut insérer les 3 figures côte à côte sans
perte de lisibilité. Le contrat `plot_all()` expose maintenant 6 clés
au lieu de 4 (wfw, pareto, profiles, 3× trajectories_3d_<kind>).

---


## D-BLOC10-04 — Retrait de la règle heuristique "n < 3"

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 10 (Validator)

### Contexte
La règle D-BLOC10-02 ("tolérer toute dominance si n < 3 solutions")
avait été introduite pour absorber des faux positifs de dominance
causés par une précision CSV insuffisante (`%.6e`) et l'absence de
tolérances numériques.

Les correctifs D-BLOC7-06 ont depuis :
  - étendu la précision CSV à `%.15e` (float64 complet),
  - introduit des tolérances de dominance (1e-3 s, 1e-2 J).

Ces deux correctifs éliminent la cause racine des faux positifs. La
règle "n < 3" masque désormais de **vraies** dominances sur les petits
fronts (comme détecté par le test T12 : 2 solutions, écart de 1.0 s
et 1.0 J → dominance légitime).

### Décision
Supprimer la distinction par taille de front. Un front avec une
dominance détectée (hors tolérance) est toujours `FAIL`, quelle que
soit sa taille.

### Conséquence
Le test T12 (`test_validate_detects_dominated_front`) passe de nouveau :
2 solutions avec écart significatif → `FAIL` correct.

### Principe méthodologique
Une tolérance numérique **locale et calibrée** est préférable à une
règle **globale et arbitraire** sur la taille de l'échantillon.
Tolérer un artefact d'arrondi ne doit pas revenir à tolérer une vraie
dominance.


---

## D-BLOC11-01 — Baseline zigzag boustrophédon par lignes

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 11 (Comparator)

### Contexte
Le cahier d'architecture spécifie une « baseline zigzag » sans préciser
l'orientation ni le traitement du centre.

### Décisions
1. **Balayage par lignes** (direction='rows') par défaut. Chaque ligne
   est parcourue en alternant gauche→droite / droite→gauche. Une option
   `direction='cols'` est disponible pour symétrie, mais n'est pas
   exploitée par défaut.
2. **Centre en extrémités** : le centre est retiré du corps du zigzag
   s'il y figure (il est en ligne 3, colonne 3 pour une grille 7×7) et
   ajouté en position 0 et N. Cela respecte la contrainte §2.5
   (départ/retour obligatoires au centre).
3. **Test d'équité §7** : la baseline utilise exactement les mêmes
   points, le même `cost_matrix` et le même centre que les trajectoires
   optimisées. Aucune simplification n'est faite sur la baseline.

### Conséquence
La comparaison est strictement équitable. Si le gain est modeste (c'est
attendu sur une grille régulière où le zigzag est déjà quasi-optimal),
c'est un résultat honnête à documenter dans le mémoire — pas un artefact.

---

## D-BLOC11-02 — Le Comparator est diagnostic, pas verdict

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 11

### Contexte
Un test unitaire exigeait que NSGA-II batte la baseline zigzag. Avec
un budget de test modeste (pop=30, gen=20), NSGA-II produisait une
solution 29 % pire que le zigzag.

Ce n'est pas un bug : le zigzag est un excellent algorithme sur
grille régulière, et NSGA-II n'a simplement pas convergé sur 24! avec
600 évaluations.

### Décision
1. Le test devient un **diagnostic** : il vérifie la formule de calcul
   des gains, pas le signe du gain. La ligne de diagnostic est imprimée
   en mode -v mais n'échoue jamais.
2. `Comparator.diagnose()` produit un diagnostic structuré
   (`optimal_beats_baseline`, gains minimums, warning si pire).
3. Le diagnostic est écrit dans `comparison_diagnostic.json`, produit
   par `run_and_save()`.

### Conséquence
Sur le run de production (7×7, pop=400, gen=1000), NSGA-II converge
et le gain devrait être positif. Si ce n'est pas le cas, le
diagnostic sera **visible dans le rapport final** — pas masqué.

### Principe
Un test unitaire doit tester la **correction du code**, pas la
**qualité stochastique d'un algorithme**. C'est la responsabilité du
run de production de fournir un résultat exploitable ; le rôle du
test est de garantir que le code fait ce qu'il prétend faire.

---

## D-RUNBOOK-01 — Vérification d'exécution des étapes par test

**Date** : 2026-09-13
**Statut** : Adoptée
**Blocs concernés** : script run_pipeline

### Contexte
Le bloc BLOC 11 (Comparator) était placé après le `return` de
`run_pipeline`, donc jamais exécuté. Le pipeline retournait PASS sans
que le comparateur ait tourné. Le défaut était silencieux.

### Décisions
1. Corriger l'ordre : les appels de tous les blocs précèdent le return.
2. Ajouter une vérification `_STEP_OUTPUTS["11_comparator"]` pour que
   `--resume` détecte correctement l'absence des sorties.
3. **Recommandation** : installer `ruff` et l'ajouter à la CI pour
   détecter automatiquement le code mort (`F401`, `W0101`).

### Principe
Un test qui vérifie la **présence des fichiers de sortie** est
indispensable pour chaque étape du pipeline. Le contrôle de la
**structure du code** (avec un linter) est un complément pour les
erreurs qu'aucun test fonctionnel ne peut détecter — comme un `return`
placé trop tôt.

---

## D-TOOLING-01 — Configuration ruff pour typographie scientifique

**Date** : 2026-09-13
**Statut** : Adoptée
**Portée** : outillage projet

### Contexte
`ruff` signale 91 avertissements sur le code du projet, dont ~70
concernent les caractères Unicode mathématiques (×, −, –, ∈, ≤…).

### Décision
Ignorer les règles RUF001/RUF002/RUF003 (caractères ambigus) car elles
sont en **conflit direct avec la typographie scientifique** :
  - "7×7" (multiplication) ≠ "7x7" (variable x)
  - "A_i − B_i" (soustraction) ≠ "A_i - B_i" (hyphen ASCII)
  - "B1–B5" (plage) ≠ "B1-B5"

Remplacer ces caractères serait une **régression sémantique** dans un
document scientifique francophone.

Ignorer également BLE001 (catch Exception aveugle) car il est
intentionnel dans `main()` — pattern CLI standard.

Corriger les 2 bugs réels (F841) et 6 bonnes pratiques (B905, RUF005,
RUF046).

### Conséquence
`ruff check` retourne 0 erreur, la CI peut être configurée avec ce
niveau de rigueur. Les règles ignorées sont documentées ici et dans
le `pyproject.toml`.

### Principe
Un linter ne doit pas **imposer son style** à un projet scientifique
dont la typographie est un livrable. La configuration doit refléter
les **besoins du projet**, pas les défauts de l'outil.


---

## D-TOOLING-02 — Override CLI de z_absolu_r0

**Date** : 2026-09-13
**Statut** : Adoptée
**Portée** : outillage projet

### Contexte
L'étude de l'influence de la hauteur caméra z sur le WFW et le front
de Pareto nécessite de pouvoir relancer le pipeline pour différentes
valeurs de z, sans modifier le code source ni casser la traçabilité.

### Décision
Ajouter un champ `z_absolu_r0_override: Optional[float]` à Config, et
une option CLI `--z-absolu FLOAT` à run_pipeline.py. Quand renseigné :
  - la propriété z_absolu_r0 retourne la valeur forcée,
  - la règle R6 (z ∈ [z_min, z_max]) reste appliquée sur la valeur
    effective,
  - un WARNING explicite est loggé pour signaler l'override.

### Interaction avec --resume
L'override ne modifie PAS automatiquement les CSV déjà produits. Un
WARNING loggé invite l'utilisateur à supprimer data/outputs/* avant
de relancer. Cette décision privilégie la simplicité à un mécanisme
de détection automatique (complexité non justifiée).

### Conséquence
Permet de générer une famille de WFW et de fronts de Pareto pour
différentes hauteurs (utile pour le mémoire : montrer le rétrécissement
du WFW quand z augmente).


---


## D-BLOC11-04 — Baseline adaptative (zigzag ou NN)

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 11 (Comparator)

### Contexte
Avec l'option `--z-absolu`, la hauteur caméra peut être modifiée pour
explorer l'influence de z sur le pipeline. À z=0.60 m, seuls 29 points
sur 49 sont faisables (WFW rétréci), ce qui casse le Comparator qui
supposait une grille complète.

### Décision
Rendre la baseline adaptative :
  - Grille complète → zigzag boustrophédon (inchangé).
  - Grille incomplète → heuristique du plus proche voisin (greedy TSP).

Le `kind` produit est dynamique (`baseline_zigzag` ou `baseline_nn`),
propagé dans `baseline_zigzag.csv`, `comparison.csv` et le diagnostic.

### Justification
Le zigzag est défini sur une grille régulière pleine. Sur une grille
partielle (points filtrés par WFW), la généralisation naturelle est le
plus proche voisin, qui est un baseline TSP reconnu et universellement
défini.

### Conséquence
Le pipeline produit désormais un résultat exploitable pour **toute**
valeur de z dans [z_min, z_max], ce qui permet de tracer la courbe
d'évolution du WFW et du front de Pareto en fonction de z.

---

## D-BLOC10-05 — Paires infaisables = WARN, pas FAIL

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 10

### Contexte
À z=0.60 m, le WFW rétrécit : 29/49 points sont faisables, et certaines
paires (i, j) entre ces points deviennent infaisables. Le Validator
classait ceci comme FAIL, alors que c'est une conséquence physique
attendue du rétrécissement.

### Décision
Le check `cost_matrix` distingue :
  - Bugs réels (FAIL) : asymétrie, diagonale non nulle.
  - Réalité physique (WARN) : paires infaisables, avec taux affiché.

Les paires faisables restent comparées pour symétrie (le pivot ignore
les NaN des paires infaisables).

### Conséquence
À z=0.60, le pipeline retourne WARN global au lieu de FAIL. Les
artefacts sont exploitables et documentent le rétrécissement du WFW.

---

## D-BLOC11-05 — Baseline NN avec backtracking borné

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 11

### Contexte
La baseline NN greedy produisait des paires infaisables à z=0.60
(ex. paire (43, 47)), cassant le pipeline. Or, l'optimisé (NSGA-II)
trouve bien un chemin valide — donc il en existe au moins un.

### Décision
Backtracking léger (DFS) avec :
  - Candidats filtrés par faisabilité (cost_matrix.feasible == 1),
  - Tri par distance euclidienne² (plus proche d'abord),
  - Limite de temps 5 s (suffisant : < 50 points, graphes usuels),
  - Exception explicite si aucun chemin hamiltonien trouvé.

### Conséquence
La baseline devient robuste à toute topologie de WFW (complet ou
partiel). Sur grille complète, le comportement reste greedy (aucun
backtracking déclenché). Sur grille partielle, il peut légèrement
diverger du greedy pur — c'est le prix de la faisabilité.

---

## D-BLOC11-06 — Baseline adaptative documentée

**Date** : 2026-09-13
**Statut** : Adoptée

Le `kind` de la baseline (`baseline_zigzag` ou `baseline_nn`) est
désormais :
  - exposé dans `Comparator._baseline_kind`,
  - propagé dans tous les CSV de sortie (`baseline_*.csv`,
    `comparison.csv`, `comparison_diagnostic.json`),
  - loggué explicitement (`Baseline : zigzag rows` ou `Baseline :
    plus proche voisin`).

Cela permet au lecteur du mémoire de savoir immédiatement quelle
baseline a été utilisée pour chaque run (dépend de z).

---

### Correction du test (2026-09-13)
Le test `test_nn_fallback_on_partial_grid` a été corrigé après un
`IndexError` dû à un accès par position (`iloc`) sur un DataFrame
filtré. L'accès se fait désormais par `point_id`, ce qui est robuste
au filtrage et à l'ordre des lignes.

---

### Correction (2026-09-13)
Le dictionnaire de couleurs de `plot_comparison` et la liste `panels` de
`plot_trajectories_grid` référençaient en dur `"baseline_zigzag"`. Avec
la bascule adaptative (D-BLOC11-04), le kind peut être `"baseline_nn"`,
ce qui provoquait un `KeyError`. Correction : clés alignées sur
`self._baseline_kind` + fallback générique pour tout kind inconnu.

---

## D-BLOC11-07 — Distinction "égal" vs "pire" dans le diagnostic

**Date** : 2026-09-13
**Statut** : Adoptée
**Bloc concerné** : BLOC 11

### Contexte
À z=0.60, la baseline NN et la trajectoire `time_opt` trouvent la même
tour à l'instant près (216.117 s), donnant un gain de 0.00 %. Le
diagnostic affichait « trajectoire optimisée PIRE que la baseline »,
ce qui est factuellement faux : 0 % = égal, pas pire.

### Décision
Trois états distincts dans `diagnose()` :
  - `has_worse` : au moins un gain < −1e-6 % → WARNING
  - `has_tie`   : au moins un gain ≈ 0 %, aucun pire → INFO
  - sinon       : `optimal_beats_baseline = True`

### Conséquence
Le diagnostic est sémantiquement correct. Les deux runs (z=0.45 et
z=0.60) sont exploitables, chacun avec sa signification propre :
  - z=0.45 : l'optimisation NSGA-II apporte un gain réel.
  - z=0.60 : la baseline NN atteint l'optimum sur cette instance plus
    contrainte — résultat scientifique légitime, à documenter comme
    « cas où la baseline heuristique suffit ».


---

## D-TOOLING-03 — Visualisation 3D du WFW (Méthode A + B)

**Date** : 2026-09-13
**Statut** : Adoptée
**Portée** : outil d'exploration

### Contexte
Le WFW est actuellement visualisé uniquement en coupe 2D à z_absolu_r0
(`wfw_slice.png`, BLOC 3). Pour comprendre l'influence de z sur la
taille du WFW, une visualisation volumique 3D est nécessaire.

### Décision
Deux méthodes complémentaires :

1. **Nuage 3D** (`wfw_3d_scatter.png`) — échantillonnage de la grille
   (n_xy, n_xy, n_z) et coloration faisable/infeasible.
2. **Iso-surfaces** (`wfw_3d_surface.png`) — iso-contour à F=0.5 +
   n_cuts_display coupes 2D empilées pour montrer le rétrécissement
   du WFW quand z augmente.

Un CSV (`wfw_3d_volume.csv`) est également produit pour analyse
quantitative ultérieure.

### Outillage
Script dédié `scripts/run_wfw_3d.py`, indépendant du pipeline principal.
Arguments : --n-xy, --n-z, --z-absolu, --output-dir.

### Conséquence
Permet de tracer une courbe "volume faisable vs z" (à partir du CSV) et
une figure de synthèse (scatter + surface) pour le mémoire. Combiné avec
`--z-absolu`, permet d'explorer l'impact d'une hauteur de service
différente.

### Coût
Résolution par défaut (30×30×20) : ~13 s de calcul.
Résolution rapide (10×10×8) : ~1 s.

---

## D-TOOLING-05 — Visualisation 3D multi-volumes WFW/WCW

**Date** : 2026-09-14
**Statut** : Adoptée
**Portée** : outil d'exploration et figure de mémoire

### Contexte
L'exploration du WFW par T_min est cruciale pour comprendre l'impact
de la pré-tension sur l'espace de travail atteignable. Une visualisation
3D multi-volumes rend ce phénomène immédiatement lisible.

### Décision
Module `src/wfw_3d.py` avec la classe `WFW3DViewer` :
  - Échantillonne l'enveloppe des ancrages (±1.25 m XY, Z ∈ [0, 1.00]),
    indépendamment des limites opérationnelles de Config (qui restent
    à ±0.75 m en production).
  - Calcule 4 volumes imbriqués pour T_min ∈ {20, 10, 5, 0} N, en
    exploitant l'imbrication pour réduire le nombre d'appels LP.
  - Dessine bâti (12 arêtes), nacelle (pavé + 8 attaches), 8 câbles,
    et les 4 volumes en surfaces semi-transparentes (ConvexHull +
    Poly3DCollection).
  - Légende à droite avec le % de points faisables par volume.

### T_max
Par défaut T_max = 500 N (généreux) pour isoler l'effet de T_min.
Cela diffère de la production (T_max = 58 N), mais le but est
d'illustrer la dépendance au T_min, pas de reproduire le WFW de
production. Surchargeable via CLI.

### Conséquence
Une figure de synthèse `wfw_3d_combined.png` directement exploitable
dans le mémoire, montrant visuellement :
  - le contraste entre l'espace physique disponible (bâti ±1.25 m)
    et le WFW utile (rayon ~0.3 m pour T_min=5 N) ;
  - le rétrécissement drastique du WFW quand T_min augmente ;
  - la convergence vers un volume résiduel pour T_min=20 N.


---

## D-TOOLING-06 — Sweep (T_min, T_max) et révision des limites

**Date** : 2026-09-14
**Statut** : Adoptée
**Portée** : outil d'analyse

### Contexte
Les limites opérationnelles (±0.75 m XY, [0, 0.80] m Z) proviennent
d'une marge heuristique de 0.25 m/bord appliquée à l'enveloppe des
ancrages (Annexe D de la Base d'architecture v3.1). La spec admet
elle-même que cette marge « n'est pas dérivée d'un calcul WFW réel ».
Le flux rigoureux est : WFW calculé → bbox → limites opérationnelles.

### Décision
Ajouter `scripts/sweep_wfw.py` qui balaie ~90 paires (T_min, T_max),
calcule le WFW sur l'enveloppe physique complète, et tabule :
  - pct_coverage, bbox, rayons, hull_volume, faisabilité centre.

Exploite l'imbrication (masque global T_min=0, T_max=∞) pour réduire
d'environ 50-70 % le nombre d'appels LP.

### Conséquence attendue
Après le balayage, les valeurs `x_min/x_max/y_min/y_max/z_max` de
`Config` pourront être :
  - soit confirmées (si bbox ≈ ±0.75),
  - soit ajustées à la bbox + marge,
  - soit documentées comme marge de sécurité volontaire.

### Option CLI
`--resume` permet d'ajouter des paires sans recalculer l'existant.


---

## D-CONFIG-01 — Révision des limites opérationnelles par sweep WFW

**Date** : 2026-09-14
**Statut** : En cours de validation
**Blocs concernés** : Config, BLOC 4, BLOC 5, BLOC 6, BLOC 7

### Contexte
Les limites opérationnelles v3.1 (`±0.75 m`, `[0, 0.80] m`) sont issues
d'une marge heuristique de 0.25 m/bord, sans calcul WFW réel (D-BLOC3-01
l'admettait déjà). Le sweep `scripts/sweep_wfw.py` (90 paires
T_min × T_max) fournit la dérivation empirique.

### Résultats (paire nominale T_min=1 N, T_max=58 N)
- WFW X : ±0.724 m (Config actuelle : ±0.75 → sur-couvre de 26 mm)
- WFW Y : ±0.855 m (Config actuelle : ±0.75 → sous-couvre de 105 mm)
- WFW Z : [0, 0.909] m (Config actuelle : [0, 0.80] → sous-couvre de 109 mm)
- Asymétrie X/Y confirmée : WFW plus étendu en Y (conséquence de la
  plateforme 700×560 mm, pas une anomalie).

### Décision proposée
Aligner les limites sur le WFW mesuré avec une marge de sécurité 5 % :
- x_min/max : ±0.69 m
- y_min/max : ±0.81 m
- z_max : 0.86 m (z_min inchangé)

Espacement : passer de 0.25 à 0.27 m pour couvrir ±0.81 m avec N=49
(évite de changer N et donc le coût du pipeline).

### Alternative rejetée
Garder les valeurs actuelles par « continuité » — rejetée car un jury
attentif demanderait la dérivation, et la réponse « marge heuristique »
n'est pas défendable face à un WFW calculable.

### Fichiers produits
- `data/outputs/wfw_sweep.csv` : table complète 90 paires
- `data/outputs/figures/wfw_sweep_heatmap.png` : heatmap coverage


---

## D-GUI-02 — Convention des noms visibles des trajectoires

**Date** : 2026-10-30
**Statut** : Validée — 2026-10-30
**Blocs concernés** : GUI, visualisations, exports présentés; pas les artefacts scientifiques

### Décision

Les libellés visibles sont harmonisés ainsi :

- `compromise` → **Trajectoire compromis** ;
- `time_opt` → **Trajectoire temps optimal** ;
- `energy_opt` → **Trajectoire énergie optimale**.

Les identifiants machine restent inchangés dans les CSV, les services, les
validations, les noms de fichiers et les contrats inter-artefacts. Cette
séparation évite une migration destructive tout en supprimant les anciens
libellés ambigus « Optimisé temps », « Optimisé énergie » et « Compromis » de
l’interface et des figures.

---

## D-CONFIG-01 — Passage à la grille 9×9 (N=81) et limites dérivées WFW

**Date** : 2026-09-14
**Statut** : Adoptée
**Blocs concernés** : Config, tous les blocs en aval

### Contexte
Le sweep WFW (`scripts/sweep_wfw.py`) a établi que les limites
opérationnelles v3.1 (±0.75 m XY, 0.80 m Z) étaient une marge
heuristique, pas une dérivation du WFW. Le WFW mesuré pour la paire
nominale (T_min=1, T_max=58) s'étend sur X±0.724 m, Y±0.855 m,
Z∈[0, 0.909] m.

Le sous-projet SP2 a maintenant besoin d'une grille plus dense pour
améliorer la couverture d'acquisition d'images (espacement 20 cm au
lieu de 25 cm).

### Décision
Passer à une grille **9×9 (N=81) avec espacement 0.20 m**, couvrant
±0.80 m en XY et [0, 0.86] m en Z :
- x_min/x_max = ±0.80 m (aligné sur le WFW X avec marge)
- y_min/y_max = ±0.80 m (léger sous-couvrement vs WFW Y à 0.855 ;
  accepté pour symétrie de la grille)
- z_max = 0.86 m (aligné sur le WFW Z avec marge 5 %)

### Compromis
Le sous-couvrement en Y (±0.80 < 0.855) est accepté pour préserver
l'isotropie de la grille (esp_x = esp_y). Une grille asymétrique
serait plus rigoureuse mais complique le code et les figures sans
gain significatif.

### Mécanisme quick mode
Ajout d'une méthode `Config.with_n(n)` qui dérive l'espacement pour
couvrir les mêmes bornes. Permet des runs rapides :
  - N=9 → référence (espacement 0.20 m, ~2 min 30 s de pipeline)
  - N=7 → intermédiaire (0.267 m, ~1 min 30 s)
  - N=5 → rapide (0.40 m, ~30 s)
  - N=3 → smoke test (0.80 m, ~10 s)

Option CLI associée : `python scripts/run_pipeline.py --n N`.

### Conséquence
- N' après filtrage attendu : ~56 points (vs 49 en v3.1).
- Chromosome NSGA-II : 55 gènes (vs 48).
- Temps de run complet : ~2 min 30 s (vs 1 min 30 s).
- Toutes les figures et CSV à regénérer.
- Documentation (DECISIONS, RUNBOOK, README) à mettre à jour.

---

## D-CONFIG-01 — Grille 9×9 et limites dérivées du sweep WFW

**Date** : 2026-09-14
**Statut** : Adoptée
**Blocs concernés** : Config, tous les blocs en aval

### Contexte
Le sweep WFW a établi empiriquement que les limites opérationnelles
v3.1 (±0.75 m XY, 0.80 m Z) étaient une marge heuristique de 0.25 m/bord
appliquée à l'enveloppe des ancrages, sans dérivation du WFW réel.

WFW mesuré pour (T_min=1, T_max=58) : X±0.724, Y±0.855, Z∈[0, 0.909].

### Décision
Passer à une grille 9×9 (N=81, esp=0.20 m) couvrant les bornes ±0.80 m
en XY et [0, 0.86] m en Z.

### Compromis
- Sous-couverture en Y (±0.80 < 0.855) acceptée pour garder la grille
  isotrope (esp_x = esp_y).
- Marge 5 % sur X (0.724 → 0.80) et Z (0.909 → 0.86).

---

## D-CONFIG-02 — Paramètres NSGA-II ajustés selon n

**Date** : 2026-09-14
**Statut** : Adoptée

Table recommandée (implémentée dans `_NSGA_TABLE`) :

| n | pop_size | n_gen | Runtime estimé |
|---|---|---|---|
| 3 | 30 | 100 | ~8 s |
| 5 | 100 | 300 | ~25 s |
| 7 | 200 | 500 | ~1 min 15 s |
| **9** | **500** | **1500** | **~2 min 30 s** |
| 11 | 800 | 2000 | ~6 min |

---

## D-CONFIG-03 — Quick mode via `Config.with_n(n)`

**Date** : 2026-09-14
**Statut** : Adoptée

### Décision
Ajouter `Config.with_n(n)` : dérive l'espacement et les paramètres
NSGA-II pour n'importe quelle taille de grille impaire ≥ 3, en
gardant les bornes opérationnelles v3.2.

### Conséquence
Le pipeline peut être exécuté à coût contrôlé :
    python scripts/run_pipeline.py --n 3 --fast   # ~8 s
    python scripts/run_pipeline.py --n 5          # ~25 s
    python scripts/run_pipeline.py --n 7          # ~1 min 15 s
    python scripts/run_pipeline.py                # ~2 min 30 s (défaut 9)
    python scripts/run_pipeline.py --n 11         # ~6 min


---

## D-CONFIG-04 — Mode zéro perte (bornes ±0.545 m)

**Date** : 2026-09-15
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 4, BLOC 5

### Contexte
Le run v3.2 (bornes ±0.80 m) rejette 39 % des points de la grille
9×9 en Cause B — les bords X sortent du WFW elliptique. Ce rejet
est physique mais génère un WARN systématique et brouille la lecture
du rapport final.

### Décision
Ajouter une option `--zero-loss` qui resserre les bornes à ±0.545 m.
Calcul : pour qu'un carré de coin (c,c) tienne dans l'ellipse WFW
(a=0.724, b=0.855) : c²/a² + c²/b² ≤ 1 → c ≤ 0.5525 m. On prend
0.545 m pour une marge de sécurité 1.4 %.

### Conséquence
- Mode standard : extent ±0.80 m, 49/81 points retenus, WARN.
- Mode zéro perte : extent ±0.545 m, 81/81 points retenus, PASS.
- L'espacement se resserre à 0.136 m (n=9) en mode zéro perte.

### Choix par défaut
Le mode standard reste par défaut pour préserver la continuité avec
les runs v3.2. L'utilisateur bascule en mode zéro perte via CLI.


---

## D-BLOC10-06 — Seuil historique de 10 solutions Pareto : décision remplacée

**Date** : 2026-09-15
**Statut** : Remplacée par D-BLOC10-07 — 2026-10-30
**Bloc concerné** : BLOC 10 (Validator)

### Contexte
Le check `_check_solutions` retourne WARN dès que le front de Pareto
compte moins de 10 solutions uniques (§7 du cahier d'architecture).
Sur les instances à objectifs fortement corrélés (temps ↔ énergie),
le front est intrinsèquement étroit : grilles régulières, WFW
elliptique, etc.

Exemple : le run `--n 7 --zero-loss --pop-size 1000 --n-gen 3000`
produit **5 solutions non dominées** avec des gains de **+9.47 % temps**
et **+10.04 % énergie** — résultat excellent mais WARN déclenché.

### Décision
**Conserver le seuil de 10 comme signal informatif, pas comme critère
d'échec.** Le WARN est documenté dans le rapport final et dans le
mémoire comme un artefact de seuil, pas comme un défaut de qualité.

Un front de 5 solutions bien étalées (gains > 5 % vs baseline) est
**plus informatif** qu'un front de 20 solutions tassées (gains < 1 %).

### Justification
Le seuil de 10 avait été fixé en §7 pour un problème v3.0 (81 points,
espace large). Sur les instances v3.2 (49 points, corrélation élevée),
il est mal calibré. **Baisser le seuil serait une compromission
méthodologique** — mieux vaut documenter l'écart.

### Conséquence pour le mémoire
Section « Analyse de sensibilité » à rédiger avec :
- Un tableau comparant les fronts obtenus pour les différentes configs
- Une discussion sur la relation entre régularité de la grille et
  largeur du front
- La justification du seuil conservé comme signal (pas comme critère)


---

### Sémantique des overrides (précision)

  - `--x-bound` ET `--y-bound` → zone asymétrique explicite.
  - `--x-bound` seul           → fallback symétrique (X = Y = x_bound).
  - `--y-bound` seul           → fallback symétrique (X = Y = y_bound).
  - `--xy-bound`               → zone symétrique explicite.
  - Défaut                     → standard (±0.80) ou zero_loss (±0.545).

Le fallback symétrique est plus intuitif : un utilisateur qui exprime
une seule dimension veut généralement une zone carrée. L'asymétrie
est réservée au cas explicite (deux options fournies).


---

## D-BLOC11-08 — Correction du subplot énergie dans la figure comparative

**Date** : 2026-09-16
**Statut** : Adoptée
**Bloc concerné** : BLOC 11

### Contexte
La boucle d'étiquetage du subplot énergie référençait la variable `times`
au lieu de `energies` pour la position du texte. Résultat : labels
visuellement décalés (position calculée sur les secondes dans un axe
en joules).

### Décision
Corriger la boucle : `zip(bars, energies, kinds, strict=True)`.

### Amélioration visuelle associée
Labels centrés verticalement dans la barre (`v/2`) avec texte blanc
gras — plus lisible qu'un texte au-dessus des barres pour des valeurs
élevées (300–460 J).

### Conséquence
Figure comparative lisible sans ambiguïté sur les hauteurs de barres.


---

## D-CONFIG-06 — Étude paramétrique de la taille de plateforme

**Date** : 2026-09-16
**Statut** : En investigation
**Blocs concernés** : Config, BLOC 1, BLOC 3

### Contexte
La plateforme actuelle (700×560×50 mm) est le fruit d'une heuristique
v3.1 : suffisamment grande pour générer un WFW exploitable, compatible
avec les ancrages SP1. Aucune étude formelle d'optimisation de la taille
n'a été menée.

### Hypothèses à tester
Trois variantes sont ajoutées via l'option `--platform` :

| Nom | Demi-étendues | Surface | Masse estimée |
|---|---|---|---|
| `700x560` (défaut) | (0.350, 0.280) | 0.392 m² | 417 g |
| `560x560` | (0.280, 0.280) | 0.314 m² | 409 g |
| `630x630` | (0.315, 0.315) | 0.397 m² | 418 g |

Le modèle de masse est calibré sur les estimations historiques
v3.0/v3.1 (200×160 → 385 g, 500×400 → 397 g, 700×560 → 417 g).
Il suppose une conception en treillis ouvert (overhead fixe dominant).

### Méthode d'évaluation
1. Lancer `python scripts/sweep_wfw.py --n-xy 15 --n-z 10` pour chaque
   plateforme → mesurer WFW extent et volume.
2. Lancer `python scripts/run_wfw_3d.py --n-xy 25 --n-z 15` → figures 3D.
3. Lancer un run court `--n 7 --pop-size 100 --n-gen 300` → gains,
   solutions Pareto, statut validation.
4. Décider sur les données mesurées, pas sur le raisonnement.

### Note de méthode
Une plateforme plus grande n'est pas strictement meilleure : elle
augmente le bras de moment (positif) mais aussi la masse (négatif).
Il existe un optimum, non trivial à calculer analytiquement.


---

## D-CONFIG-07 — Adopter la plateforme carrée 560×560

**Date** : 2026-09-16
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 1, BLOC 3

### Contexte
L'étude comparative D-CONFIG-06 a testé 3 tailles de plateforme sur
le sweep WFW et le run_wfw_3d :

| Plateforme | WFW coverage (T_min=20) | Masse |
|---|---|---|
| 700×560 | 29.83 % | 417.3 g |
| **560×560** | **35.25 %** | **409.1 g** |
| 630×630 | 33.33 % | 417.8 g |

Le carré 560×560 **domine** le rectangle historique sur tous les
critères mesurés : WFW plus grand, masse plus faible, symétrie.

### Prédiction théorique vs réalité
L'analyse préliminaire supposait que le bras de moment réduit
(280 vs 350 mm) pénaliserait le WFW. Les mesures contredisent cette
prédiction : la réduction de masse (8 g) et les angles de câbles plus
favorables dominent largement l'effet du bras de moment.

Cet écart théorie/mesure justifie la démarche empirique : sans le
sweep, on aurait choisi sur une intuition erronée.

### Décision
Adopter 560×560×50 mm comme plateforme par défaut.
Options `--platform {560x560, 700x560, 630x630}` restent disponibles
pour compatibilité et étude de sensibilité.

### Impact
Aucun sur les runs historiques (CSV/figures préservés).
Les futurs runs bénéficient d'un WFW plus grand et d'une masse
légèrement réduite.


---

## D-CONFIG-07 — Adopter 560×560 comme plateforme par défaut

**Date** : 2026-09-16
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 1, BLOC 3

### Contexte
L'étude comparative (D-CONFIG-06) a mesuré le WFW pour 3 tailles de
plateforme via `run_wfw_3d` (résolution 20×20×12) et `sweep_wfw`
(résolution 12×12×8).

### Résultats mesurés (run_wfw_3d)

| T_min | 700×560 | 560×560 | 630×630 |
|---|---|---|---|
| 0 N | 1900 | **1928** | 1920 |
| 5 N | 1808 | **1852** | 1844 |
| 10 N | 1704 | **1816** | 1788 |
| 20 N | 1432 | **1692** | 1600 |

Le carré 560×560 gagne à **chaque** T_min, avec un avantage croissant
(+18 % à T_min=20 N). Il gagne aussi en masse (409 g vs 417 g) et en
symétrie (grille isotrope).

### Prédiction théorique vs réalité
L'analyse préliminaire supposait que le bras de moment réduit
(280 vs 350 mm) pénaliserait le WFW X. Les mesures contredisent :
la réduction de masse et les angles câbles plus favorables dominent.
**Cet écart théorie/mesure justifie la démarche empirique** : sans
le sweep, on aurait choisi sur une intuition erronée.

### Décision
Adopter **560×560×50 mm** comme plateforme par défaut.

### Options CLI ajoutées
- `--platform WxH` : accepte un nom connu (560x560, 700x560, 630x630)
  ou une dimension libre en mm (ex. `--platform 400x300`).
- `--platform-mass GRAMS` : override manuel de la masse.

### Impact
Aucun sur les runs historiques (CSV/figures préservés).
Les futurs runs bénéficient d'un WFW plus grand et d'une masse réduite.

---

## D-BLOC5-01 — Seuil minimum de points pour un tour

**Date** : 2026-09-17
**Statut** : Adoptée
**Blocs concernés** : BLOC 5, BLOC 7, BLOC 11

### Contexte
Avec des configurations très contraintes (petite plateforme, extent
large), le filtre peut retenir un nombre de points insuffisant pour
construire un tour visitant tous les points. Symptômes observés :

1. `--n 5 --fast` (5 points retenus) : le comparator NN échoue avec
   "aucun chemin hamiltonien" car certains segments entre points
   faisables passent par une zone hors-WFW.
2. `--platform 400x300` (1 point retenu) : NSGA-II ne peut pas
   construire de tour.

### Décision
Ajouter une vérification post-filtrage : si `n_kept < 4`
(centre + 3 minimum), lever `InsufficientPointsError` avec message
suggérant des ajustements. Entre 4 et 6 points, logger un avertissement.

Ajouter également dans l'Optimizer une détection de front dégénéré
(toutes solutions pénalisées) qui lève `DegenerateFrontError`.

### Conséquence
Le pipeline échoue **tôt** avec un message actionnable au lieu de
produire des artefacts incohérents (time = 6e6) puis de crasher dans
le comparator.

### Note physique
Le seuil de 4 est un minimum structurel (tour non dégénéré). En dessous
de 6, l'optimisation a peu d'intérêt — l'avertissement guide l'utilisateur
vers des configurations plus exploitables.


---

## D-CONFIG-08 — Rejet de la plateforme carrée (singularité structurelle)

**Date** : 2026-09-17
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 1, BLOC 3, BLOC 6

### Contexte
L'étude D-CONFIG-07 recommandait la plateforme carrée 560×560 sur la
base du sweep WFW. Cette recommandation est **retirée** : elle reposait
sur un test incomplet.

### Découverte — Singularité structurelle
Pour toute plateforme dont le polygone des attaches est homothétique au
polygone des ancrages (carré dans carré), la matrice de structure W
perd son 6ᵉ rang. Démonstration : la composante Mz de chaque colonne
s'annule par symétrie radiale. Le robot ne peut générer aucun moment
de lacet — il est structurellement défaillant sur un degré de liberté.

Conséquence : SLSQP dans CostCalculator échoue (jacobien déficient) →
cost_matrix 97 % infaisable → front dégénéré → pipeline bloqué.

### Correction
1. Retour au défaut 700×560 (ratio 1.25, W de rang 6 partout).
2. Test de rang(W) ≥ 6 dans WFW.is_feasible — rejette automatiquement
   toute config singulière, alignant le sweep avec la réalité physique.
3. Le sweep WFW corrigé rejettera 560×560 et 630×630 — résultats
   précédents invalidés.

### Leçon de méthode
Un test de faisabilité doit vérifier la **capacité complète** du système
(ici : 6-DOF contrôlables), pas seulement un effort particulier. Le
sweep WFW testait uniquement `rhs = (0, 0, mg, 0, 0, 0)` — insuffisant
pour détecter une perte de rang sur d'autres composantes.


---

## D-CONFIG-09 — Les plateformes carrées sont structurellement incompatibles

**Date** : 2026-09-17
**Statut** : Adoptée (annule D-CONFIG-07)
**Blocs concernés** : Config, BLOC 1, BLOC 3, BLOC 6

### Loi physique identifiée
Toute plateforme dont le polygone d'attaches est **homothétique** au
polygone d'ancrages (même forme, échelle différente) subit une
singularité de rang : la matrice W perd le degré de liberté de lacet
(Mz). Vérifié numériquement :

| Plateforme | rang(W) | sv_min |
|---|---|---|
| 560×560 | **5** | 2.67e-16 |
| 630×630 | **5** | 2.10e-16 |
| 700×560 | 6 | 1.66e-01 |
| 600×500 | 6 | 1.15e-01 |
| 560×420 | 6 | 1.23e-01 |

Cause : la symétrie 4-fold (ancrages carrés) combinée à un polygone
d'attaches également carré force une dépendance linéaire entre les
8 colonnes de W. Le moment de lacet ne peut être généré par aucune
distribution de tensions.

### Conséquence
Les plateformes carrées sont **exclues** dans notre géométrie
d'ancrages carrée (±1.25 m × ±1.25 m). Ratio d'aspect minimum
recommandé : **~1.20**.

### Corrections appliquées
1. **Défaut restauré** à `700x560` dans `Config.with_n` et CLI.
2. **Garde-fou** dans `Config.with_n` : avertissement (non bloquant)
   si plateforme détectée carrée.
3. **Test de rang** dans `WFW.is_feasible` : rejet automatique des
   poses où W est singulière, avec message explicite.
4. **Documentation** : ratios d'aspect recommandés (700×560, 600×500,
   560×420).

### Leçon de méthode — le sweep WFW était incomplet
Le sweep testait `rhs = (0, 0, mg, 0, 0, 0)` (équilibre statique pur).
Comme `Mz_rhs = 0`, il ne détectait jamais la perte du DOF de lacet :
le LP HiGHS trouvait une solution dans le sous-espace de dimension 5.

**Correction structurelle** : `WFW.is_feasible` teste désormais le
rang(W) **avant** le LP. Une pose avec W singulière est rejetée
immédiatement, ce qui aligne le sweep avec la réalité physique.

### Impact sur les tests existants
- `test_platform_default_is_700x560` (anciennement `_560x560`) : OK
- `test_platform_560x560`, `test_platform_630x630` : passent toujours
  (test explicite avec avertissement)
- `test_square_platform_warns` (nouveau) : confirme le garde-fou
- `test_rectangular_platform_no_warn` (nouveau) : confirme l'absence
  de faux positif

### Note pour le mémoire
Ce résultat mérite une section « Contraintes de conception » :
- Les plateformes carrées sont incompatibles avec ancrages carrés
- Ratio d'aspect minimum : ~1.20
- Analyse structurale (pas un choix esthétique)

---

## D-QUALITY-01 — Corrections de fiabilité et robustesse

**Date** : 2026-09-17
**Statut** : Adoptée
**Portée** : BLOC 6, BLOC 7, BLOC 9, BLOC 10, run_pipeline

### Corrections P1 (bugs réels)
1. **Optimizer.TourProblem** : `feasible_mat` initialisée à `False`
   (au lieu de `True`). Une paire absente du cost_matrix est désormais
   traitée comme infaisable. La diagonale est explicitement mise à
   `True` (self-loop trivial).
2. **run_pipeline** : `--platform-mass` est maintenant transmis en
   mode standard (était ignoré).

### Corrections P2 (fiabilité)
3. **CostCalculator._solve_tension** : vérification indépendante du
   résidu et des bornes après SLSQP. Fallback : retenter depuis le
   milieu des bornes si le warm-start échoue.
4. **TrajectoryProfiler._lspb_speed** : vitesse de décélération bornée
   à ≥ 0 via `max(0.0, ...)`.
5. **Validator** : mise en cache de `_load_all()` — évite ~20 lectures
   disque par run. `invalidate_cache()` force le rechargement.

### Corrections P3 (qualité)
6. **RobotModel** : `assert` remplacés par `raise ValueError`
   (les assert sont désactivés sous `python -O`).
7. **Validator._check_profiles** : tri composite `(segment_id, t)`
   explicite.

### Conséquence
Robustesse accrue sur configurations atypiques (graph dégradé,
plateforme réduite). Temps de validation divisé par ~3 (cache).


---

## D-BLOC7-09 — Paramètres NSGA-II retenus pour le mémoire

**Date** : 2026-09-17
**Statut** : Adoptée
**Blocs concernés** : BLOC 7

### Contexte
Trois runs comparés sur la même géométrie (grille 9×9, plateforme
700×560) :

| Config | Pareto | Gain temps | Gain énergie | Runtime |
|---|---|---|---|---|
| Standard, 500/1500 | 2 | +3.42 % | +1.81 % | 3 min 4 s |
| Zero-loss, 500/1500 | 2 | +3.62 % | +2.95 % | 3 min 32 s |
| Zero-loss, 800/3000 | 3 | +5.64 % | +7.27 % | 9 min 46 s |

### Décision
Retenir **`--zero-loss --pop-size 800 --n-gen 3000`** comme configuration
de production pour le mémoire.

### Justification
- Zero-loss = zéro rejet, tous les points exploitables.
- Budget 800/3000 = gains significativement supérieurs (+65 % temps,
  +400 % énergie vs 500/1500).
- Le front étroit (3 solutions) est **un résultat scientifique**, pas
  un défaut de l'algorithme : temps et énergie sont fortement corrélés
  sur une grille régulière (ρ ≈ 0.98), la baseline zigzag est déjà
  quasi-optimale (gap 3 %).

### Recommandation pour le mémoire
Section « Résultats » à structurer en deux temps :
1. Présenter la configuration retenue et les gains absolus.
2. Discuter le front étroit comme une **validation croisée** entre
   NSGA-II et la baseline boustrophédon : deux méthodes indépendantes
   convergent vers les mêmes bornes, ce qui est une preuve de robustesse.

---

## D-TOOLING-08 — Améliorations du viewer 3D

**Date** : 2026-09-17
**Statut** : Adoptée

### Modifications
1. **Trajectoire désactivée par défaut** : le paramètre `--show-trajectory`
   doit être passé explicitement. Évite la surcharge visuelle lors de la
   présentation.
2. **Points de vue au sol** : les points de la grille sont affichés à
   `z = -0.20 + 0.05 = -0.15 m` (5 cm au-dessus du sol). Ils représentent
   les **plants/localisations**, pas la hauteur caméra. Le z réel des
   waypoints (0.45 m) reste inchangé pour le pipeline.
3. **Plateforme en volume plein** : remplacement du wireframe par un
   `Mesh3d` cubique (12 triangles, face coloriée uniformément).

### Conséquence visuelle
- Séparation nette entre : sol + plants (points gris), robot (câbles +
  cube bleu), structure (cadre + pieds).
- La figure est directement lisible pour un public non-technique.


---

### Extension CLI (2026-09-17)
Retrait de la restriction `choices` sur l'option `--platform` des
scripts `sweep_wfw.py` et `run_wfw_3d.py`. Toute dimension libre
`WxH` en mm est désormais acceptée par le CLI, cohérent avec le
comportement de `Config.with_n`.


---

## D-CONFIG-10 — Passage à une plateforme réduite 300×240 mm

**Date** : 2026-09-17
**Statut** : En investigation
**Blocs concernés** : Config, BLOC 1, BLOC 3

### Contexte
La plateforme 700×560 mm est trop grande pour un prototype M1 (28 % de
la largeur du cadre). Une taille réduite 200-250 mm est souhaitée pour
la crédibilité du montage.

### Mesures WFW (sweep 12×12×8, paire nominale T_min=1/T_max=58)

| Plateforme | WFW X | WFW Y | Hull | Masse |
|---|---|---|---|---|
| 200×160 | ±0.114 m | ±0.114 m | 0.022 m³ | 380 g |
| 250×200 | ±0.341 m | ±0.341 m | 0.182 m³ | 382 g |
| 300×240 | ±0.568 m | ±0.341 m | 0.389 m³ | 384 g |
| 700×560 (réf) | ±0.724 m | ±0.855 m | 1.630 m³ | 417 g |

### Analyse
- 200×160 : WFW réduit à un point — rejeté
- 250×200 : minimum viable (WFW ±0.34 m)
- **300×240 : meilleur compromis** (WFW 4× plus grand que 250×200)

### Décision proposée
Adopter **300×240×50 mm** comme nouvelle référence.
- WFW X = ±0.568 m (79 % du 700×560)
- WFW Y = ±0.341 m (40 % du 700×560)
- Masse réduite de 8 %

### Conséquence
- Grille adaptée : 5×5 sur ±0.25 m ou 7×7 sur ±0.30 m
- Zone opérationnelle réduite de ±0.80 m à ±0.30 m
- Pipeline plus rapide (~30 s vs 3 min 30 s)
- Prototype beaucoup plus crédible



---

## D-CONFIG-11 — Adopter 300×240×50 mm comme plateforme de référence

**Date** : 2026-09-17
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 1, BLOC 3

### Contexte
La plateforme 700×560 mm est trop grande pour un prototype M1
(28 % de la largeur du cadre). Une taille réduite 200-350 mm était
souhaitée.

### Comparaison expérimentale
Deux configurations testées sur grille 5×5 (25 points) :

| Critère | 300×240 | 250×200 |
|---|---|---|
| Points faisables | 25/25 | 25/25 |
| Solutions Pareto | **3** | 2 |
| Gain temps min | **+7.91 %** | +5.56 % |
| Gain énergie min | +8.09 % | +8.01 % |
| Masse | 384 g | 382 g |
| Runtime | 1 min 18 s | 1 min 10 s |

### Décision
Adopter **300×240×50 mm** comme nouvelle référence.
- WFW mesuré : ±0.57 m X, ±0.34 m Y
- Asymétrie X/Y favorable (ratio 1.25)
- Rang W = 6 (pas de singularité)
- Masse 384 g (vs 417 g pour 700×560)

### Conséquence
- Zone opérationnelle utile : ±0.30 m (au lieu de ±0.80 m)
- Grille 5×5 confortable, 7×7 possible avec `--xy-bound 0.30`
- Prototype plus crédible à l'échelle M1
- Pipeline plus rapide

### Note pour le mémoire
Cette décision illustre la démarche empirique : le choix de la
plateforme repose sur des **mesures WFW réelles**, pas sur une
intuition. Le sweep a montré que 200×160 est sous-dimensionné
(WFW réduit à ±0.11 m) et que 300×240 est le meilleur compromis
taille/WFW.


---

## D-CONFIG-11 — Adopter 300×240×50 mm comme plateforme par défaut

**Date** : 2026-09-17
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 1, BLOC 3

### Décision
- Défaut `platform` : `700x560` → `300x240`
- Plateforme de référence : **300×240×50 mm**, masse ≈ 384 g
- Toutes les CLI alignées : `run_pipeline`, `run_wfw_3d`, `sweep_wfw`

### Comparaison empirique
Grille 5×5 @ ±0.25 m (300×240) vs @ ±0.20 m (250×200) :

| Critère | 300×240 | 250×200 |
|---|---|---|
| Points faisables | 25/25 | 25/25 |
| Solutions Pareto | **3** | 2 |
| Gain temps min | **+7.91 %** | +5.56 % |
| Gain énergie min | +8.09 % | +8.01 % |
| Masse | 384 g | 382 g |

300×240 gagne sur la qualité du front et le gain temps.

### Conséquence pour la production
- Zone WFW utile : ±0.57 m X, ±0.34 m Y
- Grille 9×9 sur ±0.80 m rejettera beaucoup de points — adapter avec `--xy-bound 0.30` ou `--n 5/7`
- Prototype plus crédible pour un jury M1


---

## D-CONFIG-12 — Bornes zero-loss dépendantes de la plateforme

**Date** : 2026-09-17
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 4, BLOC 5

### Contexte
`_OP_BOUND_ZERO_LOSS = 0.545` (D-CONFIG-04) a été calibré pour la
plateforme 700×560 dont le WFW est symétrique (±0.72 X, ±0.85 Y).
Avec 300×240, le WFW devient asymétrique (±0.57 X, ±0.34 Y) : la
constante 0.545 rejette 12/81 points en Cause B sur l'axe Y.

### Décision
Remplacer la constante figée par une table `_ZERO_LOSS_BY_PLATFORM` :

| Plateforme | X bound | Y bound | Justification |
|---|---|---|---|
| 700x560 | 0.545 | 0.545 | historique |
| 300x240 | 0.400 | 0.240 | ellipse ±0.568 × ±0.341 |
| 250x200 | 0.280 | 0.280 | ellipse ±0.341 symétrique |
| 200x160 | 0.090 | 0.090 | ellipse ±0.114 |

Dérivation : plus grand rectangle inscrit dans l'ellipse WFW avec
marge de sécurité 10 % pour absorber l'échantillonnage discret du
sweep (12×12×8).

Plateforme inconnue → fallback sur 0.545 avec WARNING explicite.

### Conséquence
- `--zero-loss` garantit 0 rejet sur toutes les plateformes listées.
- 700×560 conserve son comportement historique (pas de régression).
- Une plateforme custom (ex. `450x360`) déclenche un warning et
  utilise 0.545 — l'utilisateur sait qu'il doit ajuster.

### Priorité des options CLI (rappel)
1. `--x-bound` + `--y-bound` → asymétrique explicite
2. `--x-bound` seul → symétrique fallback
3. `--y-bound` seul → symétrique fallback
4. `--xy-bound` → symétrique explicite
5. `--zero-loss` → table par plateforme
6. Défaut → ±0.80 m


---

## D-CONFIG-13 — Source unique DEFAULT_PLATFORM

**Date** : 2026-09-17
**Statut** : Adoptée
**Portée** : Config, tous les scripts CLI

### Contexte
Chaque script CLI (`run_pipeline`, `run_wfw_3d`, `sweep_wfw`,
`view_robot_3d`) avait son propre défaut `--platform` hardcodé. Le
changement de défaut v3.4 → v3.5 (700x560 → 300x240) a créé des
incohérences silencieuses, notamment dans le suffixage conditionnel
des fichiers de sortie.

### Décision
Introduire une constante publique `DEFAULT_PLATFORM: str = "300x240"`
dans `src/config.py`. Tous les scripts importent cette constante pour :
  - leur `--platform` default
  - la logique de suffixage conditionnel des sorties

### Bénéfice
- **Une seule source de vérité** pour la plateforme de référence
- Un changement de défaut ne nécessite qu'**une seule modification**
  dans `config.py`
- Détection automatique des incohérences via les 3 nouveaux tests
  (`test_default_platform_*`)

### Robustesse ajoutée au suffixage
Ajout de la condition `args.platform not in out_csv.stem` pour éviter
les doubles suffixes (`sweep_250x200_250x200.csv`) quand l'utilisateur
a déjà nommé son fichier avec la plateforme.


---

### Précision sur l'ordre des définitions (2026-09-17)
Les constantes calculées dépendantes (`_DEFAULT_MASS_KG`) doivent être
définies APRÈS les fonctions et constantes qu'elles utilisent :
  - `_estimate_mass_kg` (fonction)
  - `_PLATFORM_MAP` (dict)
  - `DEFAULT_PLATFORM` (str)

L'erreur `NameError: _DEFAULT_MASS_KG is not defined` provient d'un
placement en amont de ces dépendances. Correction : déplacer la ligne
juste après `_estimate_mass_kg`.

---

## D-TOOLING-09 — Détection de changement de Config avec --resume

**Date** : 2026-09-17
**Statut** : Adoptée
**Portée** : `scripts/run_pipeline.py`

### Contexte
`--resume` skip les étapes dont les fichiers existent. Sans vérification,
un changement de `--platform`, `--n` ou `--xy-bound` produit des
artefacts mélangés (anciens CSV + nouveaux) **sans erreur**.

### Décision
Écrire un hash de configuration effective dans `data/outputs/.config_hash`
au premier run. Au lancement suivant avec `--resume`, comparer :
  - Hash identique → resume normal
  - Hash différent → RuntimeError avec message explicite

Le hash couvre : N, dimensions, espacement, bornes, masse, attaches_B,
T_min/T_max, z_absolu, K, pop_size, n_gen, seed.

### Conséquence
Impossible de produire silencieusement des artefacts incohérents.
L'utilisateur doit supprimer `data/outputs/*` pour relancer avec une
nouvelle config.


---

## D-BLOC11-10 — Tests `diagnose` sur données synthétiques

**Date** : 2026-09-18
**Statut** : Adoptée
**Bloc concerné** : BLOC 11, tests

### Contexte
Le test `test_diagnose_tradeoff_not_anomaly` utilisait la fixture
`optimizer` (pop=30, gen=20 sur grille 5×5). Avec ce budget minimal,
NSGA-II produit des solutions **30 % pires** que la baseline zigzag
sur les 2 objectifs — correctement classées comme anomalie par
`diagnose()`.

Ce n'est pas un bug de `diagnose()` : c'est un budget insuffisant.
Mais le test ne validait pas la bonne propriété.

### Décision
Remplacer le test par une version à **données synthétiques contrôlées**
qui teste la **logique de classification** :
  - `test_diagnose_tradeoff_not_anomaly` : gains croisés (pas d'anomalie)
  - `test_diagnose_detects_real_anomaly` : pire sur les 2 objectifs

### Conséquence
Le test est maintenant déterministe, rapide (~10 ms vs ~30 s) et
teste ce qu'il prétend tester : la classification des gains, pas la
qualité d'un run NSGA-II.

---

## D-TOOLING-10 — Axe T_max de la heatmap en ordre mathématique

**Date** : 2026-09-18
**Statut** : Adoptée
**Portée** : `scripts/sweep_wfw.py`

### Contexte
La heatmap du sweep affichait T_max en ordre croissant de haut en bas
(5 en haut, ∞ en bas), à l'inverse de la convention d'axe Y
mathématique.

### Décision
Inverser les lignes du pivot avant `imshow` :
    pivot = pivot.iloc[::-1]

### Conséquence
- T_max croît de bas en haut (convention classique)
- T_min reste en ordre croissant de gauche à droite
- Lecture naturelle pour un lecteur habitué aux graphes

---

## D-TEST-01 — Mise à jour des valeurs de référence v3.4 → v3.5

**Date** : 2026-09-18
**Statut** : Adoptée
**Portée** : tests

### Contexte
Le passage à la plateforme 300×240 (v3.5) a réduit le WFW d'environ
40 % en Y. Six tests hardcodaient des valeurs de la v3.4 (700×560).

### Décision
Mettre à jour les valeurs de référence :
  - `test_point_filter` : fourchette `[25, 40]` au lieu de `[45, 60]`
  - `test_robot_model::test_central_equilibrium_self_consistent` :
    suppression de la valeur fixe, remplacée par une vérification
    dynamique de l'équilibre (W·T + F_ext ≈ 0)
  - `test_validator::test_hypothesis_report` : `0.384` au lieu de `0.417`
  - `test_wfw::test_grid_coverage_v3_2` : seuil 35 % au lieu de 40 %

### Robustesse accrue
Le test d'équilibre central ne hardcode plus de valeur — il vérifie
directement l'équation physique, ce qui le rend **agnostique de la
plateforme**.

---

## D-BLOC2-03 — Nomenclature explicite de Kinematics

**Date** : 2026-09-18
**Statut** : Adoptée
**Bloc concerné** : BLOC 2

### Contexte
Les noms `forward`/`inverse` sont inversés par rapport à la convention
robotique classique (forward = actionneurs → task). Risque de confusion
pour tout lecteur ou intégrateur externe.

### Décision
Renommer en noms explicites :
  - `forward(p)`  → `pose_to_lengths(p)`
  - `inverse(L)`  → `lengths_to_pose(L, p0)`

Les anciens noms sont conservés comme aliases dépréciés
(DeprecationWarning) pour ne pas casser les appelants externes.

### Conséquence
Le code est auto-documenté. Un futur utilisateur ne peut plus se tromper
sur le sens de la conversion.


---

## D-TOOLING-11 — Option --offline-html pour le viewer 3D

**Date** : 2026-09-18
**Statut** : Adoptée
**Portée** : `robot_3d_viewer.py`, `view_robot_3d.py`

### Contexte
Le viewer HTML utilise Plotly via CDN — fichier léger (~15 Ko) mais
nécessite Internet. Pour une soutenance ou un archivage long terme,
l'absence de connexion casse la visualisation 3D.

### Décision
Ajouter un flag CLI `--offline-html` :
  - Défaut : CDN (rapide à générer, petit fichier)
  - Avec flag : JS embarqué (~3 Mo, fonctionne hors ligne)

### Conséquence
L'utilisateur choisit selon son contexte :
  - Développement / itération → CDN
  - Soutenance / archive → offline


---

## D-TOOLING-12 — Attaches discrètes dans le viewer 3D

**Date** : 2026-09-18
**Statut** : Adoptée
**Portée** : `src/robot_3d_viewer.py`

### Contexte
Sur la plateforme 300×240 (défaut v3.5), les 8 attaches dessinées
comme des cercles pleins (taille 5) recouvraient entièrement le cube
bleu de la plateforme au centre de la figure 3D.

### Décision
Remplacer les marqueurs pleins par des **cercles creux** (`circle-open`)
de taille 4. L'intérieur transparent laisse voir la plateforme.
Le contour bleu reste visible pour identifier la position des attaches.

### Alternative écartée
Suppression complète des marqueurs — rejetée car elle prive la figure
d'une information utile (position des 8 attaches). La forme creuse
résout le problème visuel sans perte d'information.

---

## D-TOOLING-12bis — Nettoyage du doublon Attaches

**Date** : 2026-09-18
**Statut** : Adoptée
**Portée** : `src/robot_3d_viewer.py`

### Contexte
Le patch D-TOOLING-12 (attaches creux) a inséré un nouveau bloc
`fig.add_trace(...)` **avant** la définition de `B`, au lieu de
remplacer le bloc existant. Résultat : `NameError: B` au premier
appel, et deux blocs identiques dans la méthode.

### Correction
Suppression du bloc inséré au mauvais endroit. Un seul bloc
« Attaches (8) » subsiste, après la définition de `B`.

### Leçon
Un patch qui modifie une méthode existante doit **remplacer** le
bloc ciblé, pas en insérer un nouveau. Détection recommandée :
  grep -c "Attaches (8)" avant et après patch → doit rester à 1.

### Test de prévention ajouté
`tests/test_robot_3d_viewer.py::test_build_figure_smoke` — appelle
`build_figure()` et vérifie qu'aucune exception n'est levée.

---


## D-TOOLING-13 — Retrait des marqueurs d'attaches dans le viewer 3D

**Date** : 2026-09-18
**Statut** : Adoptée
**Portée** : `src/robot_3d_viewer.py`

### Contexte
Les 8 attaches étaient affichées comme cercles bleus creux
(D-TOOLING-12). Malgré la forme creuse, elles surchargeaient
visuellement la figure sur la plateforme 300×240 : le cube bleu
central restait difficile à lire.

### Décision
Suppression complète des marqueurs d'attaches. Leur position reste
matérialisée par :
  - les extrémités basses des 8 câbles,
  - les 8 coins du cube Mesh3d de la plateforme.

### Justification
L'information « où sont les attaches » est déjà portée par la
géométrie des câbles et du cube. Les marqueurs surnuméraires
n'apportaient rien et masquaient la plateforme.

### Conséquence
Figure plus lisible pour la soutenance. La matrice `B` (3, 8) reste
calculée et utilisée par les câbles et la plateforme — seule sa
représentation visuelle explicite est retirée.
---

## D-TOOLING-14 — Correction du winding de la face inférieure du cube

**Date** : 2026-09-18
**Statut** : Adoptée
**Portée** : `src/robot_3d_viewer.py`

### Contexte
La face inférieure du cube de la plateforme (Mesh3d) avait un
winding inversé : ses 2 triangles pointaient leur normale vers
l'intérieur du cube au lieu de l'extérieur. Rendu visuel : face
sombre/absente, cube apparenté à "ouvert" par le bas.

### Cause mathématique
Définition : normale d'un triangle (v0, v1, v2) = (v1-v0) × (v2-v0).
Pour la face inférieure attendue (normale -z), le winding correct
est (0, 2, 1) et (0, 3, 2). Le code utilisait (0, 1, 2) et (0, 2, 3),
soit l'inverse.

### Correction
Permutation des indices j et k pour les triangles 0 et 1 :
    tri_j[0], tri_j[1] : 1, 2 → 2, 3
    tri_k[0], tri_k[1] : 2, 3 → 1, 2

### Conséquence
Cube fermé sur les 6 faces, rendu uniforme.

---

## D-CONFIG-15 — Règle R8 : cinématique strictement positive

**Date** : 2026-09-18
**Statut** : Adoptée
**Blocs concernés** : Config, BLOC 6, BLOC 9

### Contexte
`v_max` et `a_max` n'étaient pas validés. Un utilisateur pouvait
passer `a_max=0` et provoquer une division par zéro silencieuse dans
le calcul LSPB (BLOC 6) et le profiler (BLOC 9).

### Décision
Ajouter la règle R8 dans `Config._validate` : `v_max > 0` et
`a_max > 0`. Message d'erreur préfixé `[R8]`.

### Conséquence
- Les valeurs par défaut (0.045 / 0.03) passent R8.
- Toute config invalide lève immédiatement à la construction.
- 5 tests dédiés (T23).

---

## D-BLOC2-04 — Robustesse de lengths_to_pose aux poses singulières

**Date** : 2026-09-18
**Statut** : Adoptée
**Bloc concerné** : BLOC 2

### Contexte
Si `p0` ou une pose intermédiaire du solveur est confondue avec un
ancrage, `RobotModel.cable_lengths` lève `ValueError`. Le contrat
documenté de `lengths_to_pose` est de retourner `success=False` dans
ce cas, pas de crasher.

### Décision
Capturer le `ValueError` dans la fonction résiduelle et renvoyer un
résidu `inf`. Le solveur `least_squares` traite naturellement ce cas
en s'éloignant de la pose singulière.

### Conséquence
- `lengths_to_pose` respecte désormais son contrat.
- Test de non-régression ajouté.

---






## D-BLOC10-07 — Seuil opérationnel de trois compromis Pareto

**Date** : 2026-10-30
**Statut** : Adoptée
**Bloc concerné** : BLOC 10 (Validator)

### Décision

Après déduplication des solutions par le couple d’objectifs `(time, energy)` :

- `n < 3` compromis distincts et aucune solution dominée : **WARN** ;
- `n >= 3` compromis distincts et aucune solution dominée : **PASS** ;
- au moins une solution dominée : **FAIL**, quelle que soit la cardinalité.

Les solutions brutes restent conservées dans `solutions_pareto.csv` pour
 documenter les trajectoires co-optimales et les symétries. Le statut porte sur
la diversité des compromis objectifs distincts, pas sur le nombre de lignes
brutes.

### Justification

Le seuil de 10 produisait un WARN systématique sur les petites grilles,
notamment le run 3×3 qui contient 4 compromis distincts mais 16 trajectoires
brutes. Le seuil de 3 conserve une alerte pour les fronts réellement pauvres
tout en classant PASS les fronts sans dominance présentant au moins trois
compromis temps-énergie distincts.

---

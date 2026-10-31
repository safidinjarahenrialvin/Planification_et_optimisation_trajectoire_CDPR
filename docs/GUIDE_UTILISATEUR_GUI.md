# Guide utilisateur — GUI Tandem SP2

## 1. Installation

Depuis la racine du dépôt :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
    pip install -e ".[gui,dev]"
```

L’extra `gui` installe Streamlit et Plotly. Le moteur scientifique reste utilisable
sans l’interface avec `pip install -r requirements.txt`.

## 2. Démarrage

```bash
streamlit run app/streamlit_app.py
```

Streamlit affiche une adresse locale, généralement `http://localhost:8501`.
La GUI démarre sans résultat ni graphique. Aucun profil 3×3, mode rapide ou
snapshot de démonstration n’est appliqué implicitement.

## 3. Parcours conseillé

1. Ouvrir **Paramètres** et choisir explicitement un profil d’exécution.
2. Choisir la plateforme dans l’onglet **Plateforme** et, si nécessaire, saisir une dimension libre
   au format `WxH` en mm.
3. Dans l’onglet **Bornes opérationnelles**, choisir le mode `zero-loss`, standard,
   symétrique (`--xy-bound`) ou asymétrique (`--x-bound`/`--y-bound`). Une masse de plateforme
   imposée peut également remplacer l’estimation automatique (`--platform-mass`).
4. Dans l’onglet **Altitude R0**, choisir le mode automatique ou saisir une valeur imposée (`--z-absolu`).
5. Dans l’onglet **Optimisation NSGA-II**, régler `K`, `pop_size`, `n_gen` et la graine (`--K`, `--pop-size`, `--n-gen`, `--seed`).
6. Cliquer sur **Actualiser l’aperçu** et vérifier la section **Prévisualisation**, l’empreinte ainsi que la durée indicative.
7. Après toute modification, actualiser à nouveau l’aperçu; une prévisualisation obsolète bloque le lancement.
8. Pour un calcul long, cocher la confirmation dédiée, puis cliquer sur **Lancer l’exécution sélectionnée**.
9. Attendre la fin du calcul et conserver l’identifiant du run.
10. Ouvrir **Résultats** : la source chargée et le choix de stratégie sont affichés en tête,
   avant les onglets spécialisés.
11. Utiliser les onglets **Scène 3D**, **Trajectoires**, **Profils cinématiques**,
   **Couverture WFW**, **Pareto**, **Analyse & comparaison** et **Validation**.
12. Dans **Analyse & comparaison**, ouvrir **Téléchargements ciblés** pour récupérer
   la trajectoire, le profil, la comparaison baseline ou l’image Pareto de la
   stratégie sélectionnée.
13. Ouvrir **Preuves techniques** dans **Validation** pour les artefacts, les coûts détaillés et la préparation du ZIP complet.

### Charger un résultat produit par le terminal

La GUI peut aussi présenter un résultat produit par `scripts/run_pipeline.py` ou
par une autre commande compatible. Copiez le dossier complet du résultat dans un
sous-dossier de `data/runs/`, par exemple :

```text
data/runs/mon_run_20261028/
├── config.json
├── validation_report.json
├── points_filtres.csv
├── trajectories.csv
├── profiles.csv
└── ...
```

Revenez ensuite à **Accueil**, choisissez `Run : mon_run_20261028`, puis
cliquez sur **Charger cette source**. Les graphiques, KPI et analyses n’apparaissent
qu’après ce chargement explicite.

Une source chargée peut être retirée avec **Revenir à l’état neutre**. Cette action
ne supprime aucun fichier : elle efface uniquement la source active de la session.
Pour être proposée dans le sélecteur, une source doit conserver son `config.json`,
car la vue 3D et l’empreinte de configuration en dépendent.

Chaque run est isolé dans `data/runs/<run_id>`. Cette séparation permet de
retrouver exactement la configuration et les résultats associés à une exécution.

### Créer puis recharger un snapshot

Depuis un run local terminé sous `data/runs/`, ouvrir **Résultats > Validation >
Preuves techniques**, saisir un nom (ou garder la proposition) et cliquer sur
**Créer le snapshot**. La création vérifie le statut `COMPLETED`, le manifeste,
l’inventaire des artefacts, `config.json`, `.config_hash` et la chargeabilité du run.
Elle refuse les runs échoués, annulés ou incomplets, les noms invalides et les
destinations existantes; le run source n’est jamais modifié. Un snapshot créé
n’est pas chargé automatiquement : revenir à **Accueil**, choisir `Snapshot :
<nom>`, puis cliquer sur **Charger cette source**. Les snapshots runtime sont
ignorés par Git et restent propres à l’installation. La publication atomique
sans écrasement nécessite Linux (`renameat2`).

Les bornes d’interface empêchent les valeurs hors budget (`K ≤ 100`,
`pop_size ≤ 2000`, `n_gen ≤ 5000`). Les options `--resume` et `--verbose` restent
gérées hors GUI : chaque lancement crée un run isolé et les logs techniques sont
contrôlés par le processus applicatif. La durée affichée reste une estimation
indicative dépendante de la machine; elle ne constitue pas une garantie de runtime.

## 4. Interpréter les résultats

Le statut `PASS`, `WARN` ou `FAIL` désigne les contrôles automatiques du pipeline,
pas une approbation scientifique humaine ou une validation expérimentale. `WARN`
n’est pas automatiquement une erreur : il faut le lire avec le détail des contrôles
et annoncer la réserve. Un statut `FAIL` doit être analysé avant l’utilisation des
résultats.

Les grandeurs temporelles doivent être distinguées :

- **Temps de mouvement** (`time_motion_s` ou `total_time_motion_s`) : durée des
  déplacements entre les waypoints ; c’est la grandeur utilisée pour calculer les
  gains de temps par rapport à la baseline et pour classer les objectifs Pareto.
- **Temps de stabilisation** (`total_time_stab_s`) : durée ajoutée aux waypoints
  pour permettre la stabilisation de la plateforme et l’acquisition.
- **Temps total** (`total_time_s`) : somme du temps de mouvement et du temps de
  stabilisation.

Un gain de temps affiché par la GUI ne doit donc pas être interprété comme un gain
sur le temps total tant que la stabilisation n’a pas été analysée séparément.

La vue 3D est une représentation des artefacts existants. Elle ne remplace pas
les contrôles numériques du pipeline et ne modifie aucun CSV.

Dans **Résultats**, la stratégie sélectionnée en tête de page est réutilisée par
les onglets **Scène 3D**, **Trajectoires**, **Profils cinématiques** et
**Analyse & comparaison**. Les métriques propres à la stratégie sont affichées
dans l’analyse comparative, tandis que chaque onglet présente ses propres figures.

Les trois trajectoires sont présentées avec les noms suivants dans le sélecteur,
les titres, les légendes et les graphiques : **Trajectoire compromis**,
**Trajectoire temps optimal** et **Trajectoire énergie optimale**. Les identifiants
techniques `compromise`, `time_opt` et `energy_opt` restent conservés dans les
CSV et les rapports afin de préserver la compatibilité des artefacts.

Dans **Couverture WFW**, le filtre **Afficher** permet de limiter la figure aux
points générés, aux points retenus ou aux points rejetés. Cette sélection ne
modifie jamais les artefacts ni les statistiques du run.

Les statistiques détaillées de la matrice des transitions ne sont plus affichées
dans le parcours principal de **Validation**, afin de préserver une lecture courte
des contrôles. Elles restent disponibles dans `summary.json`, `cost_matrix.csv`,
les rapports et l’archive ZIP. Les calculs excluent les boucles `i = j` et les
distributions portent uniquement sur les transitions faisables.

Dans le tableau des hypothèses sous **Résultats > Validation**, un statut `GELÉE`
signifie que le paramètre est figé dans le référentiel courant; cela ne signifie pas
que l’hypothèse est validée. Lire les
sources déclarées et les actions de vérification, et respecter le statut
scientifique du manifeste de campagne.

La référence comparative est identifiée par la colonne `kind` de `comparison.csv`.
Sur une grille complète, le comparateur utilise `baseline_zigzag`. Si la grille est
partielle et que le zigzag n’est pas constructible, il utilise `baseline_nn`
(`Baseline de repli historique : plus proche voisin`). La baseline nominale est
affichée comme **Baseline : zigzag**. La comparaison baseline dans la
vue **Trajectoire**, les graphiques, l’Historique et le rapport jury reprennent le
libellé correspondant au kind réel : un run historique utilisant `baseline_nn` reste chargeable et est
explicitement signalé comme fallback. Les CSV conservent les identifiants machine
`baseline_zigzag` et `baseline_nn` afin de préserver la compatibilité des artefacts.

## 5. Exports

La section **Preuves techniques** (dans **Résultats > Validation**) propose :

- les fichiers CSV pour les analyses tabulaires ;
- les fichiers JSON pour la configuration et les rapports ;
- les PNG déjà générés par le pipeline ;
- les rapports Markdown existants et un résumé généré du run ;
- une archive ZIP contenant tous les artefacts du run.

L’archive ZIP est la meilleure option pour transmettre un run complet : elle
conserve `config.json`, les rapports, les tableaux et les figures dans un seul
fichier. Elle est assemblée uniquement après clic sur **Préparer l’archive
complète (ZIP)**; le bouton de téléchargement apparaît une fois la préparation
terminée. Le contenu préparé est conservé dans la session pour éviter un nouvel
assemblage à chaque interaction.

## 6. Limites connues

La Phase 8 exporte les figures PNG produites par le pipeline. La génération
PNG à la volée d’une nouvelle caméra 3D n’est pas activée : la vue 3D reste
interactive dans le navigateur et l’archive conserve les figures scientifiques
existantes.

# Suivi de l’amélioration GUI de Tandem SP2

**Projet :** `tandem_sp2`
**Branche active :** `feature/gui-improvement`
**Version scientifique et GUI de référence :** branche publiée sur GitHub, dérivée
de `main`
**Document directeur :** [`PLAN_AMELIORATION_GUI.md`](PLAN_AMELIORATION_GUI.md)

Ce fichier est le registre de continuité du projet. Il indique ce qui est terminé, ce qui est en cours, ce qui reste à réaliser, les décisions prises et les critères à vérifier. Toute personne ou toute IA qui reprend le projet doit commencer par lire ce document et le plan directeur.

---

## 1. Règles de travail

1. Ne pas réécrire les algorithmes scientifiques sans justification et test de non-régression.
2. Ne pas importer Streamlit dans les modules scientifiques de `src/`.
3. Conserver le fonctionnement du terminal pendant toute la migration.
4. Réaliser une seule étape fonctionnelle à la fois.
5. Après chaque étape : exécuter les tests, vérifier le diff, documenter le résultat et pousser un commit identifiable.
6. Ne pas mélanger plusieurs changements fonctionnels dans un même commit.
7. Conserver la configuration et les résultats associés à chaque exécution.
8. Toute correction de bug doit être accompagnée d’un test qui reproduit le bug.

---

## 2. État global

**Statut actuel :** socle GUI, annulation asynchrone, CI, refonte des Résultats,
filtre WFW, téléchargements ciblés et paramétrage GUI de l’altitude absolue R0
livrés; l’audit responsive 1024/768 est terminé pour les quatre pages ciblées;
une première tranche d’accessibilité sémantique des graphiques et tableaux est
également livrée.
La qualification scientifique nominale et l’accessibilité approfondie restent
ouvertes.
**Dernière étape vérifiée :** seuil du contrôle Pareto harmonisé à `WARN` pour
`n < 3` compromis distincts et `PASS` à partir de 3; 406 tests non lents
réussis et 1 test lent écarté, Ruff, compilation et smoke test `--fast` validés;
Ruff, compilation, `git diff --check` et contrôle Chromium à 1024/768 réussis;
aucun débordement horizontal global ni erreur JavaScript.
**Dernière étape validée :** barre latérale automatiquement repliée à 768 px,
KPI Paramètres réagencés, options de scène 3D lisibles et onglets Résultats
visibles; preuves dans `docs/evidence/gui-responsive-20261029/README.md`.
**Étape suivante recommandée :** poursuivre l’audit clavier, focus, lecteurs
d’écran et impression PDF; ne pas déduire une validation scientifique d’un simple
statut technique `PASS`.

### Légende

- `[x]` terminé et vérifié ;
- `[~]` en cours ;
- `[ ]` à réaliser ;
- `[!]` bloqué ou nécessitant une décision.

### Backlog consolidé #1–#23

Ce tableau est la source de vérité opérationnelle du chantier. « Terminé » signifie
implémenté et vérifié dans la branche; cela ne signifie pas que le résultat
scientifique nominal 9×9 est qualifié.

| N° | Sujet | État | Preuve ou prochaine action |
|---:|---|:---:|---|
| 1 | Contrats et contrôles principaux des artefacts | [x] | Schémas, manifests, erreurs contrôlées et exclusions validés; commits `272566d`, `7992686`, `e2f7fe5`. |
| 2 | Qualification scientifique nominale 9×9, multi-seeds, B1/B2/B5 | [~] | Seeds 42/43/44 exécutées; revue humaine de stabilité, acceptation scientifique B1/B2/B5 toujours requise (rapport nominal). |
| 3 | Progression interne NSGA-II | [x] | Callback `pymoo` propagé jusqu’à la GUI; progression générationnelle réelle sans ETA spéculative, couverte par tests. |
| 4 | Annulation coopérative avec statut `CANCELLED` | [x] | Pipeline et GUI asynchrones, bouton d’annulation, worker thread-safe et tests; commits `ea7143c`, `47b0f7d`. |
| 5 | Nom physique du fichier baseline en fallback | [x] | Labels canoniques partagés; `baseline_nn` reste chargeable et s'affiche explicitement comme fallback historique; tests service, GUI et export. |
| 6 | Définition de « plus rapide » | [x] | Temps de mouvement et temps total séparés; commit `7618a03`. |
| 7 | Statistiques complètes des gains | [x] | Min/max, stratégies, baseline, périmètre et formules; commit `db747e3`. |
| 8 | Historique sans source active | [x] | Sélection/chargement explicite des snapshots et runs valides; commit `e7f3580`. |
| 9 | Qualification multi-largeurs d’écran | [x] | Accueil, Paramètres, Résultats (Scène 3D/Pareto) et Historique qualifiés à 1024/768 px; scrollWidth, sidebar, onglets et captures consignés dans `docs/evidence/gui-responsive-20261029/`. |
| 10 | Réorganisation des vues Résultats | [x] | Quatre vues principales et expander secondaire **Preuves techniques**, test AppTest exact; clôture détaillée en section 24. |
| 11 | Accessibilité et lisibilité des tableaux | [~] | Contraste, focus, statuts textuels et règles d’impression partiellement couverts; compléter clavier, lecteurs d’écran, tableaux et PDF. |
| 12 | ZIP à la demande et mesure du coût | [~] | ZIP à la demande et première mesure FAST/nominale archivées; accumuler des observations comparables sans présenter l’échantillon comme garantie. |
| 13 | Diagnostic des runs échoués/incomplets | [x] | Statut, étape, erreur et artefacts diagnostiqués par `ResultService.diagnose_run`; commit `e7f3580`. |
| 14 | Isolation des runs invalides | [x] | Exclusion des comparaisons et affichage séparé dans Historique; commit `e7f3580`. |
| 15 | Contrats CSV complémentaires | [x] | Chaînes numériques, entiers fractionnaires, champs texte et optionnels; commit `8833520`. |
| 16 | Sous-ensembles et vues vides | [x] | Politique absence/vide explicite pour les CSV optionnels; qualification de nouveaux sous-ensembles à poursuivre si besoin; commit `8833520`. |
| 17 | Cohérences inter-fichiers approfondies | [x] | Rangs, références points, profils, cumuls, `n_waypoints` et baseline; commit `8833520`. |
| 18 | Preuve GitHub Actions sur un commit poussé | [x] | CI déclenchée sur `feature/**`; run `40725284877` terminé `success`. |
| 19 | CI manuelle/planifiée pour tests lents | [x] | Workflow manuel `.github/workflows/slow-tests.yml` ajouté; exécution réelle encore à mesurer. |
| 20 | Calibration des estimations de durée | [ ] | Accumuler des mesures comparables avant calibration; conserver le fallback heuristique. |
| 21 | Paramétrage GUI de l’altitude absolue R0 | [x] | Modes Automatique/Valeur imposée, bornes R6, précision 0,001 m, aperçu invalidé si modifié, empreinte et `config.json`; propagation testée jusqu’aux points générés. |
| 22 | Noms utilisateur des trois trajectoires | [x] | Libellés centralisés dans `visualization/labels.py` et appliqués au sélecteur, aux graphiques, titres et script oral; 404 tests non lents, Ruff, compilation et smoke test `--fast` validés. |
| 23 | Seuil de statut du front Pareto | [x] | `WARN` si moins de 3 compromis temps-énergie distincts, `PASS` à partir de 3 sans dominance, `FAIL` si une solution est dominée; tests unitaires, fixture, smoke test 3×3 et documentation mis à jour. |
| 24 | Configuration GUI alignée sur le CLI | [x] | Plateforme libre, masse imposée, bornes standard/zero-loss/symétriques/asymétriques, altitude R0 et budget NSGA-II regroupés par domaines; propagation testée jusqu’à `Config.with_n`. |
| 25 | Organisation de la page Paramètres par onglets | [x] | Niveau d’étude conservé en tête, paramètres répartis dans quatre onglets, contenus redondants retirés, action de lancement harmonisée avec la charte et section **Prévisualisation** placée en dernier. |

Les points #2 et #11 ne doivent pas être déclarés terminés sur la seule base du
smoke test 3×3 ou de la santé HTTP de Streamlit. Le point #9 porte sur la mise en
page aux largeurs testées, pas sur l’accessibilité complète. Pour #19, le
workflow est livré mais sa durée et son artefact doivent encore être mesurés.

---

## 3. Tâches accomplies

- [x] Décision de conserver le projet existant au lieu de créer un projet indépendant.
- [x] Choix d’une interface Web locale basée sur Streamlit.
- [x] Choix de Plotly pour les visualisations interactives et 3D.
- [x] Définition du principe d’architecture : GUI → services → algorithmes scientifiques.
- [x] Rédaction du plan directeur dans `docs/PLAN_AMELIORATION_GUI.md`.
- [x] Création de la branche Git `feature/gui-improvement`.
- [x] Création de ce fichier de suivi.
- [x] Installation des dépendances exactes dans un environnement virtuel.
- [x] Exécution des 264 tests non lents avec succès.
- [x] Compilation Python et contrôle Ruff validés.
- [x] Exécution du smoke test `--fast` avec le code retour 0.
- [x] Création de `docs/baseline_reference.md`.
- [x] Archivage du snapshot dans `data/snapshots/20261027_fast_reference/`.
- [x] Cartographie de `scripts/run_pipeline.py`.
- [x] Documentation des entrées/sorties des BLOCs 4 à 11.
- [x] Documentation des effets de bord, exceptions et codes retour.
- [x] Documentation des risques connus du mode `--resume`.
- [x] Création de `docs/architecture_current.md`.
- [x] Création de `services.PipelineOptions`.
- [x] Création de `services.PipelineRequest`.
- [x] Création de `services.PipelineResult`.
- [x] Création de `services.PipelineService`.
- [x] Migration du CLI pour appeler `PipelineService`.
- [x] Ajout des tests du contrat du service.
- [x] Vérification du smoke test via le nouveau chemin CLI → service.
- [x] Vérification de la reprise `--resume`.
- [x] Vérification de l’identité des CSV scientifiques avec le snapshot de référence.
- [x] Création de `ConfigurationService`.
- [x] Validation explicite de `Config` et des options d’exécution.
- [x] Regroupement des paramètres par domaines fonctionnels.
- [x] Ajout des unités et valeurs dérivées dans la représentation JSON.
- [x] Écriture atomique de `config.json` pour chaque run.
- [x] Conservation de l’empreinte historique `.config_hash`.
- [x] Ajout des tests de configuration contrôlée.
- [x] Déclaration de l’extra optionnelle `gui` dans `pyproject.toml`.
- [x] Création du point d’entrée `app/streamlit_app.py`.
- [x] Création de la navigation multipage.
- [x] Création de l’état de session minimal.
- [x] Création des pages Accueil, Paramètres et Résultats.
- [x] Ajout des tests `AppTest`.
- [x] Vérification que le démarrage GUI ne lance aucun calcul scientifique.
- [x] Création du formulaire de paramètres contrôlé.
- [x] Validation des paramètres avant création du run.
- [x] Ajout du lancement explicite du mode rapide.
- [x] Ajout d’un identifiant unique de run.
- [x] Ajout de la progression par BLOC via callback indépendant de Streamlit.
- [x] Traduction des exceptions en messages utilisateur.
- [x] Création de répertoires isolés sous `data/runs/<run_id>`.
- [x] Affichage du statut et des artefacts du dernier run.
- [x] Test d’intégration du parcours GUI complet avec `AppTest`.
- [x] Création de `ResultService` et `RunResults`.
- [x] Ajout des contrôles d’artefacts manquants ou illisibles.
- [x] Ajout des statistiques des points et trajectoires.
- [x] Ajout du graphique Pareto interactif Plotly.
- [x] Ajout des tableaux de trajectoires et comparaison.
- [x] Ajout des profils cinématiques.
- [x] Ajout des contrôles PASS/WARN/FAIL.
- [x] Ajout de la consultation des hypothèses B1 à B5.
- [x] Ajout des tests du service de résultats et de la figure Pareto.
- [x] Extraction de la construction 3D dans `visualization/robot_3d.py`.
- [x] Conservation d’une façade compatible dans `src.robot_3d_viewer`.
- [x] Ajout des couches bâti, ancrages, pieds, câbles et plateforme.
- [x] Ajout des couches points valides, points rejetés, plants et centre.
- [x] Ajout des cases d’affichage/masquage dans la GUI.
- [x] Ajout du choix de trajectoire dans la GUI.
- [x] Alignement des dépendances historiques avec l’extra GUI et la contrainte pytest du packaging.
- [x] Extension de la CI à toutes les couches Python, avec compilation et santé HTTP Streamlit.
- [x] Centralisation des libellés de stratégies et correction du cas `baseline_nn` dans les vues et exports.
- [x] Distinction affichée entre solutions Pareto brutes et compromis temps-énergie distincts.
- [x] Identification des stratégies qui déterminent les gains minimaux en temps et en énergie.
- [x] Séparation de l’actualisation de l’aperçu et du lancement; bornes GUI et estimation de durée indicative ajoutées.
- [x] Validation stricte des schémas CSV, types numériques, valeurs finies, empreintes et cohérences inter-artefacts ajoutée à `ResultService`.
- [x] Manifeste `run_manifest.json` ajouté pour distinguer les runs `RUNNING`, `COMPLETED` et `FAILED` et exclure les runs non terminés.
- [x] Temps de mouvement, stabilisation et temps total explicitement distingués dans les KPI, figures, exports, script oral et guide utilisateur.
- [x] Convention de présentation harmonisée : **Trajectoire compromis**, **Trajectoire temps optimal** et **Trajectoire énergie optimale**; les identifiants machine `compromise`, `time_opt` et `energy_opt` restent inchangés dans les CSV, services et validations.

---

## 4. Phase 0 — Référence scientifique

**Objectif :** figer le comportement actuel avant modification.

- [x] Vérifier l’état complet du dépôt distant.
- [x] Exécuter les tests rapides dans un environnement propre.
- [x] Exécuter le smoke test du pipeline.
- [x] Vérifier les fichiers de sortie attendus.
- [x] Enregistrer les métriques de référence.
- [x] Enregistrer les versions Python et dépendances.
- [x] Créer `docs/baseline_reference.md`.
- [x] Créer une copie documentée de la sortie de référence.
- [x] Définir les règles initiales de comparaison numérique.
- [x] Référence prête pour le refactoring ; validation finale par tests à chaque étape.

**Critère de sortie :** le projet actuel peut être exécuté et son résultat de référence est archivé et compréhensible sans échange oral.

---

## 5. Phase 1 — Cartographie du code

- [x] Cartographier les entrées et sorties des BLOCs 0 à 11.
- [x] Identifier les fonctions d’orchestration dans `scripts/run_pipeline.py`.
- [x] Identifier les effets de bord et écritures sur disque.
- [x] Identifier les exceptions destinées à la CLI.
- [x] Identifier les paramètres réellement utilisés.
- [x] Créer `docs/architecture_current.md`.

**Critère de sortie :** une personne extérieure peut expliquer comment un paramètre devient un fichier de résultat.

---

## 6. Phase 2 — Service d’orchestration

- [x] Créer les objets de requête et d’options.
- [x] Créer `PipelineService` sans modifier les formules scientifiques.
- [x] Faire appeler le service par le CLI.
- [x] Ajouter les objets de résultat.
- [x] Conserver le répertoire de sortie fourni par l’appelant, sans mélange entre runs.
- [x] Vérifier la compatibilité avec `--fast` et `--resume`.
- [x] Ajouter les tests unitaires et d’intégration du service.
- [x] Comparer les sorties du service avec la référence.

**Critère de sortie :** le CLI et les tests utilisent le même service, sans import GUI dans `src/`.

---

## 7. Phase 3 — Configuration contrôlée

- [x] Créer la validation explicite des paramètres.
- [x] Regrouper les paramètres par domaine : géométrie, mécanique, cinématique, optimisation.
- [x] Ajouter les unités dans les noms et messages.
- [x] Sérialiser la configuration effective.
- [x] Calculer et conserver l’empreinte de configuration.
- [x] Tester les configurations valides et invalides.

**Critère de sortie :** une configuration invalide est refusée avant tout calcul long avec un message exploitable.

---

## 8. Phase 4 — Squelette GUI

- [x] Ajouter la dépendance GUI de manière contrôlée dans `pyproject.toml`.
- [x] Créer `app/streamlit_app.py`.
- [x] Créer la navigation multipage.
- [x] Créer l’état de session minimal.
- [x] Ajouter les pages Accueil, Paramètres et Résultats.
- [x] Ajouter les tests `AppTest`.

**Critère de sortie :** la GUI démarre sans lancer de calcul et conserve l’état de navigation.

---

## 9. Phase 5 — Formulaire et exécution

- [x] Ajouter le formulaire de paramètres.
- [x] Ajouter la validation avant soumission.
- [x] Ajouter le lancement explicite du mode rapide.
- [x] Ajouter l’identifiant de run.
- [x] Ajouter l’affichage de la progression par bloc.
- [x] Traduire les exceptions en messages utilisateur.
- [x] Permettre de recharger le dernier run conservé en session.

**Critère de sortie :** un utilisateur peut saisir une configuration, lancer un run rapide et retrouver ses résultats.

---

## 10. Phase 6 — Résultats et analyses

- [x] Ajouter les statistiques des points.
- [x] Ajouter les statistiques WFW.
- [x] Ajouter le graphique Pareto interactif.
- [x] Ajouter les tableaux des trajectoires.
- [x] Ajouter les profils cinématiques.
- [x] Ajouter les contrôles PASS/WARN/FAIL du BLOC 10.
- [x] Ajouter la comparaison avec la baseline du BLOC 11.
- [x] Ajouter la consultation des hypothèses B1 à B5.

**Critère de sortie :** tous les résultats principaux du pipeline sont lisibles dans l’interface sans ouvrir manuellement les CSV.

---

## 11. Phase 7 — Visualisation 3D

- [x] Transformer le visualiseur Plotly actuel en composant réutilisable.
- [x] Afficher le bâti, les pieds, les câbles et la plateforme.
- [x] Afficher les points de vue et les points rejetés avec une légende claire.
- [x] Ajouter une représentation simple des plants.
- [x] Ajouter les cases d’affichage/masquage.
- [x] Ajouter le choix de la trajectoire.
- [x] Tester la cohérence avec `RobotModel`.
- [x] Décider que l’animation temporelle reste optionnelle et hors périmètre V1.

**Critère de sortie :** la scène 3D est interactive, cohérente avec le modèle et utilisable sans recalculer le pipeline.

---

## 12. Phase 8 — Exports, packaging et documentation

- [x] Ajouter les téléchargements CSV, JSON, PNG et Markdown.
- [x] Ajouter un export ZIP d’un run.
- [x] Mettre à jour le README.
- [x] Écrire le guide utilisateur GUI.
- [x] Écrire le guide développeur GUI.
- [x] Vérifier une installation dans un environnement vierge.
- [x] Vérifier le démarrage depuis la commande documentée.
- [x] Préparer un tag de version interactive après validation finale.

**Critère de sortie :** un futur repreneur peut installer, lancer, tester et comprendre le projet sans échange oral préalable.

---

## 13. Journal des décisions et changements

| Date | Étape | Décision ou changement | Vérification | Commit |
|---|---|---|---|---|
| 2026-10-27 | Préparation | Conservation du projet existant et ajout d’une couche GUI progressive | Plan directeur rédigé | À renseigner |
| 2026-10-27 | Préparation | Création de `feature/gui-improvement` | Branche créée depuis `main` | À renseigner |
| 2026-10-27 | Préparation | Création du registre de suivi | Lecture du fichier effectuée | b0bb9d0 |
| 2026-10-27 | Phase 0 | Référence rapide créée : 264 tests, compileall et Ruff OK, smoke test code 0 | `docs/baseline_reference.md` et snapshot archivés | À renseigner |
| 2026-10-27 | Phase 1 | Cartographie complète de l’orchestrateur et des BLOCs 4–11 | `docs/architecture_current.md`, aucun algorithme modifié | À renseigner |
| 2026-10-28 | Phase 2 | Extraction de `PipelineService`, contrat typé et migration du CLI | 267 tests, Ruff, smoke test et reprise OK | À renseigner |
| 2026-10-28 | Phase 3 | Ajout de `ConfigurationService` et de `config.json` par run | 271 tests, empreinte identique, smoke test code 0 | À renseigner |
| 2026-10-28 | Phase 4 | Squelette Streamlit multipage et état de session | 274 tests, AppTest, Ruff et compilation OK | À renseigner |
| 2026-10-28 | Phase 5 | Formulaire, run isolé, progression et exécution rapide | 276 tests, parcours GUI réel validé, artefacts OK | À renseigner |
| 2026-10-28 | Phase 6 | `ResultService`, statistiques, Pareto, validation, profils et hypothèses | 280 tests, page analyses validée sur run réel | À renseigner |
| 2026-10-28 | Phase 7 | Composant 3D partagé, couches activables et trajectoire sélectionnable | 283 tests, CLI HTML et AppTest GUI validés | À renseigner |
| 2026-10-28 | Phase 8 | Exports individuels, ZIP, guides GUI et dépendances packaging | Tests exports, AppTest et installation vierge validés | À renseigner |
| 2026-10-28 | Stabilisation | Fixtures de tests reproductibles, bootstrap Streamlit et découverte setuptools explicite | 287 tests, Ruff OK, imports `app/services/src/visualization` depuis `/tmp` OK | À renseigner |
| 2026-10-28 | Validation GUI | Test d’intégration du contrôleur : run complet, progression, artefacts et rechargement | 288 tests, Ruff OK, pipeline GUI rapide validé | À renseigner |
| 2026-10-28 | Validation finale | Validation V1 complète et décision de laisser l’animation hors périmètre | `docs/VALIDATION_FINALE_GUI.md`, 288 tests, smoke code 0 | À renseigner |
| 2026-10-28 | Présentation 1 | Accueil jury alimenté par les données réelles du run courant ou du snapshot de référence | 290 tests, graphiques Plotly et tableau de comparaison vérifiés | À renseigner |
| 2026-10-28 | Présentation 2 | Profils d’exécution, confirmation des runs longs et prévisualisation de configuration | 291 tests, AppTest Paramètres et Ruff OK | À renseigner |
| 2026-10-28 | Présentation 3 | Sélection de stratégie partagée, courbes XY et profils vitesse/norme | 292 tests, figures Plotly et page Résultats vide validées | À renseigner |
| 2026-10-28 | Présentation 4 | Matrice des coûts et rapports WFW intégrés à `RunResults`, heatmaps dynamiques et alertes FOV | 293 tests, heatmaps 9×9 et onglet Résultats validés | À renseigner |
| 2026-10-28 | Présentation 5 | Rapport jury structuré exportable depuis la GUI avec conclusion, comparaison, validation et hypothèses B1–B5 | 294 tests, rapport de référence inspecté, Ruff OK | À renseigner |
| 2026-10-28 | Présentation 6 | Registre historique, comparaison A/B, empreintes et graphiques multi-runs | 296 tests, référence et état sans runs locaux validés | À renseigner |
| 2026-10-28 | Présentation 7 | Animation 3D Plotly depuis profils temporels réels, frames bornées, lecture/pause et curseur | 297 tests, animation `time_opt` validée sur fixture, Ruff OK | À renseigner |
| 2026-10-28 | Présentation 8 | Snapshot de référence navigable, configuration gelée et parcours accueil → résultats testé sans traceback | 298 tests, AppTest jury et validation complète OK | À renseigner |
| 2026-10-28 | Présentation 9 | Mode de démonstration guidée transversal avec étapes visibles et sortie réversible | 298 tests, AppTest du parcours guidé et Ruff OK | À renseigner |
| 2026-10-28 | Présentation 10 | Script oral dynamique fondé sur les KPI du run et scénario chronométré avec questions jury | 299 tests, script de référence et AppTest validés | À renseigner |
| 2026-10-28 | Présentation 11 | Charte bleu technique, cartes KPI, onglets orientés lecture et textes naturels pour le public | 299 tests, AppTest GUI, Ruff et diff-check OK | À renseigner |
| 2026-10-28 | Présentation 12 | Page Méthode & limites expliquant la chaîne de calcul, les indicateurs, la validation et la portée des résultats | 300 tests, AppTest page Méthode et parcours guidé validés | À renseigner |
| 2026-10-28 | Présentation 13 | Démarrage neutre, chargement explicite des snapshots CLI/runs et suppression du profil 3×3 implicite | 300 tests, AppTest neutre, Ruff et diff-check OK | À renseigner |
| 2026-10-28 | Présentation 14 | Audit des libellés et états vides : aucune référence affichée sans source, vocabulaire neutre et scénario aligné | 300 tests, audit grep, Ruff et diff-check OK | À renseigner |
| 2026-10-28 | Présentation 15 | Registre de sources complètes, exclusion des dossiers incomplets et tests de découverte | 301 tests, source selector et validation complète OK | À renseigner |
| 2026-10-28 | Présentation 16 | Réinitialisation de source sans suppression de fichiers et contrôle `config.json` avant chargement | 302 tests, parcours reset et validation complète OK | À renseigner |
| 2026-10-28 | Présentation 17 | Notifications détaillées, couleurs de blocs bleutées, trajectoire 3D décochée et figures Plotly dynamiques/échantillonnées | 305 tests, validation complète et contrôle statique OK | À renseigner |
| 2026-10-28 | Présentation 18 | Projection WFW interactive issue des CSV et suppression définitive des rendus PNG dans les onglets analytiques | 306 tests, page Validation et lecteur de résultats validés | À renseigner |
| 2026-10-28 | Présentation 19 | Retrait de la page Méthode, parcours guidé ramené à cinq étapes et fond global bleu-gris | 306 tests, navigation GUI et Ruff validés | À renseigner |
| 2026-10-28 | Présentation 20 | Intégration de `baseline_zigzag.csv` dans les vues, comparaison absolue à axes séparés, plan XY/3D enrichis et synthèse interprétable | 306 tests, validation complète et contrôle statique OK | À renseigner |
| 2026-10-28 | Reprise propre | Validation indépendante dans un environnement temporaire Python 3.12 : suite complète, Ruff sur toutes les couches, compilation, smoke test et santé HTTP Streamlit | 306 tests en 74,35 s ; smoke `WARN` attendu, code 0 ; HTTP `ok` | Validation locale, aucun commit |
| 2026-10-28 | Présentation 21 | Palette Tech & SaaS 60-30-10, surfaces claires, navigation sombre avec libellés accessibles, CTA indigo et ombres douces | 308 tests, Ruff, compilation et styles calculés du menu vérifiés | Validation locale, aucun commit |
| 2026-10-28 | Packaging et CI | Dépendance Streamlit ajoutée à `requirements.txt`, pytest aligné sur le packaging, Ruff/compileall étendus et santé HTTP Streamlit ajoutée à la CI | 307 tests non lents, Ruff, compilation, smoke et HTTP `ok` | 2545512 |
| 2026-10-28 | Libellés baseline | Source de vérité partagée pour les libellés; `baseline_nn` est affichée comme « Baseline plus proche voisin » dans GUI, 3D, graphiques et exports | 308 tests non lents, test ciblé `baseline_nn`, Ruff et diff-check | ff24ed4 |
| 2026-10-28 | Documentation et traçabilité | Mise à jour des références de commits, résultats de validation, installation et comportement des baselines | Références obsolètes absentes, diff-check OK | Étape courante |
| 2026-10-28 | KPI Pareto et gains | Distinction entre solutions brutes et compromis distincts; stratégie déterminante des gains minimaux ajoutée aux vues, exports et script oral | 309 tests non lents; snapshot `16` brutes, `4` distinctes; Ruff et compileall OK | 6d5f507 |
| 2026-10-28 | Aperçu Paramètres | Actualisation indépendante, invalidation après modification, confirmation des calculs longs, bornes `K/pop_size/n_gen` et estimation indicative | 311 tests non lents, 4 tests AppTest Paramètres, Ruff et compileall OK | 75901b5 |
| 2026-10-28 | Fiabilité des artefacts | Schémas CSV, normalisation des types, rejet des `NaN`/infinis, contrôles `kind`/points/empreinte et messages `ResultLoadError` explicites | 316 tests, Ruff et compileall OK | À committer |
| 2026-10-28 | Manifeste d’exécution | Statut atomique par run, étapes terminées, artefacts disponibles, étape fautive et exclusion des statuts non `COMPLETED` | 24 tests ciblés, Ruff et compileall OK | À committer |
| 2026-10-28 | Sémantique temporelle | Gains explicitement basés sur `time_motion_s`; ajout de la décomposition mouvement/stabilisation/total dans les vues et exports | 317 tests, Ruff et compileall OK | À committer |

---

## 14. Format obligatoire pour chaque prochaine étape

Avant de modifier le code :

```text
Étape visée :
Fichiers concernés :
Risque scientifique :
Tests prévus :
Critère d’acceptation :
```

Après modification :

```text
Fichiers modifiés :
Tests exécutés :
Résultats :
Limites connues :
Commit :
Push :
```

Une étape ne doit être déclarée terminée que si son critère d’acceptation est vérifié.

---

## 15. Étape 4 — validation sémantique des artefacts

**Étape visée :** compléter les contrôles existants sans reconstruire les validateurs CSV déjà présents : imposer une baseline unique, vérifier l’alignement des stratégies entre comparaison, résumé, trajectoires, profils et diagnostic, contrôler la structure minimale des rapports JSON consommés par la GUI et rejeter proprement un manifeste dont la racine n’est pas un objet.

**Fichiers concernés :** `services/result_service.py`, `tests/test_result_service.py`, `tests/test_gui_skeleton.py`, `docs/SUIVI_AMELIORATION_GUI.md`.

**Risque scientifique :** aucun changement d’algorithme ni de métrique; les runs historiques dépourvus d’une baseline unique ou dont les stratégies ne s’alignent pas seront désormais refusés au chargement plutôt que présentés comme comparables. L’artefact CSV de trajectoire baseline reste optionnel pour préserver les anciens dossiers qui ne contiennent pas ce fichier.

**Tests prévus :** tests ciblés de service et AppTest; suite non lente complète; Ruff; compilation; smoke test FAST et santé HTTP Streamlit.

**Critère d’acceptation :** les artefacts mal formés donnent un `ResultLoadError` contextualisé et l’interface affiche une erreur contrôlée sans exception; le snapshot versionné et un run FAST complet restent chargeables.

**Après modification :**

```text
Fichiers modifiés : services/result_service.py, tests/test_result_service.py, tests/test_gui_skeleton.py, docs/SUIVI_AMELIORATION_GUI.md
Tests exécutés : tests ResultService, AppTest ciblé, suite pytest -m "not slow", Ruff, compileall, pipeline FAST, endpoint /_stcore/health
Résultats : 328 tests réussis, 1 test lent écarté; Ruff et compilation réussis; pipeline FAST COMPLETED avec WARN Pareto attendu; ResultService charge 9 points et 3 stratégies; Streamlit health retourne ok.
Limites connues : aucun run scientifique nominal 9×9 ni test lent exécuté; le smoke test 3×3 ne constitue pas une qualification scientifique de production.
Commit : intitulé retenu — `fix(results): enforce artifact semantics before rendering`
Push : destination retenue — `origin/feature/gui-improvement`
```

---

## 16. Étape 5 — harmonisation de la métrique « plus rapide »

**Étape visée :** définir « plus rapide » comme le meilleur temps de mouvement, tout en exposant séparément le meilleur temps total incluant la stabilisation.

**Fichiers concernés :** `services/result_service.py`, `app/pages/home.py`, `app/pages/results.py`, `services/export_service.py`, `services/presentation_service.py`, `tests/test_result_service.py`.

**Risque scientifique :** aucun changement des calculs NSGA-II, des coûts ou des gains exportés; correction d’une incohérence de classement qui utilisait auparavant `total_time_s` alors que les libellés et les gains utilisaient `time_motion_s`.

**Tests exécutés :** 49 tests ciblés; suite non lente complète; Ruff; compilation; smoke test FAST; santé HTTP Streamlit.

**Critère d’acceptation :** les gains et le classement « plus rapide » utilisent le temps de mouvement; le classement total est affiché séparément; un test couvre le cas où les deux classements divergent.

**Après modification :**

```text
Fichiers modifiés : services/result_service.py, app/pages/home.py, app/pages/results.py, services/export_service.py, services/presentation_service.py, tests/test_result_service.py, docs/SUIVI_AMELIORATION_GUI.md
Tests exécutés : 329 tests réussis, 1 test lent écarté; Ruff et compilation réussis; pipeline FAST COMPLETED avec 6 PASS, 1 WARN attendu et 0 FAIL; Streamlit health retourne ok.
Résultats : `best_time_kind` et `best_time_motion_kind` sont fondés sur `total_time_motion_s`; `best_time_total_kind` est exposé séparément dans la GUI, les exports et le script oral.
Limites connues : la définition est harmonisée côté code et présentation; la qualification scientifique nominale 9×9 reste à réaliser.
Commit : intitulé retenu — `fix(gui): distinguish motion and total time rankings`
Push : destination retenue — `origin/feature/gui-improvement`
```

---

## 17. Étape 6 — statistiques complètes des gains

**Étape visée :** compléter les KPI de gains avec les minima et maxima, les stratégies correspondantes, le nombre de stratégies optimisées, la baseline numérique et les formules explicites.

**Fichiers concernés :** `services/result_service.py`, `app/pages/results.py`, `services/export_service.py`, `services/presentation_service.py`, `tests/test_result_service.py`, `tests/test_export_service.py`.

**Risque scientifique :** aucun changement des calculs du comparateur ni des valeurs de `comparison.csv` et `comparison_diagnostic.json`; l’évolution concerne l’agrégation et la présentation de valeurs déjà calculées.

**Tests exécutés :** tests ciblés de résultats, exports et présentation; suite non lente complète; Ruff; compilation; smoke test FAST; santé HTTP Streamlit.

**Critère d’acceptation :** chaque KPI indique son périmètre, sa baseline, sa formule, son minimum, son maximum et les stratégies correspondantes; le snapshot de référence reste numériquement inchangé.

**Après modification :**

```text
Fichiers modifiés : services/result_service.py, app/pages/results.py, services/export_service.py, services/presentation_service.py, tests/test_result_service.py, tests/test_export_service.py, docs/SUIVI_AMELIORATION_GUI.md
Tests exécutés : 329 tests réussis, 1 test lent écarté; Ruff et compilation réussis; pipeline FAST COMPLETED avec 6 PASS, 1 WARN attendu et 0 FAIL; Streamlit health retourne ok.
Résultats : gains temps min/max = 6,1536 % / 21,4113 %; gains énergie min/max = 12,8319 % / 14,0279 %; 3 stratégies optimisées comparées à `baseline_zigzag`.
Limites connues : les statistiques concernent le run chargé; la qualification scientifique nominale 9×9 reste à réaliser.
Commit : intitulé retenu — `feat(results): complete gain statistics traceability`
Push : destination retenue — `origin/feature/gui-improvement`
```

---

## 18. Étape 7 — Historique autonome et diagnostic des runs invalides

**Étape visée :** permettre à l’Historique de fonctionner sans source active, charger explicitement un snapshot ou un run valide, et isoler les runs incomplets ou échoués avec leur diagnostic.

**Fichiers concernés :** `app/pages/history.py`, `services/result_service.py`, `tests/test_gui_skeleton.py`, `tests/test_result_service.py`.

**Risque scientifique :** aucun artefact invalide n’est ajouté aux comparaisons; les dossiers non `COMPLETED`, les manifests mal formés et les artefacts manquants restent exclus du chargement scientifique.

**Tests exécutés :** tests ciblés Historique/ResultService; suite non lente complète; Ruff; compilation; smoke test FAST; santé HTTP Streamlit.

**Critère d’acceptation :** la page Historique reste utilisable sans source active, un run valide peut être chargé depuis cette page, et un run invalide expose statut, étape en cause, erreur et inventaire d’artefacts sans être présenté comme résultat valide.

**Après modification :**

```text
Fichiers modifiés : app/pages/history.py, services/result_service.py, tests/test_gui_skeleton.py, tests/test_result_service.py, docs/SUIVI_AMELIORATION_GUI.md
Tests exécutés : 331 tests réussis, 1 test lent écarté; Ruff et compilation réussis; pipeline FAST COMPLETED avec 6 PASS, 1 WARN attendu et 0 FAIL; Streamlit health retourne ok.
Résultats : l’Historique découvre et charge les sources valides sans dépendre de l’état actif; les dossiers invalides sont exclus et diagnostiqués par statut manifeste, étape fautive, erreur et artefacts manquants.
Limites connues : le diagnostic concerne les dossiers présents sous `data/runs`; la qualification scientifique nominale 9×9 reste à réaliser.
Commit : intitulé retenu — `feat(history): diagnose invalid runs and load sources`
Push : destination retenue — `origin/feature/gui-improvement`
```

---

## 19. Étape 8 — contrats CSV et cohérences inter-fichiers

**Étape visée :** compléter les contrats de lecture CSV, qualifier les cas vides et renforcer les invariants entre rangs, références de points, profils, résumés et baseline.

**Fichiers concernés :** `services/result_service.py`, `tests/test_result_service.py`.

**Risque scientifique :** aucun artefact valide n’est modifié; les CSV optionnels absents ou vides restent autorisés selon leur contrat, mais un fichier optionnel présent et malformé est désormais rejeté plutôt que silencieusement ignoré.

**Tests exécutés :** tests ciblés des contrats CSV et cohérences; suite non lente complète; Ruff; compilation; smoke test FAST; santé HTTP Streamlit.

**Critère d’acceptation :** chaînes numériques converties, entiers fractionnaires rejetés, CSV optionnels explicitement qualifiés, rangs contigus, références de points valides, `n_waypoints` et cumuls cohérents avec les trajectoires et la baseline.

**Après modification :**

```text
Fichiers modifiés : services/result_service.py, tests/test_result_service.py, docs/SUIVI_AMELIORATION_GUI.md
Tests exécutés : 335 tests réussis, 1 test lent écarté; Ruff et compilation réussis; pipeline FAST COMPLETED avec 6 PASS, 1 WARN attendu et 0 FAIL; Streamlit health retourne ok.
Résultats : schémas stricts pour baseline/rejets optionnels, politique absent/vide explicite, contrôles de rangs, n_waypoints, cumuls finaux et références de points ajoutés.
Limites connues : les règles inter-fichiers ne remplacent pas la qualification scientifique nominale 9×9; les vues réellement vides restent à qualifier au cas par cas si de nouveaux sous-ensembles sont ajoutés.
Commit : intitulé retenu — `test(results): complete CSV and cross-file contracts`
Push : destination retenue — `origin/feature/gui-improvement`
```

---

## 20. Prochaine action

La validation fonctionnelle GUI et l’animation temporelle sont présentes dans cette branche. Les prochaines étapes doivent être réalisées séparément :

1. exécuter et documenter un run de production sur la grille nominale ;
2. vérifier les hypothèses physiques B1/B2/B5 avec les encadrants ;
3. décider explicitement si l’état de la branche justifie un tag V1 ;
4. ne pas confondre le smoke test rapide avec une qualification scientifique générale.

La validation de reprise du 2026-10-28 est une validation de code et de mode rapide ; elle ne remplace pas une qualification scientifique sur la grille de production ni la mesure des hypothèses physiques B1/B2/B5.

---

## 21. Backlog de reprise après la refonte statistique

Cette section est destinée à la prochaine personne qui reprend la branche. Les
tâches sont ordonnées par risque et dépendances. Une tâche doit rester isolée
dans son propre commit fonctionnel ; ne pas présenter une campagne scientifique
comme réussie sur la seule base des tests logiciels.

### P0 — À réaliser avant une présentation publique ou un tag V1

#### 21.1 Revue visuelle Streamlit et qualification responsive

**Objectif :** vérifier que la nouvelle interface statistique reste lisible sur
une fenêtre large, une fenêtre étroite et dans un parcours de démonstration.

**Fichiers probables :** `app/pages/home.py`, `app/pages/results.py`,
`app/theme.py`, tests GUI.

**Actions :**

1. lancer `streamlit run app/streamlit_app.py` ;
2. vérifier Accueil, Résultats, Trajectoire XY, Baseline, Pareto et Artefacts ;
3. vérifier l’absence de défilement horizontal, de métriques tronquées et de
   graphiques illisibles ;
4. vérifier le parcours avec un run `3×3` et une source historique ;
5. ajouter un test ou une capture de référence uniquement pour chaque défaut
   observé.

**Critère d’acceptation :** aucun contenu essentiel n’est tronqué à 1280 px et
à 900 px de largeur ; les tableaux détaillés restent accessibles uniquement par
téléchargement ; les graphiques ont un titre, des axes et une légende lisibles.

**État au 2026-10-28 : terminé et vérifié** sur le snapshot historique
`20261027_fast_reference` (grille 3×3, sans nouveau calcul scientifique).
La revue Chromium a couvert Accueil, Résultats, Pareto, Trajectoire XY, Baseline,
Artefacts et Historique à 1280 px et 900 px. Le document ne présente aucun
défilement horizontal global (`scrollWidth` égal à la largeur du viewport) et
aucune exception Streamlit n’a été observée. La barre des onglets conserve son
défilement interne à largeur réduite ; les onglets restent accessibles.

**Corrections issues d’observations réelles :** les KPI de l’Accueil et de
Résultats sont maintenant répartis sur deux colonnes ; l’Accueil affiche un état
de source court, le nom complet restant visible dans la légende ; le guide de
démonstration distribue ses cinq étapes sur plusieurs lignes. La revue a aussi
révélé que l’Historique ne reconnaissait pas le snapshot actif à cause d’une
comparaison chemin relatif/absolu : les chemins sont désormais résolus avant
comparaison et un test de régression vérifie que la référence apparaît dans la
liste des exécutions.

**Validation :** `pytest -q -m "not slow"` — 349 réussis, 1 test lent exclu ;
Ruff — réussi ; `compileall` — réussi ; `git diff --check` — réussi. Les vues
utilisent les artefacts versionnés FAST : ce contrôle visuel ne constitue pas
une qualification scientifique nominale 9×9, ni une revue d’accessibilité.

**Captures de preuve :** `docs/evidence/gui-responsive-20261028/` (Accueil et
Pareto aux deux largeurs ; Trajectoire XY, Baseline, Artefacts et Historique à
900 px). Les artefacts restent des preuves de rendu de l’application en mode
démonstration, pas des résultats scientifiques nouveaux.

#### 21.2 Qualification scientifique nominale 9×9

**Objectif :** produire les preuves multi-seeds sans transformer la collecte en
verdict scientifique automatique.

**Commande locale :**

```bash
python scripts/qualify_nominal.py \
  --output-dir data/qualification/nominal-9x9 \
  --seeds 42 43 44
```

**Alternative GitHub :** workflow manuel `Nominal 9x9 qualification` avec les
paramètres par défaut `seeds=42 43 44`, `pop_size=500`, `n_gen=1500`.

**Critère d’acceptation :** chaque seed possède un manifeste `COMPLETED`, aucun
contrôle `FAIL`, une configuration identique hors seed et un résumé conservé.
La stabilité du front, des trajectoires et des gains doit ensuite être revue
par un responsable scientifique ; B1, B2 et B5 restent `NOT_VALIDATED` tant que
cette revue n’est pas documentée.

**Campagne exécutée le 2026-10-28 (accord préalable obtenu) :** seeds 42, 43
et 44, paramètres nominaux inchangés. Les trois runs sont `COMPLETED`, chacun
avec 81/81 points retenus et une configuration identique hors seed. Tous ont
`validation_status=WARN` pour les seeds 42 et 43, et `PASS` pour la seed 44,
avec respectivement 2, 2 et 4 compromis distincts; le nouveau seuil déclenche
WARN uniquement sous 3 compromis. Les trois trajectoires passent les
contrôles internes par seed ; les gains minimaux de temps et d’énergie sont
positifs pour les trois seeds, mais varient. La stabilité du front et la
signification physique de ces résultats restent à examiner ; aucune hypothèse
n’est déclarée validée.

Le manifeste conserve `scientific_status=NOT_VALIDATED`. Les artefacts complets
des trois seeds sont archivés sous `data/qualification/nominal-9x9/`, et les
résultats, limites et décisions encore ouvertes sont détaillés dans
`docs/RAPPORT_QUALIFICATION_NOMINALE_9X9_2026-10-28.md`. Le critère d’exécution
et de collecte des preuves est atteint ; la revue scientifique requise reste
ouverte.

#### 21.3 Décision finale sur la baseline

**Objectif :** éliminer toute ambiguïté entre `baseline_zigzag`, baseline
officielle, et `baseline_nn`, nom historique conservé pour compatibilité.

**Fichiers probables :** `visualization/labels.py`,
`services/result_service.py`, `services/export_service.py`, documentation et
tests de compatibilité.

**Critère d’acceptation :** le rapport jury, la comparaison baseline de la vue
Trajectoire, l’historique et
les exports utilisent le même libellé officiel ; les anciens runs
`baseline_nn` restent chargeables et sont explicitement identifiés comme
fallback historique.

**État au 2026-10-28 : terminé.** `baseline_zigzag` s’affiche sous le libellé
« Baseline officielle — zigzag » ; l’ancien kind `baseline_nn` s’affiche sous
« Baseline de repli historique — plus proche voisin ». Les libellés partagés
s’appliquent au rapport jury, aux vues Résultats/3D, aux figures et à la table
d’Historique. L’Historique affiche le kind par run, reprend ce label dans les
infobulles et avertit quand une comparaison A/B utilise des références
différentes. Les IDs machine dans les CSV demeurent inchangés.

Une fixture legacy valide a été ajoutée ; elle vérifie le chargement complet,
le rapport d’export, le ZIP et l’identification dans l’Historique. La priorité
du kind officiel est déterministe si plusieurs kinds sont fournis au formateur
de labels. Validation finale : suite non lente **354 passed, 1 deselected** ;
Ruff, compilation Python et `git diff --check` passent. Détails de test : `tests/conftest.py`,
`tests/test_result_service.py`, `tests/test_export_service.py` et
`tests/test_gui_skeleton.py`.

### P1 — Qualité d’exploitation et maintenance

#### 21.4 Accessibilité et mode présentation

Vérifier le contraste, la dépendance à la couleur, les textes alternatifs ou
descriptions des figures, la navigation clavier et l’impression PDF. Les
statuts `PASS/WARN/FAIL` doivent rester compréhensibles sans couleur seule.

**Critère d’acceptation :** un jury peut distinguer les statuts, comprendre les
axes et lire les indicateurs sans ouvrir les CSV bruts.

#### 21.5 Mesure du coût des exports et des campagnes

Mesurer le temps et la mémoire de `ExportService.zip_run()` sur un run FAST et
sur un run nominal. Mesurer séparément la durée des tests `slow` et de la
qualification nominale ; ne pas fabriquer d’ETA à partir d’une seule mesure.

**Critère d’acceptation :** les mesures sont enregistrées dans le suivi, le ZIP
reste construit uniquement à la demande et les estimations GUI affichent une
incertitude explicite.

**État au 2026-10-29 :** première mesure reproductible réalisée avec
`scripts/measure_costs.py`; les résultats détaillés sont archivés dans
[`docs/evidence/cost-measurement-20261029.json`](evidence/cost-measurement-20261029.json).
Dans l’environnement sandbox utilisé :

- pipeline FAST : **18,96 s** murales, **19,66 s CPU enfant**, **2,07 Mo** d’artefacts ;
- export ZIP FAST : **0,102 s**, **1,56 Mo** compressés, pic Python alloué d’environ
  **2,0 Mo** ;
- qualification nominale 9×9, seeds 42/43/44, `pop_size=500`, `n_gen=1500` :
  **595,32 s** murales, soit environ **9 min 55 s**, **595,82 s CPU enfant** et
  **11,26 Mo** d’artefacts temporaires ;
- exports ZIP des trois runs nominaux : **0,153–0,163 s** et **2,23–2,25 Mo**
  par seed ;
- les trois runs nominaux ont terminé `COMPLETED` mais avec `WARN` et seulement
  **2, 1 et 1** solutions Pareto. Cette mesure d’exploitation ne modifie pas le
  statut scientifique `NOT_VALIDATED` et ne constitue pas une ETA générale.

La mesure des tests `slow` et la vérification des artefacts du workflow GitHub
restent couvertes par 21.6. Les mesures mémoire disponibles sont explicitement
qualifiées de pics RSS/allocations observés, et non de budget garanti.

#### 21.6 Exécuter réellement les workflows manuels

Lancer une fois `Slow tests` avec les tests marqués `slow` et vérifier l’artefact
produit. Lancer la qualification nominale uniquement avec l’accord du
responsable scientifique et conserver son `run_id` GitHub.

**Critère d’acceptation :** les workflows sont non seulement présents dans le
dépôt mais leur durée, leur conclusion et leurs artefacts sont consignés ici.

**État au 2026-10-29 :**

- le workflow CI automatique déclenché par le commit `e816412` a terminé avec
  succès : [run GitHub 40770457735](https://github.com/safidinjarahenrialvin/tandem_sp2/actions/runs/40770457735) ;
- l’équivalent local de `Slow tests` a été exécuté avec `pytest -q -m slow` :
  **1 réussi, 358 tests écartés, environ 9 s murales**, code retour `0` ;
- le dispatch manuel des workflows `Slow tests` et `Nominal 9x9 qualification`
  n’est pas possible depuis cette branche seule : GitHub renvoie `404` car ces
  fichiers existent sur `feature/gui-improvement` mais pas sur la branche par
  défaut `main`. `main` ne contient actuellement que `.github/workflows/ci.yml` ;
- aucune exécution manuelle GitHub ni aucun artefact GitHub de qualification ne
  doit donc être présenté comme obtenu. La campagne nominale locale mesurée en
  21.5 reste la preuve disponible, avec `NOT_VALIDATED`.

La résolution propre est d’intégrer les workflows dans `main` via la procédure
de revue du dépôt, puis de relancer les deux dispatchs depuis l’interface ou
l’API GitHub. Il ne serait pas rigoureux de pousser directement une modification
sur `main` uniquement pour contourner cette contrainte.

#### 21.7 Renforcer la surveillance d’un worker GUI

Ajouter un test de course pour annulation immédiate, échec avant création du
manifeste, double lancement et rafraîchissement Streamlit après état terminal.
Vérifier aussi le nettoyage des références de session après un run terminé.

**État au 2026-10-29 :** implémentation et vérification navigateur terminées.

- `RunHandle.wait(timeout)` fournit désormais une synchronisation publique et
  thread-safe ; les tests ne manipulent plus directement `_thread` ;
- l’annulation demandée avant l’entrée effective dans le pipeline est couverte ;
- le double lancement reste refusé explicitement ;
- un échec avant création du manifeste est exposé comme `FAILED` sans créer de
  répertoire de run fantôme ;
- les erreurs et annulations terminales sont recopiées dans `st.session_state` ;
- le retour à l’état neutre nettoie le handle, le statut, la progression, l’étape
  et l’erreur du run ;
- tests ciblés GUI : **27 réussis** ; Ruff et compilation réussis.

Le rafraîchissement Streamlit après un état terminal est couvert par le contrat
de snapshot persistant et par les tests AppTest existants. Une interaction
navigateur réelle a ensuite été exécutée avec `n_gen=5000` : le clic sur
**Annuler l’exécution** pendant `7_optimizer` a produit un run `CANCELLED`,
avec `cancelled_step=7_optimizer`, les étapes 4 à 6 conservées comme terminées
et les artefacts partiels exclus des résultats chargeables. La preuve détaillée
est conservée dans
`docs/evidence/gui-worker-cancellation-20261029.md`.

Un premier clic intervenu pendant `10_validator` n’a pas interrompu l’étape
déjà engagée et le run a terminé `COMPLETED`. Ce comportement est conforme à
l’annulation coopérative : aucune interruption forcée n’est effectuée au milieu
d’une étape scientifique ou d’une écriture d’artefact.

**Critère d’acceptation :** aucun worker orphelin, aucune seconde exécution
simultanée, aucune exception brute affichée à l’utilisateur et clic réel
d’annulation vérifié. Critère satisfait le 2026-10-29.

### P2 — Améliorations utiles mais non bloquantes

#### 21.8 Résumé statistique exportable

Ajouter un `summary.json` ou `summary.csv` compact contenant uniquement les
indicateurs présentés dans l’interface : couverture, validation, Pareto,
baseline, gains et trajectoire sélectionnée. Le fichier détaillé reste
disponible séparément.

**État au 2026-10-29 :** implémenté avec `ExportService.summary_payload()` et
`ExportService.summary_json()`. L’onglet **Artefacts** propose maintenant le
téléchargement explicite de `summary.json`, généré à la demande sans modifier le
répertoire scientifique du run.

Le schéma versionné contient :

- identité du run, répertoire source et empreinte de configuration ;
- couverture : points générés, points retenus, taux de rétention et étendues ;
- validation : statut global et nombres `PASS/WARN/FAIL` ;
- Pareto : solutions brutes et compromis distincts ;
- baseline : type, libellé et comparaison au meilleur résultat ;
- gains : métriques, minima et maxima temps/énergie ;
- trajectoire sélectionnée et résumé des meilleurs classements.

Le résumé n’embarque volontairement ni matrice de coûts, ni tableau de
comparaison complet, ni figures, ni hypothèses détaillées. `schema_version=1`
permettra de faire évoluer le format explicitement. Les tests vérifient le
contenu, la sélection de trajectoire, l’absence de données détaillées et la
sérialisation déterministe.

Vérification de cette étape : **27 tests ciblés réussis**, Ruff, compilation et
`git diff --check` après correction du contrat de formatage.

#### 21.9 Mode rapport jury imprimable

Créer une vue ou un Markdown/PDF court composé de quatre blocs : configuration,
couverture, Pareto, comparaison baseline. Aucun tableau brut ne doit être
reproduit dans ce mode ; les détails doivent pointer vers l’archive ZIP.

#### 21.10 Comparaison multi-seeds

Ajouter une vue dédiée à la qualification qui montre moyenne, médiane, écart
type et étendue des indicateurs par seed. Cette vue ne doit être activée que si
les manifests appartiennent à la même configuration effective.

#### 21.11 Nettoyage du backlog historique

Après validation des points ci-dessus, mettre à jour les anciennes sections de
ce document qui citent des commits ou nombres de tests antérieurs. Ne jamais
supprimer l’historique : ajouter une note de clôture avec commit et preuve.

### 21.12 Procédure de clôture obligatoire

Pour chaque tâche reprise :

1. lire ce document et les fichiers concernés ;
2. définir un seul objectif testable ;
3. modifier le code et les tests associés ;
4. exécuter `pytest -q -m "not slow"`, Ruff, compilation et le smoke test si
   le périmètre le justifie ;
5. vérifier `git diff --check` ;
6. renseigner ici le résultat, les limites et le commit ;
7. pousser sur `origin/feature/gui-improvement`.

La dernière personne qui reprend doit commencer par **21.1**, puis **21.2**.
Les points **21.2** et **21.3** nécessitent une décision scientifique ou de
présentation ; ils ne doivent pas être « optimisés » silencieusement par une
modification purement logicielle.


## 21.4a — Première tranche technique accessibilité et mode présentation — implémentée

Cette étape ne clôt pas encore la revue complète d’accessibilité. Elle traite les
améliorations vérifiables directement dans le code de présentation, sans modifier
les calculs scientifiques ni les contrats d’artefacts.

### Modifications réalisées

- ajout d’un libellé textuel explicite pour les statuts `PASS`, `WARN`, `FAIL` avec
  un rôle `status`, afin que leur interprétation ne dépende pas de la couleur ;
- ajout de descriptions textuelles associées aux tableaux de l’Historique et des
  Résultats ;
- ajout de descriptions textuelles courtes pour les graphiques Pareto, profils et
  comparaisons multi-runs ;
- ajout d’un indicateur de focus visible pour les liens, boutons, onglets et
  contrôles de saisie ;
- ajout d’une prise en compte de `prefers-reduced-motion` ;
- ajout d’une feuille de style d’impression supprimant la navigation et les
  contrôles d’action, avec surfaces blanches, texte noir et blocs conservés ;
- ajout de tests unitaires et AppTest couvrant ces contrats de présentation.
- correction de `accent-primary` de `#635BFF` à `#5B52E8` après mesure WCAG :
  le ratio passe de `4.49:1` à `5.26:1` sur `bg-main` et à `5.50:1` sur
  `bg-surface` ; le texte blanc sur le bouton primaire atteint également
  `5.50:1`.

### Vérifications

- suite non lente : **358 réussis, 1 test lent écarté** ;
- Ruff : réussi ;
- compilation Python : réussie ;
- `git diff --check` : réussi ;
- smoke test FAST : `COMPLETED`, code retour `0`, `WARN` Pareto attendu ;
- vérification navigateur : démarrage Streamlit réussi, navigation principale et
  lien d’accès direct au contenu détectés.
- tranche contraste : **20 tests GUI ciblés réussis**, Ruff et compilation
  réussis ; preuve conservée dans
  `docs/evidence/accessibility-contrast-20261029.md`.

### Limites restantes

Cette étape ne constitue pas encore une validation complète avec lecteur d’écran,
ni une mesure exhaustive du contraste de tous les composants générés par
Streamlit, Plotly et les tableaux interactifs, ni une preuve PDF issue de chaque
page. La revue clavier détaillée, l’export/impression des vues de Résultats et
l’accessibilité fine des tableaux restent à effectuer avant de marquer 21.4
comme terminée.

## 22. Refonte statistique et cohérence de présentation — implémentée

**Portée :** amélioration transversale des pages Accueil, Paramètres, Résultats et Historique, sans modification des algorithmes scientifiques ni des artefacts sources.

### Modifications réalisées

- Remplacement du détail d’implémentation du thread Streamlit dans le suivi de progression par une consigne orientée utilisateur.
- Comparaison absolue temps/énergie sur deux panneaux à unités séparées; repère explicite de la baseline à 0 % dans le graphique des gains.
- Nouvel onglet **Couverture & coûts** : nombre de points et transitions distinctes, taux faisable/infaisable, distributions de distance/temps/énergie avec moyenne, écart-type, médiane, quartiles et étendue, plus cartes des quatre métriques.
- Contrat unique `RunResults.cost_statistics()` partagé entre GUI et rapport jury; les boucles `i = j` sont exclues et les distributions portent sur les transitions inter-points faisables.
- Correction du tableau Historique : couverture affichée comme pourcentage; contexte visible sur la comparabilité entre baselines/configurations.
- Onglet Hypothèses : statuts et sources consultables; un paramètre « gelé » n’est plus présenté comme une hypothèse confirmée.
- Statut `PASS/WARN/FAIL` renommé comme statut de contrôles automatiques, avec rappel qu’il ne valide pas à lui seul les hypothèses scientifiquement ou expérimentalement.
- ZIP assemblé après demande explicite et conservé pour le run actif; son coût n’a pas encore été mesuré.
- Rapports développeur et utilisateur mis à jour; tests unitaires/GUI ajoutés ou modifiés.

### Preuves de vérification

- Tests ciblés : `69 passed` sur les services résultats/export, le script jury et le GUI.
- Suite non lente : `357 passed, 1 deselected`.
- Ruff sur les dossiers concernés : `All checks passed`.
- `compileall` terminé sans erreur; smoke test FAST `COMPLETED`, `WARN` Pareto attendu, code retour 0, total observé 21,2 s pour ce run de contrôle (ce n’est pas une mesure d’exploitation).
- Vérification navigateur de l’accueil et de la synthèse du snapshot; assertions AppTest couvrant les statistiques et l’onglet coûts. Aucun test d’accessibilité ni mesure mémoire n’est revendiqué.
- `git diff --check` propre. Commit/push en cours sur `origin/feature/gui-improvement`.

Les tâches P1 demeurent séparées et ouvertes : revue d’accessibilité/impression (21.4), campagne de mesure reproductible du coût (21.5), preuves GitHub des workflows manuels (21.6) et clôture scientifique par la personne responsable (21.2/21.7 selon l’hypothèse concernée).

## 23. Démarrage neutre et première réduction de redondance — validée

**Date :** 2026-10-29
\
**Portée :** supprimer le snapshot de démonstration versionné et réduire la
duplication de l’Accueil, sans modifier le moteur scientifique.

### Modifications réalisées

- Suppression de `data/snapshots/20261027_fast_reference/` du dépôt.
- Suppression de la référence spéciale `ResultService.load_reference()` et de
  la logique qui présentait ce snapshot comme une source officielle.
- Accueil et Historique démarrent désormais sans source implicite et proposent
  uniquement les runs explicitement présents dans `data/runs/`.
- Accueil recentré sur les KPI principaux, un seul graphique Pareto et une
  conclusion courte; le graphique de comparaison et les indicateurs répétés ont
  été retirés de cette page.
- Guide utilisateur et guide de présentation adaptés à un run produit par
  l’utilisateur.
- Fixture historique déplacé vers `tests/fixtures/reference_run/`; il ne sert
  plus de source applicative et ne réactive aucun résultat par défaut.

### État de validation

- `362 passed, 1 deselected` sur la suite non lente.
- Ruff validé sur `app`, `services`, `src`, `scripts`, `tests` et `visualization`.
- Compilation Python validée et `git diff --check` propre.
- Smoke test `--fast` terminé avec `COMPLETED`, code retour `0` et `WARN` Pareto
  attendu.

### Suite prévue

- Réduire le nombre d’onglets de Résultats en regroupant les preuves par question
  scientifique : décision, trajectoire, Pareto et validation (réalisé en section 24).
- Ajouter ensuite une action explicite de création de snapshot à partir d’un run
  terminé, sans en fournir un par défaut dans Git.

## 24. Résultats en quatre vues — implémentée et vérifiée

**Date :** 2026-10-29
**Portée :** présentation et navigation Streamlit uniquement. Les calculs, les
artefacts scientifiques, leurs contrats et le service de résultats ne changent pas.

### Modifications réalisées

- remplacement des dix onglets de premier niveau par **Décision**, **Trajectoire**,
  **Pareto** et **Validation** ;
- regroupement de la scène 3D, de la trajectoire XY, des profils cinématiques et de
  la comparaison baseline dans **Trajectoire** ;
- ajout d’un repère de choix temps/énergie explicitement présenté comme aide de
  présentation, sans effet sur l’optimiseur ni prétention à un optimum universel ;
- déplacement des contrôles, hypothèses, couverture WFW et alertes FOV sous
  **Validation** ; les limites rappellent que contrôle automatique, qualification
  numérique et validation expérimentale ne sont pas interchangeables ;
- déplacement des téléchargements, du ZIP à la demande et des statistiques de
  coûts dans l’expander secondaire **Preuves techniques** ;
- retrait du bandeau KPI global redondant et ajout d’une assertion AppTest qui
  verrouille l’ordre et le nombre des vues.

### Vérifications et limites

- état initial : `362 passed, 1 deselected` avant modification ;
- état après modification : `362 passed, 1 deselected` sur `pytest -q -m "not slow"` ;
- 7 tests GUI ciblés passent ; Ruff, compilation Python et `git diff --check` passent ;
- les tests vérifient l’accès à l’expander technique et les contrôles/exports
  existants. La revue complète clavier, impression et lecteurs d’écran n’est pas
  revendiquée ; la qualification à 1280/1024/900/768 px reste au backlog #9/#11.

### Suite

La création explicite de snapshot n’est pas comprise dans cette modification.
Avant de l’implémenter, examiner les contrats de manifeste/statut, les artefacts
obligatoires, la validation de configuration, les noms de destination, les
collisions et la publication atomique. Le snapshot par défaut reste absent.


## 25. Évaluation des dix propositions de la pièce jointe — 2026-10-29

Les propositions ont une valeur réelle, mais elles ne représentent pas dix changements
à livrer en bloc. La règle du projet reste une étape fonctionnelle à la fois. Les
priorités 1 et 4 ont été intégrées à la refonte de la section 24, et la priorité 2 est
réalisée à la section 26; les autres sont classées ci-dessous selon l’état du dépôt.

| Priorité proposée | Évaluation technique et décision |
|---:|---|
| 1 — Réduire les onglets Résultats | **Validée et réalisée** (§24). Les dix vues ont été regroupées en quatre vues, sans supprimer les détails. Le critère mécanique est couvert par AppTest; la compréhension en moins de 30 secondes n’a pas encore fait l’objet d’un test utilisateur formel. |
| 2 — Création explicite d’un snapshot | **Validée et réalisée** (§26). `SnapshotService` valide le manifeste v1, les huit étapes, l’inventaire, le fingerprint et la chargeabilité; copie en staging privé, compare les empreintes avant/après et publie par `renameat2(RENAME_NOREPLACE)`. Accueil propose ensuite le chargement explicite; les copies runtime sont ignorées par Git. |
| 3 — Simplifier Accueil / accès au rapport jury | **Amélioration valable, à différer.** L’accueil est déjà neutre au démarrage et ne charge pas de source implicitement; le rapport jury est déjà généré depuis les résultats. Un lien direct depuis Accueil est une commodité, pas une lacune scientifique; éviter une deuxième implémentation du rapport et valider le parcours avant d’ajouter un bouton. |
| 4 — Clarifier la stratégie recommandée | **Validée et réalisée** (§24). Le repère temps → `time_opt`, énergie → `energy_opt`, équilibre → `compromise` est explicitement présenté comme aide de lecture; le choix de stratégie reste contrôlé par l’utilisateur et n’altère pas l’optimiseur. |
| 5 — Accessibilité et impression | **Validée, en cours.** La correction de contraste WCAG AA est mesurée et testée (`docs/evidence/accessibility-contrast-20261029.md`), mais elle ne couvre pas tout Streamlit/Plotly. Il reste clavier, ordre du focus, description des graphes, tableaux, lecture sans couleur, onglets et impression PDF. |
| 6 — Qualification responsive | **Audit 1024/768 terminé** pour Accueil, Paramètres, Résultats (Scène 3D/Pareto) et Historique; aucun débordement de page ni erreur JS. Le sidebar se replie à 768 px, les métriques et options coupées ont été corrigées. Les sept onglets ont un scroll interne à 1024 px et tiennent à 768 px; preuves dans `docs/evidence/gui-responsive-20261029/`. La vérification ne revendique ni accessibilité complète ni prise en charge de tous les formats téléphone. |
| 7 — Suivi et estimation des exécutions | **Validée, à planifier après la comparaison multi-seeds.** L’estimation actuelle est une heuristique annoncée comme indicative (`app/pages/parameters.py`). `PipelineResult` expose des timings et une première mesure d’exploitation est archivée, mais il faut collecter des observations par run/bloc, environnement et ressources avant de présenter une plage typique; aucune fausse précision ne doit être introduite. |
| 8 — Comparaison multi-seeds | **Validée, forte valeur après l’audit GUI.** La campagne versionnée contient trois seeds, statuts `WARN`, comptes de points/Pareto et gains dans `qualification_summary.csv`; les runs complets permettent d’extraire d’autres indicateurs. Comparer uniquement des configurations effectives identiques hors seed, afficher le petit effectif et les avertissements, et garder `scientific_status: NOT_VALIDATED`. Une comparaison numérique n’est pas une validation expérimentale. |
| 9 — Statut scientifique à trois niveaux | **Validée comme clarification de présentation, sous réserve de gouvernance scientifique.** Le manifeste nominal reste `NOT_VALIDATED`; l’interface peut expliquer démonstration numérique, qualification numérique et validation expérimentale, mais ne doit pas promouvoir automatiquement un run ou une campagne d’un niveau à l’autre sans critères d’acceptation humains documentés. |
| 10 — Nettoyage des données versionnées | **Valide mais non urgent.** La campagne et la fixture occupent actuellement environ 13,1 MiB sur 133 fichiers (`du -sh`). Créer d’abord des fixtures minimales et mesurer le coût d’historique; ne pas supprimer les preuves nominales ou les configurations nécessaires à la reproductibilité sans politique d’archivage explicite. |

### Ordre de reprise recommandé

1. Poursuivre les contrôles d’accessibilité clavier, focus, tableaux, graphiques et
   impression; l’audit responsive à 1024/768 px est documenté séparément.
2. Réexaminer l’accueil et le point d’accès au rapport jury après ces parcours.
3. Ajouter la synthèse multi-seeds à partir des artefacts de campagne validés, avec
   garde-fous d’effectif, d’égalité de configuration et de statut scientifique.
4. Élargir le suivi runtime/mémoire sur des environnements comparables; revoir ensuite
   les libellés d’estimation.
5. Faire valider par une personne compétente la taxonomie de statut scientifique,
   puis l’afficher sans automatiser l’acceptation des hypothèses.
6. Réduire les fixtures et artefacts versionnés uniquement si le gain mesuré justifie
   la complexité et ne rompt pas la reproductibilité.


## 26. Création explicite de snapshots — 2026-10-29

**Portée :** rendre possible l’archivage runtime d’un run complet sans le charger
implicitement, sans modifier la source ni promouvoir son statut scientifique.

**Décision et implémentation :**

- Ajout de `services/snapshot_service.py`, indépendant de Streamlit. La source doit
  être un sous-répertoire direct de `data/runs/`; seuls les noms ASCII de 1 à 64
  caractères sans séparateur sont acceptés.
- Refus si `run_manifest.json` est absent, illisible, de schéma différent de 1,
  non `COMPLETED`, incomplet en étapes, si l’inventaire déclaré diffère du contenu,
  si le fingerprint du manifeste diffère de `config.json` ou `.config_hash`, ou si
  `ResultService.load` rejette les artefacts tabulaires/JSON requis ou leurs cohérences.
- Refus des liens symboliques et fichiers spéciaux. Copie dans un staging privé sous
  `data/snapshots/`, empreintes SHA-256 avant/après pour détecter les changements de
  source, revalidation du staging puis publication atomique Linux avec
  `renameat2(RENAME_NOREPLACE)`. Une collision préexistante ou arrivée pendant la
  copie n’écrase jamais la cible; le staging est nettoyé en cas d’échec.
- Dans **Résultats > Validation > Preuves techniques**, le bouton **Créer le snapshot**
  exige une demande explicite; il ne bascule pas la source active. L’Accueil liste
  séparément `Run — …` et `Snapshot — …` et charge seulement après clic. Les copies
  runtime sont ignorées par Git; seuls `data/snapshots/.gitkeep` et
  `data/snapshots/README.md` sont suivis.
- Le parcours est documenté dans le guide utilisateur, le guide développeur,
  `README.md` et `data/snapshots/README.md`. Aucun algorithme, CSV scientifique ou
  statut `PASS/WARN/FAIL` n’est modifié.

**Vérifications :** les tests unitaires couvrent le succès nominal, les statuts
`FAILED`/`CANCELLED`/`RUNNING`, le manifeste manquant/malformé, l’inventaire et les
empreintes incohérents, `.config_hash` absent, noms invalides, liens symboliques,
fichiers spéciaux, chemins malformés, changement du run pendant la copie, collisions
sur fichier/dossier/lien, création concurrente vers un même nom, course à l’apparition
de la cible et nettoyage après erreur de copie. AppTest vérifie que l’action est
déclenchée seulement par clic et que le snapshot se charge depuis l’Accueil.
`pytest -q -m 'not slow'` : **394 tests réussis, 1 test lent écarté**; les trois suites
ciblées totalisent 90 réussites. Ruff, compilation Python et `git diff --check` passent.
Un smoke test `--fast` réel a créé puis rechargé le snapshot d’un run `COMPLETED`
(`WARN`, 32 artefacts); la découverte est confirmée après normalisation des chemins
absolu/relatif retournés par les deux APIs. Les répertoires temporaires ont été supprimés.

**Limite explicite :** `renameat2(RENAME_NOREPLACE)` rend la publication atomique et
sans remplacement sur Linux. Un système sans cette primitive échoue fermé; aucune
publication non atomique de repli n’est utilisée. La copie est destinée à une
sauvegarde locale runtime, pas à une validation scientifique ni à un archivage Git.


## 27. Présentation Résultats — synthèse en tête et onglets spécialisés — validée

**Date :** 2026-10-29

**Portée :** présentation Streamlit uniquement. Cette tranche conserve la page
`Résultats`, les services, les artefacts scientifiques et la page `Validation`.
Elle retire l’onglet `Décision` et place sa synthèse utile en haut de page.

### Modifications réalisées

- suppression de l’onglet `Décision` ;
- affichage en tête du statut automatique, des points retenus, des gains minimaux
  et du choix de stratégie ;
- suppression du résumé des trajectoires et des explications répétées sur le
  choix entre temps, énergie et temps total ;
- séparation en onglets `Scène 3D`, `Trajectoires`, `Profils cinématiques`,
  `Couverture WFW`, `Pareto`, `Analyse & comparaison` et `Validation` ;
- conservation des preuves techniques, des exports, des coûts, des hypothèses et
  des contrôles de validation dans l’onglet `Validation` ;
- mise à jour du README et des guides utilisateur/développeur ;
- ajout d’assertions GUI verrouillant l’ordre des onglets et l’absence de l’ancien
  onglet `Décision`.

### Vérifications réalisées

- suite non lente : **394 tests réussis, 1 test lent écarté** ;
- tests GUI ciblés : **23 réussis** ;
- Ruff : réussi ;
- compilation Python : réussie ;
- `git diff --check` : réussi ;
- smoke test `--fast` : `COMPLETED`, code retour `0`, `WARN` Pareto attendu ;
- santé Streamlit : endpoint `/_stcore/health` répondu `ok` ;
- aucun module scientifique ni artefact de run n’a été modifié.


## 28. Allègement de l’Accueil, de Résultats et de Validation — validée

**Date :** 2026-10-29

Cette tranche conserve la structure de navigation et les services existants, mais
réduit le texte et les répétitions visibles. L’Accueil utilise désormais le titre
principal du projet, ne présente plus le statut automatique dans ses indicateurs et
propose l’action `Rafraîchir la source`. La page Résultats ne répète plus la
synthèse du run : la stratégie est choisie en tête, puis ses métriques sont
présentées dans `Analyse & comparaison`. La trajectoire baseline n’est plus
réaffichée dans cet onglet puisqu’elle reste disponible dans `Trajectoires`.

L’onglet `Validation` est réduit aux compteurs `PASS`, `WARN` et `FAIL`, tandis que
les hypothèses, les alertes FOV et les messages explicatifs secondaires sont retirés
de la présentation courante. Les exports, snapshots et statistiques détaillées
restent accessibles dans `Preuves techniques`.

La suite non lente donne **394 tests réussis et 1 test lent écarté**. Les tests GUI
ciblés donnent **23 réussites**. Ruff, la compilation Python et `git diff --check`
sont propres. Le smoke test FAST termine avec `COMPLETED`, code retour `0` et le
`WARN` Pareto attendu. Le contrôle de santé Streamlit répond `ok`. Aucun calcul
scientifique ni artefact de run n’a été modifié.


## 29. Suppression des métriques dupliquées dans Analyse & comparaison — validée

Le bloc global affichant `Amélioration vs baseline`, `Gain temps minimal` et `Gain
énergie minimal` a été supprimé de l’onglet `Analyse & comparaison`. Les métriques
propres à la stratégie sélectionnée restent affichées une seule fois au-dessus des
graphiques : temps de mouvement, énergie, gain de temps et gain d’énergie. Un test
GUI vérifie désormais l’absence des trois libellés dupliqués. Les 23 tests GUI
ciblés, Ruff, la compilation Python et `git diff --check` passent.


## 30. Harmonisation des statuts et des graphiques — en cours validée

Cette tranche ne modifie aucun calcul scientifique ni artefact de run. Elle ajoute
`visualization/chart_style.py` comme source commune des tokens de présentation :
couleurs des stratégies et baselines, états des points WFW, surface, grille,
typographie et marges Plotly. Les figures Pareto, trajectoires, profils et
couverture WFW réutilisent désormais ces conventions au lieu de couleurs locales.

La Validation affiche aussi le statut global avec son libellé explicite et une
classe visuelle dédiée (`PASS`, `WARN`, `FAIL` ou statut inconnu). Le texte reste
obligatoire : la couleur n’est qu’un renforcement visuel et ne porte pas seule
la signification. Le message rappelle que ces contrôles décrivent l’état
technique du pipeline et ne constituent pas une validation expérimentale.

**Vérifications :** 396 tests non lents réussis, 1 test lent écarté, Ruff,
compilation Python et smoke test `--fast` réussis. Les tests ajoutés couvrent les
tokens de couleurs, le layout partagé et la présence des classes de statut.


## 31. Filtre de couverture WFW — validé

L’onglet **Couverture WFW** propose désormais trois vues explicites : **Tous les
points**, **Points retenus** et **Points rejetés**. Le sélecteur agit uniquement
sur les traces affichées par Plotly ; les CSV du run, les classifications WFW et
les statistiques restent inchangés.

La légende rappelle les conventions communes : gris pour les points générés,
vert pour les points retenus, orange ou rouge pour les rejets. Les symboles
complètent la couleur afin que l’interprétation ne dépende pas d’un seul canal
visuel. Une vue sans point rejeté reste valide et affiche un graphique vide avec
un titre explicite plutôt qu’une erreur générique.


## 32. Téléchargements ciblés — validée

La page **Résultats > Analyse & comparaison** propose maintenant un groupe
**Téléchargements ciblés** lié à la stratégie sélectionnée. Il fournit la
trajectoire CSV, le profil cinématique CSV, la ligne de comparaison avec la
baseline, le rapport de validation JSON et l’image PNG du front Pareto.

Les CSV ciblés sont construits en mémoire à partir des `DataFrame` déjà validés
par `ResultService`. Le rapport JSON est sérialisé sans réécrire l’artefact
source et l’image Pareto est lue via le contrôle de chemin existant. Une stratégie
inconnue est refusée explicitement. Le ZIP complet reste disponible pour
l’archivage de tout le run.

## 33. Première tranche d’accessibilité sémantique — validée

**Date :** 2026-10-29
**Objectif :** rendre le contenu des graphiques compréhensible sans dépendre de
la lecture visuelle ou de la couleur, et placer le contexte textuel avant les
composants interactifs pour une lecture clavier ou lecteur d’écran plus prévisible.

### Modifications réalisées

- ajout d’une description textuelle avant les graphiques de l’Accueil, de
  Résultats et d’Historique : scène 3D, trajectoires, baseline, profils,
  couverture WFW, Pareto, comparaison absolue, gains, distributions de coûts,
  cartes de coûts et comparaisons inter-runs ;
- déplacement du contexte des tableaux d’Historique avant le tableau rendu,
  au lieu de l’afficher après celui-ci ;
- conservation des unités, des axes et de la sémantique des couleurs/formes dans
  les descriptions ;
- ajout d’un test AppTest qui vérifie la présence des descriptions sur une source
  de référence ;
- aucun calcul scientifique, artefact de run ou contrat de service modifié.

### Vérifications

- tests GUI et thème : **25 réussis** ;
- suite non lente : **402 réussis, 1 test lent écarté** ;
- Ruff : réussi ;
- compilation Python : réussie ;
- `git diff --check` : réussi ;
- smoke test `--fast` : `COMPLETED`, `WARN` Pareto attendu, code retour `0` ;
- santé Streamlit : endpoint `/_stcore/health` répondu `ok`.

### Limites restantes

Cette tranche ne constitue pas encore un audit complet WCAG ou lecteur d’écran.
Il reste à vérifier expérimentalement la navigation clavier, l’ordre du focus,
les tableaux denses, les contrôles générés par Streamlit/Plotly et l’impression
PDF. Les descriptions textuelles complètent les graphiques ; elles ne remplacent
pas les données détaillées téléchargeables.

## 34. Normalisation des libellés GUI — validée

**Date :** 2026-10-29

Les pages et onglets n’affichent plus le préfixe « Description textuelle du
 graphique ». La description utile du graphique reste disponible directement,
 sans libellé redondant.

Les séparateurs typographiques utilisés dans l’interface, les titres Plotly et
les légendes ont été normalisés avec `:` : sources Run et Snapshot, profils,
statuts, baselines, titres Pareto, trajectoires, animation 3D, couverture WFW,
comparaisons et indicateurs de coûts. Les tirets mathématiques utilisés comme
opérateurs de calcul dans le code scientifique n’ont pas été modifiés.

La mise à jour inclut les tests, le guide utilisateur et les preuves GUI afin
d’éviter des libellés documentaires divergents de l’interface courante.

## 35. Simplification des descriptions et des statuts GUI — validée
**Date :** 2026-10-29

Les descriptions textuelles redondantes ont été retirées de l’Accueil et des
onglets Résultats lorsque les légendes, axes, contrôles ou titres du graphique
suffisent déjà à l’interprétation. Les descriptions conservées dans Résultats
et Historique commencent désormais par une majuscule. La légende WFW reste
portée par le graphique afin de conserver les couleurs et les formes sans
dupliquer l’explication sous la figure.

Le champ **Altitude absolue de la plateforme R0 (m)** est maintenant rendu dans
les deux modes **Automatique** et **Valeur imposée** avec le même composant et
la même zone de saisie. En mode automatique, le champ est désactivé et affiche
la valeur calculée ; en mode imposé, il reste éditable. Cette modification ne
change ni la configuration effective ni l’empreinte des runs.

Dans l’onglet **Validation**, le message textuel global de type `WARN` a été
retiré de la vue principale. Les trois compteurs `PASS`, `WARN` et `FAIL` sont
affichés sur une même ligne ; les preuves et détails techniques restent dans
l’expander dédié.

**Vérifications :** 25 tests GUI et thème réussis ; Ruff, compilation Python et
`git diff --check` réussis. Aucun algorithme scientifique ni artefact de run n’a
été modifié.

## 36. Normalisation du nom de baseline — validée
**Date :** 2026-10-29

Le libellé visible de `baseline_zigzag` est harmonisé en **Baseline : zigzag**
dans toutes les pages, onglets, figures et exports qui utilisent les labels
partagés. Les identifiants techniques `baseline_zigzag` et `baseline_nn` restent
inchangés afin de préserver la compatibilité des CSV, rapports et manifestes.

Les tests ciblés des exports, résultats et GUI passent ; la suite complète a
réussi avec **402 tests non lents**, ainsi que Ruff, la compilation, `git diff
--check` et le smoke test `--fast`. La CI GitHub `40872460959` a également
terminé avec succès. Aucun identifiant technique ni artefact scientifique n’a
été modifié.

## 37. Analyse de stabilité Pareto nominale 9×9 — implémentée, revue scientifique ouverte
**Date :** 2026-10-29

Le service `services/pareto_stability.py` et le script
`scripts/analyze_pareto_stability.py` mesurent désormais la variabilité des
fronts `solutions_pareto.csv` entre seeds. Les rapports JSON et Markdown
conservent la cardinalité, les statistiques d’objectifs, les recouvrements
d’enveloppes, les distances géométriques normalisées et la couverture par
dominance dans les deux directions.

L’analyse de la campagne existante 42/43/44 observe une cardinalité de 2, 2 et
4 solutions, aucun recouvrement des enveloppes temps/énergie et une distance de
Hausdorff normalisée moyenne de 0,8792. Le résultat reste `REVIEW_REQUIRED` et
`NOT_VALIDATED` : les seuils d’acceptation doivent être définis avec
l’encadrement scientifique, puis les trajectoires et hypothèses physiques
doivent être examinées.


## 38. Passe UX publique — couverture WFW, validation et historique — validée

**Portée :** réduire la surcharge visuelle sans retirer les artefacts scientifiques, et corriger le filtre de points rejetés de la couverture WFW.

**Réalisé :** le filtre `Afficher` accepte maintenant les causes `A` et `B` réellement produites par `PointFilter`; l’export Markdown de Validation est ramené à un bouton **Télécharger le rapport** produisant `rapport.md`; les statistiques détaillées et cartes de coûts sont retirées du parcours principal de Validation mais restent disponibles dans `summary.json`, `cost_matrix.csv`, les rapports et le ZIP; la page Historique est recentrée sur les runs, le statut, la baseline, la couverture et les KPI essentiels, avec graphiques et comparaison A/B dans des sections secondaires.

**Documentation alignée :** `docs/GUIDE_UTILISATEUR_GUI.md`, `docs/SCENARIO_SOUTENANCE.md` et `docs/UX_UI_2026-10-30.md`.

**Vérifications réalisées :** test WFW dédié, tests GUI/export ciblés (`33 passed`), suite complète (`409 passed`), Ruff sur `app services src scripts tests visualization`, compilation Python et `git diff --check`.

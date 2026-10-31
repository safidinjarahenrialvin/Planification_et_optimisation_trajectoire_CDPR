# Preuve — annulation réelle d’un worker GUI

**Date :** 2026-10-29  
**Branche :** `feature/gui-improvement`  
**Objectif :** vérifier avec une interaction navigateur réelle que le bouton d’annulation produit un état terminal cohérent et que les artefacts partiels restent exclus des résultats chargeables.

## Scénario exécuté

1. Démarrage de `streamlit run app/streamlit_app.py` en mode headless.
2. Ouverture de la page **Paramètres** dans le navigateur de test.
3. Sélection du profil `Instance courte : 3×3`.
4. Actualisation de l’aperçu.
5. Réglage temporaire de `n_gen=5000` afin de maintenir le worker dans l’optimiseur pendant l’interaction.
6. Lancement de l’exécution.
7. Clic réel sur **Annuler l’exécution** pendant `7_optimizer`.

## Résultat observé dans l’interface

L’interface a affiché :

```text
Run annulé proprement : Annulation demandée après la génération 1628/5000.
Ses artefacts restent exclus des résultats chargeables.
```

La progression affichait `7_optimizer — generation 1627/5000 (33%)` au moment de l’action navigateur.

## Manifeste produit

Run : `run_20261029T033722Z_d4b4399f`

```text
status          = CANCELLED
cancelled_step  = 7_optimizer
completed_steps = 4_point_generator, 5_point_filter, 6_cost_calculator
artifact_count  = 9
```

Le manifeste ne contient pas les étapes ultérieures `7_optimizer` à `11_comparator` dans `completed_steps`. Le run n’est donc pas présenté comme une source complète par la couche de résultats.

## Contrôles automatisés associés

```text
.venv/bin/python -m pytest -q \
  tests/test_gui_controller.py \
  tests/test_gui_skeleton.py \
  tests/test_theme.py

27 passed in 23.78s

.venv/bin/ruff check \
  app services \
  tests/test_gui_controller.py \
  tests/test_gui_skeleton.py \
  tests/test_theme.py

All checks passed!
```

La compilation Python a également réussi avec `python -m compileall -q app services src scripts tests visualization`.

## Limite documentée

L’annulation est coopérative. Elle est contrôlée à chaque génération de NSGA-II et entre les étapes du pipeline, mais elle ne force pas l’arrêt au milieu d’une étape scientifique déjà engagée. Un premier run 3×3 annulé pendant `10_validator` a donc pu atteindre `COMPLETED` avant que la demande ne soit observée. Ce comportement est attendu pour éviter un arrêt brutal au milieu de l’écriture d’artefacts.

## Conclusion

Le critère résiduel de 21.7 est satisfait : le bouton réel est fonctionnel, l’état `CANCELLED` est visible, le manifeste conserve la cause et l’étape, et le run partiel reste exclu des résultats chargeables.

# Snapshots runtime

Ce répertoire ne contient aucun résultat par défaut. Les snapshots créés par la GUI
sont ignorés par Git; seul ce README et le fichier `.gitkeep` sont versionnés. Les
snapshots ne sont ni chargés ni créés automatiquement.

## Créer un snapshot

1. Charger ou produire un run local terminé dans `data/runs/<run_id>`.
2. Dans **Résultats > Validation > Preuves techniques**, ouvrir **Snapshot persistant**.
3. Saisir un nom ou conserver la proposition, puis cliquer sur **Créer le snapshot**.

La source doit être un sous-répertoire direct de `data/runs/`. Le service exige un `run_manifest.json` de schéma 1 au statut `COMPLETED`, les huit étapes achevées, un inventaire d’artefacts exact, et un fingerprint identique dans le manifeste, `config.json` et `.config_hash`. `ResultService.load` contrôle en plus les fichiers CSV/JSON et leur cohérence. Les liens symboliques et fichiers spéciaux sont refusés.

Le contenu est copié dans un staging privé de ce répertoire, validé puis comparé au run source. Si le run change pendant la copie, la publication est annulée. Le staging est publié par renommage atomique Linux `renameat2(RENAME_NOREPLACE)`, qui refuse également une collision arrivée pendant la copie; aucun snapshot existant n’est remplacé. Les noms sont limités à 1–64 caractères ASCII : lettres, chiffres, point, tiret ou tiret bas, sans espace ni séparateur de chemin.

La création conserve `run_manifest.json`, `config.json`, `.config_hash` et tous les artefacts déclarés. Elle n’altère pas le run et ne constitue pas une validation scientifique expérimentale.

## Charger un snapshot

Après la création, le snapshot n’est pas activé automatiquement. Depuis **Accueil**, choisir `Snapshot — <nom>` dans **Source à afficher** puis cliquer sur **Charger cette source**. Le chemin actif est `data/snapshots/<nom>`.

La création atomique sans écrasement dépend de Linux et de la prise en charge système de `renameat2`. Les snapshots runtime sont locaux à l’installation et ne doivent pas être ajoutés au dépôt.

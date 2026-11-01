# Plan définitif proposé — Partie 3 rédigée par blocs

## Titre du chapitre

# ÉTUDE ET MISE EN ŒUVRE DU SYSTÈME TANDEM

Ce titre convient mieux à l’organisation retenue, car le chapitre présente à la fois le robot matériel, le fonctionnement de la chaîne de déplacement, le logiciel développé et l’évaluation des trajectoires.

---

# Logique générale du chapitre

La partie 3 sera construite autour de deux architectures complémentaires :

1. **l’architecture matérielle**, qui explique ce qu’est le robot Tandem, de quoi il est composé et comment il réalise un déplacement ;
2. **l’architecture logicielle**, qui explique comment le programme prépare les données, détermine les points atteignables, optimise la trajectoire et valide le résultat.

Le chapitre commencera par présenter les deux architectures dans leur ensemble à l’aide de deux schémas fonctionnels. Ensuite, chaque bloc sera expliqué séparément, dans l’ordre de fonctionnement du système.

Le fil directeur sera le suivant :

> Le système reçoit une mission d’acquisition, calcule une trajectoire admissible, transforme cette trajectoire en commandes de déplacement, déplace la plateforme au-dessus de la parcelle, s’arrête à chaque point de vue et produit les données nécessaires au suivi des plants.

Le chapitre ne reprendra pas longuement les définitions théoriques des chapitres 1 et 2. Il montrera comment ces notions sont concrètement appliquées au robot Tandem.

---

# Introduction du chapitre

## Contenu attendu

L’introduction doit expliquer que les chapitres précédents ont présenté :

- le fonctionnement général des robots parallèles à câbles ;
- les contraintes de tension et l’espace de travail faisable ;
- les méthodes de planification de chemin et de trajectoire ;
- le profil LSPB ;
- l’optimisation multiobjectif et NSGA-II.

La partie 3 applique maintenant ces connaissances à un système concret : le robot Tandem.

L’objectif du chapitre est double :

- décrire l’architecture matérielle et le cycle de fonctionnement du robot ;
- présenter la chaîne logicielle qui permet de calculer et de sélectionner les trajectoires.

L’introduction doit annoncer les deux grandes parties du chapitre :

- **Partie A : architecture matérielle et fonctionnement du robot ;**
- **Partie B : architecture logicielle et traitement par blocs.**

Elle doit également annoncer que les résultats des grilles `7×7` et `9×9`, ainsi que la comparaison avec la baseline zigzag, seront présentés après l’explication du fonctionnement du système.

---

# PARTIE A — ARCHITECTURE MATÉRIELLE DU ROBOT TANDEM

## Section 3.1 — Vue d’ensemble de l’architecture matérielle

### Objectif

Présenter le robot comme un système composé de blocs physiques reliés par des flux d’énergie, de commande, de mouvement et d’information.

### 3.1.1 Schéma global de l’architecture matérielle

Le schéma proposé doit présenter les blocs suivants :

```text
Mission d’acquisition
        ↓
Calculateur / commande
        ↓
Microcontrôleurs et actionneurs
        ↓
Moteurs et enrouleurs
        ↓
Câbles
        ↓
Plateforme mobile
        ↓
Caméra et capteurs
        ↓
Données acquises et informations de retour
```

Le schéma doit montrer que la plateforme mobile ne se déplace pas par roues ou par articulations rigides. Elle se déplace grâce aux variations coordonnées de la longueur des huit câbles.

### 3.1.2 Fonctionnement général du déplacement

Expliquer le cycle complet :

1. une mission définit les points de prise de vue ;
2. le logiciel calcule l’ordre de visite ;
3. la commande traduit les déplacements en variations de longueur de câble ;
4. les moteurs entraînent les enrouleurs ;
5. les câbles tirent la plateforme vers la position demandée ;
6. la plateforme atteint le point de vue ;
7. elle s’arrête et se stabilise ;
8. la caméra réalise l’acquisition ;
9. le système passe au point suivant ;
10. la plateforme revient au centre à la fin de la mission.

Cette section doit donner au lecteur une compréhension intuitive avant d’entrer dans les détails techniques.

**Figure à produire :** schéma fonctionnel global de l’architecture matérielle.

---

## Section 3.2 — Bloc matériel 1 : structure porteuse et points d’ancrage

### Contenu

Présenter :

- le rôle de la structure porteuse ;
- la position des ancrages fixes ;
- la répartition des câbles supérieurs et inférieurs ;
- le rôle de la géométrie dans la stabilité de la plateforme ;
- l’influence de la géométrie sur la matrice de structure et le WFW.

Relier cette description à la géométrie utilisée dans le modèle :

- huit câbles ;
- ancrages supérieurs à `z = 1,00 m` ;
- ancrages inférieurs à `z = 0 m` ;
- plateforme placée à la hauteur de référence `z = 0,45 m`.

Il faut expliquer que la position des ancrages détermine les directions des câbles, les moments produits et les tensions nécessaires à l’équilibre.

**Figure à produire :** vue de la structure et repérage des huit ancrages.

---

## Section 3.3 — Bloc matériel 2 : moteurs, enrouleurs et câbles

### Contenu

Présenter le rôle de chaque élément :

- moteur ;
- réducteur éventuel ;
- enrouleur ;
- câble ;
- variation de longueur active.

Expliquer le principe de fonctionnement :

- l’enroulement réduit la longueur libre du câble ;
- le déroulement augmente cette longueur ;
- les huit moteurs agissent de façon coordonnée ;
- la plateforme se déplace selon la combinaison des longueurs de câbles.

Relier ce bloc aux contraintes du chapitre 1 :

- un câble ne peut que tirer ;
- chaque câble doit rester tendu ;
- la tension doit rester comprise entre `1 N` et `58 N` ;
- le moteur et l’enrouleur doivent fournir l’effort nécessaire sans dépasser leur capacité.

Présenter le modèle de câble retenu pour l’étude : câble rigide, rectiligne, inextensible et sans prise en compte de l’affaissement dû au poids propre.

**Figure à produire :** schéma moteur–enrouleur–câble–plateforme.

---

## Section 3.4 — Bloc matériel 3 : plateforme mobile et charge utile

### Contenu

Présenter la plateforme comme l’organe terminal suspendu par les câbles.

Décrire :

- matériau : aluminium 6061-T6 ;
- dimensions : `300 × 240 mm` ;
- huit points d’attache ;
- masse à vide : environ `242 g` ;
- charge utile : environ `114 g` ;
- masse opérationnelle utilisée dans les calculs : `384 g`.

Détailler la charge utile :

- Raspberry Pi Zero 2 W ;
- Pi Camera Module 3 ;
- câble nappe CSI ;
- cellule 18650 et porte-pile ;
- convertisseur ;
- capteur HC-SR04 ;
- accéléromètre ;
- boîtier de protection.

Expliquer la fonction de la plateforme :

- transporter la caméra ;
- maintenir son orientation ;
- atteindre chaque point de vue ;
- rester stable pendant la prise de vue.

**Figure à produire :** plateforme mobile annotée.

**Tableau à conserver :** caractéristiques de la plateforme et composition de la charge utile.

---

## Section 3.5 — Bloc matériel 4 : commande, alimentation et acquisition

### Contenu

Présenter la chaîne de commande et d’acquisition sans entrer dans des détails non vérifiés expérimentalement.

Décrire les fonctions :

- calculateur ou unité de commande ;
- génération des consignes de déplacement ;
- transmission des consignes aux moteurs ;
- alimentation électrique ;
- acquisition des images ;
- mesure de distance ou de stabilité lorsque les capteurs sont utilisés.

Il faut expliquer la distinction entre :

- le programme de planification, exécuté en amont pour calculer la trajectoire ;
- la commande d’exécution, chargée de transformer la trajectoire en mouvements ;
- les capteurs, utilisés pour confirmer la position, la distance ou la stabilité.

Si certains éléments ne sont pas encore intégrés au prototype final, ils doivent être présentés comme éléments prévus de l’architecture, et non comme fonctions expérimentalement validées.

---

## Section 3.6 — Fonctionnement séquentiel d’une mission

### Objectif

Expliquer le déplacement du robot sous forme d’un scénario complet.

### Étapes proposées

1. **Initialisation** : mise sous tension, position de référence et vérification de l’état du système.
2. **Préparation de la mission** : chargement des points de vue et de l’ordre de visite.
3. **Déplacement vers le premier point** : action coordonnée des moteurs et des câbles.
4. **Atteinte de la pose demandée** : contrôle de la position et des longueurs de câbles.
5. **Stabilisation** : arrêt pendant `2 s` pour réduire les vibrations et éviter le flou.
6. **Acquisition** : prise de vue de la zone observée.
7. **Passage au point suivant** : répétition du cycle déplacement–stabilisation–acquisition.
8. **Retour au centre** : fin de la mission et remise en position de référence.

### Schéma recommandé

```text
Initialisation
      ↓
Départ au centre
      ↓
Déplacement vers le point i
      ↓
Arrêt et stabilisation
      ↓
Prise de vue
      ↓
Point suivant ? ── Oui ──> Déplacement vers le point i+1
      │
      Non
      ↓
Retour au centre
      ↓
Fin de mission
```

### Transition vers la partie logicielle

Conclure que le déplacement réel dépend d’une trajectoire calculée à l’avance. Il faut donc présenter le programme qui produit cette trajectoire et vérifie sa faisabilité avant son exécution.

---

# PARTIE B — ARCHITECTURE LOGICIELLE ET TRAITEMENT PAR BLOCS

## Section 3.7 — Vue d’ensemble de l’architecture logicielle

### 3.7.1 Outils utilisés pour le développement

Présenter les outils avant d’expliquer les blocs :

- **Python 3.11** : langage principal de développement ;
- **NumPy** : calcul matriciel et manipulation des vecteurs ;
- **SciPy** : programmation linéaire, solveur HiGHS et optimisation numérique ;
- **pandas** : gestion des tableaux de points, coûts et résultats ;
- **pymoo** : implémentation de NSGA-II ;
- **Matplotlib** : génération de figures scientifiques ;
- **Streamlit** : interface graphique interactive ;
- **Plotly** : visualisations interactives en 2D et 3D ;
- **pytest** : tests unitaires et tests d’intégration ;
- **Ruff** : contrôle de qualité et de style du code.

Il faut expliquer que Python a été choisi pour :

- sa disponibilité dans les environnements scientifiques ;
- ses bibliothèques de calcul numérique ;
- la facilité de prototypage ;
- la possibilité de séparer le moteur scientifique, les services et l’interface utilisateur ;
- la reproductibilité des campagnes de simulation.

### 3.7.2 Organisation du logiciel

Présenter l’organisation générale :

```text
Interface Streamlit
        ↓
Services applicatifs
        ↓
Blocs scientifiques Python
        ↓
Fichiers de résultats, figures et rapports
```

Expliquer que l’interface n’effectue pas directement les calculs scientifiques. Elle appelle des services qui utilisent les blocs du moteur de calcul.

### 3.7.3 Schéma global des quatre blocs principaux

Le schéma logiciel doit présenter :

```text
Bloc 1 — Préparation des données
        ↓
Bloc 2 — Génération et filtrage de l’espace de travail
        ↓
Bloc 3 — Optimisation des trajectoires
        ↓
Bloc 4 — Profilage, validation et comparaison
```

Dans le texte, il faut utiliser le mot **bloc** et non « macro-bloc ». Les sous-étapes seront expliquées une par une dans les sections suivantes.

---

## Section 3.8 — Bloc 1 : préparation des données

### Rôle du bloc

Transformer les paramètres physiques et les exigences de la mission en une configuration exploitable par le programme.

### Étapes à expliquer

#### 3.8.1 Définition de la configuration

Présenter les données d’entrée :

- dimensions de la plateforme ;
- coordonnées des ancrages ;
- coordonnées des attaches ;
- masse opérationnelle ;
- hauteur de référence ;
- bornes de tension ;
- limites de vitesse et d’accélération ;
- temps de stabilisation ;
- taille de la grille ;
- population et nombre de générations ;
- graine aléatoire.

#### 3.8.2 Validation des paramètres

Expliquer que les paramètres sont contrôlés avant le lancement :

- cohérence des bornes ;
- dimensions compatibles ;
- valeurs positives ;
- limites d’optimisation acceptables ;
- configuration complète et sérialisable.

#### 3.8.3 Construction du modèle robotique

Présenter la création de :

- la géométrie du robot ;
- la matrice de structure ;
- l’objet de calcul du WFW ;
- les fonctions de calcul des longueurs et des directions de câbles.

#### 3.8.4 Sorties du bloc

Les sorties sont :

- configuration validée ;
- modèle du robot ;
- paramètres de campagne ;
- empreinte de configuration ;
- dossier de résultats initialisé.

**Figure recommandée :** diagramme des entrées et sorties du bloc 1.

---

## Section 3.9 — Bloc 2 : génération et filtrage de l’espace de travail

### Rôle du bloc

Créer les points de vue de la mission et ne conserver que les points mécaniquement faisables.

### Étapes à expliquer

#### 3.9.1 Génération de la grille

Présenter :

- grille centrée sur la parcelle ;
- points de vue associés aux positions de prise de vue ;
- maintien de la hauteur et de l’orientation ;
- rôle du point central comme départ et retour.

#### 3.9.2 Vérification géométrique

Pour chaque point, vérifier :

- coordonnées dans les limites opérationnelles ;
- longueurs de câbles calculables ;
- position valide dans le modèle.

#### 3.9.3 Test de rang

Expliquer que la matrice de structure est contrôlée avant le test de tension. Un rang insuffisant traduit une singularité statique et entraîne le rejet du point.

#### 3.9.4 Test WFW

Présenter la résolution du problème de faisabilité :

- équilibre du poids ;
- tension minimale ;
- tension maximale ;
- prise en compte des forces et moments.

#### 3.9.5 Classification des points

Chaque point est classé comme :

- faisable et conservé ;
- rejeté pour limite opérationnelle ;
- rejeté pour singularité ou absence de tension admissible.

#### 3.9.6 Résultats du bloc

Présenter les résultats des quatre configurations :

- zone sécurisée `7×7` : `49/49` points ;
- zone sécurisée `9×9` : `81/81` points ;
- zone étendue `7×7` : `49/49` points ;
- zone étendue `9×9` : `77/81` points.

**Figure recommandée :** grille 3D avec points faisables et rejetés.

---

## Section 3.10 — Bloc 3 : construction des coûts et optimisation des trajectoires

### Rôle du bloc

Évaluer les déplacements possibles entre les points retenus, puis rechercher un ordre de visite performant.

### Étapes à expliquer

#### 3.10.1 Construction des transitions

Pour chaque paire de points, calculer :

- distance ;
- variation des longueurs de câbles ;
- faisabilité de la transition ;
- temps de déplacement ;
- énergie estimée.

Les résultats sont rassemblés dans une matrice de coûts.

#### 3.10.2 Calcul du temps avec LSPB

Expliquer :

- accélération ;
- vitesse maximale ;
- décélération ;
- profil triangulaire pour les courtes distances ;
- profil trapézoïdal pour les distances plus longues ;
- arrêt complet au point d’arrivée.

Avec les paramètres retenus :

- `v_max = 0,045 m/s` ;
- `a_max = 0,03 m/s²` ;
- `d_acc ≈ 0,034 m`.

#### 3.10.3 Calcul de l’énergie

Présenter l’estimation quasi-statique :

- subdivision du mouvement ;
- calcul des tensions à des points intermédiaires ;
- résolution d’une distribution de tensions à norme minimale ;
- somme du travail associé aux variations de longueur.

#### 3.10.4 Codage de la trajectoire

Expliquer qu’un individu de NSGA-II représente une permutation des points non centraux :

```text
Centre → point 4 → point 12 → point 8 → ... → Centre
```

#### 3.10.5 Évaluation multiobjectif

Chaque permutation est évaluée selon :

- le temps total de déplacement ;
- l’énergie totale ;
- les pénalités éventuelles si une transition est infaisable.

#### 3.10.6 Évolution par NSGA-II

Décrire uniquement l’application au projet :

- génération de la population initiale ;
- classement par dominance ;
- sélection ;
- croisement OX ;
- mutation par inversion ;
- conservation des meilleures solutions ;
- répétition jusqu’au nombre de générations fixé.

#### 3.10.7 Extraction des solutions

Présenter les trois solutions utilisées dans l’analyse :

- solution minimisant le temps ;
- solution minimisant l’énergie ;
- solution de compromis.

**Figure recommandée :** matrice des coûts, exemple de permutation et front de Pareto.

---

## Section 3.11 — Bloc 4 : profilage, validation et comparaison

### Rôle du bloc

Transformer les solutions abstraites de l’optimisation en trajectoires analysables et vérifier leur conformité.

### Étapes à expliquer

#### 3.11.1 Extraction de l’ordre de visite

Convertir chaque solution Pareto en une liste ordonnée de points et vérifier :

- présence de tous les points retenus ;
- absence de doublons ;
- départ au centre ;
- retour au centre.

#### 3.11.2 Profilage de la trajectoire

Générer les profils LSPB pour chaque segment et calculer :

- position ;
- vitesse ;
- accélération ;
- temps cumulé ;
- temps de stabilisation.

#### 3.11.3 Validation des contraintes

Vérifier :

- faisabilité des points ;
- faisabilité des transitions ;
- vitesse maximale ;
- accélération maximale ;
- cohérence temporelle ;
- arrêt aux points de prise de vue ;
- retour final au centre ;
- non-dominance des solutions Pareto.

#### 3.11.4 Construction de la baseline

Présenter la stratégie zigzag :

- visite ligne par ligne ;
- même ensemble de points ;
- même départ et retour au centre ;
- mêmes modèles de temps et d’énergie.

Cette dernière condition est importante pour garantir une comparaison équitable.

#### 3.11.5 Calcul des gains

Calculer les gains relatifs :

- gain de temps ;
- gain d’énergie ;
- différence de longueur ou de coût si nécessaire ;
- influence du nombre de points retenus.

#### 3.11.6 Génération des résultats

Présenter les artefacts produits :

- trajectoires ;
- profils cinématiques ;
- front de Pareto ;
- tableaux de comparaison ;
- rapports de validation ;
- figures 2D et 3D.

**Figure recommandée :** organigramme du bloc 4 avec les contrôles et les sorties.

---

# PARTIE C — ÉVALUATION DES BLOCS ET RÉSULTATS

Même si le chapitre est organisé autour des architectures et des blocs, les résultats doivent être regroupés dans une partie d’évaluation distincte afin de ne pas mélanger la méthode et son interprétation.

## Section 3.12 — Protocole d’évaluation

Présenter :

- les grilles `7×7` et `9×9` ;
- la zone sécurisée et la zone étendue ;
- les paramètres de simulation ;
- le nombre de populations et de générations ;
- les campagnes de dimensionnement ;
- les essais de robustesse ;
- la baseline zigzag ;
- les indicateurs utilisés.

### Dimensionnement retenu

- grille `7×7` : population de `500`, `2 000` générations ;
- grille `9×9` : population de `600`, `5 000` générations.

Il faut rappeler que ces choix sont issus de l’étude déjà validée dans le chapitre 3.

## Section 3.13 — Résultats du bloc 2 : faisabilité de l’espace de travail

Présenter :

- la couverture de la zone sécurisée ;
- les points rejetés dans la zone étendue ;
- la forme du WFW ;
- l’intérêt du mode zero-loss ;
- les limites mécaniques observées.

## Section 3.14 — Résultats du bloc 3 : optimisation

Présenter les performances obtenues sur les zones sécurisées :

| Grille | Temps optimisé | Énergie optimisée | Gain de temps | Gain d’énergie |
|---|---:|---:|---:|---:|
| `7×7` | `177,30 s` | `246,44 J` | `22,7 %` | `27,6 %` |
| `9×9` | `247,04 s` | `294,09 J` | `21,0 %` | `28,7 %` |

Interpréter les résultats en expliquant que l’optimisation réduit les retours inutiles par rapport au zigzag.

Présenter également :

- la forme du front de Pareto ;
- les solutions temps, énergie et compromis ;
- l’effet de la taille de la grille ;
- la stabilité obtenue lors des essais de robustesse.

## Section 3.15 — Résultats du bloc 4 : validation et comparaison

Présenter :

- le respect des vitesses et accélérations ;
- les profils LSPB ;
- le temps de stabilisation ;
- les tensions maximales observées ;
- la comparaison avec la baseline ;
- les figures des trajectoires optimisées.

Pour la zone sécurisée, rappeler que la tension maximale observée atteint environ `35,7 N`, donc reste inférieure à la limite de `58 N`.

## Section 3.16 — Comparaison entre zone sécurisée et zone étendue

Présenter les conséquences de l’extension de la zone :

- augmentation du temps ;
- augmentation importante de l’énergie ;
- rapprochement des limites du WFW ;
- rejet de points dans la configuration `9×9` étendue ;
- perte d’intérêt de l’extension pour la mission d’acquisition.

Conclure que la zone sécurisée constitue le meilleur compromis entre couverture, faisabilité mécanique, temps et énergie.

---

# PARTIE D — DISCUSSION ET CONCLUSION

## Section 3.17 — Discussion générale

Répondre aux questions de départ :

1. Les points de la zone sécurisée sont-ils accessibles ?
2. La plateforme peut-elle rester mécaniquement faisable pendant la mission ?
3. L’optimisation améliore-t-elle le temps et l’énergie ?
4. Pourquoi la zone sécurisée est-elle retenue ?
5. Quel est le rôle de chaque bloc dans la chaîne complète ?

La discussion doit montrer que les quatre blocs sont interdépendants :

- sans le bloc 1, les calculs ne disposent pas de paramètres cohérents ;
- sans le bloc 2, l’optimisation pourrait utiliser des points irréalisables ;
- sans le bloc 3, l’ordre de visite resterait arbitraire ;
- sans le bloc 4, il serait impossible de vérifier la conformité de la trajectoire et de mesurer le gain.

## Section 3.18 — Limites de l’étude

Présenter les limites liées :

- au modèle de câble rigide ;
- à l’énergie quasi-statique ;
- à l’absence de vent ;
- aux hypothèses de masse et de tension ;
- au nombre limité de graines ;
- à la validation essentiellement numérique ;
- à l’absence de test complet sur prototype.

## Section 3.19 — Perspectives

Présenter :

- validation expérimentale sur le prototype ;
- intégration des câbles élastiques ;
- prise en compte de l’affaissement pour les câbles longs ;
- ajout du vent et des vibrations ;
- retour capteur en temps réel ;
- recalcul dynamique de la trajectoire ;
- transmission des trajectoires au SP3 ;
- amélioration de l’interface de supervision.

## Conclusion du chapitre

La conclusion doit résumer la chaîne complète :

```text
Architecture matérielle
        ↓
Paramètres physiques
        ↓
Préparation logicielle
        ↓
Filtrage WFW
        ↓
Optimisation temps–énergie
        ↓
Profilage et validation
        ↓
Trajectoire utilisable pour l’acquisition
```

Elle doit rappeler que l’étude a permis :

- de modéliser le robot Tandem ;
- d’identifier une zone de travail sécurisée ;
- de calculer des trajectoires respectant les contraintes retenues ;
- d’obtenir des gains de temps et d’énergie par rapport au zigzag ;
- de sélectionner une solution adaptée à la mission d’imagerie.

La dernière phrase doit ouvrir vers la conclusion générale et vers l’exploitation des trajectoires par le SP3.

---

# Recommandations de rédaction

## 1. Utiliser un vocabulaire stable

Employer systématiquement :

- **bloc matériel** pour un composant physique ou une fonction physique ;
- **bloc logiciel** pour une étape du programme ;
- **plateforme mobile** pour l’organe suspendu ;
- **point de vue** pour une position de prise de vue ;
- **trajectoire optimisée** pour la séquence complète dans le temps ;
- **ordre de visite** pour la permutation des points ;
- **zone sécurisée** et **zone étendue** pour les deux scénarios.

Éviter d’alterner entre « module », « sous-module », « macro-bloc » et « bloc » sans justification.

## 2. Présenter les blocs avant de les détailler

Au début de la partie matérielle, présenter le schéma complet du robot. Au début de la partie logicielle, présenter le schéma des quatre blocs principaux. Ensuite seulement, détailler chaque bloc dans l’ordre.

## 3. Maintenir la différence entre commande et planification

Le programme Python étudié calcule et valide les trajectoires. Il ne faut pas présenter automatiquement ce programme comme le contrôleur temps réel des moteurs si cette fonction n’a pas été expérimentée dans le cadre du mémoire.

## 4. Séparer les hypothèses des résultats

Chaque paramètre doit être présenté avec son origine :

- mesure ;
- calcul ;
- choix de conception ;
- hypothèse ;
- limite mécanique ;
- résultat de simulation.

## 5. Ne pas répéter les chapitres théoriques

La théorie du WFW, de LSPB et de NSGA-II est déjà présentée dans les chapitres 1 et 2. Dans la partie 3, il faut expliquer leur utilisation dans le projet Tandem, avec les paramètres, les entrées, les sorties et les résultats.

## 6. Organiser les figures autour des flux

Les figures prioritaires sont :

1. architecture matérielle globale ;
2. cycle de déplacement et d’acquisition ;
3. géométrie du robot et ancrages ;
4. plateforme et charge utile ;
5. architecture logicielle ;
6. entrées et sorties du bloc 1 ;
7. filtrage WFW du bloc 2 ;
8. matrice des coûts et front Pareto du bloc 3 ;
9. validation et comparaison du bloc 4 ;
10. trajectoires finales et profils LSPB.

Chaque figure doit être introduite dans le texte, expliquée et reliée à la question scientifique étudiée.

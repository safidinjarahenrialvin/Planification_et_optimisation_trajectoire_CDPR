# Plan définitif de rédaction de la partie 3

## Titre proposé

# ÉTUDE, MISE EN ŒUVRE ET ÉVALUATION DU ROBOT TANDEM

Ce titre reprend l’esprit de l’ancien chapitre 3 tout en reflétant son contenu réel. Le chapitre ne présente pas uniquement le robot : il décrit également son modèle, le fonctionnement séquentiel de la mission, le programme développé, les blocs de traitement, le protocole d’étude et les résultats obtenus.

---

# Principe général de construction

La nouvelle partie 3 doit conserver les résultats validés de l’ancien chapitre 3, mais réorganiser leur présentation afin de rendre la lecture plus progressive.

La logique retenue est la suivante :

1. présenter le robot Tandem et son architecture matérielle ;
2. expliquer son fonctionnement séquentiel depuis le départ jusqu’au retour au centre ;
3. présenter l’architecture logicielle complète ;
4. détailler les quatre blocs logiciels dans l’ordre du traitement ;
5. décrire le protocole d’étude et le dimensionnement de NSGA-II ;
6. présenter les vérifications numériques ;
7. analyser les résultats sur les grilles `7×7` et `9×9` ;
8. discuter les limites et les perspectives.

La partie matérielle ne sera pas organisée en une succession de blocs détaillant séparément chaque composant. Les composants seront présentés ensemble dans une architecture cohérente. La décomposition en étapes sera utilisée uniquement pour expliquer le fonctionnement séquentiel de la mission.

La décomposition en blocs sera principalement utilisée pour l’architecture logicielle, car le programme suit effectivement une chaîne de traitement composée de quatre blocs fonctionnels :

```text
Bloc 1 — Préparation des données
        ↓
Bloc 2 — Génération et filtrage de l’espace de travail
        ↓
Bloc 3 — Optimisation des trajectoires
        ↓
Bloc 4 — Validation, profilage et comparaison
```

---

# Introduction de la partie 3

## Fonction de l’introduction

L’introduction doit assurer la transition entre les chapitres théoriques et l’étude du robot réel.

Elle doit expliquer que :

- le chapitre 1 a présenté les particularités mécaniques des CDPR et le rôle du WFW ;
- le chapitre 2 a présenté les méthodes de planification, le profil LSPB et NSGA-II ;
- ces notions sont maintenant appliquées au robot Tandem ;
- l’objectif est de calculer une trajectoire de prise de vue couvrant une parcelle tout en respectant les contraintes mécaniques et cinématiques ;
- l’étude compare les trajectoires optimisées à une trajectoire de référence en zigzag.

## Problématique appliquée

La partie 3 doit répondre à trois questions :

1. Comment le robot Tandem est-il constitué et comment réalise-t-il un déplacement au-dessus de la parcelle ?
2. Comment le programme détermine-t-il les points accessibles et l’ordre de visite des points de prise de vue ?
3. Les trajectoires optimisées permettent-elles de réduire le temps et l’énergie par rapport à la baseline zigzag ?

## Annonce du chapitre

L’introduction annonce deux architectures principales :

- l’architecture matérielle du robot et son fonctionnement séquentiel ;
- l’architecture logicielle organisée en quatre blocs.

Elle annonce ensuite l’évaluation numérique, les résultats et la discussion.

---

# PARTIE A — ARCHITECTURE MATÉRIELLE ET FONCTIONNEMENT DU ROBOT

## Section 3.1 — Présentation générale du robot Tandem

### 3.1.1 Contexte et rôle du robot

Présenter brièvement le projet Tandem et le rôle du sous-projet SP2.

Expliquer que le robot est destiné à déplacer une caméra au-dessus d’une parcelle de haricot nain afin d’acquérir des images utiles au suivi du stress hydrique.

Présenter le lien entre les sous-projets :

- le SP1 fournit la géométrie et les caractéristiques du système ;
- le SP2 calcule les trajectoires ;
- le SP3 exploite les images et les informations issues de la caméra.

### 3.1.2 Architecture matérielle générale

Présenter le robot comme un ensemble cohérent constitué de :

- structure porteuse ;
- huit points d’ancrage ;
- huit câbles ;
- moteurs et enrouleurs ;
- plateforme mobile ;
- charge utile ;
- système de commande ;
- caméra et capteurs.

Il faut expliquer que la plateforme mobile est suspendue et déplacée par la variation coordonnée des longueurs des huit câbles.

**Figure à prévoir :** schéma général annoté du robot Tandem.

### 3.1.3 Plateforme mobile et charge utile

Conserver et améliorer le contenu de l’ancien chapitre 3 :

- plateforme en aluminium 6061-T6 ;
- dimensions `300 × 240 mm` ;
- huit points d’attache ;
- masse à vide d’environ `242 g` ;
- charge utile d’environ `114 g` ;
- marge de `8 %` pour le câblage et les fixations ;
- masse opérationnelle de `384 g`.

Présenter la composition de la charge utile :

- Raspberry Pi Zero 2 W ;
- Pi Camera Module 3 ;
- câble nappe CSI ;
- cellule 18650 et porte-pile ;
- convertisseur ;
- capteur HC-SR04 ;
- accéléromètre 3 axes ;
- boîtier de protection.

Insister sur le fait que la masse opérationnelle de `384 g`, et non la masse à vide, est utilisée pour les calculs mécaniques.

**Tableau à conserver :** caractéristiques de la plateforme et composition de la charge utile.

### 3.1.4 Moteurs, enrouleurs et câbles

Présenter leur rôle dans le déplacement :

- le moteur entraîne l’enrouleur ;
- l’enrouleur modifie la longueur active du câble ;
- les huit câbles exercent uniquement des efforts de traction ;
- la plateforme se déplace par combinaison des variations de longueur.

Ne pas développer ici toute la théorie des câbles : renvoyer au chapitre 1 pour le principe général et rappeler seulement le modèle utilisé dans l’étude.

### 3.1.5 Charge utile, orientation et mission d’acquisition

Expliquer que :

- la caméra est orientée vers le bas, en vue nadir ;
- l’orientation de la plateforme est maintenue fixe ;
- la trajectoire est principalement une translation pure ;
- chaque point de la grille correspond à une position de prise de vue ;
- un arrêt est nécessaire avant l’acquisition.

### 3.1.6 Schéma global de fonctionnement matériel

Présenter un schéma simple :

```text
Mission d’acquisition
        ↓
Système de commande
        ↓
Moteurs et enrouleurs
        ↓
Variation des longueurs des câbles
        ↓
Déplacement de la plateforme
        ↓
Stabilisation de la plateforme
        ↓
Acquisition de l’image
```

Ce schéma introduit la section suivante consacrée au fonctionnement séquentiel.

---

## Section 3.2 — Fonctionnement séquentiel du robot par étapes

### Objectif de la section

Expliquer comment une trajectoire calculée devient une mission physique de prise de vue.

Cette section est la seule partie de l’architecture matérielle qui sera décomposée explicitement en étapes fonctionnelles.

### Étape 1 — Initialisation du système

Décrire :

- mise sous tension ;
- initialisation du calculateur et des actionneurs ;
- chargement de la configuration ;
- vérification de la position initiale ;
- vérification de la disponibilité des données de trajectoire.

### Étape 2 — Position de départ au centre

Expliquer pourquoi le centre constitue le point de départ :

- position de référence ;
- point commun entre les trajectoires ;
- départ et retour imposés pour comparer équitablement les solutions.

### Étape 3 — Déplacement vers le point de vue suivant

Décrire le rôle coordonné des moteurs et des câbles :

- lecture du point cible ;
- calcul des longueurs nécessaires ;
- commande des enrouleurs ;
- déplacement de la plateforme selon le profil temporel prévu.

### Étape 4 — Atteinte de la position et arrêt

Expliquer que le robot doit atteindre précisément le point de prise de vue et que la vitesse doit revenir à zéro avant l’acquisition.

### Étape 5 — Stabilisation

Présenter le temps de stabilisation de `2 s` par point. Expliquer qu’il sert à limiter les effets des vibrations et à éviter une image floue.

### Étape 6 — Acquisition de l’image

Décrire la prise de vue par la caméra et le lien avec l’objectif agronomique du projet.

### Étape 7 — Passage au point suivant

La séquence déplacement–arrêt–stabilisation–acquisition est répétée jusqu’à la fin de la liste des points.

### Étape 8 — Retour au centre et fin de mission

Décrire le retour au point central, la fin du parcours et la mise en sécurité du système.

### Schéma séquentiel à prévoir

```text
Initialisation
      ↓
Départ au centre
      ↓
Déplacement vers le point i
      ↓
Arrêt
      ↓
Stabilisation de 2 s
      ↓
Prise de vue
      ↓
Reste-t-il des points ?
   Oui ↓        ↓ Non
Point suivant   Retour au centre
                    ↓
              Fin de mission
```

### Transition vers l’architecture logicielle

Conclure que cette séquence nécessite une trajectoire préparée à l’avance. Le programme doit donc :

- définir les points ;
- vérifier leur faisabilité ;
- déterminer leur ordre de visite ;
- calculer les profils temporels ;
- valider le résultat avant toute exécution.

---

# PARTIE B — ARCHITECTURE LOGICIELLE DU PROJET

## Section 3.3 — Présentation générale du logiciel et des outils utilisés

### 3.3.1 Objectif du programme

Expliquer que le programme développé en Python transforme une configuration du robot et une mission de prise de vue en une trajectoire validée.

Le programme doit répondre à la chaîne suivante :

```text
Paramètres physiques
        ↓
Points de prise de vue
        ↓
Points faisables
        ↓
Coûts de déplacement
        ↓
Ordres de visite optimisés
        ↓
Profils temporels
        ↓
Validation et comparaison
```

### 3.3.2 Outils et bibliothèques utilisés

Présenter les outils réellement utilisés :

- **Python 3.11** : langage principal ;
- **NumPy** : vecteurs, matrices et calculs numériques ;
- **SciPy** : programmation linéaire, solveur HiGHS et résolution numérique ;
- **pandas** : tableaux de points, coûts et résultats ;
- **pymoo** : algorithme NSGA-II ;
- **Matplotlib** : figures scientifiques ;
- **Streamlit** : interface graphique ;
- **Plotly** : figures interactives ;
- **pytest** : tests ;
- **Ruff** : vérification de la qualité du code.

Expliquer le choix de Python par :

- la disponibilité des bibliothèques scientifiques ;
- la facilité de développement ;
- la possibilité de reproduire les campagnes ;
- la séparation entre calcul, services et interface ;
- la production automatisée des fichiers et figures.

### 3.3.3 Organisation des fichiers logiciels

Présenter la séparation générale :

```text
src/              Modèles et algorithmes scientifiques
services/         Orchestration et contrats applicatifs
visualization/    Figures réutilisables
app/              Interface Streamlit
tests/            Tests unitaires et d’intégration
data/            Résultats et artefacts d’exécution
```

### 3.3.4 Schéma complet des quatre blocs logiciels

Présenter le schéma avant le détail :

```text
Bloc 1 — Préparation des données
        ↓
Bloc 2 — Génération et filtrage de l’espace de travail
        ↓
Bloc 3 — Optimisation des trajectoires
        ↓
Bloc 4 — Validation, profilage et comparaison
```

Le texte doit utiliser le terme **bloc** de manière constante. Chaque bloc aura une entrée, un traitement et une sortie clairement identifiés.

---

## Section 3.4 — Bloc 1 : préparation des données

### Rôle

Préparer l’ensemble des informations nécessaires aux calculs.

### 3.4.1 Entrées du bloc

Présenter :

- géométrie du robot ;
- masse opérationnelle ;
- hauteur de référence ;
- bornes de tension ;
- limites de vitesse et d’accélération ;
- taille de la grille ;
- paramètres de NSGA-II ;
- graine aléatoire ;
- options de zone sécurisée ou étendue.

### 3.4.2 Validation de la configuration

Expliquer les contrôles effectués avant le calcul :

- cohérence des valeurs ;
- bornes physiques compatibles ;
- configuration complète ;
- paramètres d’optimisation valides ;
- création d’une empreinte de configuration.

### 3.4.3 Construction des objets scientifiques

Présenter la création :

- du modèle robotique ;
- du calculateur WFW ;
- des fonctions cinématiques ;
- des paramètres de la campagne.

### 3.4.4 Sorties

Les sorties sont :

- une configuration validée ;
- un modèle du robot ;
- une configuration sérialisée ;
- un dossier de résultats prêt à recevoir les artefacts.

### Transition

Le bloc 1 fournit les données nécessaires pour générer la grille de points du bloc 2.

---

## Section 3.5 — Bloc 2 : génération et filtrage de l’espace de travail

### Rôle

Déterminer les positions réellement utilisables par la plateforme mobile.

### 3.5.1 Génération des points

Expliquer :

- création d’une grille centrée ;
- position de la plateforme à hauteur constante ;
- orientation maintenue fixe ;
- association d’un point à une prise de vue.

### 3.5.2 Vérifications géométriques

Pour chaque point, calculer ou vérifier :

- position dans les limites opérationnelles ;
- longueurs de câbles ;
- directions des câbles ;
- validité géométrique de la pose.

### 3.5.3 Contrôle de singularité

Présenter le calcul du rang de la matrice de structure et expliquer que les points singuliers sont écartés avant la résolution du problème de tension.

### 3.5.4 Test WFW

Présenter le problème de faisabilité sous contraintes :

- équilibre du poids ;
- forces et moments ;
- tension minimale de `1 N` ;
- tension maximale de `58 N`.

### 3.5.5 Classification et export

Expliquer la séparation entre :

- points retenus ;
- points rejetés pour limites opérationnelles ;
- points rejetés pour singularité ou absence de solution en tension.

### 3.5.6 Résultats du bloc

Présenter les valeurs validées :

- zone sécurisée `7×7` : `49/49` points ;
- zone sécurisée `9×9` : `81/81` points ;
- zone étendue `7×7` : `49/49` points ;
- zone étendue `9×9` : `77/81` points.

### Transition

Le bloc 2 fournit l’ensemble des points admissibles. Le bloc 3 peut alors comparer les déplacements possibles et rechercher un ordre de visite performant.

---

## Section 3.6 — Bloc 3 : optimisation des trajectoires

### Rôle

Déterminer un ordre de visite qui concilie la durée de déplacement et l’énergie consommée.

### 3.6.1 Construction des transitions

Pour chaque paire de points, calculer :

- distance ;
- différence de longueur des câbles ;
- faisabilité de la transition ;
- temps de déplacement ;
- énergie.

Présenter la matrice de coûts comme l’interface entre le modèle mécanique et l’algorithme d’optimisation.

### 3.6.2 Calcul du temps par profil LSPB

Rappeler brièvement le principe déjà présenté au chapitre 2, puis expliquer son application :

- accélération constante ;
- vitesse maximale ;
- décélération ;
- profil triangulaire ou trapézoïdal ;
- vitesse nulle à l’arrivée.

Paramètres utilisés :

- `v_max = 0,045 m/s` ;
- `a_max = 0,03 m/s²` ;
- `d_acc ≈ 0,034 m`.

### 3.6.3 Calcul de l’énergie

Présenter l’estimation quasi-statique :

- subdivision de chaque transition ;
- évaluation des tensions aux points intermédiaires ;
- résolution à norme minimale ;
- somme du travail des tensions sur les variations de longueur.

### 3.6.4 Représentation d’une solution

Expliquer qu’un individu correspond à une permutation des points non centraux, avec le centre imposé au départ et au retour.

### 3.6.5 Optimisation NSGA-II

Présenter l’application au projet :

- population initiale ;
- évaluation du temps et de l’énergie ;
- classement par dominance ;
- croisement OX ;
- mutation par inversion ;
- conservation des solutions non dominées ;
- répétition pendant le nombre de générations fixé.

Ne pas répéter toutes les explications théoriques du chapitre 2 ; se concentrer sur le codage et les paramètres utilisés dans le projet.

### 3.6.6 Extraction des solutions

Présenter :

- `time_opt` ;
- `energy_opt` ;
- `compromise`.

### Transition

Le bloc 3 fournit des ordres de visite optimisés. Le bloc 4 les transforme en trajectoires temporelles, contrôle leur validité et les compare à la baseline.

---

## Section 3.7 — Bloc 4 : validation, profilage et comparaison

### Rôle

Vérifier qu’une solution issue de l’optimisation peut être interprétée comme une trajectoire cohérente et comparée de manière équitable à une référence.

### 3.7.1 Extraction de l’ordre de visite

Vérifier :

- présence de tous les points ;
- absence de doublons ;
- départ au centre ;
- retour au centre ;
- cohérence de la séquence.

### 3.7.2 Profilage temporel

Générer les profils LSPB et calculer :

- position ;
- vitesse ;
- accélération ;
- temps cumulé ;
- temps de stabilisation.

### 3.7.3 Vérifications numériques

Présenter les contrôles :

- points faisables ;
- transitions faisables ;
- vitesse maximale ;
- accélération maximale ;
- arrêt aux waypoints ;
- cohérence des coûts ;
- non-dominance du front ;
- retour final au centre.

### 3.7.4 Construction de la baseline zigzag

Expliquer que la baseline :

- parcourt les points ligne par ligne ;
- utilise le même ensemble de points ;
- commence et se termine au centre ;
- utilise les mêmes modèles de temps et d’énergie.

### 3.7.5 Calcul des gains

Présenter les formules ou la méthode de calcul des gains de temps et d’énergie par rapport à la baseline.

### 3.7.6 Sorties du bloc

Présenter les résultats produits :

- profils ;
- trajectoires ;
- front de Pareto ;
- rapport de validation ;
- comparaison avec la baseline ;
- figures 2D et 3D.

---

# PARTIE C — PROTOCOLE D’ÉTUDE ET RÉSULTATS

## Section 3.8 — Protocole expérimental numérique

### 3.8.1 Configuration de référence

Présenter dans un tableau :

- plateforme `300 × 240 mm` ;
- masse opérationnelle `0,384 kg` ;
- hauteur de référence `0,45 m` ;
- tension minimale `1 N` ;
- tension maximale `58 N` ;
- vitesse maximale `0,045 m/s` ;
- accélération maximale `0,03 m/s²` ;
- stabilisation `2 s` par point.

### 3.8.2 Scénarios étudiés

Présenter les quatre configurations :

- zone sécurisée `7×7` ;
- zone sécurisée `9×9` ;
- zone étendue `7×7` ;
- zone étendue `9×9`.

### 3.8.3 Dimensionnement de NSGA-II

Conserver l’étude de l’ancien chapitre 3 : campagne de 50 exécutions et étude de robustesse avec plusieurs graines.

Présenter les réglages retenus :

- `7×7` : population de `500`, `2 000` générations ;
- `9×9` : population de `600`, `5 000` générations.

Expliquer que le choix tient compte de la qualité des solutions, de leur stabilité et du coût de calcul.

### 3.8.4 Indicateurs d’évaluation

Présenter :

- nombre de points générés et retenus ;
- taux de couverture ;
- temps de déplacement ;
- temps total avec stabilisation ;
- énergie ;
- nombre de solutions Pareto ;
- gains par rapport à la baseline ;
- tension maximale ;
- respect des contraintes cinématiques.

---

## Section 3.9 — Résultats du bloc 2 : espace de travail et faisabilité

Présenter :

- la grille générée ;
- la forme du WFW ;
- les points faisables ;
- les points rejetés ;
- la différence entre zone sécurisée et zone étendue.

Conclure que le mode zero-loss permet de retenir une zone dans laquelle tous les points nécessaires à l’acquisition sont faisables.

---

## Section 3.10 — Résultats du bloc 3 : optimisation des trajectoires

### 3.10.1 Résultats sur la grille `7×7` sécurisée

Présenter :

- `177,30 s` de déplacement optimisé ;
- `246,44 J` d’énergie ;
- `22,7 %` de gain de temps ;
- `27,6 %` de gain d’énergie ;
- comparaison avec la baseline `229,3 s` et `340,3 J`.

### 3.10.2 Résultats sur la grille `9×9` sécurisée

Présenter :

- `247,04 s` de déplacement optimisé ;
- `294,09 J` d’énergie ;
- `21,0 %` de gain de temps ;
- `28,7 %` de gain d’énergie ;
- comparaison avec la baseline `312,9 s` et `412,6 J`.

### 3.10.3 Analyse du front de Pareto

Présenter :

- solution minimisant le temps ;
- solution minimisant l’énergie ;
- solution de compromis ;
- différence entre les deux tailles de grille ;
- intérêt de conserver plusieurs solutions non dominées.

---

## Section 3.11 — Résultats du bloc 4 : validation et profils

Présenter :

- profils LSPB ;
- vitesse et accélération ;
- arrêts aux points de vue ;
- ajout des `2 s` de stabilisation ;
- retour au centre ;
- cohérence des trajectoires ;
- vérification des contraintes.

Présenter l’analyse des tensions :

- environ `3,8 N` au centre ;
- jusqu’à `35,7 N` vers les bords de la zone sécurisée ;
- limite maximale de `58 N` ;
- marge restante par rapport à cette limite.

---

## Section 3.12 — Effet de la couverture de la zone de travail

Reprendre l’analyse de l’ancien chapitre 3.

### Zone étendue `7×7`

Présenter :

- temps d’environ `191,83 s` ;
- énergie d’environ `314,93 J` ;
- gain de temps d’environ `22,9 %` ;
- gain d’énergie d’environ `25,5 %`.

### Zone étendue `9×9`

Présenter :

- `77` points retenus sur `81` ;
- temps d’environ `301,15 s` ;
- énergie d’environ `636,65 J` ;
- gain de temps d’environ `2,0 %` ;
- gain d’énergie d’environ `2,7 %`.

### Interprétation

Expliquer que l’extension de la zone :

- augmente les distances ;
- rapproche les points des limites du WFW ;
- augmente fortement l’énergie ;
- peut conduire au rejet de certains points ;
- réduit l’intérêt de l’optimisation pour la grille `9×9` étendue.

Conclure que la zone sécurisée est retenue pour la mission d’acquisition.

---

# PARTIE D — DISCUSSION, LIMITES ET CONCLUSION

## Section 3.13 — Discussion générale

La discussion doit interpréter les résultats en suivant les quatre blocs :

- le bloc 1 garantit la cohérence des données ;
- le bloc 2 garantit la faisabilité des positions ;
- le bloc 3 recherche le meilleur compromis temps–énergie ;
- le bloc 4 transforme les solutions en trajectoires vérifiées et mesurables.

Répondre clairement à la problématique :

- les points de la zone sécurisée sont tous atteignables ;
- les tensions restent sous la limite retenue ;
- l’optimisation réduit le temps et l’énergie face au zigzag ;
- la zone étendue est plus coûteuse, surtout pour la grille `9×9` ;
- le robot dispose donc d’une trajectoire numérique exploitable pour la mission d’imagerie.

## Section 3.14 — Limites

Conserver les limites de l’ancien chapitre 3 :

- câbles modélisés comme rigides ;
- absence de vent ;
- énergie quasi-statique ;
- modèle nominal des masses et des tensions ;
- robustesse testée sur un nombre limité de graines ;
- tensions non étudiées de manière complète dans les zones étendues ;
- validation expérimentale sur prototype encore nécessaire.

Présenter ces limites comme les conditions de validité des résultats, et non comme une remise en cause de l’étude numérique.

## Section 3.15 — Perspectives

Présenter :

- validation sur le prototype du SP1 ;
- prise en compte de l’élasticité des câbles ;
- prise en compte de l’affaissement pour les grandes longueurs ;
- intégration des vibrations et du vent ;
- retour des capteurs en temps réel ;
- replanification en cours de mission ;
- transmission des trajectoires au SP3 ;
- extension vers une commande expérimentale complète.

## Conclusion de la partie 3

La conclusion doit reprendre le parcours complet :

```text
Robot Tandem
    ↓
Modèle géométrique et mécanique
    ↓
Points de vue générés
    ↓
Points faisables selon le WFW
    ↓
Matrice des coûts
    ↓
Optimisation NSGA-II
    ↓
Profilage et validation
    ↓
Trajectoire de prise de vue
```

Elle doit rappeler que l’étude a permis :

- de caractériser le robot Tandem ;
- de relier son fonctionnement matériel à une chaîne logicielle ;
- de déterminer une zone sécurisée ;
- d’optimiser les trajectoires selon le temps et l’énergie ;
- d’obtenir des gains significatifs par rapport au zigzag ;
- de sélectionner une solution adaptée à l’acquisition d’images.

La conclusion doit ouvrir sur la conclusion générale du mémoire et sur l’exploitation des images par le SP3.

---

# Correspondance avec l’ancien chapitre 3

| Ancien chapitre 3 | Nouvelle organisation |
|---|---|
| Architecture et modélisation du robot | Partie A, sections 3.1 et 3.2 |
| Présentation du robot et de la charge utile | Section 3.1 |
| Modèle géométrique inverse et contraintes | Section 3.1, puis application dans le bloc 2 |
| WFW et singularité | Bloc 2, section 3.5 |
| Configuration de référence | Section 3.8.1 |
| Chaîne de traitement en quatre macro-blocs | Section 3.3, sans employer « macro-bloc » |
| Préparation des données | Bloc 1, section 3.4 |
| Génération de l’espace de travail | Bloc 2, section 3.5 |
| Optimisation des trajectoires | Bloc 3, section 3.6 |
| Validation de la trajectoire | Bloc 4, section 3.7 |
| Dimensionnement de NSGA-II | Section 3.8.3 |
| Vérification numérique | Section 3.11 |
| Résultats et analyse | Sections 3.9 à 3.12 |
| Discussion et perspectives | Sections 3.13 à 3.15 |

# Règles de rédaction à respecter

1. Présenter d’abord les deux architectures dans leur ensemble.
2. Ne pas découper la partie matérielle en blocs indépendants de composants.
3. Décomposer uniquement le fonctionnement séquentiel du robot en étapes.
4. Détailler les quatre blocs dans la partie logicielle.
5. Donner pour chaque bloc : son objectif, ses entrées, son traitement et ses sorties.
6. Ne pas répéter la théorie déjà développée dans les chapitres 1 et 2.
7. Conserver les résultats validés de l’ancien chapitre 3.
8. Séparer clairement la méthode, le protocole, les résultats et la discussion.
9. Expliquer chaque figure avant de l’insérer et interpréter son contenu après l’insertion.
10. Employer un style progressif, naturel et humain, en reliant chaque section à la question principale du mémoire.

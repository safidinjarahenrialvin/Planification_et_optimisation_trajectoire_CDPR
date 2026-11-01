# Référence scientifique — résultats du chapitre 3 du mémoire

## 1. Objet du document

Ce document rassemble les informations scientifiques de référence utilisées dans le chapitre 3 du mémoire consacré à l’étude du robot Tandem. Il constitue la base documentaire pour la description du système, l’explication du pipeline de planification et l’interprétation des résultats de simulation.

Les résultats présentés ici correspondent aux campagnes étudiées et validées dans le cadre du mémoire. Ils doivent être utilisés en priorité pour toute rédaction, présentation ou analyse portant sur le fonctionnement et les performances du sous-projet SP2.

Les autres documents du dépôt peuvent décrire des évolutions logicielles, des campagnes complémentaires ou des contrôles techniques. Ils ne remplacent pas les résultats de référence du mémoire sans décision explicite de mise à jour scientifique.

## 2. Système étudié

Le robot Tandem est un robot parallèle à câbles suspendu comportant huit câbles. La plateforme mobile est conçue en aluminium 6061-T6 et présente des dimensions de 300 × 240 mm. Elle porte le module de prise de vue et les éléments électroniques associés.

La masse à vide de la plateforme est estimée à 242 g. La charge utile représente environ 114 g. En ajoutant une marge de 8 % pour le câblage et les fixations, la masse opérationnelle retenue pour les calculs est de 384 g.

La mission consiste à déplacer la caméra au-dessus d’une parcelle de haricot nain afin d’acquérir des images à des points de vue prédéfinis. L’orientation de la plateforme est maintenue fixe et la planification porte principalement sur les translations dans l’espace.

## 3. Modèle mécanique et contraintes

Les huit câbles sont reliés à des ancrages fixes et à des points d’attache répartis sur la plateforme mobile. Les quatre premiers câbles sont associés aux ancrages supérieurs et les quatre suivants aux ancrages inférieurs.

Pour une position donnée de la plateforme, le modèle géométrique inverse calcule la longueur de chaque câble par une distance euclidienne entre l’ancrage fixe et l’attache mobile. La matrice de structure rassemble les directions des câbles et les moments produits autour de l’origine du repère.

La faisabilité mécanique est vérifiée dans l’espace de travail faisable en tension, ou WFW. Pour chaque pose, le programme recherche une distribution des tensions capable d’équilibrer le poids de la plateforme tout en respectant les bornes :

- tension minimale : `T_min = 1 N` ;
- tension maximale : `T_max = 58 N` ;
- masse opérationnelle : `0,384 kg` ;
- accélération de la pesanteur : `9,81 m/s²`.

La vérification prend en compte les six composantes statiques, c’est-à-dire les trois forces et les trois moments. La condition de faisabilité est formulée comme un problème de programmation linéaire. Le rang de la matrice de structure est également contrôlé afin d’écarter les configurations singulières.

La hauteur de référence de la plateforme est fixée à 0,45 m dans le repère utilisé pour la modélisation. Cette valeur correspond à une distance opérationnelle d’environ 0,30 m entre la caméra et les plants, pour une hauteur de plants de 0,35 m et un décalage du repère sol de 0,20 m.

Les contraintes cinématiques retenues sont :

- vitesse maximale : `0,045 m/s` ;
- accélération maximale : `0,03 m/s²` ;
- temps de stabilisation avant prise de vue : `2 s` par point.

## 4. Pipeline de traitement

La méthode développée est organisée en quatre macro-blocs.

### 4.1 Préparation des données

Cette étape centralise les paramètres géométriques, mécaniques, cinématiques et agronomiques. Elle construit également le modèle du robot et les éléments nécessaires au calcul des longueurs de câbles, des directions et de la matrice de structure.

### 4.2 Génération de l’espace de travail

Une grille de points de vue est générée au-dessus de la parcelle. Chaque point est ensuite soumis au test de faisabilité WFW. Les points qui ne respectent pas les limites opérationnelles ou qui ne permettent pas une distribution de tensions admissible sont rejetés.

Deux types de zones sont étudiés :

- une zone sécurisée, volontairement restreinte afin de conserver 100 % des points faisables ;
- une zone étendue, plus proche de la frontière du WFW et susceptible de contenir des points rejetés.

### 4.3 Optimisation des trajectoires

Une matrice de coûts est construite entre chaque paire de points retenus. Elle contient la distance, le temps de déplacement et l’énergie estimée.

Le temps de déplacement est calculé avec un profil LSPB. Ce profil peut être triangulaire lorsque la distance est courte ou trapézoïdal lorsque la plateforme atteint sa vitesse maximale.

L’énergie est estimée à partir du travail mécanique associé aux variations de longueur des câbles et aux tensions calculées le long du déplacement. Les tensions sont évaluées sur plusieurs sous-pas afin de mieux représenter l’évolution de la configuration entre deux points.

L’ordre de visite est ensuite optimisé avec NSGA-II. Chaque individu correspond à une permutation des points non centraux. Le centre de la grille est imposé comme point de départ et de retour. L’optimisation poursuit deux objectifs simultanément : réduire le temps total de déplacement et réduire l’énergie totale.

Trois solutions sont ensuite retenues pour l’analyse :

- `time_opt` : solution minimisant le temps ;
- `energy_opt` : solution minimisant l’énergie ;
- `compromise` : solution représentant un compromis entre les deux objectifs.

### 4.4 Validation et comparaison

Les trajectoires sélectionnées sont profilées avec la loi LSPB. Le validateur vérifie notamment la faisabilité des points, la cohérence des coûts, le respect de la vitesse maximale, l’arrêt aux waypoints et le retour au centre.

Les performances sont comparées à une baseline construite selon un balayage en zigzag. Cette baseline visite les points ligne par ligne et impose également un départ et un retour au centre. Les gains sont calculés à partir des mêmes points et des mêmes coûts afin de conserver une comparaison équitable.

## 5. Résultats sur la zone sécurisée

### 5.1 Grille 7 × 7

La grille 7 × 7 comporte 49 points, tous conservés après le filtrage WFW. La meilleure trajectoire optimisée présente les performances suivantes :

- temps de déplacement : `177,30 s` ;
- énergie consommée : `246,44 J` ;
- baseline zigzag : `229,3 s` et `340,3 J` ;
- gain de temps : `22,7 %` ;
- gain d’énergie : `27,6 %` ;
- temps total avec stabilisation : `275,3 s`.

Les trois trajectoires extraites du front de Pareto sont très proches et correspondent, dans cette configuration, à une solution pratiquement unique. Le parcours optimisé évite plusieurs retours inutiles du balayage en zigzag.

### 5.2 Grille 9 × 9

La grille 9 × 9 comporte 81 points, tous conservés dans la zone sécurisée. Les résultats de référence sont :

- temps de déplacement : `247,04 s` ;
- énergie consommée : `294,09 J` ;
- baseline zigzag : `312,9 s` et `412,6 J` ;
- gain de temps : `21,0 %` ;
- gain d’énergie : `28,7 %` ;
- temps total avec stabilisation : `409,0 s`.

La grille plus fine augmente le nombre de points à visiter, mais l’optimisation conserve un avantage net sur la baseline. Le front de Pareto présente de légères différences entre les solutions, ce qui permet d’étudier le compromis entre rapidité et consommation énergétique.

## 6. Résultats sur la zone étendue

L’extension de la zone de travail augmente les distances parcourues et rapproche la trajectoire des limites de faisabilité mécanique.

Pour la grille 7 × 7 étendue, les résultats obtenus sont :

- temps de déplacement : `191,83 s` ;
- énergie : environ `314,93 J` ;
- gain de temps : `22,9 %` ;
- gain d’énergie : `25,5 %`.

Pour la grille 9 × 9 étendue, 77 points sur 81 sont retenus après filtrage. Les résultats sont :

- temps de déplacement : `301,15 s` ;
- énergie : `636,65 J` ;
- gain de temps : `2,0 %` ;
- gain d’énergie : `2,7 %` par rapport à la baseline utilisée pour cette configuration.

La zone étendue entraîne donc une hausse du coût global. Pour la grille 7 × 7, elle augmente le temps d’environ 8,2 % et l’énergie d’environ 28 %. Pour la grille 9 × 9, l’augmentation atteint environ 22 % pour le temps et 116 % pour l’énergie. Ces résultats justifient le choix de la zone sécurisée comme zone de service privilégiée pour la mission d’acquisition d’images.

## 7. Dimensionnement de NSGA-II

Le dimensionnement de NSGA-II a été étudié par une campagne de 50 exécutions correspondant à deux tailles de grille, cinq tailles de population et cinq nombres de générations. Cette étude a été complétée par des essais de robustesse utilisant plusieurs graines aléatoires.

Pour la grille 7 × 7, la convergence est atteinte relativement rapidement. Le réglage retenu dans l’étude est une population de 500 individus et 2 000 générations.

Pour la grille 9 × 9, l’espace de recherche est plus grand et la convergence demande un budget plus important. Le réglage retenu est une population de 600 individus et 5 000 générations.

L’analyse de robustesse montre que l’augmentation de la population réduit la dispersion des résultats et améliore la reproductibilité des solutions. Les solutions obtenues avec les différentes graines se regroupent dans le plan temps–énergie, ce qui confirme la stabilité numérique de l’optimisation dans les configurations étudiées.

## 8. Analyse des tensions

La tension nécessaire varie selon la position de la plateforme. Elle est plus faible au centre de la zone de travail et augmente vers les bords, car les câbles doivent produire des efforts plus importants lorsque la plateforme s’éloigne des ancrages.

Dans la zone sécurisée 7 × 7, la tension maximale minimale varie approximativement de 3,8 N au centre à 35,7 N dans les zones périphériques. Cette valeur reste inférieure à la limite de 58 N, avec une marge d’environ 22,3 N au point le plus sollicité observé dans l’étude.

Cette analyse confirme que les trajectoires étudiées restent compatibles avec les bornes de tension retenues pour la simulation.

## 9. Statut des résultats

Les résultats de ce document sont les résultats de référence du chapitre 3 du mémoire. Ils doivent être utilisés pour expliquer :

- la configuration du robot Tandem ;
- la méthode de planification ;
- le choix de NSGA-II ;
- la comparaison avec la baseline zigzag ;
- l’effet de la taille de la grille ;
- l’effet de l’extension de la zone de travail ;
- la variation des tensions ;
- la justification du choix de la zone sécurisée.

Ces résultats proviennent de simulations utilisant un modèle de câbles rigides, une énergie quasi-statique et des conditions sans vent. Ils valident les choix méthodologiques et les performances numériques obtenues dans le cadre de l’étude. Ils ne doivent pas être confondus avec une validation expérimentale complète du prototype réel. La validation sur prototype constitue une étape ultérieure destinée à confirmer les hypothèses mécaniques et les performances en conditions réelles.

## 10. Documents associés

- `Rapport_memoire/chapters/chapitre3.tex` — chapitre 3 contenant l’étude détaillée et les figures de résultats.
- `src/config.py` — paramètres de configuration du modèle.
- `src/robot_model.py` — modèle géométrique du CDPR.
- `src/wfw.py` — calcul de l’espace de travail faisable.
- `src/cost_calculator.py` — calcul du temps et de l’énergie.
- `src/optimizer.py` — optimisation multiobjectif NSGA-II.
- `src/profiler.py` — génération des profils LSPB.
- `src/comparator.py` — comparaison avec la baseline.

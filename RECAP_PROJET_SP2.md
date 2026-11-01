# Récapitulatif du projet Tandem SP2

## 1. Finalité du projet

Le dépôt correspond au sous-projet SP2 du projet Tandem, réalisé dans le cadre de la collaboration ESP–ENIM Metz portée par Diasporeines Africa. L’objectif est de planifier et d’optimiser les trajectoires d’un robot parallèle à câbles suspendu, ou CDPR, destiné à acquérir des images de plants de haricot nain pour le suivi du stress hydrique.

Le SP2 se situe entre le SP1, qui fournit la géométrie et les caractéristiques mécaniques du robot, et le SP3, qui exploite les images et impose les besoins liés à la caméra, à la hauteur de prise de vue et à la stabilisation. La mission du SP2 est donc de transformer les contraintes mécaniques et agronomiques en trajectoires exécutables, tout en recherchant un compromis entre durée de déplacement et énergie consommée.

## 2. Système robotique étudié

Le robot est modélisé comme un CDPR à huit câbles. La plateforme mobile possède une orientation fixe et se déplace principalement en translation dans l’espace. Le modèle statique conserve cependant les six composantes d’effort et de moment : les trois forces et les trois moments doivent être équilibrés par les tensions des huit câbles.

Le modèle géométrique inverse calcule la longueur de chaque câble à partir de la position de la plateforme. Pour une pose donnée, le vecteur unitaire d’un câble est orienté de l’attache mobile vers l’ancrage fixe, conformément à la force réellement exercée par un câble en tension. La matrice de structure \(W\) rassemble les forces et les moments produits par les huit câbles.

La configuration courante du code utilise principalement une plateforme de 300 × 240 mm, une masse estimée d’environ 0,384 kg, une tension minimale de 1 N et une tension maximale de 58 N. La hauteur de référence calculée par la configuration est de 0,45 m dans le repère fixe. La vitesse maximale est de 0,045 m/s, l’accélération maximale de 0,03 m/s² et le temps de stabilisation de 2 s par point.

Ces valeurs ne doivent toutefois pas toutes être présentées comme des mesures expérimentales. Plusieurs sont des hypothèses de conception, des valeurs dérivées du dimensionnement ou des paramètres à confirmer avec le SP1 et le prototype.

## 3. Principe de faisabilité mécanique

L’espace de travail faisable en tension, appelé WFW, est déterminé pose par pose. Pour chaque position, le programme cherche une distribution de tensions comprise entre 1 N et 58 N et capable d’équilibrer le poids de la plateforme. Cette recherche est formulée comme un problème de programmation linéaire résolu avec le solveur HiGHS de SciPy.

Avant le problème linéaire, le code vérifie le rang de la matrice de structure. Une matrice de rang inférieur à six signale une singularité statique : la géométrie ne permet pas de contrôler les six composantes d’effort et de moment. Cette vérification explique notamment pourquoi une plateforme carrée peut devenir problématique, tandis que la géométrie rectangulaire 300 × 240 mm conserve un rang égal à six dans la configuration retenue.

Le pipeline génère ensuite une grille de points de vue, puis élimine les points qui sortent des limites opérationnelles ou qui ne sont pas faisables au regard du WFW. Le mode « zero-loss » restreint volontairement la zone de service afin d’obtenir une couverture complète des points retenus.

## 4. Chaîne algorithmique

Le projet est organisé en douze blocs scientifiques regroupés en quatre macro-blocs :

1. **Préparation des données** : validation de la configuration, construction du modèle robotique et calcul des primitives cinématiques.
2. **Génération de l’espace de travail** : création de la grille, test WFW et filtrage des points non faisables.
3. **Optimisation des trajectoires** : construction de la matrice des coûts puis recherche de l’ordre de visite.
4. **Validation de la trajectoire** : génération des profils temporels, contrôle des invariants et comparaison avec une trajectoire de référence.

Pour chaque paire de points, le calculateur évalue la distance, le temps de déplacement et l’énergie. Le temps utilise un profil LSPB, c’est-à-dire un profil à accélération constante, éventuellement suivi d’une phase à vitesse constante puis d’une phase de décélération. L’énergie est estimée par un travail mécanique quasi-statique. Les tensions sont calculées à des points milieux de sous-segments grâce à une résolution à norme minimale, avec une résolution SLSQP bornée lorsque la pseudo-inverse ne suffit pas.

L’optimisation utilise NSGA-II, une métaheuristique multiobjectif. Un individu représente une permutation des points non centraux. Le centre est imposé comme point de départ et de retour. Les deux objectifs sont la somme des temps de déplacement et la somme des énergies. Les opérateurs utilisés sont un échantillonnage par permutations, le croisement OX et la mutation par inversion. Les solutions infaisables sont pénalisées.

Le pipeline extrait ensuite trois stratégies : une solution minimisant le temps, une solution minimisant l’énergie et une solution de compromis. Les profils sont générés avec LSPB et doivent respecter la vitesse maximale, l’arrêt aux waypoints et la cohérence des temps cumulés.

## 5. Comparaison et validation

La référence principale est un balayage en zigzag lorsque la grille est complète. Lorsque des points sont rejetés et que la grille devient incomplète, le comparateur bascule vers une heuristique du plus proche voisin avec vérification des transitions faisables. Les gains sont calculés à nombre de points comparable, à partir de la même matrice de coûts.

Le projet possède une validation technique importante : tests unitaires et d’intégration, contrôle de la symétrie de la matrice de coûts, vérification de la non-dominance, contrôle des profils LSPB, contrôle de la faisabilité des trajectoires et comparaison inter-fichiers. La GUI Streamlit est séparée du moteur scientifique par une couche de services, ce qui évite d’introduire Streamlit dans les modules de calcul.

Le smoke test rapide documenté sur une grille 3 × 3 produit 9 points, 81 entrées de matrice de coûts et un front de Pareto exploitable. La référence historique rapporte 16 solutions Pareto brutes, quatre couples temps-énergie distincts et des gains minimaux de 6,15 % sur le temps et de 12,83 % sur l’énergie face à la baseline zigzag.

## 6. Résultats historiques déjà présents dans le chapitre 3

Le chapitre 3 actuel rapporte principalement une étude sur des grilles 7 × 7 et 9 × 9, avec comparaison entre une zone sécurisée et une zone étendue. Dans cette version historique, la zone sécurisée donne environ :

- grille 7 × 7 : 177,30 s et 246,44 J, contre 229,3 s et 340,3 J pour la baseline ;
- grille 9 × 9 : 247,04 s et 294,09 J, contre 312,9 s et 412,6 J pour la baseline.

Les gains annoncés sont respectivement de 22,7 % et 21,0 % sur le temps, puis de 27,6 % et 28,7 % sur l’énergie. L’étude conclut aussi que l’extension de la zone de travail augmente fortement le coût énergétique, surtout pour la grille 9 × 9.

Le chapitre explique également le dimensionnement historique de NSGA-II : 500 individus et 2 000 générations pour la grille 7 × 7, puis 600 individus et 5 000 générations pour la grille 9 × 9. Il présente une campagne de 50 exécutions ainsi que 12 essais de robustesse sur plusieurs graines.

## 7. Point critique pour la réécriture de la partie 3

Les informations du chapitre 3 ne sont pas entièrement alignées avec l’état documentaire le plus récent du dépôt. Le code et le protocole nominal actuels retiennent une grille 9 × 9 sur plateforme 300 × 240 mm, avec une population de 500, 1 500 générations et trois graines : 42, 43 et 44.

La campagne nominale récente a produit 81 points faisables pour chaque graine, mais seulement 2, 2 et 4 compromis Pareto distincts. Les gains minimaux restent positifs, mais ils varient selon la graine. L’analyse de stabilité donne une variabilité importante des fronts, sans recouvrement des enveloppes temporelles et énergétiques. Pour cette raison, le dépôt conserve le statut scientifique `NOT_VALIDATED` et demande une revue humaine avant toute conclusion générale.

Il faudra donc distinguer dans la nouvelle partie 3 :

- les résultats historiques utilisés pour illustrer le fonctionnement et les tendances ;
- les résultats nominaux récents utilisés pour qualifier la reproductibilité ;
- les contrôles numériques internes du logiciel ;
- la validation scientifique et physique, qui n’est pas encore acquise sur prototype.

Il faudra également éviter de présenter une simulation quasi-statique avec câbles rigides, sans vent et sans validation expérimentale comme une preuve définitive de performance. Les paramètres de masse, de tension maximale, de stabilisation et les hypothèses agronomiques doivent être présentés avec leur origine et leur niveau de validation.

## 8. Conclusion du récapitulatif

Le projet est un pipeline scientifique complet de planification de trajectoires pour un CDPR à huit câbles. Sa contribution principale consiste à relier la modélisation mécanique, le filtrage par espace de travail faisable, le calcul de coûts temps-énergie, l’optimisation multiobjectif NSGA-II, le profilage LSPB et la validation automatisée dans une chaîne reproductible.

La partie 3 du mémoire peut donc être structurée autour de trois idées : la modélisation concrète du robot Tandem, la réalisation du pipeline de calcul et l’analyse expérimentale des résultats. La priorité avant la rédaction finale est d’harmoniser les paramètres et les résultats avec la campagne nominale la plus récente, tout en conservant les anciennes campagnes comme résultats historiques clairement datés et qualifiés.

## Sources internes principales

- `README.md` : objectif, structure et exécution du projet.
- `src/config.py` : configuration courante et paramètres par défaut.
- `src/robot_model.py` : modèle géométrique et matrice de structure.
- `src/wfw.py` : test de faisabilité mécanique.
- `src/cost_calculator.py` : calcul des coûts temps-énergie.
- `src/optimizer.py` : optimisation NSGA-II.
- `src/profiler.py` : profils cinématiques LSPB.
- `src/comparator.py` : baseline et comparaison.
- `docs/RAPPORT_QUALIFICATION_NOMINALE_9X9_2026-10-28.md` : qualification nominale récente.
- `Rapport_memoire/chapters/chapitre3.tex` : version actuelle de la partie 3.

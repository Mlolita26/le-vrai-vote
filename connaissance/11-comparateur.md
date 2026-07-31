# Comparateur

Page `/comparer/`, générée par la fonction `page_comparer` de `ingestion/build_site.py`
(environ 600 lignes de JavaScript produit). Le script est **inline dans la page**, sans
dépendance, et lit `../data.json`.

Point de méthode : tout le comportement décrit ici est écrit en Python, sous forme de
chaînes de caractères JavaScript. Modifier le comparateur signifie modifier
`build_site.py`, jamais `web/comparer/index.html`, qui est régénéré.

## De 2 à 6 candidats, deux rendus différents

Le comparateur accepte de 2 à `MAX_CANDIDATS` candidats, soit 6. Deux sélecteurs sont
présents d'emblée et ne peuvent pas être retirés ; les suivants s'ajoutent par un bouton et
portent chacun une croix de suppression.

La fonction `rendre()` choisit entre deux rendus :

| Nombre | Fonction | Rendu |
|---|---|---|
| 2 | `rendreDeux(a, b)` | Deux bannières côte à côte, plus les barres de posture sur les axes budget |
| 3 et plus | `rendreMulti(slugs)` | Regroupement par position, dans le même format que la page d'un vote |

**Pourquoi deux rendus.** Un tableau à colonnes reste lisible à deux candidats et devient
illisible à cinq. Au-delà de deux, la question change aussi de nature : on ne demande plus
« sont-ils d'accord » mais « qui est d'accord avec qui ». Le regroupement par position
répond à la seconde, en listant sous chaque position les candidats qui l'ont adoptée.

## Le pourcentage disparaît au-delà de deux candidats

À deux candidats, `texteChiffres` affiche un pourcentage de positions identiques sur les
votes comparables. À trois et plus, `texteChiffresMulti` affiche un décompte
« unanimes sur comparables », **sans pourcentage**.

Ce n'est pas un oubli. Un pourcentage global entre cinq candidats ne veut rien dire : il
mêle des accords qui ne concernent pas les mêmes personnes, et invite à une lecture fausse.
Le décompte des votes où tous sont unanimes est, lui, interprétable.

Le même choix s'applique aux puces de thème et de sous-section : elles portent un
pourcentage à deux candidats, un décompte au-delà.

## Ce qui est comparé, et sur quelle base

Un vote est **comparable** quand au moins deux des candidats sélectionnés ont une position
connaissable, au sens « au plus précis » décrit dans `10-etats-daffichage.md` : vote
personnel, sinon équivalent au Sénat, sinon position du parti clairement étiquetée.

Deux filtres coexistent :

- **« Votes comparables » contre « Tous les votes clés »** : le premier masque les votes où
  la comparaison n'a pas de sens ;
- **les puces de thème**, plus des **sous-filtres** pour les thèmes qui en ont
  (`SOUS_SECTIONS_THEME` et les axes budget). Le sous-filtre ne s'affiche que lorsque son
  thème est le filtre actif, sinon il encombrerait la vue d'ensemble.

Détail d'affichage qui a demandé une décision : dans un thème à sous-sections, les votes
n'appartenant à aucune sous-section sont rendus **en premier**, avant les sections
étiquetées. L'ordre inverse laissait croire que tout le thème portait sur la première
sous-section.

## Les barres de posture, à deux candidats seulement

Sur le thème Budget, les votes sont regroupés par **axes** (`AXES_BUDGET`), chacun formulé
comme une question avec deux sens explicites, du type « qui taxe qui ». Une barre indique la
posture d'un candidat sur l'axe, calculée par `postureCompute` et rendue par `postureBar`.

Garde-fou : la barre est **masquée sous `MIN_POSTURE_VOTES`**, soit 3 votes. Une posture
déduite d'un seul vote serait une caricature.

## Détails qui ont demandé une correction

Ces points ont été des bugs réels ; ils sont documentés ici pour ne pas être défaits par
inadvertance.

- **Pas de doublon de sélection.** `majOptionsDisponibles` désactive, dans chaque sélecteur,
  les candidats déjà choisis ailleurs. Elle doit être appelée non seulement au changement
  d'un sélecteur, mais aussi **à la création d'un nouveau slot** : sans cela, un sélecteur
  fraîchement ajouté permettait de choisir un candidat déjà pris.
- **Le résultat du scrutin est affiché** sur chaque carte, à droite du titre, comme sur les
  fiches candidat. Il vient du champ `resultat` de `data.json`.
- **Le filtre par thème remonte en haut de page**, et non en haut de la barre de filtres,
  faute de quoi le lecteur ne voyait pas que le contenu avait changé.
- **L'en-tête du mode multi ne porte pas de décompte global** : il avait été retiré car
  jugé confus, les décomptes par thème suffisant.

## Pré-remplissage par URL

Le comparateur accepte `?a=slug&b=slug&c=slug` jusqu'à six lettres. C'est ce qui permet aux
fiches candidat de proposer « comparer avec » en un clic. Les slugs inconnus sont ignorés
silencieusement.

## Les données consommées

`web/data.json`, écrit par `build_site.py`, contient les candidats, les thèmes, les votes
(avec leur résumé, leur sens, leur résultat, leur axe) et la matrice `positions`. Chaque
entrée de `positions` porte, par candidat et par vote : la position personnelle, celle du
parti, le nom du parti, et les justifications éventuelles.

Ce fichier existe parce que le comparateur et la Communauté fonctionnent **entièrement côté
navigateur** : il n'y a pas de serveur pour répondre à une requête de comparaison.

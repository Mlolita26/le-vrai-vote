# États d'affichage

Pour chaque couple candidat et vote clé, le site affiche toujours quelque chose. Une case
vide serait ambiguë : le lecteur ne saurait pas si le candidat s'est abstenu, n'était pas
là, ou si la donnée manque.

## Les quatre états

| État | Signification |
|---|---|
| `pour`, `contre`, `abstention`, `absent`, `non_votant` | Position réellement importée |
| `non_concerne` | La personne n'était pas en poste dans cette chambre à la date du scrutin |
| `indisponible` | La personne n'a jamais été parlementaire : aucun vote ne peut exister |
| `a_importer` | Elle était en poste, mais la position n'est pas encore chargée |

La distinction entre `indisponible` et `a_importer` est essentielle. La première dit « il
n'y a rien à trouver », la seconde admet « nous ne l'avons pas encore ». Confondre les deux
reviendrait soit à masquer une lacune, soit à reprocher à un candidat de ne pas avoir voté
alors qu'il ne pouvait pas.

`non_votant` mérite une mention à part : à l'Assemblée, cela signifie **présent sans
prendre part au vote**, par exemple quand on préside la séance. Ce n'est pas une absence, et
le site ne les confond pas.

## Où c'est calculé : en SQL, pas en Python

La logique vit dans la vue `couverture`, définie dans `db/schema.sql`. C'est le point le
plus utile de ce document : chercher dans `build_site.py` pourquoi un candidat est « non
concerné » est une perte de temps. Le générateur lit cette vue, il ne la recalcule pas.

La vue fait un `CROSS JOIN` entre toutes les personnes et tous les votes clés, puis
applique une cascade de conditions dans cet ordre :

1. **Aucun mandat parlementaire** (député, sénateur ou eurodéputé), jamais : `indisponible`.
2. **Aucun mandat de la bonne chambre actif à la date du scrutin** : `non_concerne`. La
   correspondance est explicite : un scrutin de l'Assemblée exige un mandat de député, un
   scrutin européen un mandat d'eurodéputé, et un scrutin du **Congrès accepte les deux**,
   députés comme sénateurs, puisqu'ils y votent ensemble.
3. **Une position existe** dans `positions_vote` : c'est elle qui s'affiche.
4. Sinon : `a_importer`.

L'ordre compte. Un ancien eurodéputé sans mandat français ne sera jamais `indisponible`,
mais `non_concerne` sur les votes de l'Assemblée : il a bien été parlementaire, simplement
pas dans cette chambre.

## L'absence est déduite, pas publiée

L'Assemblée nationale **ne publie jamais la liste des absents**. Un parlementaire est donc
compté « absent (déduit) » quand son mandat était actif à la date du scrutin et qu'il
n'apparaît sur aucune liste de votants.

Cette déduction est **désactivée** dans trois cas, pour ne pas produire une fausse absence,
qui serait une accusation implicite :

- quand les totaux officiels annoncés ne correspondent pas aux listes nominatives, ce qui
  arrive avec les mises au point publiées après coup ;
- sur les **motions de censure**, où seules les voix « pour » sont enregistrées : ne pas
  voter est la façon normale de ne pas soutenir la censure ;
- sur les scrutins anciens à **publication partielle** (position du groupe et dissidents
  seulement) : on importe ce qui est explicite et on ne déduit rien.

Le site affiche « absent (déduit) » et non « absent », précisément parce que c'est une
inférence.

## La position affichée : « au plus précis »

Un candidat peut n'avoir aucun vote personnel sur un vote clé tout en ayant une position
connaissable. Le site applique alors une cascade, dans `build_site.py` :

1. **le vote personnel** s'il existe ;
2. sinon **l'équivalent au Sénat**, si le vote clé en déclare un ;
3. sinon **la position majoritaire de son groupe** pour cette législature, affichée avec
   l'étiquette explicite « position du parti » ;
4. sinon « aucune donnée ».

Une position de parti n'est jamais présentée comme un vote personnel. C'est ce qui permet de
comparer des candidats qui n'ont pas siégé aux mêmes moments, sans leur attribuer des votes
qu'ils n'ont pas émis.

## La pastille de couverture d'un candidat

À l'échelle d'une fiche, les historiques sont très inégaux : un député cumule des milliers
de scrutins, un maire aucun. Une pastille annonce d'emblée ce qu'on peut montrer :

| Pastille | Signification |
|---|---|
| votes disponibles | La personne a effectivement voté, au moins `SEUIL_COMPARABLE` fois |
| couverture partielle | Ses mandats sortent de la période couverte, ou relèvent d'une chambre pas encore intégrée |
| positions déclaratives | Elle n'a jamais siégé : ses positions ne peuvent venir que de déclarations publiques |

`SEUIL_COMPARABLE` vaut 30 dans `build_site.py` : c'est le nombre minimal de votes exprimés
pour entrer dans le comparateur. En dessous, un pourcentage de similitude n'aurait pas de
sens statistique.

## Ce que cette mécanique protège

Elle existe pour une raison politique, pas technique. Sans elle, le site paraîtrait sévère
envers les parlementaires, simplement parce qu'ils sont les seuls dont tout est traçable.
Rendre l'asymétrie visible est ce qui rend la comparaison honnête.

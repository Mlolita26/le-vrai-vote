# Sources de données

Les données parlementaires publiques sont sous Licence ouverte : réutilisation libre avec
mention de la source. L'export HowTheyVote est sous ODbL. Chaque fait enregistré pointe
une ligne de la table `sources`, avec l'URL et la date de collecte.

## Les sources réellement utilisées

| Source | Ce qu'elle fournit | Format | Où c'est archivé |
|---|---|---|---|
| data.assemblee-nationale.fr | Scrutins de l'Assemblée et du Congrès, positions individuelles, décomptes par groupe, référentiel des acteurs et mandats | JSON dans des zips | Coffre, `dump_manuel_2026-07-23` |
| senat.fr | Scrutins publics du Sénat et positions | HTML scrapé | `data/dumps/senat/<date>/` |
| data.europarl.europa.eu (API v2) | Votes par appel nominal du Parlement européen, 2019 et après | JSON-LD | `data/dumps/pe/<date>/` |
| HowTheyVote.eu | Votes du Parlement européen déjà structurés, avec les décomptes par délégation | CSV | Coffre, `Howtheyvote/export/` |
| HATVP | Déclarations d'intérêts, mandats et fonctions non parlementaires | PDF | Coffre, `HATVP/` |
| Wikimedia Commons | Portraits libres et leurs crédits | JPEG via API | `web/photos/` |
| Presse et communiqués | Justifications de vote, candidatures | HTML | URL citée dans `sources` |

## Le piège de chaque source

Cette section est la raison d'être du document. Chaque piège ci-dessous a été rencontré,
et la plupart sont désormais gérés dans le code.

### Assemblée nationale

- **Clés au pluriel ou au singulier.** Les séances ordinaires utilisent `pours`, `contres`,
  `abstentions` ; le Congrès de Versailles utilise le singulier. Les deux formes sont
  traitées dans `ingestion/assemblee/parse_scrutins.py`.
- **Deux préfixes d'identifiant.** `VTANR` désigne un scrutin de l'Assemblée, `VTCGR` un
  scrutin du Congrès. Le préfixe détermine la chambre, et donc qui est concerné : au
  Congrès, députés et sénateurs votent ensemble.
- **Deux conditionnements selon la législature.** Jusqu'à la 14e, un fichier agrégé
  contient tous les scrutins ; à partir de la 15e, un fichier par scrutin.
- **Publication partielle sur d'anciens scrutins.** Quand le champ
  `modePublicationDesVotes` vaut `DecompteDissidentsPositionGroupe`, seules la position du
  groupe et les voix dissidentes sont publiées. Dans ce cas on importe les positions
  explicites et **on ne déduit rien** : ni « a suivi son groupe », ni absence.
- **Les absences ne sont jamais publiées.** Elles sont déduites : mandat actif à la date du
  scrutin et aucune mention dans le fichier. Cette déduction est désactivée dans deux cas,
  pour éviter une fausse absence : quand les totaux annoncés ne correspondent pas aux
  listes nominatives (mises au point publiées après coup), et sur les motions de censure.
- **Motions de censure.** Seules les voix « pour » sont enregistrées : ne pas voter est la
  façon de ne pas soutenir la censure. Aucune absence ne peut en être déduite, et le sens
  du vote est inversé par rapport à un vote ordinaire.
- **Un numéro de scrutin n'est pas un numéro d'amendement.** Confusion facile et déjà
  faite : le scrutin n°3106 n'a aucun rapport avec l'amendement II-3106.

### Sénat

- Les scrutins sont **scrapés depuis des pages HTML**, page par page, avec un cache local.
- La position se lit sur le **texte nettoyé** : le HTML brut est trompeur.
- Le matricule d'un sénateur peut apparaître avec une casse variable.
- Aucun vote clé n'a pour scrutin principal un scrutin du Sénat : les scrutins sénatoriaux
  servent d'équivalent (champ `scrutin_senat_id` de `votes_cles`), affiché comme « au
  Sénat » sur la fiche du candidat.

### Parlement européen

- **Le nominatif n'existe pas avant 2019** dans l'API officielle. Les mandats européens de
  Marine Le Pen, Jean-Luc Mélenchon et Florian Philippot restent donc sans positions : ce
  n'est pas un oubli, c'est une limite de la source, et l'affichage le dit.
- **HowTheyVote ne couvre que la 9e législature et les suivantes.** Un vote antérieur n'y
  figure pas, même s'il a bien eu lieu par appel nominal.
- **Le piège le plus coûteux : `is_main`.** Avant d'ajouter un identifiant à la liste
  `VOTES_CLES_PE` de `ingestion/pe/import_votes_cles_pe.py`, vérifier dans `votes.csv` que
  `display_title` correspond au sujet **et** que `is_main` vaut `True`. Deux votes clés ont
  longtemps pointé des lignes `is_main=False`, c'est-à-dire des amendements : l'un était un
  amendement rejeté sur la Libye, affiché sur le site comme un vote sur les logiciels
  espions.
- **Le champ `result` est souvent vide**, en particulier pour les positions de première
  lecture. Ce n'est pas une anomalie. Le site affiche alors le décompte réel sans qualifier
  l'issue, qui n'est pas sourcée.
- **Un identifiant de député européen à ne pas confondre** : celui de Jordan Bardella est
  131580, et non 197819.
- Les intentions de vote déclarées après coup (`had_voter_intended`) ne sont pas comptées.

### HATVP

- Les déclarations sont en PDF, transcrites à la main, avec une **précision parfois
  mensuelle** seulement pour les dates de mandat.
- Pour les mandats parlementaires, le référentiel de l'Assemblée a **préséance** sur la
  HATVP : il est plus précis et plus fiable.

### Presse

Utilisée uniquement pour les justifications de vote et les candidatures, jamais pour une
position de vote. Règles dans `09-justifications-de-vote.md`. Le point essentiel : la
source doit contenir la citation exacte que l'on publie, ce qui n'allait pas de soi (une
citation authentique pointait un article qui ne la contenait pas).

## Sources écartées, et pourquoi

- **NosDéputés.fr, Datan, CIVIX, Eutyn** : pratiques pour prototyper, mais ce sont des
  intermédiaires. La production s'appuie sur les sources officielles, pour pouvoir prouver
  que les données brutes sont un import reproductible.
- **Wikipédia** : point de départ acceptable pour trouver une piste, jamais source finale.
- **Bases judiciaires en open data** : pseudonymisées, leur croisement serait illégal.

## Ce qui est automatisable

Environ 80 % de la base peut être alimentée automatiquement : identités, mandats,
scrutins, positions, absences déduites. Les 20 % restants font la valeur du site et
demandent un travail humain : sélection et rédaction des votes clés, justifications,
recoupement des candidatures.

La collecte de masse suppose un accès réseau ouvert vers les domaines de données
publiques. Les dumps sont horodatés et archivés **avant** transformation, pour que tout
import soit reproductible et vérifiable après coup.

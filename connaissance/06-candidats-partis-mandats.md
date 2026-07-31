# Candidats, partis et mandats

## Qui est suivi, et pourquoi ce n'est pas une liste officielle

Le site suit **24 candidatures** pour 26 personnes en base. Il n'existe **aucune liste
officielle de candidats avant la validation des parrainages par le Conseil
constitutionnel**, prévue en mars 2027. Le site ne peut donc que recenser des déclarations
publiques, ce qui a deux conséquences :

- le statut d'une candidature est `declaree` ou `primaire`, jamais `officielle`. Le schéma
  réserve cette dernière valeur au moment où elle aura un sens ;
- chaque candidature porte une source de presse datée, et les dates issues d'un simple
  agrégateur sont marquées « à re-sourcer » dans le champ de détail.

Fichier : `ingestion/seed_candidatures.py`. La liste `CANDIDATS` contient des tuples
`(nom, prénom, slug, statut, date, detail, source)`.

**Le parti n'a pas de colonne dédiée** : il est en tête du champ `detail`, et
`build_site.py` l'extrait par une expression régulière qui coupe au premier séparateur
(parenthèse, virgule, deux-points). Cette fragilité a déjà cassé une fois : quand les
tirets cadratins ont été retirés du projet, le séparateur historique a disparu et
l'extraction est devenue incorrecte jusqu'à ce que la regex soit adaptée.

## Deux cas particuliers à connaître

**Jordan Bardella est en base sans être candidat.** Marine Le Pen s'est déclarée le
7 juillet 2026, après l'arrêt d'appel la concernant. Bardella n'a donc pas de ligne dans
`candidatures`, mais ses données restent en base à titre historique : c'est un eurodéputé
dont les votes sont importés, et il servait de référence avant la déclaration de Le Pen.

**Clémentine Autain a retiré sa candidature** le 11 juillet 2026, après l'échec de la
primaire de la gauche unitaire. Sa ligne de candidature a été retirée, ses données
personnelles conservées, sur le même principe que Bardella. Elle apparaît donc encore dans
certaines justifications de vote historiques.

Le principe général : **retirer une candidature ne retire pas une personne**. Les votes
qu'elle a émis restent des faits.

## Les mandats et la question de la préséance

`mandats` est alimentée par quatre scripts, ce qui pose un problème d'autorité quand deux
sources se contredisent sur les mêmes dates.

| Script | Ce qu'il apporte | Précision |
|---|---|---|
| `assemblee/parse_amo.py` | Mandats de député et sénateur | au jour |
| `seed_mandats_europeens.py` | Mandats européens avant 2019, saisis à la main | au jour |
| `pe/seed_pe_ids.py` | Mandats européens 2019 et après, dérivés des adhésions de groupe | au jour |
| `seed_identites.py` | Fonctions non parlementaires issues des déclarations HATVP | souvent au mois |

**Règle de préséance : le référentiel de l'Assemblée l'emporte** sur la HATVP pour les
mandats parlementaires. Il est plus précis et fait autorité. La HATVP sert pour ce que
l'Assemblée ne couvre pas : fonctions ministérielles, mandats locaux.

Deux garde-fous dans `parse_amo.py` : le script s'arrête s'il détecte une homonymie ou une
divergence de date de naissance, plutôt que d'apparier au hasard. L'appariement se fait sur
nom, prénom et date de naissance, jamais sur le seul nom.

Pourquoi les mandats comptent autant : l'**absence à un scrutin est déduite** d'un mandat
actif à la date du vote. Un mandat mal daté produit donc de fausses absences, ce qui est
une accusation implicite. C'est la raison pour laquelle les mandats doivent être complets
avant tout import de positions.

## Le rattachement candidat vers groupe parlementaire

Table `groupes_reference`, remplie par `ingestion/seed_groupes_reference.py` (liste
`RATTACHEMENTS` : slug, législature, abrégé du groupe, justification).

À quoi ça sert : quand un candidat n'a pas voté personnellement sur un vote clé, le site
peut afficher **la position de son parti**, clairement étiquetée comme telle. C'est ce qui
permet de comparer des candidats qui n'ont pas siégé aux mêmes moments.

Trois règles :

1. **Seuls les rattachements nets sont saisis.** L'absence de ligne signifie « pas de
   groupe rattachable », et s'affiche comme telle plutôt que d'être devinée.
2. **Le rattachement est par législature**, parce que les groupes changent de nom et
   d'existence. Renaissance a siégé successivement sous « La République en Marche », puis
   « Renaissance », puis « Ensemble pour la République ».
3. **Un parti sans groupe constitué n'a pas de rattachement.** Le Rassemblement national
   avec huit députés en 2017 était sous le seuil de quinze requis : il n'y a donc aucun
   décompte de groupe pour lui sur la législature 2017-2022. Horizons n'existait pas avant
   octobre 2021. Ces absences sont dites explicitement à l'écran.

Sont volontairement absents de la liste : les partis sans groupe (Lutte ouvrière, UPR,
Debout la France, Révolution permanente, NPA, Équinoxe, Nouvelle Énergie, La Convention,
Nous France, Les Patriotes, UDB) et les cas ambigus (Génération écologie n'est pas Les
Écologistes ; les mouvements récents distincts de LFI).

## La position du parti au Parlement européen

Le rattachement y est plus délicat, parce qu'un groupe européen mêle plusieurs partis
nationaux. Le choix fait : on ne prétend jamais isoler « le vote d'un parti », on affiche
le décompte de la **délégation française** du groupe où siège le parti du candidat, avec un
libellé qui le dit (« Délégation française du groupe Renew Europe (Renaissance, MoDem,
Horizons) »).

Ce libellé a d'ailleurs été corrigé : il utilisait auparavant une formulation qui laissait
croire à un vote du parti seul.

## Portraits et crédits

`ingestion/telecharge_photos.py` récupère les portraits depuis Wikimedia Commons,
uniquement des images libres, et écrit `web/photos/credits.json`. Les crédits sont affichés
sur la page Méthode, ce qui est une obligation de licence et non une politesse.

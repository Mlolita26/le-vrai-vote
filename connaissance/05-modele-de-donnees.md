# Modèle de données

Schéma complet : `db/schema.sql`. Base : `data/levraivote.sqlite`, régénérable.

## Trois idées structurantes

1. **Le pivot est `personnes`, pas « candidats ».** Un même individu est successivement
   député, ministre, puis candidat. Une seule fiche identité, à laquelle s'accrochent tous
   ses rôles datés via `mandats`. C'est ce qui permet de répondre à « était-il en poste ce
   jour-là ».
2. **Tout fait est daté et sourcé.** Chaque enregistrement pointe une ligne de `sources`,
   avec l'URL et la date de collecte.
3. **`votes_cles` ne duplique pas `scrutins`.** C'est une couche éditoriale posée au-dessus
   d'un scrutin réel : le scrutin reste intouchable, le vote clé porte le titre, le résumé
   et le thème.

## La séparation brut contre éditorial

C'est la règle la plus structurante du projet. Elle permet, en cas de contestation, de
prouver que les données factuelles sont un import automatique reproductible, et que
l'appréciation humaine est cantonnée à des tables identifiées.

**Tables brutes**, miroir des sources, jamais éditées à la main :

| Table | Contenu | Volume actuel |
|---|---|---|
| `personnes` | Identité pivot, avec `slug` | 26 |
| `mandats` | Rôles datés, avec la granularité de la date (`precision`) | 58 |
| `identifiants_externes` | Identifiant Assemblée, député européen, matricule Sénat | |
| `scrutins` | Un scrutin par ligne, `uid_officiel` unique | 22 082 |
| `positions_vote` | Position d'une personne sur un scrutin | 120 892 |
| `presence` | Présence ou absence, dérivée des scrutins | |
| `positions_groupes` | Décomptes officiels par groupe sur les votes clés | 1 599 |

`positions_groupes` est bien une table **brute** malgré sa place dans le fichier de schéma :
ce sont des décomptes officiels extraits des mêmes dumps, pas une appréciation.

**Tables éditoriales**, curation humaine, chacune alimentée par un script `seed_*` :

| Table | Contenu | Volume actuel |
|---|---|---|
| `thematiques` | Les thèmes de premier niveau | 15 |
| `votes_cles` | Titre, résumé neutre, sens du vote, thème, axe budget | 165 |
| `candidatures` | Candidatures déclarées ou en primaire, sourcées | 24 |
| `groupes_reference` | Rattachement candidat vers groupe, par législature | 50 |
| `nuances` | Justification d'une personne sur un vote | 18 |
| `justifications_groupes` | Justification d'un groupe sur un vote | 129 |
| `programmes` | Site de campagne officiel vérifié | 21 |
| `affaires_judiciaires` | Volet judiciaire, non affiché actuellement | 0 |

**Table mixte** : `declarations` (intérêts, patrimoine, discours, programme).

**Transverse** : `sources` (212 lignes) et `imports_journal`, qui trace chaque import avec
le script, le nombre de lignes et l'horodatage.

À savoir : `programmes` est créée par `ingestion/seed_programmes.py` et **ne figure pas dans
`db/schema.sql`**. Une base reconstruite depuis le seul schéma ne l'aura pas jusqu'à
l'exécution de ce script.

## Les points de vigilance du schéma

- **L'unicité d'un scrutin n'est pas son numéro.** La numérotation de l'Assemblée repart à 1
  à chaque législature, et le Congrès a la sienne. La clé fiable est `uid_officiel`
  (`VTANR5L17V3690`, `PE-HTV-161873`, `SEN-2023-208`). C'est aussi cet identifiant qui sert
  de clé à la fonctionnalité Communauté.
- **`non_votant` n'est pas une absence.** À l'Assemblée, « non votant » signifie présent
  sans prendre part au vote, par exemple quand on préside la séance. L'absence, elle, est
  déduite et jamais publiée par la source.
- **`mandats.precision`** indique si la date vient au jour, au mois ou à l'année : les
  déclarations HATVP ne donnent souvent que le mois.
- **`mandats.source_id` est obligatoire**, contrairement à ce que prévoyait la note de
  conception initiale, en application de la règle « tout fait porte une source ».
- **`affaires_judiciaires` porte une contrainte SQL** qui impose le drapeau de présomption
  d'innocence hors décision définitive. La règle de prudence est dans le schéma, pas
  seulement dans la doctrine.
- **`votes_cles.scrutin_senat_id`** permet de rattacher un scrutin sénatorial équivalent à
  un vote clé de l'Assemblée, affiché comme « au Sénat » sur la fiche.

## Les deux vues calculées

Elles sont dans `db/schema.sql` et constituent l'essentiel de la logique métier. Le
générateur les lit, il ne recalcule pas.

**`couverture`** produit un état pour chaque couple personne et vote clé, par un
`CROSS JOIN` suivi d'une cascade de conditions. C'est le cœur de l'affichage à quatre
états, détaillé dans `10-etats-daffichage.md`. Point important : cette logique est en SQL,
pas en Python. Chercher dans `build_site.py` pourquoi un candidat est « non concerné » est
une perte de temps.

**`justifications`** réunit `nuances` et `justifications_groupes` sous un concept unique.
C'est le seul objet que le site interroge pour afficher une explication de vote, ce qui
garantit que les deux niveaux sont traités de la même façon. Voir
`09-justifications-de-vote.md`.

## Ce que la structure interdit

La matrice ci-dessous justifie l'affichage à quatre états et **interdit de combler un vide
par une supposition**.

| Type de candidat | Positions de vote | Mandats | Déclarations |
|---|---|---|---|
| Parlementaire actuel ou ancien | complet sur la période | complet | complet |
| Eurodéputé depuis 2019 | votes européens seulement | complet | complet |
| Eurodéputé avant 2019 | **aucun** (source sans nominatif) | complet | complet |
| Ministre non parlementaire | aucun | via déclarations | complet |
| Élu local | aucun | selon les seuils | selon les seuils |
| Société civile | aucun | aucun | candidature seulement |

Un candidat sans position n'est pas un candidat sans opinion : c'est un candidat dont les
positions ne sont pas traçables par un vote. La différence doit rester lisible à l'écran.

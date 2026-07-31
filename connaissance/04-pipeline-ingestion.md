# Pipeline d'ingestion

Tous les scripts vivent dans `ingestion/`. Ils s'exécutent à la main, en local : il n'y a
pas de planificateur, et l'intégration continue ne fait que publier `web/`.

## L'ordre d'exécution

Cet ordre n'est écrit nulle part dans le code : il se déduit des gardes que les scripts
posent les uns sur les autres. Le voici explicitement, pour une reconstruction complète
depuis une base vide.

```
1.  init_db.py                          crée la base et le schéma
2.  seed_identites.py                   identités socle, premiers mandats
3.  seed_candidatures.py                les candidatures 2027
4.  assemblee/parse_amo.py              identifiants Assemblée et mandats précis
5.  assemblee/parse_scrutins.py         tous les scrutins AN et Congrès, positions
6.  seed_mandats_europeens.py           mandats européens antérieurs à 2019
    pe/seed_pe_ids.py                   identifiants européens et mandats 2019+
7.  senat/collecte_senat.py             scrutins du Sénat
8.  pe/import_votes_cles_pe.py          votes clés européens
    pe/collecte_pe.py                   (optionnel) collecte de masse européenne
9.  seed_votes_cles.py                  la couche éditoriale : thèmes et votes clés
10. assemblee/parse_positions_groupes.py décomptes par groupe des votes clés
11. seed_groupes_reference.py           rattachement candidat vers groupe
12. seed_justifications_groupes.py      justifications par groupe
13. seed_nuances.py                     justifications individuelles
14. seed_programmes.py                  sites de campagne
    telecharge_photos.py                portraits et crédits
15. validate.py                         contrôles
16. build_site.py                       génération du site
```

Les dépendances qui imposent cet ordre :

- `parse_amo.py` doit précéder `parse_scrutins.py`, qui exige les identifiants de
  l'Assemblée pour relier un vote à une personne ;
- les mandats doivent être complets **avant** tout import de positions, parce que l'absence
  est déduite d'un mandat actif à la date du scrutin ;
- `seed_votes_cles.py` exige que les scrutins visés soient déjà importés, et refuse de
  tourner sinon ;
- `parse_positions_groupes.py` ne traite que les scrutins **promus votes clés** : il faut
  donc le relancer après tout ajout de vote clé, sinon le nouveau vote n'affichera aucune
  position de groupe ;
- `seed_justifications_groupes.py` refuse une justification pour un groupe qui n'a pas de
  décompte, donc il passe après.

## Les scripts un par un

| Script | Rôle | Écrit dans | Relançable |
|---|---|---|---|
| `init_db.py` | Applique `db/schema.sql` | tout (DDL) | oui |
| `seed_identites.py` | Identités socle, mandats issus des déclarations HATVP | `personnes`, `mandats`, `declarations`, `identifiants_externes` | **non** |
| `seed_candidatures.py` | Candidatures déclarées ou en primaire | `candidatures` | **non** |
| `assemblee/parse_amo.py` | Appariement nom vers identifiant Assemblée, mandats datés au jour | `identifiants_externes`, `mandats`, `personnes.naissance` | oui |
| `assemblee/parse_scrutins.py` | Scrutins AN et Congrès, positions, absences déduites | `scrutins`, `positions_vote`, `presence` | **non** |
| `seed_mandats_europeens.py` | Mandats européens avant 2019, saisis à la main | `mandats` | oui |
| `pe/seed_pe_ids.py` | Identifiants européens, mandats dérivés des groupes | `identifiants_externes`, `mandats` | oui |
| `senat/collecte_senat.py` | Scrutins publics du Sénat | `scrutins`, `positions_vote`, `presence` | oui |
| `pe/import_votes_cles_pe.py` | Votes clés européens et décomptes par délégation | `scrutins`, `positions_vote`, `positions_groupes` | oui |
| `pe/collecte_pe.py` | Collecte de masse européenne via l'API officielle | idem | oui |
| `seed_votes_cles.py` | Thèmes, votes clés, sens du vote, axes budget | `thematiques`, `votes_cles` | oui |
| `assemblee/parse_positions_groupes.py` | Décomptes par groupe des votes clés | `positions_groupes` | oui |
| `seed_groupes_reference.py` | Rattachement candidat vers groupe par législature | `groupes_reference` | oui |
| `seed_justifications_groupes.py` | Justifications de vote par groupe | `justifications_groupes` | oui |
| `seed_nuances.py` | Justifications individuelles | `nuances` | oui |
| `seed_programmes.py` | Sites de campagne vérifiés | `programmes` | oui |
| `telecharge_photos.py` | Portraits et crédits | `web/photos/` | oui |
| `validate.py` | Contrôles de cohérence | rien (lecture) | oui |
| `build_site.py` | Génère le site | `web/` | oui |

## Idempotence : le point qui a déjà coûté cher

Trois comportements différents cohabitent, et la confusion entre eux est une source
d'erreur réelle.

**Les scripts relançables qui corrigent.** `seed_votes_cles.py` et
`seed_justifications_groupes.py` mettent à jour les lignes existantes et suppriment celles
qui ont disparu de la liste. Ce sont eux qu'il faut relancer après une correction
éditoriale.

**Les scripts relançables qui n'écrasent pas.** `seed_nuances.py` et `seed_programmes.py`
sautent une ligne déjà présente. Conséquence : **corriger le texte dans le script ne suffit
pas**, la base garde l'ancienne version. C'est exactement le piège rencontré pendant
l'audit : une justification corrigée dans le fichier restait fausse sur le site. Il faut
alors appliquer la mise à jour explicitement, ou supprimer la ligne avant de relancer.

**Les scripts qui refusent de tourner deux fois.** `seed_identites.py` et
`seed_candidatures.py` s'arrêtent si leur table n'est pas vide, pour éviter les doublons
d'identité. Modifier une candidature suppose donc soit une mise à jour ciblée, soit une
reconstruction complète.

`parse_scrutins.py` est un cas à part : il n'a pas de garde mais insère sans tolérance aux
doublons, et échouera sur une contrainte d'unicité au second passage. Pour réimporter, il
faut repartir d'une base neuve.

## Après une correction éditoriale, la séquence utile

C'est la séquence à connaître par cœur, celle qu'on utilise dix fois par jour :

```
python3 ingestion/seed_votes_cles.py                    si un vote clé a changé
python3 ingestion/assemblee/parse_positions_groupes.py  si un vote clé a été ajouté
python3 ingestion/seed_justifications_groupes.py        si une justification a changé
PYTHONIOENCODING=utf-8 python3 ingestion/validate.py    contrôles
python3 ingestion/build_site.py                         régénère web/
```

Puis un commit de `web/` déclenche la publication. Voir `13-generation-et-deploiement.md`.

## Pourquoi `PYTHONIOENCODING=utf-8`

Sur Windows, la console utilise une page de code qui ne sait pas écrire certains caractères
(flèches, tirets typographiques). Sans cette variable, `validate.py` s'interrompt sur une
erreur d'encodage **avant** d'avoir affiché ses résultats, ce qui donne l'illusion d'un
plantage du script alors que les données vont bien. Le script a été rendu tolérant, mais la
variable reste la façon la plus sûre de lancer n'importe quel script du projet.

# CLAUDE.md — contexte projet pour Claude Code

Ce fichier oriente tout travail automatisé sur le dépôt. Lis-le entièrement avant d'écrire du code.

## Ce qu'est ce projet

Une plateforme web de transparence pour la présidentielle française de 2027. Elle affiche, par candidat, ses votes réels au Parlement, sa présence, son parcours et un volet judiciaire, à partir de données publiques officielles. Objectif : aider les citoyens à décider sur des faits vérifiables, pas sur des promesses.

Consulte `README.md` pour la vision et `docs/` pour le détail (méthode, arborescence, modèle de données, acquisition, stack).

## Règles absolues (ne jamais transgresser)

Ce projet manipule des données sur des personnes réelles dans un contexte électoral. Les règles suivantes priment sur toute considération de rapidité ou de complétude.

1. **Ne jamais inventer une donnée.** Aucune position de vote, aucun taux de présence, aucune affaire judiciaire ne doit être saisie « de mémoire » ou générée. Toute valeur affichée provient d'un import vérifiable ou d'une saisie éditoriale sourcée. En l'absence de donnée, utiliser l'état « à importer » ou « indisponible » — jamais une valeur plausible.

2. **Séparer le brut de l'éditorial.** Les tables brutes (`scrutins`, `positions_vote`, `presence`, `mandats`…) sont un miroir automatique des sources officielles et ne sont jamais éditées à la main. Les tables éditoriales (`votes_cles`, `thematiques`, résumés, `affaires_judiciaires`) sont curées par des humains. Ne jamais mélanger les deux flux.

3. **Tout fait porte une source.** Chaque enregistrement de fait référence une entrée `sources` (URL officielle + date de collecte). Un fait sans source ne s'affiche pas.

4. **Neutralité de la langue.** Résumés et libellés décrivent, ne jugent pas. « Autorise la réintroduction de… », pas « loi controversée qui… ». « A voté contre », pas « s'est opposé à ». Cette règle s'applique au code (noms de variables, textes d'UI) comme au contenu.

5. **Volet judiciaire : manuel et prudent.** Aucune automatisation. Distinguer condamnation définitive et procédure en cours. Toute procédure en cours porte la mention de présomption d'innocence. Ne pas croiser automatiquement des bases judiciaires (les décisions en open data sont pseudonymisées — ce croisement est illégal et techniquement bloqué par conception).

6. **Affichage à trois états.** Pour chaque candidat et chaque vote clé, calculer et afficher : *position connue* / *non concerné* (pas en poste à la date du scrutin) / *indisponible* (n'a jamais été parlementaire). Ne jamais laisser une case vide et ambiguë.

## Conventions de code

- Langue de l'interface et du contenu : **français**.
- Sentence case dans l'UI ; pas de majuscules décoratives.
- Les libellés d'état sont centralisés (une seule source de vérité pour « pour / contre / abstention / absent / non concerné / indisponible »).
- L'information n'est jamais codée par la seule couleur (accessibilité RGAA) : toujours un texte dans le badge.
- Mobile-first : la majorité du trafic viendra de liens partagés sur mobile. Tester d'abord en ~380 px de large.
- URLs lisibles et stables : `/candidats/{slug}`, `/themes/{slug}`, `/votes/{slug}`, `/comparer/{a}-vs-{b}`.

## Garde-fous techniques

- La collecte de masse nécessite un accès réseau ouvert vers les domaines de données publiques (data.assemblee-nationale.fr, data.senat.fr, PE, HATVP, data.gouv.fr, PISTE). Les scripts d'ingestion tournent côté serveur, pas dans un bac à sable restreint.
- Toujours horodater et archiver les dumps bruts avant transformation (traçabilité et reproductibilité).
- Prévoir une supervision : alerter si une source change de format ou si un import échoue.

## Ce qui reste à faire (voir README pour l'état complet)

- Finaliser la grille de sélection des votes clés (critères objectifs, publiés).
- Implémenter le pipeline de collecte (commencer par l'Assemblée nationale).
- Brancher le front sur une vraie API alimentée par la base.

## Contexte local de ce dépôt (ajouté le 23 juillet 2026)

Ce dépôt contient le code : `db/` (schéma SQLite), `ingestion/` (pipelines Python par source), `web/` (front Next.js statique), `docs/` et `prototype/` (références). Architecture retenue : SQLite locale → export JSON → site 100 % statique sur GitHub Pages ; migration PostgreSQL possible plus tard.

Les données brutes déjà téléchargées, les tableurs d'analyse hérités et la feuille de route (`FEUILLE_DE_ROUTE.md`, `ETAT_DES_LIEUX.md`) vivent dans le coffre OneDrive : `C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles`. Pièges connus : les CSV Civix AN de ce coffre sont des échantillons de 100 lignes (jamais les importer en base) ; les captures Datan.fr servent au recoupement, pas de source ; le MEP ID de Bardella est 131580 (pas 197819) ; HowTheyVote ne couvre pas les votes de Mélenchon.

## Quand un choix est ambigu

Par défaut, privilégier la prudence : afficher moins mais sûr, sourcer davantage, et exposer les limites de la donnée plutôt que de les masquer. La crédibilité du site est sa seule valeur ; une seule donnée fausse sur une personne réelle peut la détruire.

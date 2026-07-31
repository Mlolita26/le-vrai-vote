# CLAUDE.md — contexte projet pour Claude Code

Ce fichier oriente tout travail automatisé sur le dépôt. Lis-le entièrement avant d'écrire du code.

## Ce qu'est ce projet

Une plateforme web de transparence pour la présidentielle française de 2027. Elle affiche, par candidat, ses votes réels au Parlement, sa présence, son parcours et un volet judiciaire, à partir de données publiques officielles. Objectif : aider les citoyens à décider sur des faits vérifiables, pas sur des promesses.

Consulte `README.md` pour la vision et **`connaissance/00-index.md`** pour tout le reste : ce dossier rassemble la documentation du projet (sources, pipeline, modèle de données, règles éditoriales, contrôles qualité, journal des problèmes rencontrés). Sa table « par où entrer » indique quoi lire selon la tâche.

## Règles absolues (ne jamais transgresser)

Ce projet manipule des données sur des personnes réelles dans un contexte électoral. Les règles suivantes priment sur toute considération de rapidité ou de complétude.

1. **Ne jamais inventer une donnée.** Aucune position de vote, aucun taux de présence, aucune affaire judiciaire ne doit être saisie « de mémoire » ou générée. Toute valeur affichée provient d'un import vérifiable ou d'une saisie éditoriale sourcée. En l'absence de donnée, utiliser l'état « à importer » ou « indisponible » — jamais une valeur plausible.

2. **Séparer le brut de l'éditorial.** Les tables brutes (`scrutins`, `positions_vote`, `presence`, `mandats`…) sont un miroir automatique des sources officielles et ne sont jamais éditées à la main. Les tables éditoriales (`votes_cles`, `thematiques`, résumés, `affaires_judiciaires`) sont curées par des humains. Ne jamais mélanger les deux flux.

3. **Tout fait porte une source.** Chaque enregistrement de fait référence une entrée `sources` (URL officielle + date de collecte). Un fait sans source ne s'affiche pas.

4. **Neutralité de la langue.** Résumés et libellés décrivent, ne jugent pas. « Autorise la réintroduction de… », pas « loi controversée qui… ». « A voté contre », pas « s'est opposé à ». Cette règle s'applique au code (noms de variables, textes d'UI) comme au contenu.

5. **Volet judiciaire : manuel et prudent.** Aucune automatisation. Distinguer condamnation définitive et procédure en cours. Toute procédure en cours porte la mention de présomption d'innocence. Ne pas croiser automatiquement des bases judiciaires (les décisions en open data sont pseudonymisées — ce croisement est illégal et techniquement bloqué par conception).

6. **Affichage à quatre états.** Pour chaque candidat et chaque vote clé, calculer et afficher : *position connue* / *non concerné* (pas en poste à la date du scrutin) / *indisponible* (n'a jamais été parlementaire) / *à importer* (source pas encore collectée). Ne jamais laisser une case vide et ambiguë. Ces états sont calculés par la vue SQL `couverture`, pas en Python : voir `connaissance/10-etats-daffichage.md`.

7. **Décrire le texte voté, pas l'intention.** Une description de vote clé porte sur le texte tel qu'il a été voté ce jour-là : ni le projet initial, ni l'exposé des motifs de l'amendement, ni la loi finale. Lire le texte adopté (« T.A. n° … ») ou le dispositif de l'amendement, jamais le dossier de presse. **Avant d'ajouter ou de modifier un vote clé, lire `connaissance/08-rediger-et-verifier-un-vote.md`** : l'audit du 30 juillet 2026 a trouvé une erreur de fond dans 71 des 165 descriptions, et ce document liste les pièges avec les cas réels.

## Conventions de code

- Langue de l'interface et du contenu : **français**.
- Sentence case dans l'UI ; pas de majuscules décoratives.
- Les libellés d'état sont centralisés (une seule source de vérité pour « pour / contre / abstention / absent / non concerné / indisponible »).
- L'information n'est jamais codée par la seule couleur (accessibilité RGAA) : toujours un texte dans le badge.
- Mobile-first : la majorité du trafic viendra de liens partagés sur mobile. Tester d'abord en ~380 px de large.
- URLs lisibles et stables : `/candidats/{slug}`, `/votes/{slug}`, `/comparer/`, `/communaute/`, `/methode/`. Les pages par thème ont été retirées en juillet 2026 (le filtrage par thème vit dans le comparateur et les fiches) : leurs fonctions de génération subsistent en code mort, signalé comme tel.

## Garde-fous techniques

- La collecte de masse nécessite un accès réseau ouvert vers les domaines de données publiques (data.assemblee-nationale.fr, data.senat.fr, PE, HATVP, data.gouv.fr, PISTE). Les scripts d'ingestion tournent côté serveur, pas dans un bac à sable restreint.
- Toujours horodater et archiver les dumps bruts avant transformation (traçabilité et reproductibilité).
- Prévoir une supervision : alerter si une source change de format ou si un import échoue.
- **Choix des scrutins du Parlement européen** (`VOTES_CLES_PE` dans `ingestion/pe/import_votes_cles_pe.py`) : avant d'ajouter un identifiant, vérifier dans `votes.csv` de l'export HowTheyVote que `display_title` correspond bien au sujet **et** que `is_main` vaut `True`. Deux votes clés ont longtemps pointé sur des lignes `is_main=False`, dont un amendement sur la Libye affiché comme un vote sur les logiciels espions.
- **Un rapport de recherche n'est pas une source.** Les chiffres, citations et unités issus d'une recherche préalable doivent être relus sur le document primaire avant publication : deux erreurs de l'audit de juillet 2026 venaient de rapports détaillés mais inexacts sur un détail.

## Où en est le projet (voir README pour l'état complet)

Le site est **en production sur `levraivote.fr`** : 165 votes clés, 15 thèmes, 25 candidats, l'Assemblée, le Sénat et le Parlement européen importés, la grille de sélection appliquée et publiée, le comparateur et la fonctionnalité Communauté en service.

## Contexte local de ce dépôt (ajouté le 23 juillet 2026, revu le 31 juillet 2026)

Ce dépôt contient le code : `db/` (schéma SQLite), `ingestion/` (pipelines Python par source et générateur du site), `web/` (le site publié), `connaissance/` (la documentation), `visualisations/` (cartes et posts), `worker/` (API Communauté) et `prototype/` (référence de design).

Architecture réelle, à ne pas confondre avec ce qui avait été envisagé au départ : SQLite locale, puis `ingestion/build_site.py` qui écrit du **HTML, CSS et JavaScript vanille** dans `web/`, publié tel quel par GitHub Pages. Il n'y a **ni Next.js, ni React, ni étape de compilation, ni serveur applicatif, ni base de données en production**. La génération tourne en local et `web/` est commité : un commit qui modifie un script d'ingestion sans régénérer `web/` ne change rien au site en ligne.

Les données brutes déjà téléchargées, les tableurs d'analyse hérités et la feuille de route (`FEUILLE_DE_ROUTE.md`, `ETAT_DES_LIEUX.md`) vivent dans le coffre OneDrive : `C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles`. Pièges connus : les CSV Civix AN de ce coffre sont des échantillons de 100 lignes (jamais les importer en base) ; les captures Datan.fr servent au recoupement, pas de source ; le MEP ID de Bardella est 131580 (pas 197819) ; HowTheyVote ne couvre pas les votes de Mélenchon.

## Quand un choix est ambigu

Par défaut, privilégier la prudence : afficher moins mais sûr, sourcer davantage, et exposer les limites de la donnée plutôt que de les masquer. La crédibilité du site est sa seule valeur ; une seule donnée fausse sur une personne réelle peut la détruire.

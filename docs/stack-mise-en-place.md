# Stack technique et mise en place

> Proposition de départ, à adapter. L'essentiel est de respecter les règles de `CLAUDE.md`, pas le choix précis des outils.

## Stack proposée

**Frontend** : Next.js (React) + TypeScript. Rendu côté serveur pour le SEO (les gens chercheront « X vote immigration » sur Google) et pour des URLs partageables. Le prototype existant (`prototype/transparence-2027.jsx`) donne la forme des composants et la structure des données attendues par l'UI.

**Base de données** : PostgreSQL. Schéma dans `docs/modele-donnees.md`. Un ORM (Prisma ou Drizzle) pour les migrations et le typage.

**Ingestion** : service séparé (Python ou Node) qui télécharge, normalise et charge les sources officielles. Planifié par cron ou GitHub Actions. Écrit dans les tables brutes uniquement.

**API** : endpoints en lecture servant le front (candidats, thèmes, votes clés, comparaison, couverture). Jamais d'écriture depuis le front.

**Hébergement** : un serveur avec accès réseau ouvert vers les domaines de données publiques (voir contrainte plus bas).

## Structure de dépôt suggérée

```
/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── concept-methode.md
│   ├── arborescence.md
│   ├── modele-donnees.md
│   ├── acquisition-donnees.md
│   └── stack-mise-en-place.md
├── web/                # front Next.js
│   ├── app/            # routes : /candidats, /themes, /comparer, /methode
│   ├── components/     # badge position, ligne vote clé, carte indicateur…
│   └── lib/            # client API, libellés d'état centralisés
├── ingestion/          # scripts de collecte
│   ├── assemblee/
│   ├── senat/
│   ├── parlement-europeen/
│   ├── hatvp/
│   └── rne/
├── db/                 # schéma, migrations, seeds
└── prototype/          # prototype React de référence
```

## Ordre de mise en place

1. **Socle** : dépôt, PostgreSQL, schéma + migrations, planificateur, stockage des dumps bruts horodatés.
2. **Identités et mandats** : peupler `personnes` + `mandats` (Wikidata + état civil AN/Sénat + RNE + JO). Sans ce socle daté, rien ne se relie.
3. **Données parlementaires brutes** : `scrutins`, `positions_vote`, `presence`. Commencer par l'Assemblée (format le mieux documenté), puis Sénat, puis PE.
4. **Déclarations** : HATVP + discours (vie-publique).
5. **Couche éditoriale** : `thematiques`, `votes_cles` avec résumés et sources — nécessite la grille de sélection finalisée.
6. **Volet judiciaire** : saisie manuelle sourcée, relecture juridique.
7. **Couche calculée** : `couverture` + agrégats de présence.
8. **Front connecté** : remplacer les données de démonstration du prototype par l'API réelle.

## Contrainte réseau importante

La collecte de masse s'exécute sur un serveur disposant d'un accès ouvert vers les domaines de données publiques (data.assemblee-nationale.fr, data.senat.fr, Parlement européen, hatvp.fr, data.gouv.fr, API PISTE). Un environnement de développement restreint (sandbox) ne peut pas télécharger ces jeux de données ; les scripts s'y écrivent et s'y testent sur des fichiers d'exemple, mais s'exécutent en production dans l'environnement ouvert.

## Qualité et supervision

- Horodater et archiver chaque dump brut avant transformation (reproductibilité).
- Tests de non-régression sur le format des sources : alerter si une source change de schéma.
- Journaliser chaque import (source, date, nombre de lignes) pour prouver la traçabilité.
- Afficher publiquement la date de dernière mise à jour par catégorie de données.

## Rappels transverses (issus de CLAUDE.md)

- Jamais de donnée inventée ; états « à importer » / « indisponible » à défaut.
- Brut jamais édité à la main ; éditorial séparé.
- Tout fait sourcé.
- Trois états d'affichage calculés, jamais de vide ambigu.
- Volet judiciaire manuel, prudent, présomption d'innocence.
- Mobile-first, URLs stables, RGAA, neutralité de la langue.

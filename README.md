# Le Vrai Vote, plateforme de transparence électorale (présidentielle 2027)

## 🔗 Voir le site

**➡️ [levraivote.fr](https://levraivote.fr)**

En ligne : les candidatures recensées et sourcées, une fiche par candidat (mandats officiels,
positions de vote, présence), 165 votes clés répartis sur 15 thèmes, un comparateur de 2 à 6
candidats, et la méthode. Le site est publié depuis `web/` par GitHub Actions à chaque push
touchant `web/**`.

## L'idée en une phrase

Un site qui montre, pour chaque candidat à la présidentielle 2027, **ce qu'il a réellement voté** — pas seulement ce qu'il promet — avec pour chaque position le lien vers le scrutin officiel, afin que chacun se forge son opinion sur des faits vérifiables.

## Ce que le site donne à voir

- **Qui sont les candidats** : parti, parcours, mandats successifs.
- **Ce qu'ils ont voté** : positions sur des « votes clés » regroupés par thème, chacun accompagné d'un résumé neutre de la loi et d'un lien vers le scrutin officiel.
- **Leur assiduité** : présence aux scrutins et en commission, comparée à la médiane de l'assemblée.
- **Leur parcours** : biographie, déclarations d'intérêts/patrimoine (HATVP).
- **Le volet judiciaire** : uniquement des faits publics et sourcés, dans le respect de la présomption d'innocence.

## Les quatre principes non négociables

1. **Tout est sourcé.** Chaque fait renvoie à un document officiel vérifiable en un clic.
2. **Neutralité.** Méthodologie publique et identique pour tous ; aucune éditorialisation (« a voté contre », jamais « a trahi »).
3. **Honnêteté sur les manques.** Quatre états d'affichage (position connue, non concerné, indisponible, à importer), jamais de vide ambigu ni de supposition.
4. **Prudence juridique.** Présomption d'innocence, RGPD, diffamation traités avec le plus grand soin.

## Contenu de ce dépôt

| Chemin | Rôle |
|---|---|
| `CLAUDE.md` | Les sept règles absolues du projet, **à lire en premier** |
| `connaissance/` | **Toute la documentation.** Entrer par `connaissance/00-index.md`, dont la table indique quoi lire selon la tâche |
| `db/schema.sql` | Schéma SQLite, dont la vue `couverture` qui calcule les états d'affichage |
| `ingestion/` | Pipelines de collecte par source, et `build_site.py` qui génère le site |
| `web/` | Le site publié, généré. Ne pas éditer à la main |
| `visualisations/` | Cartes, posts Instagram, éléments de marque |
| `worker/` | API Cloudflare de la fonctionnalité Communauté |
| `prototype/transparence-2027.jsx` | Référence de design (données de démonstration) |

Deux documents de `connaissance/` méritent d'être signalés à part :
`08-rediger-et-verifier-un-vote.md`, obligatoire avant de toucher à un vote clé, et
`15-journal-des-problemes.md`, qui recense les erreurs déjà commises et leur cause.

## État d'avancement

Au 31 juillet 2026.

- [x] Concept, méthodologie et architecture définis
- [x] Schéma de données (`db/schema.sql`), états d'affichage calculés par la vue `couverture`
- [x] **22 082 scrutins** importés : 18 310 à l'Assemblée nationale, 3 734 au Sénat, 37 au Parlement européen, 1 au Congrès
- [x] **120 892 positions de vote** nominatives
- [x] Identités et mandats officiels des candidats suivis (AMO30, précision au jour)
- [x] 26 personnes suivies, 24 candidatures recensées et sourcées (18 déclarées, 6 en primaire)
- [x] Grille de sélection des votes clés appliquée et publiée sur la page Méthode
- [x] Couche éditoriale : **165 votes clés** sur **15 thèmes**, chacun avec un résumé sourcé et le sens de « pour » et « contre »
- [x] Fiches candidat, comparateur de 2 à 6 candidats, fonctionnalité Communauté
- [x] Domaine propre `levraivote.fr` en HTTPS, sitemap et référencement
- [x] Audit éditorial des 165 descriptions de votes clés (juillet 2026)
- [ ] Présence et assiduité affichées sur les fiches
- [ ] Volet judiciaire (manuel, sourcé, présomption d'innocence)
- [ ] Déclarations d'intérêts et de patrimoine (HATVP) exploitées

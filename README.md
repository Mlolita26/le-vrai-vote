# Le Vrai Vote — plateforme de transparence électorale (présidentielle 2027)

> Nom de code provisoire. À choisir en évitant tout terme suggérant un parti pris.

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
3. **Honnêteté sur les manques.** Trois états d'affichage — position connue / non concerné / indisponible — jamais de vide ambigu ni de supposition.
4. **Prudence juridique.** Présomption d'innocence, RGPD, diffamation traités avec le plus grand soin.

## Contenu de ce dépôt

| Fichier | Rôle |
|---|---|
| `CLAUDE.md` | Contexte et règles pour Claude Code — **à lire en premier** |
| `docs/concept-methode.md` | L'idée détaillée et la méthodologie |
| `docs/arborescence.md` | Structure du site, pages, composants, URLs |
| `docs/modele-donnees.md` | Schéma de base de données |
| `docs/acquisition-donnees.md` | Sources et pipeline de collecte |
| `docs/stack-mise-en-place.md` | Stack technique et étapes de démarrage |
| `prototype/transparence-2027.jsx` | Prototype React fonctionnel (données de démonstration) |

## État d'avancement

- [x] Concept, méthodologie, architecture définis
- [x] Schéma de données conçu
- [x] Prototype d'interface fonctionnel (données fictives puis roster réel)
- [ ] Grille de sélection des votes clés finalisée
- [ ] Pipeline de collecte implémenté
- [ ] Base de données peuplée depuis les sources officielles
- [ ] Front connecté à une vraie API

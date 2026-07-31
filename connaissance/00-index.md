# Connaissances du projet Le Vrai Vote

Ce dossier rassemble tout ce qu'il faut savoir pour travailler sur ce site sans le
casser. Il remplace l'ancien dossier `docs/`, dont une partie décrivait une
architecture qui n'a jamais existé.

Les documents sont numérotés dans l'ordre où ils prennent sens pour quelqu'un qui
découvre le projet. Personne n'a besoin de tout lire : la table ci-dessous indique où
entrer selon la tâche.

## Les sept règles absolues

Elles figurent aussi dans `CLAUDE.md`, à la racine du dépôt, et priment sur toute
considération de rapidité ou de complétude.

1. **Ne jamais inventer une donnée.** En l'absence de donnée, afficher « à importer » ou
   « indisponible », jamais une valeur plausible.
2. **Séparer le brut de l'éditorial.** Les tables brutes sont un miroir automatique des
   sources ; les tables éditoriales sont curées à la main. Les deux flux ne se mélangent
   jamais.
3. **Tout fait porte une source.** Un fait sans source ne s'affiche pas.
4. **Neutralité de la langue.** Décrire, ne pas juger.
5. **Volet judiciaire manuel et prudent.** Aucune automatisation, présomption
   d'innocence systématique.
6. **Affichage à quatre états.** Position connue, non concerné, indisponible, à
   importer. Jamais de case vide et ambiguë.
7. **Décrire le texte voté, pas l'intention.** Ni le projet initial, ni l'exposé des
   motifs, ni la loi finale.

## Par où entrer

| Ce que vous voulez faire | Lire |
|---|---|
| Comprendre le projet | `01-but-et-principes.md` |
| Retrouver un fichier, savoir où vit quoi | `02-architecture-et-fichiers.md` |
| Ajouter ou mettre à jour des données | `03-sources-de-donnees.md`, puis `04-pipeline-ingestion.md` |
| Comprendre la base | `05-modele-de-donnees.md` |
| Travailler sur un candidat, un parti, un mandat | `06-candidats-partis-mandats.md` |
| **Ajouter un vote clé** | `07-choisir-un-vote-cle.md` puis **`08-rediger-et-verifier-un-vote.md`** (le plus important) |
| Ajouter une justification de vote | `09-justifications-de-vote.md` |
| Comprendre « non concerné », « indisponible » | `10-etats-daffichage.md` |
| Toucher au comparateur | `11-comparateur.md` |
| Toucher à la fonctionnalité Communauté | `12-communaute.md` |
| Générer et publier le site | `13-generation-et-deploiement.md` |
| Vérifier que rien n'est cassé | `14-controles-qualite.md` |
| Comprendre une erreur déjà rencontrée | `15-journal-des-problemes.md` |
| **Faire un post Instagram sur un thème** | `16-post-instagram.md`, puis `08-rediger-et-verifier-un-vote.md` |

## Les documents

| Fichier | Sujet |
|---|---|
| `01-but-et-principes.md` | Pourquoi ce site existe, ce qu'il refuse de faire |
| `02-architecture-et-fichiers.md` | Arborescence réelle, ce qui est versionné, le coffre OneDrive |
| `03-sources-de-donnees.md` | Les sources utilisées et le piège propre à chacune |
| `04-pipeline-ingestion.md` | Les scripts, leur ordre, lesquels sont relançables |
| `05-modele-de-donnees.md` | Tables brutes contre éditoriales, vues calculées |
| `06-candidats-partis-mandats.md` | Qui est suivi, comment les mandats et groupes sont établis |
| `07-choisir-un-vote-cle.md` | La grille de sélection et ce qui a été écarté |
| `08-rediger-et-verifier-un-vote.md` | Comment décrire un vote sans se tromper |
| `09-justifications-de-vote.md` | Justification d'une personne contre celle d'un groupe |
| `10-etats-daffichage.md` | Les quatre états et où ils sont calculés |
| `11-comparateur.md` | Comparaison de 2 à 6 candidats |
| `12-communaute.md` | « M'a aidé à décider », Worker Cloudflare, D1 |
| `13-generation-et-deploiement.md` | `build_site.py`, GitHub Pages, domaine, référencement |
| `14-controles-qualite.md` | `validate.py` et les vérifications manuelles |
| `15-journal-des-problemes.md` | Les erreurs réelles, leur cause, leur correction |
| `16-post-instagram.md` | Où prendre la matière d'un post et quoi revérifier avant de publier |

## Tenir ce dossier à jour

Ces documents ne valent que s'ils restent vrais. Deux réflexes :

- quand une décision de fond est prise (un vote écarté, une source disqualifiée, un
  piège découvert), l'écrire ici, pas seulement dans un message de commit ;
- quand un problème est corrigé, l'ajouter à `15-journal-des-problemes.md` avec sa
  cause. Un problème compris est un problème qui ne revient pas.

Convention de rédaction : pas de tiret cadratin, par cohérence avec la règle appliquée
au contenu du site.

# Architecture et fichiers

## Le principe technique en une phrase

Une base SQLite locale est alimentée par des scripts Python, puis un générateur produit un
site entièrement statique dans `web/`, que GitHub Pages publie tel quel. Il n'y a **aucun
serveur applicatif** et **aucune base de données en production**.

```
sources officielles  ->  scripts d'ingestion  ->  SQLite locale  ->  build_site.py  ->  web/  ->  GitHub Pages
```

Seule exception : la fonctionnalité Communauté, qui a besoin d'écrire, s'appuie sur un
Worker Cloudflare et une base D1 (voir `12-communaute.md`).

Attention à un contresens possible : le site n'est pas une application Next.js. Une
ancienne note de projet décrivait une stack Next.js avec PostgreSQL et une API ; elle n'a
jamais été réalisée. `web/` contient du HTML, du CSS et du JavaScript sans dépendance,
écrits par `ingestion/build_site.py`.

## Arborescence du dépôt

Dépôt local : `C:\Users\mlolita\dev\le-vrai-vote`. Distant : `github.com/Mlolita26/le-vrai-vote`.

| Chemin | Rôle | Versionné |
|---|---|---|
| `ingestion/` | Tous les scripts Python : collecte, saisie éditoriale, génération du site, contrôles | oui |
| `ingestion/assemblee/`, `pe/`, `senat/` | Collecteurs par source | oui |
| `db/schema.sql` | Schéma SQLite complet, tables et vues | oui |
| `data/levraivote.sqlite` | La base | **non** (`.gitignore`) |
| `data/dumps/` | Dumps horodatés des collectes (Sénat, Parlement européen) | **non** |
| `web/` | Le site publié, racine de GitHub Pages | oui |
| `worker/` | Worker Cloudflare et schéma D1 pour la Communauté | oui |
| `connaissance/` | Ce dossier | oui |
| `visualisations/` | Scripts de graphiques pour les réseaux sociaux | oui |
| `prototype/` | Maquette JSX historique, référence de design | oui |
| `.github/workflows/pages.yml` | Déploiement GitHub Pages | oui |

### Pourquoi la base n'est pas versionnée

`data/levraivote.sqlite` est **entièrement régénérable** à partir des scripts et des dumps
archivés. Ce sont les scripts `seed_*.py` qui constituent la source de vérité éditoriale,
pas la base : une correction se fait toujours dans le script, jamais par un `UPDATE`
manuel qui serait perdu à la prochaine régénération.

Conséquence pratique : si un script refuse de tourner deux fois (voir
`04-pipeline-ingestion.md`), corriger le script puis répercuter le changement en base
demande une manipulation explicite. Cela s'est produit plusieurs fois pendant l'audit de
juillet 2026.

## Contenu de `web/`

| Chemin | Contenu |
|---|---|
| `index.html` | Accueil |
| `candidats/` | Index et une page par candidat |
| `votes/` | Une page par vote clé (165 actuellement) |
| `comparer/` | Comparateur, JavaScript inline |
| `communaute/` | Classement des votes jugés utiles |
| `methode/` | Méthode et sources, page publique |
| `data.json` | Export consommé par le comparateur et la Communauté |
| `styles.css`, `theme.js`, `config.js`, `communaute.js` | Feuille de style et scripts |
| `photos/`, `assets/` | Portraits, favicons, icône d'en-tête, logotype, image de partage |
| `CNAME`, `robots.txt`, `sitemap.xml` | Domaine et référencement, **générés par le script** |

Trois pièges à connaître :

- **Tout `web/` est généré.** Ne jamais y éditer un fichier à la main : la prochaine
  génération l'écrasera. `CNAME`, `robots.txt` et `sitemap.xml` sont produits par
  `build_site.py`, malgré leur apparence de fichiers de configuration.
- **`web/` est commité.** La génération se fait en local, pas dans l'intégration continue.
  Le workflow GitHub ne fait que publier le dossier.
- **Les pages orphelines sont purgées** à chaque génération. Renommer un vote clé change
  son slug donc son URL ; sans purge, l'ancienne page resterait en ligne avec son ancien
  contenu. Ce bug a réellement laissé 17 pages fautives accessibles en juillet 2026
  (voir `15-journal-des-problemes.md`).

## Le coffre OneDrive

`C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles` contient ce qui n'a pas sa
place dans le dépôt : les dumps sources volumineux, les tableurs d'analyse hérités d'une
première itération, et les notes de travail.

| Chemin | Contenu |
|---|---|
| `donnees_brutes/Assemblee_Nationale/dump_manuel_2026-07-23/` | Dumps officiels de l'Assemblée, archivés et horodatés. **Source des scrutins et des mandats** |
| `donnees_brutes/Howtheyvote/export/` | Export CSV de HowTheyVote (licence ODbL), source des votes européens |
| `donnees_brutes/HATVP/` | Déclarations d'intérêts en PDF |
| `analyses/` | Tableurs éditoriaux v1 à v6, matière de travail, jamais importés tels quels |
| `ETAT_DES_LIEUX.md` | Ce qui est réutilisable dans l'héritage, et à quelles conditions |
| `FEUILLE_DE_ROUTE.md` | Jalons et liste de courses manuelle |
| `CANDIDATS_2027.md` | Les candidatures sourcées, document de référence éditorial |
| `notes_projet/` | URLs à télécharger, protocoles, notes de méthode |

Pièges du coffre, tous vérifiés :

- les **CSV Civix de l'Assemblée sont des échantillons de 100 lignes**, jamais exhaustifs :
  ne pas les importer en base ;
- **Datan.fr** sert au recoupement, jamais de source citée ;
- les dumps de l'Assemblée sont un **téléchargement manuel daté**. Ils ne se
  rafraîchissent pas tout seuls : un scrutin postérieur au 23 juillet 2026 n'est pas dans
  la base.

## Les deux fichiers de contexte

`CLAUDE.md`, à la racine du dépôt, porte les sept règles absolues et les conventions. Il
est lu en premier par un agent qui travaille sur le projet.

Un second `CLAUDE.md` existait dans le coffre OneDrive, dans une version antérieure à six
règles. Il a été remplacé par un renvoi vers le dépôt, pour qu'il ne puisse plus être lu
comme une consigne concurrente.

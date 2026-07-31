# Génération du site et déploiement

## La commande

```
python3 ingestion/build_site.py
```

Elle lit la base et réécrit tout `web/`. Elle ne prend aucune option, et elle est
idempotente : la relancer deux fois produit le même résultat.

## Ce que fait `build_site.py`

Fichier d'environ 2 160 lignes, découpé ainsi :

| Partie | Contenu |
|---|---|
| Constantes | `BASE_URL`, `SEUIL_COMPARABLE`, `CANDIDATS_PRIORITAIRES`, `THEME_SLUGS`, `AXES_BUDGET`, `SOUS_SECTIONS_THEME`, `ETATS` |
| Helpers de rendu | `slugify`, `badge_etat`, `chip_groupe`, `resultat_texte`, `sens_html`, `date_fr` |
| `charger(base)` | **Une seule lecture SQLite**, qui retourne tout ce dont les pages ont besoin |
| Fonctions de page | `page_accueil`, `page_liste`, `fiche_candidat`, `page_vote`, `page_comparer`, `page_communaute`, `page_methode` |
| `generer(base)` | Orchestration, écriture des fichiers, purge, référencement |

Deux choses à savoir avant de modifier ce fichier :

- **les états d'affichage ne sont pas calculés ici** mais dans la vue SQL `couverture`
  (voir `10-etats-daffichage.md`) ;
- **deux fonctions sont du code mort volontaire** : `page_themes_index` et `page_theme` ne
  sont plus appelées depuis le retrait des pages de thème en juillet 2026. Elles sont
  conservées au cas où, avec un commentaire qui le dit. `concordances()` est également
  inutilisée.

`CANDIDATS_PRIORITAIRES` mérite une mention : cette liste impose l'ordre d'affichage des
candidats partout sur le site (accueil, liste, comparateur), parce que les consommateurs de
cette liste sont tous alimentés par le même tri.

## Ce qui est écrit

| Sortie | Contenu |
|---|---|
| `web/index.html` | Accueil |
| `web/candidats/` | Index et une page par candidat |
| `web/votes/` | Une page par vote clé |
| `web/comparer/`, `web/communaute/`, `web/methode/` | Pages fonctionnelles |
| `web/data.json` | Export consommé par le comparateur et la Communauté |
| `web/CNAME` | `levraivote.fr` |
| `web/sitemap.xml` | Toutes les URLs publiques |
| `web/robots.txt` | Autorisation d'exploration et renvoi au sitemap |

Les trois derniers **sont générés**, malgré leur allure de fichiers de configuration. Les
éditer à la main est inutile : ils seront écrasés.

## La purge des pages orphelines

En fin de génération, tout dossier de `web/votes/` et `web/candidats/` qui ne correspond
plus à un slug généré est supprimé.

Cette purge existe à cause d'un incident réel. Le générateur écrivait par-dessus les
fichiers sans jamais rien supprimer. Renommer un vote clé changeait son slug donc son URL,
et laissait l'ancienne page en ligne **avec son ancien contenu**. Après l'audit, dix-sept
pages portant les descriptions fautives corrigées le jour même restaient accessibles et
indexables, dont une « taxe sur les jets privés et les yachts » alors que le texte ne
mentionne aucun yacht.

Le nombre de suppressions est affiché à la fin du build. Une purge inattendue signale
qu'un slug a changé, ce qui est une information utile en soi.

## Référencement

- **Métadonnées par page** : titre, description, `canonical`, `og:` et `twitter:` sont
  produits par la fonction `page()`. Les descriptions sont génériques pour les pages fixes,
  spécifiques pour chaque candidat et chaque vote.
- **Sitemap** : environ 194 URLs, régénéré à chaque build.
- **Search Console** : la propriété est vérifiée par une balise `google-site-verification`
  présente dans le `<head>` de toutes les pages. Ne pas la retirer.
- **Statistiques** : Cloudflare Web Analytics, un script sans cookie, donc sans bandeau de
  consentement. Comme la Communauté, il passe par un domaine Cloudflare et peut être bloqué
  par une extension anti-pistage : voir le piège de diagnostic dans `12-communaute.md`.

## Déploiement

`.github/workflows/pages.yml`, unique workflow :

- **déclencheur** : `push` sur `main`, limité aux chemins `web/**` et au workflow lui-même,
  plus un déclenchement manuel ;
- **étapes** : `checkout`, `configure-pages`, `upload-pages-artifact` avec `path: web`,
  `deploy-pages` ;
- **durée** : environ 20 à 35 secondes.

**Il n'y a aucune génération dans l'intégration continue.** `build_site.py` tourne en local
et `web/` est commité. Conséquence directe : un commit qui modifie un script d'ingestion
sans régénérer `web/` ne change rien au site en ligne. C'est une source de confusion
possible.

Autre conséquence, utile : modifier ce dossier `connaissance/` ou la documentation ne
déclenche pas de déploiement, puisque le workflow ne surveille que `web/**`.

## Domaine

`levraivote.fr`, acheté chez OVH, servi par GitHub Pages en HTTPS.

Configuration DNS chez OVH, à connaître en cas de migration :

- quatre enregistrements `A` sur la racine, vers `185.199.108.153`, `.109.153`, `.110.153`,
  `.111.153` ;
- un `CNAME` pour `www` vers `mlolita26.github.io.` ;
- côté GitHub, le domaine est déclaré dans Settings puis Pages, et « Enforce HTTPS » activé.

Deux pièges rencontrés à la mise en place :

- OVH crée par défaut des enregistrements `A` et `TXT` sur `www` qui **empêchent d'ajouter
  un CNAME** : il faut les supprimer d'abord ;
- un enregistrement `A` résiduel vers l'ancienne page de parking OVH (`213.186.33.5`) faisait
  pointer le domaine vers cinq adresses, ce qui a retardé la délivrance du certificat HTTPS
  de plusieurs heures. Le certificat n'arrive qu'une fois le DNS **propre et stable**.

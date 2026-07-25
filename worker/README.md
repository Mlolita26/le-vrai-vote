# Service « Communauté » — déploiement (≈ 15 min, gratuit)

Ce dossier contient un petit **Cloudflare Worker** + une base **D1** qui comptent,
par loi, les clics sur l'ampoule « m'a aidé à décider ». Gratuit (palier gratuit :
~100 000 votes/jour, des millions de lectures/jour ; aucune carte bancaire requise).

## Prérequis
- Node.js installé (https://nodejs.org).
- Un compte Cloudflare gratuit (https://dash.cloudflare.com/sign-up).

## Étapes

Ouvre un terminal **dans ce dossier `worker/`** et lance :

```bash
# 1. Installer l'outil Cloudflare
npm install -g wrangler

# 2. Se connecter (ouvre le navigateur)
wrangler login

# 3. Créer la base de données D1
wrangler d1 create levraivote
```

➡️ La commande affiche un bloc avec `database_id = "xxxxxxxx-..."`.
**Copie cet identifiant** dans `wrangler.toml` à la place de
`A_REMPLACER_APRES_wrangler_d1_create`.

```bash
# 4. Créer la table (schéma) dans la base distante
wrangler d1 execute levraivote --remote --file=schema.sql

# 5. Déployer le service
wrangler deploy
```

➡️ La commande affiche l'URL publique, du type :
`https://levraivote-communaute.TON-SOUS-DOMAINE.workers.dev`

## Dernière étape : brancher le site

Ouvre `web/config.js` (à la racine du site) et colle l'URL entre les guillemets :

```js
window.LVV_API = "https://levraivote-communaute.TON-SOUS-DOMAINE.workers.dev";
```

Puis régénère et redéploie le site :

```bash
python ingestion/build_site.py
git add web && git commit -m "Communauté : activer le service de vote" && git push
```

C'est tout : les ampoules deviennent actives et le classement se remplit.

## Vérifier que ça marche
- `https://…workers.dev/counts` doit renvoyer `{}` (puis se remplir avec les votes).
- Un clic sur une ampoule du site doit incrémenter le compteur.

## Notes
- **Rien n'est facturé** : au-delà du palier gratuit, les écritures sont
  temporairement refusées, jamais facturées (sauf si tu ajoutes toi-même un plan payant).
- Le Worker n'accepte que des `uid` de scrutins au bon format (anti-abus) ; le
  « 1 vote par appareil » est géré côté navigateur.
- Pour repartir de zéro : `wrangler d1 execute levraivote --remote --command "DELETE FROM votes"`.

# Communauté

La seule fonctionnalité du site qui écrit des données. Elle demande aux visiteurs quels
votes les aident vraiment à se décider, et en publie un classement.

## Ce que c'est, et ce que ce n'est pas

À côté de chaque vote clé, une ampoule « m'a aidé à décider ». Un clic incrémente un
compteur ; un second clic l'annule. La page `/communaute/` publie les 25 votes les plus
signalés, et l'accueil en montre les 10 premiers.

Ce que le site prend soin de dire, et qu'il faut préserver : **ce classement ne mesure ni la
popularité d'un candidat, ni l'opinion générale, et n'est pas représentatif**. C'est un
signal indicatif sur ce qui aide à choisir. Sans cet avertissement, un lecteur pourrait le
lire comme un sondage.

Ce n'est pas non plus un vote sur le fond : on ne dit pas si l'on approuve le texte, on dit
que ce vote éclaire un choix.

## L'architecture, et pourquoi elle est à part

Le site est statique, sans serveur. Écrire un compteur exige pourtant un service. D'où une
brique séparée :

```
navigateur  ->  Worker Cloudflare  ->  base D1
```

| Élément | Fichier | Rôle |
|---|---|---|
| Client | `web/communaute.js` | Ampoules, classements, appels API |
| Configuration | `web/config.js` | `window.LVV_API`, l'URL du service |
| Service | `worker/worker.js` | `GET /counts`, `POST /vote`, `POST /unvote` |
| Base | `worker/schema.sql` | Table `votes(uid, count)` |
| Déploiement | `worker/README.md` | Tutoriel wrangler pas à pas |

Le service tourne sur `levraivote-communaute.le-vrai-vote.workers.dev`, sur le palier
gratuit de Cloudflare.

## La clé d'identification : l'uid officiel

Un vote est identifié par l'**uid officiel du scrutin** (`VTANR5L17V3690`, `PE-HTV-161873`,
`SEN-2023-208`), jamais par son slug ni par son identifiant en base.

C'est un choix qui s'est révélé heureux. Pendant l'audit de juillet 2026, dix-sept titres de
votes clés ont été corrigés, donc dix-sept slugs et URLs ont changé : **aucun compteur n'a
été perdu**. Un slug est un libellé éditorial, il bouge ; l'uid vient du producteur de la
donnée, il ne bouge pas.

Le Worker valide l'uid contre une expression régulière avant d'écrire, pour empêcher la
création de clés fantaisistes.

## L'anti-doublon, et ses limites assumées

Un vote par appareil, réversible, via une clé `lvv_v_<uid>` dans le `localStorage` du
navigateur. Il n'y a **aucune identité côté serveur** : ni compte, ni adresse IP stockée, ni
empreinte de navigateur.

C'est un choix de sobriété : la fonctionnalité ne justifie pas de collecter des données
personnelles. La contrepartie est explicite : quelqu'un qui vide son stockage local ou change
de navigateur peut voter à nouveau. Le classement est un signal, pas une mesure, et il est
présenté comme tel.

Détail d'interface : le compteur est mis à jour **avant** la réponse du réseau (mise à jour
optimiste), puis corrigé par la valeur du serveur. Le clic paraît instantané même sur une
connexion lente.

## La dégradation quand le service tombe

Elle est volontaire et silencieuse. Trois niveaux :

- **`LVV_API` vide** : les ampoules s'affichent en mode « bientôt », sans compteur ; le bloc
  de l'accueil est masqué ; le classement affiche un message d'attente ;
- **API injoignable** : l'erreur est absorbée, les ampoules restent sans compteur, le
  classement se dit « momentanément indisponible » ;
- **la page ne casse jamais** : aucune erreur visible, aucun blocage du reste du contenu.

## Le piège de diagnostic à connaître

Un classement vide chez un visiteur ne signifie pas que le service est en panne.

Le domaine `workers.dev` est fréquemment **bloqué par les extensions anti-pistage** (uBlock,
Brave, protections intégrées). Pour le visiteur concerné, l'API est injoignable et le
classement paraît désert, alors qu'il est complet pour tout le monde.

Le cas s'est présenté, et le réflexe utile est celui-ci : avant de suspecter le service,
vérifier depuis un navigateur sans extension ou en navigation privée. Un test en ligne de
commande n'est pas concluant, `curl` échouant de son côté sur la négociation TLS avec ce
domaine. Le diagnostic fiable passe par un vrai navigateur, en observant les appels réseau.

Le même bloqueur affecte généralement les statistiques de fréquentation, qui passent aussi
par un domaine Cloudflare : les deux symptômes vont souvent ensemble et ont la même cause.

## Injection dans les pages

`communaute.js` place une ampoule sur tout élément portant `data-vote-id`. Il surveille
aussi les ajouts au document via un `MutationObserver`, ce qui lui permet de traiter les
cartes créées dynamiquement par le comparateur, sans que celui-ci ait à s'en occuper.

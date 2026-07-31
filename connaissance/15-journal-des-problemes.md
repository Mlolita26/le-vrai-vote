# Journal des problèmes rencontrés

Ce journal existe pour une raison simple : un problème dont on a oublié la cause revient.
Chaque entrée dit ce qui s'est passé, pourquoi, et ce qui empêche désormais la récidive.

Les erreurs de description de vote ne sont pas listées une par une ici : elles sont
analysées par famille dans `08-rediger-et-verifier-un-vote.md`, qui est le document à lire
avant d'écrire une description.

## Juillet 2026, audit des 165 votes clés

### Deux votes pointaient sur le mauvais scrutin

**Ce qui s'est passé.** « Enquête sur les logiciels espions » renvoyait à un amendement
rejeté sur la situation en Libye. Le site attribuait donc à chaque candidat une position sur
la Libye en l'affichant comme une position sur Pegasus. « Preuves électroniques » renvoyait
à la directive annexe sur les représentants légaux au lieu du règlement de fond.

**Cause.** Une erreur de sélection dans la liste `VOTES_CLES_PE`. Les deux identifiants
correspondaient à des lignes `is_main=False` de l'export HowTheyVote, c'est-à-dire des
amendements et non des votes principaux. Aucun contrôle ne comparait le titre affiché avec
l'objet officiel du scrutin.

**Parade.** Vérifier `is_main=True` et `display_title` avant d'ajouter un identifiant, règle
écrite dans `CLAUDE.md` et dans `03-sources-de-donnees.md`.

### Un sens de vote inversé

**Ce qui s'est passé.** Sur la déclaration du Gouvernement de décembre 2018 relative à la
taxe carbone, le site affichait « Pour égale défendre la taxe carbone ». Or le Premier
ministre venait annoncer la **suspension** des hausses : voter pour approuvait un
renoncement.

**Cause.** Les déclarations au titre de l'article 50-1 sont des votes sur une position, qui
peut être un abandon. Le sens ne se déduit pas du sujet.

**Parade.** La liste des scrutins à sens inversé, dans
`08-rediger-et-verifier-un-vote.md`.

### Un mécanisme économique inversé

**Ce qui s'est passé.** Sur le financement des pompiers, la description affirmait que les
assureurs et les assurés paieraient davantage. L'amendement ne touchait à aucun taux : il
transférait aux départements une part d'une taxe déjà perçue, au détriment du budget de
l'État. Personne ne payait plus.

**Cause.** Le titre de l'amendement mentionnait une taxe, et la conclusion « donc quelqu'un
paie plus » a été tirée sans lire le dispositif.

### Dix-sept pages fantômes avec les descriptions fausses

**Ce qui s'est passé.** L'audit a corrigé dix-sept titres de votes, donc dix-sept slugs et
URLs. Les anciennes pages sont restées en ligne **avec leur ancien contenu**, c'est-à-dire
les descriptions fautives corrigées le jour même. Elles ne figuraient plus au sitemap mais
restaient accessibles et indexables. L'une affichait encore une « taxe sur les jets privés et
les yachts » alors que le texte ne mentionne aucun yacht.

**Cause.** `build_site.py` écrivait par-dessus les fichiers existants sans jamais rien
supprimer.

**Parade.** Une purge des dossiers orphelins en fin de génération, avec affichage du nombre
de suppressions. Voir `13-generation-et-deploiement.md`.

### Un script de seed qui ne corrigeait rien

**Ce qui s'est passé.** Des justifications corrigées dans le fichier source restaient fausses
sur le site.

**Cause.** `seed_justifications_groupes.py` sautait les lignes déjà présentes en base. Une
correction du texte n'avait donc aucun effet.

**Parade.** Le script met désormais à jour les lignes modifiées et supprime celles qui ont
disparu de la liste. Attention, `seed_nuances.py` conserve l'ancien comportement : voir
`04-pipeline-ingestion.md`.

### Le filet de sécurité était hors service

**Ce qui s'est passé.** `validate.py` ne tournait plus du tout : il s'interrompait sur une
erreur d'encodage de la console Windows avant d'afficher ses résultats. Forcé à tourner,
sept de ses contrôles échouaient.

**Cause.** Deux causes distinctes. L'encodage, d'abord : la console Windows ne sait pas
écrire les caractères typographiques des libellés. Les effectifs attendus, ensuite : codés
en dur et jamais mis à jour, ils annonçaient 115 votes clés contre 165 réels. Un contrôle
qui échoue en permanence ne protège de rien.

**Parade.** Sortie reconfigurée en UTF-8 dans le script, et effectifs regroupés dans un
dictionnaire `ATTENDU` en tête de fichier pour que la dérive soit visible.

**Trouvé au passage.** Un contrôle sur les axes budget était silencieusement inopérant : il
testait `sens_axe NOT IN ('pour','contre')`, or en SQL une comparaison avec une valeur nulle
ne vaut pas vrai. Les valeurs manquantes passaient donc le test. Le contrôle a été scindé,
parce que le champ `axe_budget` porte deux usages : les axes du Budget, qui ont un sens, et
les sous-sections d'autres thèmes, qui n'en ont pas.

### Une correction automatisée a cassé l'encodage du code

**Ce qui s'est passé.** Lors du retrait des tirets cadratins, un fichier a vu ses caractères
accentués remplacés par des séquences d'échappement littérales (`é` au lieu de « é »)
dans le code source lui-même.

**Cause.** Une édition automatisée du fichier qui a réécrit les chaînes en les échappant.

**Parade.** Après toute modification massive d'un fichier Python, vérifier qu'il ne contient
pas de séquences `\uXXXX` inattendues, en plus du contrôle de syntaxe.

### Le retrait des tirets a cassé l'extraction du nom de parti

**Ce qui s'est passé.** Le parti d'un candidat n'apparaissait plus correctement sur les
fiches.

**Cause.** Le parti est stocké en tête du champ `detail` de `candidatures`, et
`build_site.py` le séparait du reste sur le tiret cadratin. En retirant les tirets du
projet, le séparateur a disparu.

**Parade.** Une expression régulière qui accepte plusieurs séparateurs. La fragilité de fond
subsiste : le parti n'a pas de colonne dédiée. Voir `06-candidats-partis-mandats.md`.

### Débordement horizontal en mobile

**Ce qui s'est passé.** Sous environ 410 pixels de large, les cinq entrées du menu, forcées
sur une seule ligne, dépassaient l'écran. Le lien « Méthode » était coupé. Le défaut était
en production.

**Cause.** Une règle de style imposait `nowrap` sur la barre de navigation, sans prévoir que
le texte deviendrait trop large.

**Parade.** Deux paliers de resserrement sous 430 puis 350 pixels, en conservant une hauteur
tactile de 44 pixels. Tester à 380 pixels, largeur de référence du projet.

## Faux problèmes, à ne pas rouvrir

Ces symptômes ont déjà été investigués et n'ont pas la cause qu'ils suggèrent.

**« Le classement de la Communauté est vide. »** Le plus souvent, une extension anti-pistage
bloque le domaine `workers.dev` chez le visiteur. Le service, lui, répond. Vérifier en
navigation privée avant de suspecter une panne. Voir `12-communaute.md`.

**« Les statistiques de fréquentation n'affichent rien. »** Même cause, même domaine
Cloudflare. Et rappel : le suivi ne peut compter que les visites postérieures à sa mise en
place, il n'existe aucune donnée rétroactive.

**« Le terminal affiche des caractères illisibles à la place des accents. »** La console
Windows utilise une page de code qui ne sait pas afficher l'UTF-8. Le contenu des fichiers
et de la base est intact : cela a été vérifié plusieurs fois en inspectant les octets. Ne
pas « corriger » un problème d'affichage dans les données.

**« La page d'un vote renvoie une erreur. »** Après un renommage, l'ancienne URL est
supprimée volontairement par la purge. Ce n'est pas une régression : le sitemap et les liens
internes pointent la nouvelle.

# Vérifier une description de vote clé

Ce document consigne ce qu'a appris l'audit du 30 juillet 2026, au cours duquel les
165 votes clés du site ont été vérifiés un par un contre leurs sources primaires.
**71 descriptions sur 165 comportaient une erreur de fond**, soit 43 %. Les règles
ci-dessous viennent toutes d'une erreur réellement commise et corrigée ; elles ne
sont pas des précautions théoriques.

À lire avant d'ajouter ou de modifier un vote clé dans `ingestion/seed_votes_cles.py`.

---

## 1. La règle qui résume toutes les autres

> Décrire **le texte tel qu'il a été voté ce jour-là**, jamais l'intention de ses
> auteurs, jamais le projet initial, jamais la loi finale.

Un vote clé porte sur un état précis d'un texte, à une date précise. Trois documents
différents circulent autour de ce même vote et disent trois choses différentes :

| Document | Ce qu'il dit | Utilisable ? |
|---|---|---|
| Projet ou proposition initiale | ce que le Gouvernement ou l'auteur voulait | non, sauf pour raconter l'écart |
| Exposé des motifs d'un amendement | ce que l'auteur souhaite obtenir | non, jamais comme description |
| **Texte adopté (« T.A. n° … ») ou dispositif de l'amendement** | ce qui a été voté | **oui, c'est la seule référence** |
| Loi promulguée | ce qui subsiste après navette et Conseil constitutionnel | seulement en contexte, daté |

## 2. Les trois familles d'erreurs, avec les cas réels

### a) Confondre l'intention et le dispositif

C'est l'erreur la plus fréquente. L'exposé des motifs d'un amendement annonce un
objectif ; le dispositif, souvent, fait tout autre chose ou beaucoup moins.

- *Pistes cyclables (VTANR5L16V1989)* : la description annonçait « un objectif de
  80 000 km ». Le dispositif réserve 1 % de l'enveloppe d'artificialisation. Les
  80 000 km n'étaient qu'un rappel du plan vélo dans l'exposé des motifs.
- *Protections périodiques (VTANR5L17V3620 et V4613)* : deux fois, la description
  annonçait une prise en charge. Les deux amendements ne demandaient qu'un
  **rapport**.
- *Passoires thermiques (VTANR5L16V491)* : décrite comme portant sur le calendrier
  d'interdiction de location. C'était un amendement de **crédits** transférant
  1,1 milliard d'euros. Un amendement de crédits ne peut pas modifier un calendrier
  législatif : ce seul indice suffisait à détecter l'erreur.

### b) Décrire une version dépassée du texte

- *Loi ELAN (VTANR5L15V928)* : la part de logements accessibles était de **10 %**
  dans le texte voté ; les 20 % viennent de la commission mixte paritaire, plus tard.
- *Déchéance de nationalité (VTANR5L14V1237)* : la condition de double nationalité
  avait été **supprimée par amendement avant le vote**. La décrire revenait à
  attribuer aux députés un vote qu'ils n'ont pas émis.
- *Présomption de légitime défense (VTANR5L17V7987)* : le dispositif décrit avait été
  **supprimé en séance** et remplacé par un autre, de portée différente.
- *Congé de naissance (VTANR5L17V3690)* : des amendements adoptés juste avant le vote
  autorisaient le fractionnement, que la description niait implicitement.

### c) Présenter comme acquis ce qui relève d'un décret

Un chiffre précis dans une loi doit toujours éveiller le soupçon : il est souvent
renvoyé au pouvoir réglementaire, parfois pour des années.

- *Ratios de soignants (VTANR5L17V600)* : la loi ne fixe **aucun ratio**, et le
  dispositif n'entre en vigueur qu'en 2027. Cela explique les nombreuses abstentions,
  que la description rendait incompréhensibles.
- *Assurance chômage (VTANR5L16V236)* : simple habilitation ; la modulation a été
  fixée par un décret **trois mois après** le vote.
- *Congé de naissance* : les taux de 70 % et 60 % ne figurent pas dans l'article voté.

## 3. Erreurs de fait à traquer spécifiquement

**Ne jamais compléter une liste par ce qui « sonne plausible ».** Deux fois dans
l'audit, des yachts ont été ajoutés à des textes qui n'en parlaient pas (taxe sur les
jets privés, taxe sur les holdings). De même, l'École nationale de la magistrature
avait été citée parmi des écoles non concernées, et les « grandes entreprises »
ajoutées à une loi ne visant que la fonction publique.

**Vérifier qui paie et qui perd.** Sur le financement des pompiers
(VTANR5L17V4114), la description affirmait que les assureurs et les assurés
paieraient davantage. La mesure ne fait que transférer aux départements une part
d'une taxe **déjà perçue** : personne ne paie plus, l'argent change de destinataire.

**Vérifier le champ géographique.** Deux textes concernaient un seul territoire :
le droit du sol **à Mayotte** (VTANR5L17V1308) et l'encadrement des loyers **dans
les outre-mer** (VTANR5L17V2262). Les décrire comme nationaux était un contresens.

**Vérifier les dates avant d'écrire « après ».** Les frappes en Syrie
(VTANR5L14V1195) ont commencé le 27 septembre 2015, **avant** les attentats du
13 novembre, et non « après » comme l'affirmait la description.

**Attribuer un texte au bon groupe.** La résolution employant le terme d'« apartheid »
(VTANR5L16V1456) a été déposée par les députés communistes, pas par LFI.

## 4. Le sens du vote (`SENS`) demande une attention propre

Le couple « Pour = … / Contre = … » est ce qui permet de comparer des candidats : une
inversion y est plus grave qu'une description imprécise.

Vérifier systématiquement pour ces types de scrutins, où voter « pour » ne veut pas
dire soutenir le texte :

- **amendement de suppression** : voter pour, c'est retirer une disposition ;
- **motion de rejet préalable ou motion de censure** : voter pour, c'est s'opposer
  au texte (le site le gère déjà correctement pour les censures) ;
- **déclaration du Gouvernement (art. 50-1)** : voter pour approuve la position du
  Gouvernement, qui peut être un **renoncement**. C'est l'erreur commise sur la taxe
  carbone de décembre 2018 (VTANR5L15V1536) : le Premier ministre annonçait la
  *suspension* des hausses, et le site affichait « Pour = défendre la taxe carbone ».

## 5. Les liens et le choix du scrutin

**Le lien est construit automatiquement** à partir de la chambre, de la législature
et du numéro (voir `seed_votes_cles.py`, fonction `seed`). Formats en vigueur, tous
vérifiés en juillet 2026 :

- Assemblée nationale, législatures 14 à 17 : `assemblee-nationale.fr/dyn/{leg}/scrutins/{numero}`
  (le format `dyn/14/...` fonctionne, malgré l'ancien format `/14/scrutins/jo0436.asp`) ;
- Parlement européen : `howtheyvote.eu/votes/{id}` ;
- Congrès de Versailles : pas de page officielle de scrutin, d'où un lien de presse,
  signalé comme tel dans le contexte.

**Le vrai risque n'est pas le lien mort mais le mauvais scrutin.** Deux votes clés
pointaient sur un scrutin sans rapport avec leur titre :

- « Enquête sur les logiciels espions » renvoyait à un **amendement rejeté sur la
  Libye**. Le site attribuait donc aux candidats une position sur la Libye en
  l'affichant comme une position sur Pegasus.
- « Preuves électroniques » renvoyait à la directive annexe (« représentants
  légaux ») au lieu du règlement de fond.

**Conséquence pratique, pour les votes du Parlement européen** (liste
`VOTES_CLES_PE` dans `ingestion/pe/import_votes_cles_pe.py`) : avant d'ajouter un
identifiant, vérifier dans `votes.csv` de l'export HowTheyVote que
`display_title` correspond au sujet **et** que `is_main` vaut `True`. Les deux erreurs
ci-dessus portaient sur des lignes `is_main=False`, c'est-à-dire des amendements.

Enfin, un scrutin dont le champ `result` est vide chez HowTheyVote n'est pas une
anomalie : c'est fréquent pour les positions de première lecture. Le site affiche
alors le décompte réel sans qualifier l'issue, qui n'est pas sourcée
(`resultat_texte` dans `build_site.py`).

## 6. Neutralité : ce qui s'est glissé malgré la règle

La règle 4 du `CLAUDE.md` interdit de juger. Les manquements observés étaient plus
discrets qu'un adjectif militant :

- des **appréciations d'efficacité** (« l'effet réel de la loi sur les prix a été jugé
  décevant », « sa solidité juridique a été débattue ») : non sourcées, et souvent
  postérieures au vote ;
- des **pronostics** (« cette disposition est un candidat plausible à une nouvelle
  censure ») : ce n'est pas un fait ;
- des **formules de communication institutionnelle** reprises telles quelles
  (« premier cadre juridique complet au monde ») ;
- des **appréciations glissées dans un constat** (« le coût réel, *souvent bas*, des
  énergies décarbonées »).

## 7. Vérification à faire avant de publier un vote clé

1. Ouvrir la page du scrutin et confirmer : numéro, date, **objet officiel cohérent
   avec le titre affiché**, décomptes identiques à la base.
2. Lire le **dispositif** voté : texte adopté (« T.A. n° … ») pour un texte entier,
   PDF de l'amendement pour un amendement. Pas le dossier de presse, pas l'annexe
   d'évaluation du projet initial.
3. Lister les amendements adoptés **avant** le vote sur l'article ou l'ensemble :
   modifient-ils ce que la description affirme ?
4. Repérer chaque chiffre de la description et se demander : figure-t-il dans le
   texte, ou dans un décret ?
5. Relire le sens Pour/Contre en se demandant ce qu'un « pour » impliquait vraiment.
6. Relire la description en cherchant tout mot qui juge, prédit ou évalue.

Un doute qui subsiste se traite comme le reste du projet : afficher moins mais sûr,
et exposer la limite plutôt que de la masquer.

## 8. Enseignement de méthode

Deux erreurs de cet audit ont été introduites **le jour même**, en ajoutant de
nouveaux votes à partir de rapports de recherche : un nombre de cosignataires faux
(159 au lieu de 123) et une unité manquante sur un seuil (milligrammes **par
kilogramme d'anhydride phosphorique**). Un rapport de recherche, même détaillé,
n'est pas une source : les chiffres et les citations doivent être relus sur le
document primaire avant publication.

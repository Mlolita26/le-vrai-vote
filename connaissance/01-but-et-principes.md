# But du site et principes

## Le problème auquel il répond

L'écart entre le discours de campagne et les actes votés est réel, documenté, et
pourtant invisible pour le grand public. Les briques existent séparément
(NosDéputés.fr, Datan, HATVP, les portails open data des assemblées), mais personne ne
les agrège autour d'une élection présidentielle avec l'angle « ce qu'ils disent contre
ce qu'ils ont voté ». C'est là que se situe l'apport du site.

Le site s'adresse à un citoyen qui hésite, pas à un spécialiste. Il doit pouvoir
répondre en trente secondes à « qu'a voté cette personne sur ce sujet », avec le lien
vers le scrutin officiel pour vérifier.

## Le défi central : l'asymétrie des parcours

Tous les candidats n'ont pas le même historique traçable. Un député cumule des milliers
de scrutins publics ; un eurodéputé vote au Parlement européen ; un maire, un ministre
non parlementaire ou une personnalité de la société civile n'ont presque rien de
comparable.

Cette asymétrie est le principal risque de biais du site : sans précaution, il paraîtrait
sévère envers les parlementaires, simplement parce qu'ils sont les seuls dont on peut
tout voir. D'où la règle des états d'affichage, détaillée dans `10-etats-daffichage.md` :
une case n'est jamais vide, et l'absence de donnée est toujours qualifiée.

## Ce que le site refuse de faire

- **Inventer une donnée**, même vraisemblable. Un vote non importé s'affiche « à
  importer », pas « probablement pour ».
- **Noter les candidats.** Aucun score global, aucun classement de « bon élève ». Le site
  montre des positions, il ne décerne pas de mention.
- **Juger un texte.** « Autorise la réintroduction de » et non « loi controversée qui ».
  Voir `08-rediger-et-verifier-un-vote.md`.
- **Coder l'information par la seule couleur.** Un badge porte toujours son libellé écrit,
  pour l'accessibilité comme pour l'honnêteté.
- **Croiser automatiquement des bases judiciaires.** Les décisions en open data sont
  pseudonymisées : ce croisement serait illégal, et il est écarté par conception.

## Pourquoi la crédibilité est la seule valeur

Un site politique n'a pas de marque, pas de capital, pas de public captif. Il n'a que sa
réputation d'exactitude. Une seule donnée fausse sur une personne réelle, reprise et
démentie, suffit à disqualifier l'ensemble : le lecteur n'a aucun moyen de savoir que
c'était la seule erreur.

C'est la raison pour laquelle le projet accepte des coûts qui paraîtraient absurdes
ailleurs :

- afficher moins mais sûr, plutôt que compléter par déduction ;
- écarter un vote intéressant faute de scrutin nominatif réel, même quand la mesure est
  politiquement marquante (voir `07-choisir-un-vote-cle.md`) ;
- publier la méthode et le code, y compris les erreurs corrigées.

C'est aussi ce qui justifie l'audit consigné dans `08-` et `15-` : la vérification
n'est pas une formalité de fin de chantier, c'est le travail lui-même.

## Le présentéisme, et pourquoi il est traité avec prudence

L'assiduité parlementaire est très demandée par le public et très facile à mal mesurer.
Le site s'y tient à trois principes :

- **des indicateurs séparés**, jamais un score unique d'assiduité ;
- **une comparaison à la médiane** de l'assemblée, pas à un idéal de 100 % ;
- **la prise en compte des fonctions** (un ministre ou un président de commission vote
  moins) et des absences légitimes.

Ce qui est mesurable : la participation aux scrutins, surtout solennels. Ce qui ne l'est
pas : la présence physique hors votes, et tout le travail hors les murs (circonscription,
auditions). Une absence à un scrutin majeur reste une donnée en soi, de même que son
évolution dans le temps.

## Volet judiciaire

Il a existé sur les fiches candidat, puis a été retiré du site en juillet 2026. La
doctrine reste écrite ici parce qu'elle s'appliquera si le volet revient :

- les **condamnations définitives** sont publiques et factuelles : décision, date,
  juridiction, source ;
- les **poursuites en cours** relèvent de la présomption d'innocence, mentionnée
  explicitement, avec une formulation neutre ;
- chaque fait renvoie à un document officiel ou un article de presse fiable. Wikipédia
  peut servir de point de départ, jamais de source finale ;
- la table `affaires_judiciaires` porte une contrainte SQL qui impose le drapeau de
  présomption hors décision définitive : la règle est dans le schéma, pas seulement dans
  la doctrine.

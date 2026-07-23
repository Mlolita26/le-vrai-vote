# Concept et méthodologie

## Le problème

L'écart entre le discours de campagne et les actes votés est réel mais invisible pour le grand public. Des briques existent (NosDéputés.fr, Datan, HATVP…) mais personne n'agrège tout autour d'une présidentielle avec l'angle « ce qu'ils disent vs ce qu'ils ont voté ». C'est là que se situe la valeur ajoutée.

## Le défi central : l'asymétrie des parcours

Tous les candidats n'ont pas le même historique traçable. Un député a des milliers de scrutins publics ; un eurodéputé vote au PE ; un maire, un ministre non-parlementaire ou une personnalité de la société civile n'ont quasiment rien de comparable. Le site doit être transparent sur cette asymétrie, sinon il paraît biaisé contre les parlementaires (les plus « traçables »).

D'où la règle des **trois états** appliquée à chaque case candidat × vote clé :
- **Position connue** : le candidat était en poste et a voté (ou s'est abstenu, ou était absent).
- **Non concerné** : le vote a eu lieu avant/hors de son mandat.
- **Indisponible** : le candidat n'a jamais été parlementaire ; ses positions viennent alors de ses déclarations publiques.

## Les votes clés

Arborescence : **thématiques → votes clés**. Une dizaine de thèmes de premier niveau maximum (au-delà, l'utilisateur se perd), chacun contenant 5 à 15 votes clés.

Thèmes proposés : pouvoir d'achat/fiscalité/retraites ; sécurité/justice ; immigration ; écologie/agriculture/énergie ; santé/social ; éducation/jeunesse ; questions de société ; Europe/international ; institutions/démocratie ; numérique/libertés.

Chaque vote clé porte :
- la **position** du candidat (avec « absent » et « non-votant » comme catégories à part entière) ;
- un **résumé neutre** de la loi (une phrase, décrivant le contenu sans jugement) ;
- le **lien vers le scrutin officiel** et vers le dossier législatif ;
- un champ **nuance** optionnel quand le vote brut est trompeur (ex. « a voté contre car jugeait le texte insuffisant », sourcé sur l'explication de vote).

## Grille de sélection des votes clés (anti cherry-picking)

Critères objectifs, publics et identiques pour tous :
- scrutins solennels (les plus significatifs, programmés à l'avance) ;
- textes ayant fait l'objet d'un large débat public (presse, pétition, mobilisation) ;
- votes ayant divisé au sein des groupes (dissidences) ;
- amendements/votes ciblés révélateurs, même peu médiatisés.

Mélanger volontairement gros scrutins médiatiques et votes discrets mais parlants. Documenter chaque sélection. Publier la grille sur la page Méthode.

Exemples de votes clés récents et clivants : loi Duplomb (néonicotinoïdes), loi Climat et Résilience, CETA, réforme des retraites (64 ans), taxe Zucman, suppression de l'ISF, loi immigration 2023, AME, loi narcotrafic, présomption de légitime défense des forces de l'ordre, IVG dans la Constitution, aide à mourir, soutien à l'Ukraine, Mercosur. Au niveau européen : pacte migratoire, restauration de la nature, fin des moteurs thermiques 2035, glyphosate.

## Résumés de loi : règle de rédaction

Décrire ce que contient le texte, pas s'il est bon ou mauvais. Une phrase, une idée. La brièveté est une fonctionnalité : un résumé de plus de deux lignes sur mobile n'est pas lu. Chaque résumé est relu et renvoie au dossier législatif officiel (l'Assemblée a une page par texte, avec l'exposé des motifs).

## Présentéisme

Le « présentéisme » n'est pas une donnée unique ; il se reconstruit à partir de plusieurs traces, chacune avec ses limites.

Mesurable automatiquement :
- **participation aux scrutins** (surtout solennels) — la plus fiable ;
- **présence en commission** (comptes rendus nominatifs) ;
- **activité législative** (amendements, interventions, questions).

Non mesurable : la présence physique hors votes, et tout le travail hors les murs (circonscription, auditions informelles).

Pièges à éviter :
- afficher des **indicateurs séparés**, jamais un score unique de « bon élève » ;
- comparer à la **médiane** de l'assemblée, pas à un idéal de 100 % ;
- tenir compte des **fonctions** (ministre, président de groupe/commission) et des **congés légitimes** (maternité, maladie) ;
- l'**absence** à un scrutin majeur est une donnée en soi ; l'évolution dans le temps aussi (« assidu 4 ans, absent depuis l'annonce de sa candidature »).

## Volet judiciaire

Le seul volet entièrement manuel, et le plus sensible juridiquement.
- Les **condamnations définitives** sont publiques et factuelles : mentionner décision, date, juridiction, source.
- Les **poursuites en cours** relèvent de la présomption d'innocence : formulation neutre (« mis en examen pour X, présumé innocent »), jamais « coupable de ».
- Le casier judiciaire n'est pas public ; les décisions en open data sont pseudonymisées : **aucun croisement automatique possible ni autorisé**.
- Chaque fait renvoie à un document officiel ou un article de presse fiable. Wikipédia peut servir de point de départ, jamais de source finale.

## Neutralité comme condition de survie

Méthodologie publiée et identique pour tous ; sources primaires cliquables partout ; gouvernance et financement affichés (sinon accusation de financement partisan). La page Méthode est une page de premier niveau, accessible depuis partout : sur un site politique, la crédibilité est une fonctionnalité.

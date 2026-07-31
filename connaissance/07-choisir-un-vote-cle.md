# Choisir un vote clé

La sélection des votes clés est le principal risque éditorial du site. Choisir les
scrutins qui arrangent une thèse détruirait sa crédibilité en une seule reprise
médiatique. La parade : des critères publics, appliqués identiquement à tous, décidés
avant de regarder les résultats.

Le site compte actuellement **165 votes clés** répartis sur **15 thèmes**.

## Le prérequis absolu : un scrutin nominatif réel

Avant toute question de sélection, un vote clé exige **un scrutin public nominatif**,
c'est-à-dire un vote où le sens de chaque parlementaire est publié. Cela paraît évident et
c'est le filtre qui élimine le plus de candidats intéressants.

Beaucoup de mesures politiquement marquantes n'ont **aucun scrutin nominatif** :

- adoptées à main levée, sans enregistrement des noms ;
- adoptées via l'article 49.3, sans vote (seule la motion de censure existe alors) ;
- prises par circulaire ou décret, donc jamais votées ;
- inscrites dans un budget global, sans scrutin dédié à la mesure elle-même.

Exemples réels de recherches abouties à un refus : l'interdiction de l'abaya à l'école (une
note de service ministérielle, jamais une loi), la chasse à courre (propositions mortes en
commission ou abandonnées faute de temps), la corrida à l'Assemblée (texte retiré avant tout
vote face à l'obstruction).

Dans ce cas, la bonne réponse est de **ne rien afficher**, pas de rattacher la mesure à un
vote approchant.

## Critères d'inclusion, au moins un requis

- **C1. Scrutin solennel sur l'ensemble d'un texte.** Annoncés à l'avance, ce sont par
  construction les plus significatifs et les plus suivis.
- **C2. Motion de censure liée à un engagement de responsabilité (49.3).** Quand un texte
  est adopté sans vote, la motion est le seul vote existant. Le contexte doit expliquer ce
  que signifie voter pour ou contre.
- **C3. Scrutin du Congrès** (révision constitutionnelle), exceptionnel par nature. C'est
  aussi le seul cas où députés et sénateurs sont directement comparables.
- **C4. Vote d'ensemble ordinaire d'un texte à large débat public**, à condition que le
  débat soit documenté dans le champ de contexte.
- **C5. Vote ciblé révélateur** (amendement, article), même peu médiatisé, uniquement avec
  une justification écrite et sourcée expliquant en quoi il est révélateur.
- Les **déclarations du Gouvernement** (article 50-1) sont admissibles au titre de C1 ou C4 :
  ce sont des positions formelles exprimées en scrutin public. Attention à leur sens, voir
  `08-rediger-et-verifier-un-vote.md`.

## Règles d'application

1. **Lecture retenue** : le dernier vote d'ensemble à l'Assemblée (lecture définitive ou
   texte de commission mixte paritaire) ; à défaut la première lecture. Les autres lectures
   peuvent figurer en contexte. Une exception se justifie par écrit.
2. **Un vote égale un thème.** Les textes transversaux sont rattachés à leur objet
   principal, et le choix est documenté. Exemple assumé : un texte mêlant sécurité et
   immigration est classé en immigration.
3. **Équilibre** : viser 3 à 6 votes par thème, sur plusieurs législatures quand c'est
   possible.
4. **Irréversibilité du critère.** On ne retire pas un vote parce que son résultat dérange,
   on ne l'ajoute pas parce qu'il arrange. Les ajouts suivent la grille.
5. **Qualité obligatoire** : résumé neutre, lien vers le scrutin, date et chambre, états
   calculés pour tous les candidats.

## Le critère pratique qui a émergé : la couverture

La grille dit ce qui est **admissible**. L'expérience a ajouté une question de choix : ce
vote **apporte-t-il quelque chose** ?

Deux cas ont conduit à écarter des votes pourtant valides :

- **Un vote unanime ne différencie personne.** Le remboursement intégral des soins liés au
  cancer du sein a été adopté deux fois à l'unanimité (93 contre 0, puis 141 contre 0).
  Aucun candidat ne s'y oppose : le vote n'aide pas à choisir.
- **Un vote où un seul candidat a une position** apporte peu. Plusieurs scrutins du Sénat
  sur l'aide médicale d'État ou la corrida ne concernaient que Bruno Retailleau, seul
  sénateur parmi les candidats suivis.

Ce n'est pas un critère d'exclusion automatique : un vote très clivant peut valoir la peine
même avec peu de positions personnelles, surtout si les décomptes par groupe permettent
d'afficher la position du parti pour beaucoup de candidats. C'est précisément ce qui a
justifié d'ajouter les votes sur le congé de naissance, où deux votes personnels seulement
devenaient dix à onze positions affichées grâce aux groupes.

**La bonne question à se poser** : combien de candidats auront une position affichée, en
comptant les positions de parti ? Elle se vérifie avant l'ajout, en interrogeant
`positions_groupes` et `groupes_reference`.

## Où saisir un vote clé

`ingestion/seed_votes_cles.py` :

- `THEMES` : la liste des thèmes, avec leur slug ;
- `VOTES` : un tuple `(uid, thème, titre, résumé, contexte)` par vote ;
- `SENS` : le couple « Pour égale ... / Contre égale ... », **obligatoire** ;
- `AXES` : rattachement à un axe budget ou à une sous-section de thème ;
- `EQUIV_SENAT` : scrutin sénatorial équivalent, le cas échéant.

Le script refuse de tourner si l'identifiant du scrutin n'est pas déjà en base : un vote clé
ne peut pas précéder l'import de son scrutin.

Après l'ajout, **relancer `assemblee/parse_positions_groupes.py`**, sinon le nouveau vote
n'affichera aucune position de parti.

## Puis, impérativement

Passer à `08-rediger-et-verifier-un-vote.md`. C'est là que se trouvent les erreurs les plus
fréquentes, et un audit a montré que 43 % des descriptions en comportaient une.

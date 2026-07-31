# Justifications de vote

Une justification explique **pourquoi** un vote a été émis, telle que l'explication a été
rendue publique par l'intéressé ou son groupe. Elle rapporte une position déclarée : elle
décrit, elle ne juge pas, et elle n'est jamais endossée par le site.

## Deux niveaux, deux tables

| Niveau | Table | Contenu | Volume |
|---|---|---|---|
| Une personne | `nuances` | Pourquoi cet individu a voté ainsi | 18 |
| Un groupe | `justifications_groupes` | Pourquoi ce groupe a voté ainsi | 129 |

Les deux sont réunies par la vue SQL `justifications`, seul objet interrogé par le site.
Cela garantit qu'un même niveau d'exigence s'applique aux deux.

Scripts : `ingestion/seed_nuances.py` et `ingestion/seed_justifications_groupes.py`.

## Pourquoi le niveau du groupe est le plus utile

Une justification individuelle est rare et réservée aux votes contre-intuitifs, par
exemple quand un parlementaire s'écarte de la ligne de son groupe. La justification de
groupe, elle, sert bien plus souvent : elle permet d'expliquer un vote pour tous les
candidats rattachés à ce groupe, y compris ceux qui n'ont pas voté personnellement.

C'est ce qui permet de comprendre un décompte qui paraîtrait absurde : sur les ratios de
soignants, 70 abstentions ne s'expliquent que si l'on sait que les ratios eux-mêmes
étaient renvoyés à un décret.

## Les règles

**Pas de source, pas d'affichage.** C'est la règle 3 du projet, appliquée sans exception.
Une justification vraie mais non sourcée ne s'affiche pas.

**La source doit contenir la citation.** Ce point paraît redondant avec le précédent. Il ne
l'est pas : c'est la première erreur trouvée sur ce site. Une citation authentique de
Sylvie Josserand (le texte jugé « mièvre », voté comme « un signal ») pointait un article
de LCP qui ne la contenait pas du tout. La citation existait, dans un autre article. Il
faut donc vérifier que **la source citée** porte les mots publiés, pas seulement que les
mots ont été prononcés.

**Attribuer à la bonne personne et au bon groupe.** Deux erreurs réelles :
« discours réactionnaires » attribué à LFI alors que la formule était de Benjamin Lucas,
du groupe Écologiste ; « casse sociale » attribué à LFI alors qu'elle venait de Pierre
Dharréville, du groupe communiste. Un article qui cite plusieurs orateurs invite à ce genre
de glissement.

**Ne pas dupliquer la position du groupe.** Si une justification individuelle répète, en
moins précis, la justification du groupe déjà affichée juste au-dessus, elle doit être
retirée. Le cas s'est présenté deux fois : Guedj et Brun sur le paquet pouvoir d'achat,
puis Mélenchon, Ruffin et Autain sur la loi Climat. Une justification individuelle ne se
justifie que si elle **ajoute** quelque chose, comme le désaccord propre de Delphine Batho
sur l'ambition du même texte.

**Une justification de parti n'est pas un vote personnel.** L'interface le marque
explicitement (« position du parti »), et le rattachement candidat vers groupe est
éditorial, pas automatique. Voir `06-candidats-partis-mandats.md`.

## Les garde-fous dans le code

Ils existent parce que ces erreurs sont faciles à commettre :

- `seed_nuances.py` **refuse une justification individuelle si la personne n'a pas de vote
  personnel** sur ce scrutin. Une position de parti relève de l'autre table ;
- `seed_justifications_groupes.py` **refuse une justification pour un groupe qui n'a pas de
  décompte** sur ce scrutin. Il faut donc que `parse_positions_groupes.py` soit passé ;
- `seed_justifications_groupes.py` **met à jour et purge** : corriger le texte dans le
  script suffit à corriger la base ;
- `seed_nuances.py` **ne met pas à jour** : il saute les lignes déjà présentes. Corriger le
  texte dans le script ne suffit pas, il faut appliquer la mise à jour explicitement. Ce
  piège a fait rester une justification fausse en ligne alors qu'elle était corrigée dans
  le fichier.

## L'audit de juillet 2026

Les 151 justifications ont été vérifiées contre leurs 93 sources, ouvertes une par une.
**28 comportaient une erreur.** Les catégories, par ordre de gravité :

1. **Source hors sujet** : le vote du RN sur l'article 7 contre la Hongrie était sourcé
   vers un article traitant des élections hongroises de 2026 ; la loi santé de 2016 vers la
   page d'accueil du Parti socialiste ; le vote de LaREM sur l'hôpital public vers un
   communiqué du groupe communiste, c'est-à-dire le discours de son adversaire.
2. **Contresens** : la justification LFI sur les énergies renouvelables dénonçait « le
   quasi-droit de veto laissé aux maires », alors que la source explique que ce droit de
   veto avait été **retiré** du texte.
3. **Anachronisme** : le RN décrit comme « principal allié d'Orbán au Parlement européen »
   alors que le groupe en question n'existait qu'après le scrutin cité.
4. **Position déformée** : LFI présenté comme « favorable à la suppression des ZFE », alors
   que sa position est une suspension conditionnée à une alternative de transport.
5. **Citations fantômes** : une douzaine de formules entre guillemets absentes de la source
   citée (« souveraineté énergétique », « mirage » fiscal, « suspicion généralisée »,
   « gravée dans le marbre »), plus des détails biographiques inventés sur un député.

Les corrections ont consisté soit à repointer vers la vraie source, soit à reprendre les
mots réellement prononcés, soit à retirer la justification quand rien ne l'étayait.

## Vérification avant publication

1. Ouvrir la source et y **retrouver la citation**, mot pour mot.
2. Vérifier **qui parle** : nom et groupe, surtout si l'article cite plusieurs orateurs.
3. Vérifier que la source est **contemporaine ou postérieure** au vote, et qu'elle parle
   bien de ce texte.
4. Vérifier que la justification **n'est pas déjà dite** au niveau du groupe.
5. Relire en cherchant tout mot qui juge : la justification rapporte, elle n'approuve pas.

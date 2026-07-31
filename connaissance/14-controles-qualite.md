# Contrôles qualité

## Le contrôle automatique

```
python3 ingestion/validate.py
```

Code de sortie 0 si tout passe, 1 sinon. À lancer après toute modification de données, et
avant de générer le site.

Le script fait deux choses très différentes :

1. **Il teste la logique des états** sur une base en mémoire peuplée de données fictives
   étiquetées `TEST`, jamais écrites dans la vraie base. Un cas par état :
   `indisponible`, `non_concerne`, position connue, `a_importer`. C'est un vrai test
   unitaire de la vue SQL `couverture`.
2. **Il contrôle la base réelle** : intégrité des clés étrangères, effectifs attendus,
   faits connus vérifiés un par un, cohérences croisées.

## Ce qu'il vérifie sur la base réelle

| Famille | Exemples de contrôles |
|---|---|
| Intégrité | Clés étrangères, aucune donnée `TEST` résiduelle, toute naissance renseignée est sourcée |
| Effectifs | Nombre de personnes, candidatures par statut, votes clés, thèmes, justifications, rattachements |
| Faits connus | Bardella eurodéputé actif à une date donnée, Le Pen déclarée le 07/07/2026, Mélenchon sans position après la fin de son mandat |
| Votes clés | Titre, résumé et source non vides ; sens du vote toujours renseigné ; résultat officiel présent |
| Couverture | Un état pour chaque couple personne et vote clé, aucun état vide |
| Cas limites | Censure de 2023 : Le Pen a une position, Attal est non concerné, Lisnard est indisponible ; IVG au Congrès : Retailleau, sénateur, a bien un état |
| Justifications | Chacune adossée à une position ou un décompte réel, et sourcée avec une URL non vide |
| Axes budget | Chaque vote d'axe porte un sens, aucune sous-section n'en porte |
| Absences | Aucune absence déduite hors période de mandat |

Le contrôle sur les absences mérite d'être signalé : une absence déduite hors mandat serait
une accusation fausse. C'est le genre d'erreur qu'un humain ne verrait jamais sur 120 000
positions.

## Ce qu'il ne vérifie pas

À connaître, pour ne pas se croire couvert :

- **l'exactitude d'une description de vote.** Aucun contrôle automatique ne peut dire qu'un
  résumé décrit fidèlement le texte adopté. C'est le travail décrit dans
  `08-rediger-et-verifier-un-vote.md`, et c'est là que se trouvaient 71 erreurs ;
- **la validité d'un lien** vers un scrutin. Le script vérifie qu'une URL n'est pas vide,
  pas qu'elle répond ni qu'elle pointe le bon scrutin ;
- **la cohérence entre un titre et l'objet officiel** du scrutin. C'est ce trou qui a permis
  qu'un vote sur la Libye s'affiche comme un vote sur les logiciels espions.

## Les effectifs attendus, et leur piège

Le script compare les volumes à des nombres écrits en dur, regroupés dans le dictionnaire
`ATTENDU` en tête de fichier. **Ces nombres doivent être mis à jour à chaque ajout** de vote
clé, de justification ou de candidature.

Pourquoi c'est important : en juillet 2026, ils étaient périmés et **sept contrôles
échouaient en permanence** alors que les données allaient bien (115 votes clés attendus
contre 165 réels, 124 justifications contre 129). Un contrôle qui crie au loup en continu
ne protège de rien, puisqu'on ne distingue plus un vrai défaut d'un chiffre à rafraîchir.
C'est la raison du regroupement en tête : la dérive devient visible et se corrige en un
seul endroit.

Deux contrôles sont volontairement exprimés en **seuil plancher** plutôt qu'en égalité
(l'axe « capital », par exemple), parce que leur nombre croît naturellement et qu'une
égalité stricte n'y apporterait rien.

## Les contrôles manuels de l'audit

Certaines vérifications ne sont pas automatisables mais restent reproductibles. Voici celles
qui ont servi en juillet 2026, avec leur méthode.

**Tous les liens répondent.** Extraire les URL de `votes_cles.source_resume` et tester le
code HTTP de chacune, en parallèle. Résultat : 165 sur 165 en réponse correcte, y compris
les votes de la 14e législature dont le format d'URL était douteux.

**Le lien pointe le bon scrutin.** Ouvrir la page et comparer le numéro, la date et l'objet
officiel avec la base. C'est ainsi qu'ont été trouvés les deux votes européens mal
sélectionnés. Un contrôle automatique est possible côté Parlement européen en comparant
`display_title` de l'export à notre titre, ce que fait désormais la consigne du document
`03-sources-de-donnees.md`.

**Les décomptes correspondent.** Impossible à automatiser sur les pages de l'Assemblée, qui
chargent les chiffres en JavaScript : `curl` ne voit rien. Il faut soit un navigateur, soit
se fier au dump officiel, qui est de toute façon la source des décomptes en base.

**La couverture d'un vote.** Avant d'ajouter un vote clé, compter combien de candidats
auront une position affichée, positions de parti incluses. C'est ce qui distingue un vote
utile d'un vote décoratif (voir `07-choisir-un-vote-cle.md`).

## Vérifications à faire sur le site généré

Après `build_site.py` :

- **aucune page orpheline** : le build affiche le nombre de pages supprimées. Une purge
  inattendue signale un slug qui a changé ;
- **aucun tiret cadratin** dans les pages, la convention typographique du projet. Le
  caractère à traquer est U+2014, à ne pas confondre avec le tiret demi-cadratin U+2013 qui
  sert légitimement de séparateur dans les scores (`296-224` s'affiche avec un demi-cadratin).
  Un comptage par point de code évite cette confusion :
  `python3 -c "import io,glob; print(sum(io.open(f,encoding='utf-8').read().count(chr(0x2014)) for f in glob.glob('web/**/*.html',recursive=True)))"`
  doit afficher zéro ;
- **pas de débordement horizontal en mobile**, à tester à 380 pixels de large, largeur de
  référence du projet. Un débordement de la barre de navigation est passé inaperçu jusqu'en
  production ;
- **les liens partagés** affichent bien le logo, ce qui suppose que le certificat HTTPS soit
  actif : voir `13-generation-et-deploiement.md`.

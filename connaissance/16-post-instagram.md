# Faire un post Instagram sur un thème

Un post sort du site, il ne le double pas. Tout chiffre, toute position, toute description
vient de la base. Rien n'est saisi dans le script de génération.

Le risque propre au format est simple à nommer : **une image se partage et ne se corrige
pas.** Une page fautive se rectifie en un build ; une capture d'écran fausse circule
indéfiniment. La vérification avant publication est donc plus stricte que pour le site.

## Ce qui existe déjà

| Fichier | Rôle |
|---|---|
| `visualisations/posts_insta.py` | Boîte à outils et trois formats : quiz, « un vote, une loi », comparaison de deux parlementaires |
| `visualisations/posts_incendies.py` | Le modèle d'un post **thématique** : une vue d'ensemble puis un scrutin par slide |
| `visualisations/carousel.py` | Carrousel générique |
| `visualisations/post_insta/` | Images produites (JPG) |
| `visualisations/marque/` | Logos, fonds clair et sombre |

Format : portrait 4:5, 1440 x 1800 px, qualité 97. Charte reprise de `web/styles.css`
(constantes `FOND`, `ENCRE`, `ACCENT`, `BADGES` en tête de `posts_insta.py`), pour que le
post et la page se reconnaissent.

**Pour un post thématique, partir de `posts_incendies.py`**, pas de `posts_insta.py` : c'est
lui qui porte le bon squelette (vue d'ensemble, puis un scrutin par slide, avec la
distinction vote personnel contre position du parti).

## Étape 1 : choisir le sujet

Deux granularités possibles.

**Une thématique entière**, quand elle est de taille raisonnable :

|  Votes | Thématique |  Votes | Thématique |
|---:|---|---:|---|
| 35 | Écologie et agriculture | 9 | Immigration |
| 16 | Défense | 8 | Institutions et vie démocratique |
| 15 | Droits des femmes | 7 | Éducation |
| 14 | Santé | 7 | Taxe et impôts |
| 13 | Travail | 5 | Questions de société |
| 12 | Sécurité et justice | 5 | Europe et international |
| 11 | Budget | 4 | Économie |
| | | 4 | Logement |

**Une sous-section**, ce qui donne des posts plus nets. Elles vivent dans la colonne
`votes_cles.axe_budget` :

| Votes | Sous-section | Thématique |
|---:|---|---|
| 16 | `climat-energie` | Écologie et agriculture |
| 6 | `fiscalite-energie` | Écologie et agriculture |
| 5 | `elevage` | Écologie et agriculture |
| 5 | `incendies` | Écologie et agriculture |
| 3 | `agriculture-alimentation` | Écologie et agriculture |
| 5 | `engagements` | Défense |
| 4 | `budget-defense` | Défense |
| 4 | `ukraine` | Défense |
| 3 | `proche-orient` | Défense |
| 8 | `capital` | Budget (axe, avec sens) |
| 2 | `pouvoir-achat` | Budget (axe, avec sens) |
| 1 | `ecologie-fiscale` | Budget (axe, avec sens) |

Attention : `axe_budget` porte deux usages. Dans le thème Budget ce sont des **axes**, avec
un `sens_axe` qui alimente les barres de posture ; ailleurs ce sont de simples
**sous-sections** sans sens. Voir `05-modele-de-donnees.md`.

Un sujet où tous les candidats votent pareil ne fait pas un post : il n'y a rien à montrer.
Les critères de `07-choisir-un-vote-cle.md` valent aussi ici.

## Étape 2 : où chercher la matière

Cinq sources, par ordre d'autorité croissante. En cas de désaccord, **la source officielle
tranche**, toujours.

### 1. La base, pour rassembler

`data/levraivote.sqlite`. Elle est **régénérable et non versionnée** : si elle manque, la
reconstruire avec le pipeline de `04-pipeline-ingestion.md`.

Cette requête sort toute la matière d'un thème ou d'une sous-section. Mettre `SOUS` à `None`
pour prendre le thème entier :

```python
import sqlite3
con = sqlite3.connect("data/levraivote.sqlite")
con.row_factory = sqlite3.Row
THEME, SOUS = "Écologie et agriculture", "incendies"   # SOUS = None pour tout le thème

for r in con.execute("""
    SELECT vc.id, s.uid_officiel, s.chambre, s.date, s.sort,
           s.total_pour, s.total_contre, s.total_abstention,
           vc.axe_budget, vc.titre, vc.sens_pour, vc.sens_contre,
           vc.source_resume, vc.resume
    FROM votes_cles vc
    JOIN scrutins s    ON s.id = vc.scrutin_id
    JOIN thematiques t ON t.id = vc.thematique_id
    WHERE t.libelle = ?
      AND (? IS NULL OR vc.axe_budget = ?)
    ORDER BY s.date""", (THEME, SOUS, SOUS)):
    print(r["id"], r["uid_officiel"], r["date"], r["sort"], r["titre"])
```

Et celle-ci donne, pour un scrutin, la position de chaque candidat avec son repli parti :

```python
con.execute("""
    SELECT pe.prenom || ' ' || pe.nom AS qui,
           pv.position               AS perso,
           gr.groupe_abrege          AS groupe,
           pg.pour, pg.contre, pg.abstention
    FROM personnes pe
    LEFT JOIN positions_vote pv
           ON pv.personne_id = pe.id AND pv.scrutin_id = ?
    LEFT JOIN groupes_reference gr
           ON gr.personne_id = pe.id AND gr.legislature = ?
    LEFT JOIN positions_groupes pg
           ON pg.scrutin_id = ? AND pg.groupe_abrege = gr.groupe_abrege
    WHERE pe.nom IN ('Mélenchon', 'Le Pen', 'Attal', 'Philippe')""",
    (sid, str(legislature), sid))
```

La `legislature` doit être passée **en texte** : c'est le type de la colonne dans
`groupes_reference`.

Pour l'état d'affichage officiel, ne pas le recalculer : lire la vue `couverture`
(`personne_slug`, `vote_cle_id`, `etat`). C'est elle qui fait foi, voir
`10-etats-daffichage.md`.

### 2. `ingestion/seed_votes_cles.py`, pour le texte

C'est la **source de vérité éditoriale** des titres, résumés, `sens_pour` et `sens_contre`.
La base n'en est qu'une copie. Une correction se fait ici, jamais directement en base.

### 3. `web/data.json`, pour ne pas contredire le site

Ce que le site sert réellement. Utile en fin de parcours pour confronter le post à la page.

### 4. La page publique du vote

`https://levraivote.fr/votes/{slug}/`. C'est ce qu'un lecteur verra en cliquant. Le post doit
y mener sans surprise.

### 5. Le scrutin officiel

L'URL de `votes_cles.source_resume`. **La seule chose qui tranche.** Un rapport de recherche,
un article de presse ou un résumé de séance ne sont pas des sources : c'est une leçon de
l'audit de juillet 2026, où deux erreurs sont nées de la confiance faite à un intermédiaire.

## Étape 3 : générer

```bash
python visualisations/posts_incendies.py                       # sortie par défaut
python visualisations/posts_incendies.py chemin/de/sortie      # ailleurs
```

Dépendances : `Pillow` et `numpy`.

### Le piège des identifiants codés en dur

Les scripts épinglent les votes par leur **clé primaire de table**, pas par leur uid
officiel :

```python
VOTES = [129, 130, 131, 132, 133]     # posts_incendies.py
post_quiz(con, 68, sortie)            # posts_insta.py
post_vote(con, 127, sortie)           # posts_insta.py
```

Or `votes_cles.id` est un rowid attribué à l'insertion. Les 165 votes occupent aujourd'hui
les ids 1 à 168 : **il y a déjà des trous**, donc la numérotation a bougé au moins une fois.
Rien ne garantit qu'un id désigne demain le vote qu'il désignait hier, et le script ne
s'apercevrait de rien : il produirait un post cohérent portant sur les mauvais scrutins.

**Contrôler avant chaque regénération** que les ids pointent toujours où il faut :

```python
for vid in (129, 130, 131, 132, 133):
    r = con.execute("""SELECT s.uid_officiel, vc.titre FROM votes_cles vc
                       JOIN scrutins s ON s.id = vc.scrutin_id
                       WHERE vc.id = ?""", (vid,)).fetchone()
    print(vid, r["uid_officiel"] if r else "ID INEXISTANT", r["titre"] if r else "")
```

Au 31 juillet 2026, les ids sont justes : 129 à 133 portent bien les cinq scrutins incendies
(`VTANR5L16V133`, `V1509`, `V1545`, `V1556`, `VTANR5L17V4114`), 68 l'autonomie de la Corse
(`VTANR5L17V7454`) et 127 la loi d'urgence agricole (`VTANR5L17V8427`).

Pour un nouveau post, préférer une sélection par uid ou par sous-section plutôt que par id.

## Étape 4 : vérifier avant de publier

À faire pour **chaque slide**, sur l'image finale et non sur le script. C'est le cœur de ce
document.

### a. Le scrutin est le bon

Ouvrir l'URL de `source_resume` et confronter **le numéro, la date et l'objet officiel** au
contenu de la slide. C'est le contrôle qui a rattrapé deux votes européens pointant sur un
amendement sans rapport avec leur titre. Pour un vote du Parlement européen, vérifier en plus
`is_main=True` : voir `03-sources-de-donnees.md`.

### b. La description décrit le texte voté

**Relire `08-rediger-et-verifier-un-vote.md` avant d'écrire une accroche.** Ce document
existe parce que 71 des 165 descriptions étaient fautives. Les trois pièges, transposés au
post :

- ne pas décrire l'intention, l'exposé des motifs ou le projet initial, mais le dispositif
  effectivement voté ;
- attention aux **scrutins à sens inversé**, où voter pour approuve un renoncement (la
  déclaration de décembre 2018 sur la taxe carbone en est l'exemple) ;
- ne pas déduire un mécanisme du titre. L'amendement `VTANR5L17V4114` de la sous-section
  incendies avait été résumé comme faisant payer les assurés : il ne changeait aucun taux,
  il transférait aux départements une part d'une taxe déjà perçue. Un post aurait figé cette
  erreur dans une image.

Sur une slide, la place manque et la tentation de raccourcir est forte. Un raccourci qui
change le sens est un mensonge : couper le détail, jamais le dispositif.

### c. Les décomptes

Comparer les chiffres de la slide au dump officiel. Ne pas essayer de les lire avec `curl`
sur les pages de l'Assemblée : elles chargent les totaux en JavaScript, la commande ne
verrait rien. La base est la référence, puisqu'elle vient du dump.

### d. Vote personnel ou position du parti

La distinction la plus facile à perdre, et la plus grave : afficher une position de parti
comme si c'était le vote de la personne est une affirmation fausse sur quelqu'un de réel.

Convention de `posts_incendies.py`, à conserver :

- **pastille pleine** : la personne a voté elle-même ;
- **pastille cerclée** : aucune position personnelle exprimée, c'est la position majoritaire
  de son groupe, et le motif (absente, ou pas en poste) est écrit sous son nom.

Vérifier la mention écrite pour chaque pastille cerclée. Exemple réel sur `VTANR5L16V133` :
Le Pen a une position personnelle (abstention), les trois autres n'en ont pas et affichent
leur groupe (RE contre, LFI pour, HOR contre).

Rappel de règle : **une absence n'est pas une position.** Le repli sur le groupe s'applique
aussi quand la personne était en poste mais absente, exactement comme sur le site.

### e. Les quatre états

Un candidat sans position ne doit jamais apparaître avec une case vide et ambiguë. Lire
l'`etat` dans la vue `couverture` et le refléter. « Non concerné » (pas en poste à la date du
scrutin) et « indisponible » (jamais parlementaire) ne veulent pas dire la même chose, et
aucun des deux ne veut dire « n'a pas voulu se prononcer ».

### f. La langue reste neutre

Décrire, ne pas juger, y compris dans l'accroche et la légende. « A voté contre », pas
« s'est opposé à ». Un post cherche l'attention : c'est précisément là que la règle 4 se perd.

Pas de tiret cadratin, dans l'image comme dans la légende.

### g. Le post ne peut pas contredire le site

Ouvrir la page du vote sur `levraivote.fr` à côté de la slide. Position, résultat, sens de
« pour » et de « contre » : tout doit concorder. `posts_incendies.py` réutilise volontairement
la règle de repli et le calcul de majorité de `ingestion/build_site.py` pour cette raison ;
si vous écrivez un nouveau script, reprenez ces fonctions plutôt que de les réécrire.

Si le site a changé depuis le dernier build, regénérer le site **avant** de faire le post.

### h. Typographie

Le site utilise Spectral et Libre Franklin. **Ces polices ne sont pas installées sur le poste
de travail** : vérifié le 31 juillet 2026, les scripts retombent donc sur Georgia et Segoe UI.
Les posts ne sont pas typographiquement identiques au site. Ce n'est pas bloquant, mais il
faut le savoir avant de juger un rendu, et installer les deux familles si l'on veut la
correspondance exacte.

### i. Regarder les images

Ouvrir chaque JPG produit. Un texte tronqué, un débordement, une pastille sans libellé se
voient à l'œil et pas dans la sortie du script.

Vérifier aussi que l'information ne repose jamais sur la seule couleur : chaque badge porte
un texte. C'est la règle d'accessibilité du projet, et sur Instagram elle sert en plus les
captures en noir et blanc.

## Ce qui ne doit jamais figurer dans un post

- **Le volet judiciaire.** Manuel, prudent, et hors de portée d'un format qui ne permet pas
  de poser la présomption d'innocence correctement.
- **Une donnée absente de la base.** Pas de chiffre « de mémoire », pas d'estimation, pas de
  moyenne calculée pour l'occasion sans la documenter.
- **Un taux de similitude non qualifié.** Un pourcentage sans son dénominateur ne veut rien
  dire. Le comparateur affiche toujours « sur N votes comparables » : un post aussi.
- **Une position attribuée à quelqu'un qui n'a pas voté**, sans la mention du repli parti.

## Après publication

Recopier les images dans le coffre OneDrive, comme les autres visualisations, et noter la
date. Le code reste hors OneDrive, règle du projet.

Si une erreur est découverte après coup, la corriger dans `seed_votes_cles.py`, regénérer le
site **et** l'image, puis consigner la cause dans `15-journal-des-problemes.md`.

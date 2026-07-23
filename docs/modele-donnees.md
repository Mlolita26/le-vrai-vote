# Modèle de données

## Trois idées structurantes

1. **Le pivot est `personnes`, pas « candidats ».** Un même individu est successivement député, ministre, puis candidat : une seule fiche identité, à laquelle s'accrochent tous ses rôles dans le temps via `mandats`.
2. **Tout est daté et sourcé.** Chaque fait porte une date et pointe vers `sources`.
3. **`votes_cles` ne duplique pas `scrutins`** : c'est une couche éditoriale au-dessus d'un scrutin réel.

## Tables

### personnes (pivot identité)
`id (uuid, PK)`, `nom`, `prenom`, `naissance (date)`, `slug`.

### mandats (rôles datés)
`id (PK)`, `personne_id (FK)`, `type` (depute | senateur | eurodepute | ministre | maire | conseiller | …), `debut (date)`, `fin (date, nullable)`, `detail`.
Sert à déterminer si une personne était en poste à la date d'un scrutin (logique « non concerné »).

### scrutins (brut)
`id (PK)`, `chambre` (an | senat | pe), `numero`, `objet`, `date`, `source_id (FK)`.

### positions_vote (brut, jointure)
`personne_id (FK)`, `scrutin_id (FK)`, `position` (pour | contre | abstention | absent).
Clé primaire composite (personne_id, scrutin_id). Gros volume.

### presence (brut)
`personne_id (FK)`, `type` (scrutin | commission | seance), `date`, `statut` (present | absent | excuse), `source_id (FK)`.

### thematiques (éditorial)
`id (PK)`, `libelle`, `ordre`.

### votes_cles (éditorial)
`id (PK)`, `scrutin_id (FK)`, `thematique_id (FK)`, `resume` (phrase neutre), `source_resume` (URL dossier législatif), `contexte` (texte), `ordre`.
Champ nuance par position : voir table `nuances` ou champ optionnel sur `positions_vote` selon implémentation.

### declarations (mixte)
`id (PK)`, `personne_id (FK)`, `type` (interets | patrimoine | discours | programme), `contenu`, `date`, `source_id (FK)`.

### affaires_judiciaires (manuel)
`id (PK)`, `personne_id (FK)`, `statut` (mise_en_examen | condamnation_definitive | relaxe | …), `date`, `detail`, `presomption (bool)`, `source_id (FK)`.

### sources (transverse)
`id (PK)`, `url`, `type`, `collecte (date)`.

## Relations

```
PERSONNES ─1:N─ MANDATS
PERSONNES ─1:N─ POSITIONS_VOTE ─N:1─ SCRUTINS
PERSONNES ─1:N─ PRESENCE
PERSONNES ─1:N─ DECLARATIONS
PERSONNES ─1:N─ AFFAIRES_JUDICIAIRES
SCRUTINS  ─1:1─ VOTES_CLES ─N:1─ THEMATIQUES
SOURCES   ─1:N─ (SCRUTINS, DECLARATIONS, AFFAIRES_JUDICIAIRES, PRESENCE)
```

## Séparation brut / éditorial / calculé

- **Brut** (miroir automatique, jamais édité à la main) : personnes, mandats, scrutins, positions_vote, presence.
- **Éditorial** (curation humaine) : thematiques, votes_cles (+ résumés, nuances), affaires_judiciaires.
- **Calculé** (régénéré à chaque import) : couverture, agrégats de présence.

## Logique de couverture (affichage à trois états)

Pour chaque `personne` et chaque `vote_cle`, calculer l'état à afficher :

```
si la personne n'a jamais eu de mandat parlementaire pertinent
    → "indisponible"
sinon si aucun mandat n'était actif à la date du scrutin
    → "non concerné"
sinon si une position existe dans positions_vote
    → position (pour | contre | abstention | absent)
sinon
    → "à importer"   (donnée pas encore chargée)
```

Un champ calculé `couverture` par personne (ex. « 58/72 votes documentés, 14 hors mandat ») alimente les badges.

## Disponibilité des données par type de candidat

| Type de candidat | positions_vote | presence | mandats | declarations | affaires |
|---|---|---|---|---|---|
| Député / sénateur actuel | complet | complet | complet | complet | si applicable |
| Ancien parlementaire | complet (période) | complet (période) | complet | complet | si applicable |
| Eurodéputé | votes UE seulement | partiel (PE) | complet | complet | si applicable |
| Ministre non-parlementaire | aucun | aucun | décrets JO | complet | si applicable |
| Élu local (maire, région) | aucun | aucun | RNE | selon seuil HATVP | si applicable |
| Société civile | aucun | aucun | aucun | candidature seulement | presse seulement |

Cette matrice justifie l'affichage à trois états et interdit de « combler » un vide par une supposition.

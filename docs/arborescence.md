# Arborescence, pages et composants

## Trois principes d'architecture

1. **Deux portes d'entrée, un cœur.** L'utilisateur arrive avec une question sur une *personne* (« que vaut vraiment X ? ») ou sur un *sujet* (« qui défend quoi sur l'immigration ? »). Les deux chemins sont d'égale importance et convergent vers la fiche vote clé.
2. **La comparaison est le produit.** Le tableau candidats × positions est ce que personne d'autre n'offre et ce qui sera partagé sur les réseaux. Section à part entière, pas fonctionnalité cachée.
3. **La méthode est de premier niveau.** « Comment on choisit les votes clés » accessible en un clic depuis n'importe où.

## Plan du site

```
Accueil
├── Candidats (liste, recherche, filtres)
│   └── Fiche candidat
│       ├── En bref (identité, parti, mandats)
│       ├── Votes clés (par thème)  ──┐
│       ├── Présence (indicateurs)     │
│       ├── Parcours (bio, HATVP)      │
│       ├── Justice (faits sourcés)    │
│       └── Programme                  │
├── Thématiques (10 thèmes)            │  convergence
│   └── Page thématique                │  vers
│       └── Tableau candidats × votes ─┤  la fiche
├── Comparateur (deux candidats)  ─────┘  vote clé
├── Méthode (méthodologie, sources, grille)
└── (v2) Actualité des votes (scrutins de la semaine)
```

## Détail des pages

### Accueil
Hero orienté « leurs votes, pas leurs promesses ». Recherche de candidat. Accès direct aux thèmes et au comparateur.

### Liste des candidats
Cartes avec avatar (initiales), nom, parti, archétype de mandat, et un badge de **couverture** (« 58/72 votes documentés » ou « sans mandat parlementaire »). Recherche live, filtres par bord/parti/type de mandat.

### Fiche candidat
En-tête : identité + bouton « Comparer ». Indicateurs de présence (toujours avec la médiane à côté). Onglets :
- **Votes clés** groupés par thème ; chaque ligne = titre de la loi + badge position + résumé neutre + lien source + éventuelle nuance.
- **Présence** : indicateurs séparés (scrutins, commission), évolution dans le temps.
- **Parcours** : biographie, mandats datés, déclarations HATVP.
- **Justice** : sobre, factuel, avec bandeau présomption d'innocence pour les procédures en cours. Pas de badges rouges alarmistes.
- **Programme** : positions déclarées (surtout pour les non-parlementaires).

Pour un candidat sans mandat parlementaire : bandeau explicatif + bascule sur les positions déclarées, jamais un profil vide.

### Page thématique
Tableau candidats × votes clés du thème (la vue la plus partageable). Chaque vote porte son résumé. Sur mobile : cartes empilées par vote plutôt que tableau large.

### Comparateur
Deux candidats côte à côte, positions par vote clé, **divergences surlignées** automatiquement. Résumé de loi affiché sous chaque vote.

### Méthode
Page de premier niveau : d'où viennent les données, comment sont choisis les votes clés (grille publiée), pourquoi certaines cases sont vides (trois états), neutralité des résumés, traitement du volet judiciaire.

## Composants transverses

- **Badge de position** : pour / contre / abstention / absent / non concerné / indisponible. Toujours avec texte (pas seulement couleur). Libellés centralisés.
- **Ligne de vote clé** : titre + badge + résumé + source + nuance. Réutilisée sur fiche, thème et comparateur.
- **Carte d'indicateur** : valeur + médiane de référence + période mesurée.
- **Bandeau de couverture** : explique l'état des données d'un candidat.
- **Footer permanent** : date de dernière mise à jour par catégorie de données.

## Choix de design

- **Mobile-first** ; le comparateur et les tableaux pensés d'abord en cartes empilées.
- **URLs parlantes et stables** pour le partage et le référencement.
- **Transparence dans les micro-détails** : « 58/72 votes, 14 hors mandat », médiane affichée partout, source cliquable partout.
- **Accessibilité RGAA** : contrastes, navigation clavier, jamais d'information par la couleur seule.
- **Sobriété du volet judiciaire** : le design lui-même reflète la prudence juridique.

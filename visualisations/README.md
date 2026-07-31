# Visualisations

Cartes et graphiques produits à partir de la base `data/levraivote.sqlite`. Rien
n'est saisi à la main ici : chaque nœud et chaque lien sort d'une requête sur la
base, et tout ce qui est écarté est listé dans la sortie des scripts et dans la
note de bas de carte.

## Carte du réseau (`carte_reseau.png`)

Un graphe multi-couches : candidats, votes clés, thématiques, groupes
parlementaires, institutions et sources. Le placement est calculé par simulation
de forces (ForceAtlas2) — la position d'un nœud ne dépend que de ses liens, jamais
de son étiquette politique. La couleur ne code que le type de nœud.

### Produire la carte

```bash
python visualisations/extraire_graphe.py    # base → graphe.json
python visualisations/carte_reseau.py       # graphe.json → carte_reseau.png
```

Dépendances : `networkx`, `matplotlib`, `numpy`, `adjustText`.

### Ce que contient le graphe

| Couche | Nœuds | Provenance |
|---|---|---|
| Candidats | 26 | `personnes` |
| Votes clés | 165 | `votes_cles` joint à `scrutins` |
| Thématiques | 15 | `thematiques` |
| Groupes parlementaires | 36 | `groupes_reference` + `positions_groupes` |
| Institutions | 5 | chambres de `scrutins` + HATVP |
| Sources | 52 | `sources`, regroupées par domaine |

| Relation | Arêtes | Provenance |
|---|---|---|
| Position d'un groupe sur un vote clé | 1 547 | `positions_groupes` (position majoritaire) |
| Source d'un fait | 636 | `source_id` des tables de faits |
| Position d'un candidat sur un vote clé | 534 | `positions_vote` (positions exprimées) |
| Rattachement d'un vote clé à sa thématique | 165 | `votes_cles.thematique_id` |
| Chambre du scrutin | 165 | `scrutins.chambre` |
| Justification éditoriale d'une position de groupe | 129 | `justifications_groupes` |
| Appartenance à un groupe | 50 | `groupes_reference` |
| Mandat | 50 | `mandats` |
| Accord de vote entre deux candidats | 34 | calculé sur `positions_vote` |

### Choix de méthode, et leurs limites

- **L'accord de vote est une mesure, pas une opinion.** Pour chaque paire de
  candidats, on compte les scrutins où tous deux ont exprimé une position et on
  divise les positions identiques par ce total. Une paire est écartée sous
  100 scrutins partagés : en dessous, le taux n'est pas lisible. 34 paires
  qualifient sur les 325 possibles.
- **L'absence n'est pas une position.** Seuls `pour`, `contre` et `abstention`
  produisent une arête. Les 100 541 absences de la base ne sont pas des liens.
- **Les domaines institutionnels sont rabattus sur leur institution.** Le portail
  open data de l'Assemblée *est* l'Assemblée ; le garder à part créait un nœud
  relié à presque tout, qui écrasait la carte. La couche « source » ne contient
  donc que la presse, les partis et les jeux de données tiers.
- **Les forces d'attraction sont pondérées par type de relation.** Les liens
  structurants (thématique, accord de vote) pèsent plus que les liens
  documentaires, sans quoi le graphe forme une pelote illisible. Toutes les
  forces viennent de liens réels — c'est leur poids relatif qui est réglé, pas
  leur existence.
- **Ce qui n'est pas montré est dit.** 22 groupes de faible présence ne sont pas
  nommés faute de place, et 10 domaines sources sans lien exploitable sont
  écartés : les deux chiffres figurent sur la carte elle-même.
- **La couleur ne porte jamais seule l'information** (règle RGAA du projet) : le
  type d'un nœud se lit aussi à sa forme, et les thématiques, institutions et
  candidats sont tous nommés.

### Palette

Slots 1, 2, 3 et 7 de la palette du projet, validées en mode « toutes paires » :
pire écart ΔE 9,2 en vision daltonienne, 16,3 en vision normale. L'aqua des
thématiques passe sous 3:1 de contraste sur le fond clair — d'où l'étiquette
visible sur chaque thématique, qui est la contrepartie exigée.

## Pièce plastique (`neurones.png`)

Un objet graphique, pas un graphique : ni titre, ni légende, ni texte, uniquement
des cercles et des filaments. Il n'est pas fait pour être décodé.

```bash
python visualisations/neurones.py                                          # fond sombre
python visualisations/neurones.py data/... neurones_clair.png 314159 clair  # fond ivoire
python visualisations/neurones.py data/... essai.png 7 sombre               # autre tirage
```

Arguments : base, sortie, graine, thème (`sombre` ou `clair`).

### Ce qu'il y a dedans

61 556 filaments, sur les 11 944 scrutins où au moins un parlementaire de la base
s'est exprimé : **20 242 positions exprimées** (pour / contre / abstention) et
**41 314 absences** sur ces mêmes scrutins. Une absence est tracée comme un fil
sombre — c'est le tissu de fond. Une seule ligne est écartée (une personne sans
aucun vote exprimé n'a pas d'ancrage d'où partir).

### Aléatoire assumé, données préservées

C'est la seule visualisation du dossier où une part du placement est arbitraire.
La frontière est nette :

| Aléatoire (choix plastique) | Issu des données |
|---|---|
| Position des 14 ancrages | Position des 11 944 points de scrutin |
| Nombre et angle des ramifications | Étendue de chaque touffe (nombre de scrutins) |
| Longueur des giclées | Teinte de chaque ancrage (rang sur l'axe d'accord) |
| | Couleur de chaque filament (sens de la position) |
| | Densité de la masse centrale (le vote commun) |

Le tirage est reproductible (graine fixée) : la même commande redonne la même
image. Celui retenu, 314159, a été choisi parmi six comparés.

### Les réglages de forme

Quatre constantes en tête de fichier commandent l'allure générale :

| Constante | Effet |
|---|---|
| `TORSION` | Enroulement des faisceaux. Les points de contrôle des courbes pivotent autour du centre, d'autant plus que le rayon est petit ; les extrémités ne bougent pas, donc aucun nœud ne quitte la place que la donnée lui assigne. À 0, les touffes rayonnent droit ; à 0,85, elles s'enroulent en tourbillon. |
| `VIDE_CENTRAL` | Rayon minimal imposé aux scrutins partagés, ce qui creuse le trou au milieu. L'angle reste celui du barycentre des votants — le scrutin demeure du côté de ceux qui l'ont voté. |
| `DEBORD` | Longueur des mèches au-delà de leur point d'attache. |
| `EVASEMENT` | Écartement des mèches en bout : plus une mèche est longue, plus elle quitte l'axe de sa brindille, ce qui donne le plumeau. |

Le nombre d'ancrages couvre tout le cercle par secteurs tirés au sort : sans cette
stratification, un gros éventail dominait et le reste du cadre se vidait.

### Résolution

`PPP = 600`, soit 8 400 × 8 400 px (≈ 63 Mo par image) et 44 points
d'échantillonnage par courbe — à 24, les faisceaux montraient des facettes au
zoom. Le format suit l'extension du fichier de sortie : un `.pdf` ou un `.svg`
donne un tracé vectoriel, net à n'importe quel zoom, mais lourd à ouvrir
(≈ 185 000 chemins).

### Palette

Bleu, blanc et rouge du drapeau, saturés, sur fond noir ou ivoire, à quelques
millièmes d'opacité par trait : c'est la superposition de milliers de traits qui
construit la couleur, pas l'opacité de chacun. Passée au validateur, cette palette
**échoue** aux critères d'un graphique — et c'est voulu : sans légende ni
étiquette, rien n'a besoin d'être discriminable. Ce compromis ne serait pas
acceptable sur une visualisation destinée au site.

Sur fond clair, ce n'est pas une inversion : les traits s'y accumulent en encre au
lieu de s'additionner en lumière, donc le blanc du milieu de rampe devient un gris
argenté — un blanc pur ne laisserait aucune trace.

## Copies dans OneDrive

Les PNG sont recopiés datés dans
`OneDrive - CGIAR/Documents/presidentielles/visualisations/` pour consultation.
Le code, lui, reste hors OneDrive (règle du projet).

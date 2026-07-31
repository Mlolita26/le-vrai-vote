"""Rendu plastique des positions de vote : une pièce graphique, pas un graphique.

Aucun titre, aucune légende, aucun texte — l'image n'est pas faite pour être
décodée. La structure, elle, sort entièrement de la base.

  · un corps cellulaire = un parlementaire de la base (14 ont exprimé un vote)
  · un point pâle       = un scrutin
  · un filament clair   = une position exprimée (61 557 lignes en tout)
  · un filament sombre  = une absence sur un scrutin où d'autres ont voté

Placement — ce qui est aléatoire et ce qui ne l'est pas :

  · les 14 ancrages sont dispersés au hasard (tirage reproductible), avec une
    distance minimale entre eux. C'est un choix plastique : l'effet
    d'éclaboussure vient de ce désordre, et non des données.
  · les 11 944 points de scrutin, en revanche, sont placés par leurs votants
    réels. Un scrutin voté par un seul part en dendrite depuis son ancrage ; un
    scrutin partagé est tiré vers le barycentre de ceux qui l'ont voté — la masse
    dense du centre est donc, littéralement, le vote commun.
  · les filaments passent par trois niveaux de ramification, ce qui les fait
    converger en faisceaux au lieu de rayonner en droites.
  · l'étendue de chaque touffe suit le nombre de scrutins concernés : les volumes
    inégaux viennent des données.

Teintes : chaque ancrage reçoit une teinte prise sur une rampe bleu → blanc →
rouge selon son rang sur le premier axe d'accord de vote, infléchie par le sens de
chaque position. La couleur suit donc le comportement de vote, mais elle n'est là
que pour faire tableau : désaturée et transparente, elle échoue volontairement aux
critères de lisibilité d'un graphique.

Usage : python visualisations/neurones.py [base] [sortie.png] [graine] [sombre|clair]
"""
import json
import sqlite3
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
SORTIE_DEFAUT = Path(__file__).resolve().parent / "neurones.png"

EXPRIMEES = ("pour", "contre", "abstention")
# Tirage retenu parmi six comparés : c'est celui qui remplit le mieux le cadre.
GRAINE = 314159

# Deux thèmes. Sur fond sombre les traits s'additionnent en lumière, donc ils sont
# clairs ; sur fond clair ils s'accumulent en encre, donc il faut des teintes
# profondes — un bleu pâle sur blanc disparaîtrait, et le « blanc » de la rampe
# devient un gris chaud pour rester visible.
#
# Les opacités sont très basses (quelques millièmes par passe) : c'est la
# superposition de milliers de traits qui construit la matière, et non l'opacité
# de chacun. Plus haut, le centre se refermait en masse opaque et perdait tout
# le tissu interne.
THEMES = {
    "sombre": {
        "fond": "#05060a",
        # Bleu, blanc, rouge du drapeau, saturés. La transparence extrême fait
        # tout le travail : à quelques millièmes d'opacité, une couleur vive
        # devient une teinte, et les superpositions mélangent les trois.
        # Bleu, blanc, rouge du drapeau, saturés. Volontairement un bleu franc et
        # non le marine officiel : sur fond noir, à quelques millièmes d'opacité,
        # le marine s'éteint. Version validée — ne pas y toucher.
        "rampe": np.array([
            [0.00, 0.22, 1.00],
            [0.20, 0.48, 1.00],
            [1.00, 1.00, 1.00],
            [1.00, 0.26, 0.32],
            [0.88, 0.00, 0.06],
        ]),
        "positions": {
            "pour": np.array([0.00, 0.28, 1.00]),
            "abstention": np.array([1.00, 1.00, 1.00]),
            "contre": np.array([0.88, 0.00, 0.06]),
        },
        "absence": (0.17, 0.20, 0.28),
        "alpha_absence": 0.017,
        "passes": [(3.6, 0.0060), (1.4, 0.0155), (0.40, 0.043)],
        "points": ("#e9edf4", 0.145),
        "coeur_corps": "#f4f7fb",
        "alpha_coeur": 0.26,
        "halos": ((7.0, 0.009), (3.0, 0.017), (1.5, 0.029)),
    },
    "clair": {
        "fond": "#fbfaf7",
        # Mêmes couleurs vives, mais le blanc du milieu devient un gris argenté :
        # sur fond ivoire, un blanc pur ne laisserait aucune trace.
        # Sur fond ivoire, le marine du drapeau passe tel quel.
        "rampe": np.array([
            [0.00, 0.02, 0.50],
            [0.04, 0.16, 0.66],
            [0.70, 0.70, 0.72],
            [0.94, 0.16, 0.22],
            [0.85, 0.00, 0.06],
        ]),
        "positions": {
            "pour": np.array([0.00, 0.04, 0.57]),
            "abstention": np.array([0.68, 0.68, 0.70]),
            "contre": np.array([0.88, 0.00, 0.06]),
        },
        "absence": (0.62, 0.61, 0.58),
        "alpha_absence": 0.009,
        "passes": [(3.6, 0.0030), (1.4, 0.0078), (0.40, 0.022)],
        "points": ("#3a3a38", 0.08),
        "coeur_corps": "#1a1a19",
        "alpha_coeur": 0.20,
        "halos": ((7.0, 0.005), (3.0, 0.009), (1.5, 0.016)),
    },
}

THEME = THEMES["sombre"]
POIDS_POSITION = 0.35

NB_TRONCS = 5            # ramifications principales par corps
NB_RAMEAUX = 5           # sous-ramifications par tronc
NB_BRINDILLES = 4        # extremites par sous-ramification
# Échantillonnage des courbes. À 24 points, les faisceaux montraient des facettes
# dès qu'on zoomait ; 44 les rend lisses à l'échelle de l'affiche.
POINTS_COURBE = 44
POINTS_ABSENCE = 24
# 600 ppp : 8400 × 8400 px. La sortie peut aussi être un .pdf ou .svg — le format
# suit l'extension du fichier — et le tracé est alors vectoriel, donc net à
# n'importe quel zoom.
PPP = 600

# --- Réglages de forme -------------------------------------------------------
# Torsion : chaque point de contrôle est pivoté autour du centre d'un angle qui
# décroît avec le rayon. Les extrémités ne bougent pas, seule la courbure change,
# si bien que les faisceaux s'enroulent au lieu de rayonner droit.
TORSION = 0.85
# Rayon minimal imposé aux scrutins partagés : sans lui le vote commun remplit le
# centre, alors que la forme visée est un anneau troué. L'angle, lui, reste celui
# du barycentre des votants — c'est-à-dire la donnée.
VIDE_CENTRAL = 0.40
# Débord des mèches au-delà de leur point d'attache, et évasement en bout.
DEBORD = 1.22
EVASEMENT = 0.42


def rampe(t):
    """Interpolation linéaire dans RAMPE pour t dans [0, 1]."""
    r = THEME["rampe"]
    x = np.clip(t, 0, 1) * (len(r) - 1)
    i = int(np.floor(x))
    if i >= len(r) - 1:
        return r[-1]
    f = x - i
    return r[i] * (1 - f) + r[i + 1] * f


def torsion(points, force=TORSION):
    """Pivote des points autour de l'origine, d'autant plus que le rayon est petit."""
    p = np.atleast_2d(points)
    r = np.linalg.norm(p, axis=1)
    a = force / (r + 0.55)
    cos, sin = np.cos(a), np.sin(a)
    return np.stack([p[:, 0] * cos - p[:, 1] * sin,
                     p[:, 0] * sin + p[:, 1] * cos], axis=1)


def charger(base):
    """Toutes les lignes de vote portant sur un scrutin où quelqu'un s'est exprimé."""
    con = sqlite3.connect(base)
    con.execute(f"""CREATE TEMP TABLE vus AS
                    SELECT DISTINCT scrutin_id FROM positions_vote
                    WHERE position IN {EXPRIMEES}""")
    exprimees = defaultdict(list)
    absences = []
    for personne, scrutin, position in con.execute(
            """SELECT pv.personne_id, pv.scrutin_id, pv.position
               FROM positions_vote pv JOIN vus v ON v.scrutin_id = pv.scrutin_id"""):
        if position in EXPRIMEES:
            exprimees[scrutin].append((personne, position))
        else:
            absences.append((personne, scrutin))
    con.close()
    return exprimees, absences


def noms_des_personnes(base):
    """Identifiant → « Prénom Nom », pour étiqueter les ancrages à l'export."""
    con = sqlite3.connect(base)
    noms = {i: f"{prenom} {nom}" for i, prenom, nom
            in con.execute("SELECT id, prenom, nom FROM personnes")}
    con.close()
    return noms


def distances_accord(exprimees, personnes):
    """Distance = 1 − taux d'accord sur les scrutins communs."""
    par_personne = defaultdict(dict)
    for sid, votes in exprimees.items():
        for p, pos in votes:
            par_personne[p][sid] = pos

    idx = {p: i for i, p in enumerate(personnes)}
    d = np.ones((len(personnes), len(personnes)))
    np.fill_diagonal(d, 0.0)
    for a, b in combinations(personnes, 2):
        va, vb = par_personne[a], par_personne[b]
        communs = va.keys() & vb.keys()
        if len(communs) < 100:
            # Trop peu de scrutins partagés pour mesurer : distance maximale,
            # plutôt que de leur inventer une proximité.
            continue
        taux = sum(1 for s in communs if va[s] == vb[s]) / len(communs)
        d[idx[a], idx[b]] = d[idx[b], idx[a]] = 1.0 - taux
    return d


def mds(distances):
    """Positionnement multidimensionnel classique (Torgerson)."""
    n = len(distances)
    centrage = np.eye(n) - np.ones((n, n)) / n
    b = -0.5 * centrage @ distances**2 @ centrage
    valeurs, vecteurs = np.linalg.eigh(b)
    ordre = np.argsort(valeurs)[::-1][:2]
    return vecteurs[:, ordre] * np.sqrt(np.maximum(valeurs[ordre], 1e-9))


def arborescence(exprimees, rng):
    """Corps cellulaires, teintes et deux niveaux de ramification."""
    personnes = sorted({p for votes in exprimees.values() for p, _ in votes})
    corps = mds(distances_accord(exprimees, personnes))
    corps -= corps.mean(axis=0)
    corps /= np.abs(corps).max()
    idx = {p: i for i, p in enumerate(personnes)}

    # Teinte : rang sur le premier axe d'accord → position sur la rampe. Le rang
    # est calculé avant l'étalement, sur les distances mesurées.
    rang = np.argsort(np.argsort(corps[:, 0])) / max(len(personnes) - 1, 1)
    # Léger désordre de teinte : une rampe parfaitement ordonnée fait dégradé
    # d'atelier plutôt que tissu vivant.
    teintes = {p: rampe(rang[idx[p]] + rng.normal(0, 0.06)) for p in personnes}

    # Volume : la racine du nombre de scrutins votés en solitaire. C'est la donnée
    # qui décide de la taille de chaque touffe.
    solos = defaultdict(int)
    for votes in exprimees.values():
        if len(votes) == 1:
            solos[votes[0][0]] += 1
    maxi = max(solos.values())
    # Écart resserré à un rapport 2:1 : à pleine échelle, le parlementaire le plus
    # actif produisait une touffe quatre fois plus grande que les autres, qui
    # avalait la composition.
    portee = {p: 0.78 + 0.62 * (solos.get(p, 0) / maxi) ** 0.45 for p in personnes}

    # Dispersion aléatoire des ancrages. Ni anneau ni grille : des rayons tirés au
    # sort, une distance minimale respectée, ce qui produit des voisinages
    # inégaux — certains corps se touchent, d'autres restent isolés. C'est ce
    # désordre qui donne l'allure d'éclaboussure. Les 11 944 points de scrutin,
    # eux, restent placés par leurs votants réels.
    # Un secteur par ancrage, tiré au hasard à l'intérieur : le cercle est couvert
    # en entier — sans quoi un gros éventail domine et le reste du cadre se vide —
    # mais les écarts restent irréguliers. Rayon sur un anneau large, ce qui
    # dégage le centre.
    secteurs = rng.permutation(len(personnes))
    nouveau = np.zeros_like(corps)
    for i, k in enumerate(secteurs):
        angle = 2 * np.pi * (k + rng.uniform(0.12, 0.88)) / len(personnes)
        rayon = rng.uniform(0.80, 1.20)
        nouveau[i] = rayon * np.array([np.cos(angle), np.sin(angle)])
    corps = nouveau
    # Ouverture vers l'extérieur de l'anneau, avec une forte marge de désordre :
    # les touffes s'échappent en biais, jamais toutes dans l'axe.
    angles_corps = {}
    for p in personnes:
        c = corps[idx[p]]
        angles_corps[p] = np.arctan2(c[1], c[0]) + rng.normal(0, 0.65)

    # Deux niveaux : le tronc part loin du corps, le rameau plus loin encore. Des
    # milliers de filaments partageant le même couple tronc/rameau se soudent en
    # faisceau — c'est ce qui remplace les rayons droits par des ramifications.
    ramifications = {}
    for p in personnes:
        c = corps[idx[p]]
        base = angles_corps[p]
        # Nombre de troncs tiré au sort, et ouverture large : certaines touffes
        # giclent dans toutes les directions, d'autres restent en éventail serré.
        nb_troncs = int(rng.integers(4, 10))
        ouverture = rng.uniform(1.1, np.pi)
        troncs = []
        for angle_tronc in base + rng.uniform(-ouverture, ouverture, nb_troncs):
            # Loi à queue lourde : la plupart des troncs sont courts, quelques-uns
            # partent très loin — ce sont les giclées.
            long_tronc = portee[p] * min(0.26 * rng.pareto(1.7) + 0.30, 1.55)
            pt_tronc = c + long_tronc * np.array(
                [np.cos(angle_tronc), np.sin(angle_tronc)])
            rameaux = []
            nb_rameaux = int(rng.integers(3, 7))
            for angle_rameau in angle_tronc + rng.uniform(-0.75, 0.75, nb_rameaux):
                long_rameau = portee[p] * rng.uniform(0.14, 0.55)
                pt_rameau = pt_tronc + long_rameau * np.array(
                    [np.cos(angle_rameau), np.sin(angle_rameau)])
                # Une extrémité sur quatre est une grappe satellite : un paquet
                # compact projeté à distance, comme une goutte de peinture
                # détachée du jet.
                satellite = rng.random() < 0.24
                dispersion = 0.035 if satellite else 0.0
                brindilles = []
                nb_br = int(rng.integers(2, 6))
                for angle_br in angle_rameau + rng.uniform(-0.55, 0.55, nb_br):
                    long_br = portee[p] * rng.uniform(0.08, 0.32)
                    brindilles.append((angle_br, pt_rameau + long_br * np.array(
                        [np.cos(angle_br), np.sin(angle_br)]), dispersion))
                rameaux.append((pt_rameau, brindilles))
            troncs.append((pt_tronc, rameaux))
        ramifications[p] = troncs
    return personnes, corps, idx, teintes, portee, ramifications


def tisser(exprimees, absences, corps, idx, portee, ramifications, rng):
    """Position de chaque scrutin, puis tracé de chaque filament."""
    pos_scrutin = {}
    brins = []  # (points, couleur_base, position)

    for sid, votes in exprimees.items():
        votants = [p for p, _ in votes]

        if len(votants) == 1:
            p = votants[0]
            troncs = ramifications[p]
            pt_tronc, rameaux = troncs[rng.integers(len(troncs))]
            pt_rameau, brindilles = rameaux[rng.integers(len(rameaux))]
            angle, pt_brindille, dispersion = brindilles[rng.integers(len(brindilles))]
            if dispersion:
                # Grappe satellite : le paquet se referme sur lui-même au lieu
                # de s'effiler.
                feuille = pt_brindille + rng.normal(0, dispersion, 2)
            else:
                # Distribution longue : quelques scrutins partent loin, la plupart
                # restent courts — c'est l'effilement des dendrites.
                r = portee[p] * DEBORD * (0.04 + rng.gamma(1.9, 0.10))
                # Évasement : plus la mèche est longue, plus elle s'écarte de
                # l'axe de sa brindille — les bouts se déploient en plumeau.
                ecart = rng.normal(0, EVASEMENT * min(r / portee[p], 1.0) + 0.10)
                feuille = pt_brindille + r * np.array(
                    [np.cos(angle + ecart), np.sin(angle + ecart)])
            pos_scrutin[sid] = feuille
            # Quatre points de contrôle sur cinq positions : la courbe épouse la
            # ramification tronc → rameau → brindille → feuille.
            brins.append((np.array([corps[idx[p]],
                                    0.35 * pt_tronc + 0.65 * pt_rameau,
                                    pt_brindille, feuille]),
                          p, votes[0][1]))
        else:
            # Plus il y a de votants, plus le scrutin est tiré vers le barycentre.
            centre = corps[[idx[p] for p in votants]].mean(axis=0)
            pos = centre + rng.normal(0, 0.26 / len(votants) ** 0.7, 2)
            # Repoussé hors du trou central, sans changer sa direction : le
            # scrutin reste du côté de ceux qui l'ont voté.
            r = np.linalg.norm(pos)
            if r < VIDE_CENTRAL:
                pos = pos / max(r, 1e-9) * (VIDE_CENTRAL + abs(rng.normal(0, 0.13)))
            pos_scrutin[sid] = pos
            for p, position in votes:
                depart = corps[idx[p]]
                # Le nombre de troncs varie d'un corps à l'autre depuis le passage
                # en dispersion aléatoire : on tire dans la liste réelle.
                pt_tronc = ramifications[p][rng.integers(len(ramifications[p]))][0]
                # Le filament sort par un tronc avant de rejoindre le noyau :
                # il s'incurve au lieu de tirer une corde droite.
                milieu = 0.45 * pt_tronc + 0.55 * pos
                brins.append((np.array([depart, pt_tronc, milieu, pos]), p, position))

    # Absences : le scrutin est ailleurs, dans le territoire d'un autre. Le brin
    # traverse en s'infléchissant vers le centre, ce qui tisse le fond.
    centre_global = corps.mean(axis=0)
    fils_absence = []
    ignorees = 0
    for p, sid in absences:
        cible = pos_scrutin.get(sid)
        # Une personne qui n'a jamais exprimé de vote n'a pas de corps cellulaire :
        # ses absences n'ont nulle part d'où partir.
        if cible is None or p not in idx:
            ignorees += 1
            continue
        depart = corps[idx[p]]
        milieu = (depart + cible) / 2
        infl = milieu + 0.55 * (centre_global - milieu) + rng.normal(0, 0.05, 2)
        fils_absence.append((np.array([depart, infl, infl, cible]), p))

    if ignorees:
        print(f"{ignorees} absences ignorées (personne sans vote exprimé)")
    return pos_scrutin, brins, fils_absence


def bezier_lot(points, n=POINTS_COURBE):
    """Échantillonne un lot de Béziers cubiques : (m, 4, 2) → (m, n, 2).

    Les deux points de contrôle intermédiaires sont pivotés par la torsion : les
    extrémités ne bougent donc pas — un nœud reste où la donnée l'a mis — mais la
    courbe s'enroule au lieu de filer droit.
    """
    p = np.asarray(points).copy()
    p[:, 1] = torsion(p[:, 1])
    p[:, 2] = torsion(p[:, 2])
    t = np.linspace(0, 1, n)[None, :, None]
    return ((1 - t) ** 3 * p[:, None, 0] + 3 * (1 - t) ** 2 * t * p[:, None, 1]
            + 3 * (1 - t) * t**2 * p[:, None, 2] + t**3 * p[:, None, 3])


def rendre(exprimees, absences, sortie, noms=None):
    noms = noms or {}
    donnees_votes = exprimees
    rng = np.random.default_rng(GRAINE)
    personnes, corps, idx, teintes, portee, ramifications = arborescence(exprimees, rng)
    pos_scrutin, brins, fils_absence = tisser(
        exprimees, absences, corps, idx, portee, ramifications, rng)

    fig, ax = plt.subplots(figsize=(14, 14), dpi=PPP)
    fig.patch.set_facecolor(THEME["fond"])
    ax.set_facecolor(THEME["fond"])
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # ------------------------------------------------ fond : les absences
    # Teintées par le corps dont elles partent et fortement assombries : le
    # tissu de fond garde la couleur de son origine sans venir au premier plan.
    absences_par_teinte = defaultdict(list)
    for pts, p in fils_absence:
        absences_par_teinte[tuple(0.34 * teintes[p] + 0.66 * np.array(
            THEME["absence"]))].append(pts)
    for couleur, lot in absences_par_teinte.items():
        ax.add_collection(LineCollection(
            list(bezier_lot(lot, n=POINTS_ABSENCE)), colors=[couleur], linewidths=0.30,
            alpha=THEME["alpha_absence"], capstyle="round", zorder=1))

    # ------------------------------------- filaments des positions exprimées
    # Couleur = teinte du corps, infléchie vers la teinte de la position.
    groupes = defaultdict(list)
    for pts, p, position in brins:
        couleur = tuple((1 - POIDS_POSITION) * teintes[p]
                        + POIDS_POSITION * THEME["positions"][position])
        groupes[couleur].append(pts)

    # Trois passes : halo large presque invisible, corps du trait, cœur net.
    # C'est l'empilement qui fait la matière et le volume.
    for couleur, lot in groupes.items():
        courbes = list(bezier_lot(lot))
        for largeur, alpha in THEME["passes"]:
            ax.add_collection(LineCollection(
                courbes, colors=[couleur], linewidths=largeur, alpha=alpha,
                capstyle="round", zorder=2))

    # ------------------------------------------------------------ les points
    pts = np.array(list(pos_scrutin.values()))
    couleur_pts, alpha_pts = THEME["points"]
    ax.scatter(pts[:, 0], pts[:, 1], s=0.7, c=couleur_pts, alpha=alpha_pts,
               linewidths=0, zorder=3)

    # Corps cellulaires : halo dégradé puis petit disque. Uniquement des cercles,
    # et volontairement discrets — de gros pastilles blanches faisaient
    # repères de schéma au milieu d'une image qui n'en veut pas.
    tailles = np.array([34 + 66 * (portee[p] / max(portee.values())) ** 2
                        for p in personnes])
    couleurs_corps = [tuple(teintes[p]) for p in personnes]
    for facteur, alpha in THEME["halos"]:
        ax.scatter(corps[:, 0], corps[:, 1], s=tailles * facteur,
                   c=couleurs_corps, alpha=alpha, linewidths=0, zorder=4)
    ax.scatter(corps[:, 0], corps[:, 1], s=tailles * 0.30,
               c=THEME["coeur_corps"], alpha=THEME["alpha_coeur"],
               linewidths=0, zorder=5)

    # Cadrage sur le cœur de la matière : quelques scrutins très excentrés ne
    # doivent pas imposer un cadre à moitié vide.
    ax.set_aspect("equal")
    bornes = np.percentile(pts, [0.6, 99.4], axis=0)
    demi = (bornes[1] - bornes[0]).max() / 2 * 1.06
    milieu = bornes.mean(axis=0)
    ax.set_xlim(milieu[0] - demi, milieu[0] + demi)
    ax.set_ylim(milieu[1] - demi, milieu[1] + demi)

    # Coordonnées des ancrages dans l'image produite. Sans cet export, impossible
    # de poser une étiquette au bon endroit sur un recadrage : le carrousel n'a
    # aucun moyen de retrouver où sont tombés les corps cellulaires.
    fig.canvas.draw()
    hauteur_px = fig.get_size_inches()[1] * PPP
    ecran = ax.transData.transform(corps)
    exprimes = defaultdict(int)
    for votes in donnees_votes.values():
        for p, _ in votes:
            exprimes[p] += 1
    ancrages = [{
        "nom": noms.get(p, str(p)),
        "x": round(float(ecran[idx[p], 0]), 1),
        "y": round(float(hauteur_px - ecran[idx[p], 1]), 1),
        "portee": round(float(portee[p]), 3),
        "positions_exprimees": exprimes[p],
    } for p in personnes]
    Path(sortie).with_suffix(".ancrages.json").write_text(
        json.dumps({"image": Path(sortie).name,
                    "largeur": int(fig.get_size_inches()[0] * PPP),
                    "hauteur": int(hauteur_px),
                    "ancrages": ancrages}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    fig.savefig(sortie, dpi=PPP, facecolor=THEME["fond"])
    plt.close(fig)
    return len(brins), len(fils_absence), len(pos_scrutin), len(personnes)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else SORTIE_DEFAUT
    if len(sys.argv) > 3:
        globals()["GRAINE"] = int(sys.argv[3])
    if len(sys.argv) > 4:
        globals()["THEME"] = THEMES[sys.argv[4]]
    exprimees, absences = charger(base)
    print(f"{len(exprimees)} scrutins, {len(absences)} absences")
    nb_b, nb_a, nb_s, nb_p = rendre(exprimees, absences, sortie,
                                    noms_des_personnes(base))
    print(f"{nb_b} filaments exprimés, {nb_a} filaments d'absence, "
          f"{nb_s} points, {nb_p} corps")
    print(f"écrit : {sortie}")


if __name__ == "__main__":
    main()

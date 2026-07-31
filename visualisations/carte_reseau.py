"""Rend la carte du réseau (PNG haute résolution) à partir de graphe.json.

Le placement des nœuds est calculé par un algorithme de force : la position
d'un nœud ne dépend que de ses liens réels, jamais de son étiquette politique.
La couleur ne code que le type de nœud ; les regroupements visibles sont donc
un résultat, pas une mise en scène.

Usage : python visualisations/carte_reseau.py [graphe.json] [sortie.png]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from adjustText import adjust_text
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

DOSSIER = Path(__file__).resolve().parent
GRAPHE_DEFAUT = DOSSIER / "graphe.json"
SORTIE_DEFAUT = DOSSIER / "carte_reseau.png"

# --- Palette (validée : all-pairs, pire ΔE CVD 9,2 · vision normale 16,3) -----
SURFACE = "#fcfcfb"
ENCRE = "#0b0b0b"
ENCRE_2 = "#52514e"
SOURDINE = "#898781"

COULEURS = {
    "candidat": "#2a78d6",     # slot 1 — bleu
    "vote": "#eb6834",         # slot 2 — orange
    "theme": "#1baf7a",        # slot 3 — aqua (étiqueté : règle de relief)
    "groupe": "#4a3aa7",       # slot 7 — violet
    "source": SOURDINE,        # substrat documentaire, pas une série
    "institution": ENCRE,      # ancrage structurel
}
LIBELLES_TYPES = {
    "candidat": "Candidat ou candidate",
    "vote": "Vote clé",
    "theme": "Thématique",
    "groupe": "Groupe parlementaire",
    "institution": "Institution",
    "source": "Source (par domaine)",
}
MARQUEURS = {
    "candidat": "o", "vote": "o", "theme": "s",
    "groupe": "^", "institution": "D", "source": "o",
}

# Style des arêtes par famille de relation : (couleur, épaisseur, opacité).
STYLE_ARETES = {
    "accord_vote": (COULEURS["candidat"], 2.0, 0.55),
    "vote_pour": (COULEURS["candidat"], 0.7, 0.30),
    "vote_contre": (COULEURS["candidat"], 0.7, 0.30),
    "vote_abstention": (COULEURS["candidat"], 0.6, 0.22),
    # 1 547 liens : tracés très pâles, ils font la texture de fond sans masquer
    # les rosettes thématiques.
    "groupe_pour": (COULEURS["groupe"], 0.35, 0.07),
    "groupe_contre": (COULEURS["groupe"], 0.35, 0.07),
    "groupe_abstention": (COULEURS["groupe"], 0.35, 0.06),
    "thematique": (COULEURS["theme"], 0.9, 0.45),
    "chambre": (ENCRE, 0.5, 0.16),
    "mandat": (ENCRE, 0.7, 0.28),
    "appartenance_groupe": (COULEURS["groupe"], 0.8, 0.35),
    "justification": (SOURDINE, 0.5, 0.22),
    "sourcee_par": (SOURDINE, 0.4, 0.16),
}

# Force d'attraction utilisée par le calcul de position, par famille de lien.
# Les liens structurels (thématique, chambre) tiennent les grappes ensemble ;
# les liens documentaires tirent faiblement pour ne pas écraser la structure.
ATTRACTION = defaultdict(lambda: 1.0, {
    # Structure : ce qui doit former les grappes visibles. La thématique tire fort
    # pour que chaque thème forme une rosette identifiable.
    "thematique": 50.0, "accord_vote": 8.0, "appartenance_groupe": 3.0,
    "vote_pour": 0.30, "vote_contre": 0.30, "vote_abstention": 0.25,
    "mandat": 1.0,
    # Les positions de groupe relient presque tous les groupes à presque tous les
    # votes : à pleine force elles homogénéisent la carte, donc elles tirent peu.
    "groupe_pour": 0.10, "groupe_contre": 0.10, "groupe_abstention": 0.09,
    # Couche documentaire : quelques domaines sont cités par presque tout, donc
    # une attraction forte les transformerait en aimants qui écrasent la carte.
    "chambre": 0.25, "sourcee_par": 0.12, "justification": 0.45,
})

# Rayon de répulsion par type : empêche les marques de se chevaucher, à l'échelle
# de leur taille dessinée.
RAYON = {"candidat": 22, "vote": 14, "theme": 26, "groupe": 16,
         "institution": 34, "source": 7}


def courbe(p1, p2, courbure=0.14, n=14):
    """Arc de Bézière quadratique entre deux points — le trait courbe évite la
    bouillie de segments droits quand des milliers de liens se superposent."""
    p1, p2 = np.asarray(p1), np.asarray(p2)
    milieu = (p1 + p2) / 2
    normale = np.array([-(p2 - p1)[1], (p2 - p1)[0]])
    controle = milieu + courbure * normale
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * p1 + 2 * (1 - t) * t * controle + t**2 * p2


def charger(chemin):
    g = json.loads(Path(chemin).read_text(encoding="utf-8"))
    G = nx.Graph()
    for n in g["noeuds"]:
        G.add_node(n["id"], **n)
    for a in g["aretes"]:
        # Multi-arêtes fusionnées : on garde la force d'attraction cumulée.
        poids = ATTRACTION[a["relation"]] * a["poids"]
        if G.has_edge(a["source"], a["cible"]):
            G[a["source"]][a["cible"]]["weight"] += poids
        else:
            G.add_edge(a["source"], a["cible"], weight=poids,
                       relation=a["relation"])
    return g, G


def positions(G, scaling_ratio=250.0, gravity=6.0, linlog=False, max_iter=2500):
    """Place les nœuds par simulation de forces (ForceAtlas2).

    distributed_action répartit la force des nœuds très connectés (institutions,
    domaines officiels) : sans lui, ils aspirent toute la carte et les grappes
    disparaissent. node_size active l'anti-chevauchement.
    """
    graine = nx.spring_layout(G, weight="weight", seed=20270422, iterations=200)
    tailles = {n: RAYON[G.nodes[n]["type"]] for n in G}
    return nx.forceatlas2_layout(
        G, pos=graine, weight="weight", max_iter=max_iter,
        scaling_ratio=scaling_ratio, gravity=gravity, linlog=linlog,
        distributed_action=True, strong_gravity=False,
        node_size=tailles, seed=20270422,
    )


def rendre(donnees, G, pos, sortie):
    degres = dict(G.degree(weight=None))
    # Le graphe est à peu près circulaire : la zone de dessin doit être carrée,
    # d'où la hauteur totale (bandeaux titre et notes compris).
    fig, ax = plt.subplots(figsize=(13, 15.4), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_axis_off()
    # Géométrie arrêtée ici : le désencombrement des étiquettes raisonne en
    # coordonnées écran, il ne doit plus rien bouger après lui.
    fig.subplots_adjust(left=0.03, right=0.97, top=0.905, bottom=0.095)

    # ------------------------------------------------------------------ arêtes
    # Tracées par famille, du plus discret au plus lisible, pour que les liens
    # forts restent visibles au-dessus du voile documentaire.
    ordre = sorted(STYLE_ARETES, key=lambda r: STYLE_ARETES[r][2])
    par_relation = defaultdict(list)
    for a in donnees["aretes"]:
        if a["source"] in pos and a["cible"] in pos:
            par_relation[a["relation"]].append(a)

    for relation in ordre:
        liens = par_relation.get(relation, [])
        if not liens:
            continue
        couleur, epaisseur, opacite = STYLE_ARETES[relation]
        segments, largeurs = [], []
        for a in liens:
            segments.append(courbe(pos[a["source"]], pos[a["cible"]]))
            # Le poids ne module que les liens où il porte un sens mesuré.
            facteur = a["poids"] if relation in ("accord_vote",) else 1.0
            largeurs.append(epaisseur * max(facteur, 0.25))
        ax.add_collection(LineCollection(
            segments, colors=couleur, linewidths=largeurs, alpha=opacite,
            capstyle="round", zorder=1))

    # ------------------------------------------------------------------- nœuds
    # Taille en racine du degré : l'aire reste proportionnelle au nombre de liens
    # sans qu'un moyeu à 80 liens n'avale la carte.
    tailles = {
        "candidat": lambda d: 45 + 30 * d**0.5,
        "vote": lambda d: 16 + 9 * d**0.5,
        "theme": lambda d: 95,
        "groupe": lambda d: 28 + 12 * d**0.5,
        "institution": lambda d: 230,
        "source": lambda d: 8 + 7 * d**0.5,
    }
    zordre = {"source": 2, "vote": 3, "groupe": 4, "theme": 5,
              "institution": 6, "candidat": 7}
    par_type = defaultdict(list)
    for nid, attrs in G.nodes(data=True):
        par_type[attrs["type"]].append(nid)

    for t, ids in par_type.items():
        xy = np.array([pos[i] for i in ids])
        # Anneau blanc de 2 px : sépare les marques qui se chevauchent.
        ax.scatter(xy[:, 0], xy[:, 1],
                   s=[tailles[t](degres[i]) for i in ids],
                   c=COULEURS[t], marker=MARQUEURS[t],
                   linewidths=0 if t == "source" else 1.1,
                   edgecolors=SURFACE, alpha=0.55 if t == "source" else 0.92,
                   zorder=zordre[t])

    # ---------------------------------------------------------------- libellés
    etendue = max(np.ptp([p[0] for p in pos.values()]),
                  np.ptp([p[1] for p in pos.values()]))

    # Les groupes les plus présents seulement : au-delà, les étiquettes se
    # chevauchent et plus rien n'est lisible. Les autres restent identifiables
    # par leur forme et leur couleur, et par la version interactive à venir.
    groupes_nommes = sorted(par_type["groupe"], key=lambda i: -degres[i])[:14]
    non_nommes = len(par_type["groupe"]) - len(groupes_nommes)

    # Les bornes sont fixées avant de placer les étiquettes : le désencombrement
    # travaille en coordonnées écran et a besoin du cadre définitif.
    ax.set_aspect("equal")
    marge = 0.06 * etendue
    ax.set_xlim(min(p[0] for p in pos.values()) - marge,
                max(p[0] for p in pos.values()) + marge)
    ax.set_ylim(min(p[1] for p in pos.values()) - marge,
                max(p[1] for p in pos.values()) + marge)

    a_placer = []
    for ids, taille, couleur, poids in (
        (par_type["institution"], 9.5, ENCRE, "bold"),
        (par_type["theme"], 7.2, "#0e7a55", "bold"),
        (par_type["candidat"], 7.4, "#1b4f8f", "bold"),
        (groupes_nommes, 6.0, "#3a2d85", "normal"),
    ):
        for i in ids:
            x, y = pos[i]
            a_placer.append(ax.text(
                x, y + 0.016 * etendue, G.nodes[i]["libelle"], fontsize=taille,
                color=couleur, weight=poids, ha="center", va="center", zorder=9,
                path_effects=[matplotlib.patheffects.withStroke(
                    linewidth=2.8, foreground=SURFACE)]))

    # Désencombrement : les 60 étiquettes sont écartées jusqu'à ne plus se
    # recouvrir, et reliées à leur nœud par un filet quand elles ont dû s'éloigner.
    adjust_text(a_placer, ax=ax, expand=(1.15, 1.35),
                force_text=(0.35, 0.5), force_static=(0.15, 0.25),
                max_move=28, iter_lim=400,
                arrowprops=dict(arrowstyle="-", color=SOURDINE,
                                lw=0.45, alpha=0.8, shrinkA=1, shrinkB=2))

    # ------------------------------------------------------- titre et légende
    fig.text(0.055, 0.972, "La carte des votes", fontsize=27, color=ENCRE,
             weight="bold", ha="left", va="top")
    fig.text(0.055, 0.947,
             "Ce que 22 082 scrutins officiels relient entre eux : candidats à la présidentielle 2027,\n"
             "votes clés, thématiques, groupes parlementaires, institutions et sources.",
             fontsize=10.5, color=ENCRE_2, ha="left", va="top", linespacing=1.5)

    nb = {t: len(ids) for t, ids in par_type.items()}
    entrees = [Line2D([0], [0], marker=MARQUEURS[t], color="none",
                      markerfacecolor=COULEURS[t], markeredgecolor=SURFACE,
                      markersize=9 if t != "source" else 6,
                      label=f"{LIBELLES_TYPES[t]} ({nb.get(t, 0)})")
               for t in ("candidat", "vote", "theme", "groupe", "institution", "source")]
    # Légende dans le bandeau d'en-tête, hors du dessin : posée sur le graphe,
    # elle recouvrait des nœuds.
    fig.legend(handles=entrees, loc="upper left", bbox_to_anchor=(0.055, 0.925),
               frameon=False, ncol=6, fontsize=9, labelcolor=ENCRE_2,
               handletextpad=0.5, columnspacing=1.5, borderaxespad=0.0)

    meta = donnees["meta"]
    fig.text(0.055, 0.026,
             "Lecture — chaque trait est une relation enregistrée en base : un candidat relié à un vote clé y a exprimé une position ; "
             "un trait bleu épais\nentre deux candidats indique un taux d'accord élevé, calculé sur les scrutins où tous deux ont voté "
             f"(≥ {meta['min_scrutins_partages']} scrutins partagés).\n"
             "La position des nœuds ne découle que de ces liens — les liens structurants (thématique, accord de vote) pèsent plus que les liens documentaires.\n"
             "Les regroupements visibles sont un résultat du calcul, pas un classement éditorial.\n"
             f"{non_nommes} groupes parlementaires de faible présence ne sont pas nommés, faute de place ; "
             f"{len(meta['noeuds_exclus_sans_lien'])} domaines sources sans lien exploitable sont écartés.",
             fontsize=8.6, color=ENCRE_2, ha="left", va="bottom", linespacing=1.6)
    fig.text(0.945, 0.026,
             "Le Vrai Vote\ndonnées publiques\nAN · Sénat · PE · HATVP",
             fontsize=8.2, color=SOURDINE, ha="right", va="bottom",
             linespacing=1.6)

    fig.savefig(sortie, dpi=300, facecolor=SURFACE)
    plt.close(fig)
    return sortie


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else GRAPHE_DEFAUT
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else SORTIE_DEFAUT
    donnees, G = charger(chemin)
    print(f"graphe : {G.number_of_nodes()} nœuds, {G.number_of_edges()} arêtes fusionnées")
    print("calcul des positions (force)…")
    pos = positions(G)
    print("rendu…")
    rendre(donnees, G, pos, sortie)
    print(f"écrit : {sortie}")


if __name__ == "__main__":
    import matplotlib.patheffects  # noqa: F401  (utilisé via matplotlib.patheffects)
    main()

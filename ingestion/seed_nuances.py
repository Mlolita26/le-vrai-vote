"""Nuances éditoriales : explication PERSONNELLE d'un vote (par un candidat qui
a réellement pris part au scrutin), chacune attribuée et SOURCÉE (règle : une
nuance sans source ne s'affiche pas).

Une nuance rapporte la justification déclarée par l'intéressé — elle ne juge pas.
Les justifications de PARTI (position d'un groupe, notamment au Parlement européen
quand la personne n'y siégeait pas) vivent, elles, dans `justifications_groupes`
(voir seed_justifications_groupes.py) : une seule entrée par (scrutin, groupe).

Usage : python ingestion/seed_nuances.py [chemin_base]
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

SOURCES = {
    "lcp_climat": ("https://lcp.fr/actualites/loi-climat-l-assemblee-nationale-adopte-le-texte-en-premiere-lecture-64120",
                   "LCP, 04/05/2021 — adoption de la loi Climat en première lecture, positions des groupes"),
    "politis_batho": ("https://www.politis.fr/articles/2021/04/delphine-batho-concilier-productivisme-et-ecologie-nest-pas-possible-43029/",
                      "Politis, avril 2021 — entretien avec Delphine Batho sur la loi Climat"),
    "f24_immigration": ("https://www.france24.com/fr/france/20231220-loi-immigration-le-jour-o%C3%B9-emmanuel-macron-a-offert-une-victoire-politique-%C3%A0-l-extr%C3%AAme-droite",
                        "France 24, 20/12/2023 — revirement du RN et « victoire idéologique » revendiquée"),
    "fi_ukraine_rn": ("https://www.franceinfo.fr/politique/front-national/guerre-en-ukraine-pourquoi-le-rn-a-prevu-de-s-abstenir-sur-le-vote-d-une-resolution-appelant-a-saisir-les-avoirs-russes-geles_7125243.html",
                      "franceinfo, mars 2025 — raisons de l'abstention du RN sur la résolution Ukraine"),
    "fi_findevie": ("https://www.franceinfo.fr/societe/euthanasie/presidentielle-2027-les-candidats-hostiles-a-la-loi-sur-la-fin-de-vie-vont-ils-promettre-de-l-abroger_8108582.html",
                    "franceinfo, juillet 2026 — positions des responsables politiques sur la loi aide à mourir"),
    "ici_narcotrafic": ("https://www.ici.fr/infos/politique/la-loi-contre-le-narcotrafic-definitivement-adoptee-par-le-parlement-8444881",
                        "ICI (Radio France), avril 2025 — adoption définitive de la loi narcotrafic, positions des groupes"),
    "lfa_enr": ("https://www.lafranceagricole.fr/actualites/article/836388/les-deputes-adoptent-le-projet-de-loi-sur-l-acceleration-des-energies-renouvelab",
                "La France Agricole, janvier 2023 — adoption de la loi énergies renouvelables, positions et critiques des groupes"),
    "lcp_pouvoir_achat": ("https://lcp.fr/actualites/pouvoir-d-achat-le-parlement-adopte-definitivement-le-texte-133297",
                          "LCP, 03/08/2022 — adoption définitive du paquet pouvoir d'achat, explications des groupes"),
    "fi_fraudes": ("https://www.franceinfo.fr/economie/fraude/l-assemblee-nationale-approuve-largement-un-texte-pour-lutter-contre-les-fraudes-sociales-et-fiscales_7922048.html",
                   "franceinfo, avril 2026 — adoption du texte fraudes sociales et fiscales, critiques de la gauche"),
    "cr_ukraine_2022": ("https://www.assemblee-nationale.fr/dyn/16/comptes-rendus/seance/session-ordinaire-de-2022-2023/deuxieme-seance-du-mercredi-30-novembre-2022",
                        "Compte rendu officiel de séance, AN, 30/11/2022 — explications de vote sur la résolution Ukraine"),
    "jdd_philippe": ("https://www.lejdd.fr/Politique/mariage-pour-tous-loi-renseignement-qua-vote-edouard-philippe-a-lassemblee-3331199",
                     "Le JDD — récapitulatif des votes d'Édouard Philippe à l'Assemblée (mariage pour tous, loi renseignement)"),
    "e1_tscg": ("https://www.europe1.fr/politique/Traite-europeen-ces-non-alignes-au-PS-384464",
                "Europe 1, octobre 2012 — les députés PS ayant voté contre le TSCG et leurs motifs"),
}

# (slug personne, uid scrutin, texte de la nuance PERSONNELLE, clé source)
NUANCES = [
    # Loi Climat 2021 : le groupe LFI a voté contre en jugeant le texte trop faible.
    ("jean-luc-melenchon", "VTANR5L15V3738",
     "A voté contre avec l'ensemble du groupe LFI, qui déplorait la faiblesse du texte et non son principe.",
     "lcp_climat"),
    ("clementine-autain", "VTANR5L15V3738",
     "A voté contre avec l'ensemble du groupe LFI, qui déplorait la faiblesse du texte et non son principe.",
     "lcp_climat"),
    ("francois-ruffin", "VTANR5L15V3738",
     "A voté contre avec l'ensemble du groupe LFI, qui déplorait la faiblesse du texte et non son principe.",
     "lcp_climat"),
    ("delphine-batho", "VTANR5L15V3738",
     "A voté contre en jugeant la loi « à des années-lumière de ce que disent les scientifiques », un désaccord sur l'ambition, pas sur l'objectif.",
     "politis_batho"),
    # Loi immigration 2023 : le RN annonçait voter contre puis a voté pour.
    ("marine-le-pen", "VTANR5L16V3213",
     "Le RN, qui annonçait voter contre, a finalement voté pour en séance ; Marine Le Pen a revendiqué une « victoire idéologique », y voyant une consécration de la « priorité nationale ».",
     "f24_immigration"),
    # Résolution Ukraine 2025 : abstention RN malgré un discours de soutien.
    ("marine-le-pen", "VTANR5L17V988",
     "Abstention motivée par le refus des passages sur l'adhésion de l'Ukraine à l'Union européenne, « ligne rouge » du RN, malgré un soutien déclaré à l'Ukraine.",
     "fi_ukraine_rn"),
    # Aide à mourir 2026 : opposition personnelle, liberté de vote au groupe.
    ("marine-le-pen", "VTANR5L17V8280",
     "S'est dite personnellement opposée à un texte jugé insuffisamment encadré, tout en laissant la liberté de vote à son groupe (12 députés RN ont voté pour).",
     "fi_findevie"),
    # Narcotrafic 2025 : opposition d'une partie de la gauche sur la méthode.
    ("clementine-autain", "VTANR5L17V1473",
     "A voté contre, comme les députés ex-insoumis, en dénonçant une approche jugée uniquement répressive au détriment de la prévention.",
     "ici_narcotrafic"),
    # Énergies renouvelables 2023 : LFI contre, pour des motifs propres.
    ("francois-ruffin", "VTANR5L16V823",
     "A voté contre avec le groupe LFI, qui critiquait notamment le classement de la valorisation des déchets parmi les énergies renouvelables et le dispositif des « zones d'accélération », pas le principe des renouvelables.",
     "lfa_enr"),
    # Pouvoir d'achat 2022 : la gauche jugeait le paquet insuffisant.
    ("clementine-autain", "VTANR5L16V186",
     "A voté contre avec les groupes de la NUPES, qui jugeaient le texte « insoutenable sur le plan social et environnemental » et lui reprochaient d'esquiver la question des bas salaires et de la hausse du Smic.",
     "lcp_pouvoir_achat"),
    ("delphine-batho", "VTANR5L16V186",
     "A voté contre avec les groupes de la NUPES, qui jugeaient le texte « insoutenable sur le plan social et environnemental » et lui reprochaient d'esquiver la question des bas salaires et de la hausse du Smic.",
     "lcp_pouvoir_achat"),
    ("francois-ruffin", "VTANR5L16V186",
     "A voté contre avec les groupes de la NUPES, qui jugeaient le texte « insoutenable sur le plan social et environnemental » et lui reprochaient d'esquiver la question des bas salaires et de la hausse du Smic.",
     "lcp_pouvoir_achat"),
    # (Les nuances SOC de Guedj et Brun sur ce vote ont été retirées : elles
    #  répétaient mot pour mot la justification du groupe Socialistes, désormais
    #  affichée sous le chip du parti — pas de double emploi.)
    # Fraudes sociales et fiscales 2026 : opposition unanime de la gauche sur l'équilibre du texte.
    ("clementine-autain", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, s'en prenant aux « plus précaires », pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    ("francois-ruffin", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, s'en prenant aux « plus précaires », pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    ("jerome-guedj", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, s'en prenant aux « plus précaires », pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    ("philippe-brun", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, s'en prenant aux « plus précaires », pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    # Résolution Ukraine 2022 : abstentions LFI et RN, motifs distincts (compte rendu officiel).
    ("clementine-autain", "VTANR5L16V652",
     "Abstention avec le groupe LFI : son orateur Aurélien Saintoul critiquait un « bellicisme rhétorique » et l'absence de perspective de négociation et de conditions de paix dans le texte.",
     "cr_ukraine_2022"),
    ("marine-le-pen", "VTANR5L16V652",
     "Abstention avec le groupe RN : son oratrice reprochait au texte de ne rien dire du cessez-le-feu et de la paix, et estimait que la livraison d'armes offensives risquait de rendre la France « cobelligérante ».",
     "cr_ukraine_2022"),
    # Extension L14 (24/07/2026)
    ("edouard-philippe", "VTANR5L14V511",
     "S'est abstenu : une position intermédiaire dans un groupe UMP qui a très majoritairement voté contre le texte.",
     "jdd_philippe"),
    ("edouard-philippe", "VTANR5L14V1109",
     "A voté contre, jugeant que la loi posait « des questions graves en matière de libertés individuelles », malgré le consensus des mois suivant les attentats de janvier 2015.",
     "jdd_philippe"),
    ("jerome-guedj", "VTANR5L14V30",
     "A voté contre avec une vingtaine de députés de l'aile gauche du PS, contre la position de son propre gouvernement : « C'est un traité Merkozie, pas un traité Hollande. C'est un remède qui tue le malade. »",
     "e1_tscg"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    existantes = {(pid, sid) for pid, sid in cur.execute(
        "SELECT personne_id, scrutin_id FROM nuances")}

    a_inserer = []
    for slug, uid, texte, cle_source in NUANCES:
        pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (slug,)).fetchone()
        sid = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
        if not (pid and sid):
            sys.exit(f"Nuance orpheline : {slug} / {uid} introuvable.")
        if (pid[0], sid[0]) in existantes:
            continue  # idempotent : déjà en base
        # Garde-fou : la nuance PERSONNELLE doit expliquer un vote réellement en base.
        if not cur.execute("SELECT 1 FROM positions_vote WHERE personne_id=? AND scrutin_id=?",
                           (pid[0], sid[0])).fetchone():
            sys.exit(f"Nuance sans vote personnel en base : {slug} / {uid} — refusée "
                     "(une position de PARTI relève de justifications_groupes).")
        a_inserer.append((pid[0], sid[0], texte, cle_source))

    if not a_inserer:
        print("nuances : déjà à jour, rien à ajouter.")
        con.close()
        return

    ids_source = {}
    for cle in {item[3] for item in a_inserer}:
        url, detail = SOURCES[cle]
        cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?, 'presse', '2026-07-23', ?)",
                    (url, detail))
        ids_source[cle] = cur.lastrowid

    for pid, sid, texte, cle_source in a_inserer:
        cur.execute("INSERT INTO nuances (personne_id, scrutin_id, texte, source_id) VALUES (?,?,?,?)",
                    (pid, sid, texte, ids_source[cle_source]))

    con.commit()
    print(f"Semé : {len(a_inserer)} nuance(s) personnelle(s) ajoutée(s) ({len(ids_source)} source(s)).")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

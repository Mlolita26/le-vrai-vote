"""Nuances éditoriales : explication des votes contre-intuitifs, chacune
attribuée et SOURCÉE (règle : une nuance sans source ne s'affiche pas).

Une nuance rapporte la justification déclarée par l'intéressé ou son groupe
(explication de vote, communiqué, presse) — elle ne juge pas. Les cas sans
source individuelle vérifiable (ex. l'abstention de F. Ruffin sur la
résolution Ukraine de 2025, dont il n'a pas publié d'explication trouvée)
ne reçoivent volontairement PAS de nuance.

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
}

# (slug personne, uid scrutin, texte de la nuance, clé source)
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
     "A voté contre en jugeant la loi « à des années-lumière de ce que disent les scientifiques » — un désaccord sur l'ambition, pas sur l'objectif.",
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
     "A voté contre avec le groupe LFI, qui critiquait notamment le classement de la valorisation des déchets parmi les énergies renouvelables et le dispositif des « zones d'accélération » — pas le principe des renouvelables.",
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
    ("jerome-guedj", "VTANR5L16V186",
     "Abstention avec le groupe Socialistes — « le compte n'y est pas » : des revalorisations jugées inférieures à l'inflation, sans opposition frontale au principe des mesures.",
     "lcp_pouvoir_achat"),
    ("philippe-brun", "VTANR5L16V186",
     "Abstention avec le groupe Socialistes — « le compte n'y est pas » : des revalorisations jugées inférieures à l'inflation, sans opposition frontale au principe des mesures.",
     "lcp_pouvoir_achat"),
    # Fraudes sociales et fiscales 2026 : opposition unanime de la gauche sur l'équilibre du texte.
    ("clementine-autain", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, et une « suspicion généralisée » envers les allocataires — pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    ("francois-ruffin", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, et une « suspicion généralisée » envers les allocataires — pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    ("jerome-guedj", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, et une « suspicion généralisée » envers les allocataires — pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    ("philippe-brun", "VTANR5L17V6319",
     "A voté contre, comme l'ensemble de la gauche, qui dénonçait un texte trop centré sur la fraude sociale et pas assez sur la fraude fiscale, et une « suspicion généralisée » envers les allocataires — pas la lutte contre la fraude en soi.",
     "fi_fraudes"),
    # Résolution Ukraine 2022 : abstentions LFI et RN, motifs distincts (compte rendu officiel).
    ("clementine-autain", "VTANR5L16V652",
     "Abstention avec le groupe LFI : son orateur Aurélien Saintoul critiquait un « bellicisme rhétorique » et l'absence de perspective de négociation et de conditions de paix dans le texte.",
     "cr_ukraine_2022"),
    ("marine-le-pen", "VTANR5L16V652",
     "Abstention avec le groupe RN : son oratrice reprochait au texte de ne rien dire du cessez-le-feu et de la paix, et estimait que la livraison d'armes offensives risquait de rendre la France « cobelligérante ».",
     "cr_ukraine_2022"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    if cur.execute("SELECT COUNT(*) FROM nuances").fetchone()[0]:
        sys.exit("La table nuances n'est pas vide — la vider avant de re-semer.")

    ids_source = {}
    for cle, (url, detail) in SOURCES.items():
        cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?, 'presse', '2026-07-23', ?)",
                    (url, detail))
        ids_source[cle] = cur.lastrowid

    for slug, uid, texte, cle_source in NUANCES:
        pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (slug,)).fetchone()
        sid = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
        if not (pid and sid):
            sys.exit(f"Nuance orpheline : {slug} / {uid} introuvable.")
        # Garde-fou : la nuance doit expliquer une position réellement en base.
        if not cur.execute("SELECT 1 FROM positions_vote WHERE personne_id=? AND scrutin_id=?",
                           (pid[0], sid[0])).fetchone():
            sys.exit(f"Nuance sans position correspondante en base : {slug} / {uid} — refusée.")
        cur.execute("INSERT INTO nuances (personne_id, scrutin_id, texte, source_id) VALUES (?,?,?,?)",
                    (pid[0], sid[0], texte, ids_source[cle_source]))

    con.commit()
    print(f"Semé : {len(NUANCES)} nuances sourcées ({len(SOURCES)} sources presse).")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

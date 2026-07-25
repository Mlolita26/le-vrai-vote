"""Justifications éditoriales PAR GROUPE parlementaire : pourquoi chaque parti
a voté comme il l'a fait sur un scrutin clé. Chacune est ATTRIBUÉE et SOURCÉE
(règle absolue : un fait sans source ne s'affiche pas) et rapporte la position
déclarée — elle décrit, elle ne juge pas (CLAUDE.md §4).

Complète les décomptes bruts de `positions_groupes` (miroir des dumps, jamais
édités) par le « pourquoi » éditorial, parti par parti. Sert surtout les lois
où les familles politiques divergent nettement (ex. LFI vs RN).

Garde-fou : une justification n'est écrite que si le groupe a réellement un
décompte en base pour ce scrutin (sinon on refuse — pas de parti fantôme).

Usage : python ingestion/seed_justifications_groupes.py [chemin_base]
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

# clé -> (url, détail). URLs vérifiées le 25/07/2026.
SOURCES = {
    "lcp_nucleaire": ("https://lcp.fr/actualites/acceleration-du-nucleaire-le-projet-de-loi-definitivement-adopte-par-le-parlement-188296",
                      "LCP, mai 2023 — adoption définitive de la loi d'accélération du nucléaire, positions des groupes"),
    "bdt_nucleaire": ("https://www.banquedesterritoires.fr/le-parlement-adopte-largement-le-projet-de-loi-de-relance-du-nucleaire",
                      "Banque des Territoires, 2023 — adoption large du projet de loi de relance du nucléaire"),
    "lcp_indverte": ("https://lcp.fr/actualites/assemblee-nationale-adoption-du-projet-de-loi-industrie-verte-fin-de-la-session",
                     "LCP, juillet 2023 — adoption du projet de loi industrie verte, explications et critiques des groupes"),
    "ps_simplification": ("https://www.publicsenat.fr/actualites/politique/le-parlement-adopte-definitivement-la-loi-sur-la-simplification-de-la-vie-economique-et-enterine-la-suppression-des-zfe",
                          "Public Sénat, avril 2026 — adoption définitive de la loi de simplification (suppression des ZFE), votes des groupes"),
    "lcp_mineurs": ("https://lcp.fr/actualites/delinquance-des-mineurs-que-contient-la-proposition-de-loi-de-gabriel-attal-que-le",
                    "LCP, 2025 — contenu et débats de la proposition de loi Attal sur la justice des mineurs"),
    "bdt_mineurs": ("https://www.banquedesterritoires.fr/la-proposition-de-loi-attal-sur-la-justice-des-mineurs-definitivement-adoptee",
                    "Banque des Territoires, 2025 — adoption définitive de la loi Attal, oppositions de la gauche"),
    "lcp_bienvieillir": ("https://lcp.fr/actualites/bien-vieillir-assemblee-nationale-adopte-texte-premiere-lecture-241649",
                         "LCP, 23/11/2023 — adoption en première lecture de la loi « bien vieillir », positions des groupes"),
    "lcp_corse": ("https://lcp.fr/actualites/l-assemblee-nationale-vote-en-faveur-de-l-autonomie-de-la-corse-437977",
                  "LCP, juin 2026 — vote de l'Assemblée sur l'autonomie de la Corse, positions du RN et de LFI"),
    "maireinfo_corse": ("https://www.maire-info.com/corse/autonomie-de-la-corse-le-projet-de-loi-adopte-en-premiere-lecture-mais-les-incertitudes-demeurent-sur-son-avenir-article-30919",
                        "Maire-Info, juin 2026 — adoption en première lecture du projet de loi Corse autonome"),
    "lcp_caledonie": ("https://lcp.fr/actualites/nouvelle-caledonie-le-projet-de-loi-constitutionnelle-sur-le-degel-du-corps-electoral",
                      "LCP, mai 2024 — adoption du dégel du corps électoral calédonien, débats des groupes"),
    "lcp_municipales": ("https://lcp.fr/actualites/municipales-le-parlement-etend-le-scrutin-de-liste-paritaire-aux-petites-communes-a",
                        "LCP, avril 2025 — extension du scrutin de liste paritaire aux petites communes, débat RN / gauche"),
    # Sources des justifications de groupe au Parlement européen (+ loi immigration 2023).
    "aubry_seqe": ("https://manonaubry.eu/mes-combats/vote/revision-du-systeme-dechange-de-quotas-demission-de-gaz-effet-de-serre-dans-lunion",
                   "manonaubry.eu — fiche de vote de Manon Aubry (LFI/The Left) sur la révision du marché carbone"),
    "lfi_electricite": ("https://lafranceinsoumise.fr/2024/04/11/le-parlement-europeen-vote-la-catastrophique-reforme-du-marche-de-lelectricite-seul-le-groupe-lfi-sy-oppose/",
                        "lafranceinsoumise.fr, 11/04/2024 — opposition de LFI à la réforme du marché de l'électricité"),
    "rn_pacte_migration": ("https://rassemblementnational.fr/communiques/communique-de-presse-de-jordan-bardella",
                           "rassemblementnational.fr — communiqué de Jordan Bardella (RN) contre le « pacte de submersion » (avril 2024)"),
    "rn_ecologie_punitive": ("https://rassemblementnational.fr/communiques/mondial-de-lauto-2024-le-rassemblement-national-se-tient-aux-cotes-des-automobilistes-et-constructeurs-automobiles-francais-victimes-expiatoires-de-lecologie-punitive",
                             "rassemblementnational.fr — communiqué RN (oct. 2024) contre « l'écologie punitive », défense des automobilistes"),
    "lm_rn_climat": ("https://www.lemonde.fr/politique/article/2024/11/24/l-inaction-climatique-ligne-de-conduite-assumee-du-rassemblement-national",
                     "Le Monde, 24/11/2024 — « L'inaction climatique, ligne de conduite assumée du Rassemblement national »"),
    "hayer_pacte": ("https://www.lopinion.fr/international/avec-le-pacte-asile-et-migration-leurope-a-repondu-presente-par-valerie-hayer",
                    "L'Opinion — tribune de Valérie Hayer (Renaissance) défendant le pacte : « fermeté, humanité et efficacité »"),
    "hayer_greendeal": ("https://www.touteleurope.eu/vie-politique-des-etats-membres/elections-europeennes-2024-le-programme-de-valerie-hayer-et-de-renaissance/",
                        "Touteleurope.eu — programme de Valérie Hayer (Renaissance) : compléter le Pacte vert, cap sur la neutralité 2050"),
    "toussaint_pacte": ("https://www.marietoussaint.eu/actualites/pacte-asile-migration",
                        "marietoussaint.eu — communiqué de Marie Toussaint (Les Écologistes) contre le pacte : « les pires idées de l'extrême droite »"),
    "toussaint_nature": ("https://www.marietoussaint.eu/actualites/vote-loi-restauration-nature",
                         "marietoussaint.eu, 27/02/2024 — Marie Toussaint : « une victoire pour le vivant »"),
    "glucksmann_pacte": ("https://www.franceinfo.fr/elections/europeennes/pacte-europeen-sur-la-migration-et-l-asile-je-vais-voter-contre-la-majorite-des-textes-previent-raphael-glucksmann_6455306.html",
                         "franceinfo — Raphaël Glucksmann (PS/Place publique) : voter contre la majorité des textes, pacte « pas assez équilibré »"),
    "bellamy_co2_2035": ("https://www.fxbellamy.fr/2023/02/14/ppe-contre-l-interdiction-de-la-vente-de-vehicules-a-moteurs-thermiques-en-2035/",
                         "fxbellamy.fr, 14/02/2023 — F.-X. Bellamy (LR/PPE) : « erreur historique », « désastreuse pour l'industrie », « la grande gagnante est la Chine »"),
    "lfi_immigration_2023": ("https://lafranceinsoumise.fr/2023/12/15/stop-a-la-loi-immigration/",
                             "lafranceinsoumise.fr, 15/12/2023 — LFI appelle à rejeter la loi immigration (« xénophobie et racisme »)"),
    "ps_immigration_2023": ("https://www.parti-socialiste.paris/communique_loi_immigration_2023",
                            "Parti socialiste — communiqué contre la loi immigration 2023 (« populisme de la droite et de l'extrême droite »)"),
    "lcp_pouvoir_achat": ("https://lcp.fr/actualites/pouvoir-d-achat-le-parlement-adopte-definitivement-le-texte-133297",
                          "LCP, 03/08/2022 — adoption définitive du paquet pouvoir d'achat, explications des groupes"),
    "lfi_mercosur": ("https://lafranceinsoumise.fr/2024/11/26/nous-votons-contre-laccord-de-libre-echange-ue-mercosur/",
                     "lafranceinsoumise.fr, 26/11/2024 — LFI vote contre la déclaration : refuse l'accord « tout court », pas seulement « en l'état »"),
}

# (uid scrutin, groupe_abrege EXACT tel qu'en base, texte de la justification, clé source)
# Les abrégés diffèrent par législature : L16 « LFI - NUPES » / « GDR - NUPES » /
# « Ecolo - NUPES » ; L17 « LFI-NFP » / « GDR » / « EcoS » / « EPR » / « DR ».
JUSTIFS = [
    # ── Relance du nucléaire, 2023 (L16) ──────────────────────────────────────
    ("VTANR5L16V1533", "RN",
     "A voté pour : le RN soutient une relance du nucléaire, qu'il présente comme une énergie souveraine, pilotable et bas-carbone.",
     "bdt_nucleaire"),
    ("VTANR5L16V1533", "LFI - NUPES",
     "A voté contre, par hostilité à une relance du nucléaire : le groupe lui préfère un scénario reposant sur les énergies renouvelables et la sobriété.",
     "lcp_nucleaire"),
    ("VTANR5L16V1533", "Ecolo - NUPES",
     "A voté contre, opposé au principe d'une relance du nucléaire (coût, déchets, sûreté), au profit des renouvelables.",
     "lcp_nucleaire"),

    # ── Loi industrie verte, 2023 (L16) ──────────────────────────────────────
    ("VTANR5L16V2721", "RN",
     "A voté pour, en soutien à la réindustrialisation, tout en jugeant le texte insuffisant — « la montagne accouche d'une souris » (Alexandre Loubet).",
     "lcp_indverte"),
    ("VTANR5L16V2721", "LFI - NUPES",
     "A voté contre : le groupe jugeait les moyens de l'État très inférieurs à l'effort d'autres pays (le plan américain IRA) et le texte trop peu contraignant sur l'environnement.",
     "lcp_indverte"),
    ("VTANR5L16V2721", "Ecolo - NUPES",
     "A voté contre, qualifiant le texte d'« occasion manquée » et jugeant ses ambitions environnementales insuffisantes (Charles Fournier).",
     "lcp_indverte"),

    # ── Simplification de la vie économique, 2026 (L17) ──────────────────────
    ("VTANR5L17V6184", "RN",
     "A voté pour, en soutien à l'allègement des contraintes sur les entreprises et à la suppression des zones à faibles émissions (ZFE).",
     "ps_simplification"),
    ("VTANR5L17V6184", "LFI-NFP",
     "A voté contre l'ensemble du texte, jugé porteur de régressions — tout en étant, de longue date, favorable à la suppression des ZFE qu'il contient.",
     "ps_simplification"),
    ("VTANR5L17V6184", "EPR",
     "Une partie du groupe macroniste a voté contre le texte final : le compromis du Gouvernement, qui laissait aux collectivités le choix de maintenir ou non les ZFE, avait été repoussé.",
     "ps_simplification"),

    # ── Justice des mineurs (loi Attal), 2025 (L17) ──────────────────────────
    ("VTANR5L17V1624", "RN",
     "A voté pour, en soutien à un durcissement de la réponse pénale à la délinquance des mineurs.",
     "bdt_mineurs"),
    ("VTANR5L17V1624", "LFI-NFP",
     "A voté contre, avec toute la gauche, estimant que le texte remet en cause le principe fondateur de la justice des mineurs : la primauté de l'éducation sur la répression.",
     "lcp_mineurs"),
    ("VTANR5L17V1624", "SOC",
     "A voté contre, son orateur Hervé Saulignac qualifiant le texte d'« injuste, régressif et aussi complet qu'inefficace ».",
     "bdt_mineurs"),

    # ── Société du bien vieillir, 2023 (L16) ─────────────────────────────────
    ("VTANR5L16V3045", "RN",
     "A voté pour, malgré des critiques : sa porte-parole Sandrine Dogor-Such a dénoncé un texte « à mille lieues des problèmes de la vieillesse » et un « manque de volonté politique ».",
     "lcp_bienvieillir"),
    ("VTANR5L16V3045", "LFI - NUPES",
     "A voté contre, Martine Étienne y voyant « la quintessence de ce que fait le macronisme au quotidien » : des annonces sans les moyens de la « loi grand âge » attendue.",
     "lcp_bienvieillir"),
    ("VTANR5L16V3045", "GDR - NUPES",
     "A voté contre, avec LFI, jugeant le texte très en deçà des besoins du grand âge et du financement de l'autonomie.",
     "lcp_bienvieillir"),

    # ── Autonomie de la Corse, 2026 (L17) — rôles inversés ───────────────────
    ("VTANR5L17V7454", "RN",
     "A voté contre : le RN s'oppose à une autonomie normative de la Corse, qu'il juge contraire à l'unité de la République, et a dénoncé un amendement porté par LFI.",
     "lcp_corse"),
    ("VTANR5L17V7454", "LFI-NFP",
     "A voté pour : Éric Coquerel y a salué « un signal fort et positif » envoyé à la Corse, le groupe étant favorable à la reconnaissance de ses spécificités.",
     "lcp_corse"),

    # ── Corps électoral en Nouvelle-Calédonie, 2024 (L16) ────────────────────
    ("VTANR5L16V3725", "RN",
     "A voté pour le dégel, favorable à l'ouverture du corps électoral aux résidents installés de longue date dans l'archipel.",
     "lcp_caledonie"),
    ("VTANR5L16V3725", "LFI - NUPES",
     "A voté contre, refusant un dégel unilatéral et partiel hors d'un accord global avec les forces calédoniennes ; Alexis Corbière a averti qu'il placerait l'archipel « sous tension ».",
     "lcp_caledonie"),

    # ── Parité dans les petites communes, 2025 (L17) — rôles inversés ────────
    ("VTANR5L17V1303", "RN",
     "A voté contre : Jordan Guitton a fait valoir que, dans beaucoup de petites communes, « il n'y aura qu'une seule liste, il n'y aura pas de choix pour les électeurs », jugeant difficile d'y constituer des listes paritaires.",
     "lcp_municipales"),
    ("VTANR5L17V1303", "LFI-NFP",
     "A voté pour, en soutien à la parité ; la gauche a fustigé des « discours réactionnaires » comparables, selon elle, aux arguments opposés à la parité au début des années 2000.",
     "lcp_municipales"),

    # ── Parlement européen ────────────────────────────────────────────────────
    ("PE-HTV-154173", "LFI",
     "A voté contre : LFI rejette le marché carbone comme une « fausse solution » fondée sur des « logiques spéculatives » et l'échange de « droits à polluer », et dénonçait un texte affaibli par « l'alliance des droites » — un désaccord sur le mécanisme, pas sur l'objectif climatique.",
     "aubry_seqe"),
    ("PE-HTV-167334", "LFI",
     "A voté contre, dénonçant la fin des tarifs réglementés, le maintien de l'indexation de l'électricité sur le gaz et un risque de privatisation ; le groupe défend un contrôle public des prix de l'énergie.",
     "lfi_electricite"),
    ("PE-HTV-167531", "RN",
     "A voté contre, qualifiant le texte de « pacte de submersion » : le mécanisme « accueil ou contribution financière » y est présenté comme « la submersion ou la punition », et le pacte comme un « appel d'air » migratoire.",
     "rn_pacte_migration"),
    ("PE-HTV-152544", "RN",
     "A voté contre, refusant une « écologie punitive » qui ferait des automobilistes et de l'industrie automobile française des « victimes expiatoires » ; le RN met en avant le pouvoir d'achat et l'emploi.",
     "rn_ecologie_punitive"),
    ("PE-HTV-118521", "RN",
     "A voté contre : le RN assume une opposition aux objectifs climatiques contraignants de l'Union, jugés coûteux pour les ménages et attentatoires à la souveraineté.",
     "lm_rn_climat"),
    ("PE-HTV-167531", "RE",
     "A voté pour, défendant un pacte fondé sur « fermeté, humanité et efficacité » : réponse européenne coordonnée, maîtrise des frontières et lutte contre l'immigration illégale.",
     "hayer_pacte"),
    ("PE-HTV-118521", "RE",
     "A voté pour, défendant le Pacte vert et l'objectif de neutralité carbone en 2050 comme feuille de route de l'Union.",
     "hayer_greendeal"),
    ("PE-HTV-167531", "VERT",
     "A voté contre, dénonçant un pacte qui « consacre les pires idées de l'extrême droite » : détention généralisée aux frontières, fichage dès six ans et recul des droits fondamentaux des personnes exilées.",
     "toussaint_pacte"),
    ("PE-HTV-164499", "VERT",
     "A voté pour, saluant « une victoire pour le vivant » face aux tentatives de « sabotage » du texte par l'extrême droite.",
     "toussaint_nature"),
    ("PE-HTV-167531", "PS",
     "A voté contre la majorité des textes du pacte, jugé « pas assez équilibré » et insuffisant sur la protection des droits.",
     "glucksmann_pacte"),
    ("PE-HTV-152544", "LR",
     "A voté contre, y voyant une « erreur historique » : une mesure jugée « désastreuse pour l'industrie européenne » et coûteuse pour les citoyens, dont « la grande gagnante est la Chine ».",
     "bellamy_co2_2035"),

    # ── Loi immigration 2023 (Assemblée, L16) : compléter RN (déjà en nuance perso) ──
    ("VTANR5L16V3213", "LFI - NUPES",
     "A voté contre, dénonçant une loi de « xénophobie et de racisme » et une atteinte aux droits ; le groupe a ensuite saisi le Conseil constitutionnel, qui a censuré une large partie du texte.",
     "lfi_immigration_2023"),
    ("VTANR5L16V3213", "SOC",
     "A voté contre, refusant de « sombrer dans le populisme de la droite et de l'extrême droite » et jugeant le texte contraire à l'accueil des personnes forcées de fuir.",
     "ps_immigration_2023"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # Table créée à la demande (idempotent) — permet d'exécuter ce seed sur une
    # base initialisée avant l'ajout de la table au schéma.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS justifications_groupes (
            id            INTEGER PRIMARY KEY,
            scrutin_id    INTEGER NOT NULL REFERENCES scrutins(id),
            groupe_abrege TEXT NOT NULL,
            texte         TEXT NOT NULL,
            source_id     INTEGER NOT NULL REFERENCES sources(id),
            UNIQUE (scrutin_id, groupe_abrege)
        )""")

    existantes = {(sid, ab) for sid, ab in cur.execute(
        "SELECT scrutin_id, groupe_abrege FROM justifications_groupes")}

    a_inserer = []
    for uid, abrege, texte, cle_source in JUSTIFS:
        r = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
        if not r:
            sys.exit(f"Justification orpheline : scrutin {uid} introuvable.")
        sid = r[0]
        if (sid, abrege) in existantes:
            continue  # idempotent
        # Garde-fou : le groupe doit avoir un décompte réel pour ce scrutin.
        if not cur.execute("SELECT 1 FROM positions_groupes WHERE scrutin_id=? AND groupe_abrege=?",
                           (sid, abrege)).fetchone():
            sys.exit(f"Justification refusée : aucun décompte pour {abrege} au scrutin {uid} "
                     f"(exécuter parse_positions_groupes.py après avoir ajouté le vote clé).")
        a_inserer.append((sid, abrege, texte, cle_source))

    if not a_inserer:
        print("justifications de groupe : déjà à jour, rien à ajouter.")
        con.close()
        return

    ids_source = {}
    for cle in {item[3] for item in a_inserer}:
        url, detail = SOURCES[cle]
        cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?, 'presse', '2026-07-25', ?)",
                    (url, detail))
        ids_source[cle] = cur.lastrowid

    for sid, abrege, texte, cle_source in a_inserer:
        cur.execute("INSERT INTO justifications_groupes (scrutin_id, groupe_abrege, texte, source_id) "
                    "VALUES (?,?,?,?)", (sid, abrege, texte, ids_source[cle_source]))

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM justifications_groupes").fetchone()[0]
    print(f"Semé : {len(a_inserer)} justification(s) de groupe ajoutée(s) "
          f"({len(ids_source)} source(s)) ; {n} au total.")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

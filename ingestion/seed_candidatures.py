"""Saisie éditoriale sourcée : déclarations publiques de candidature à la
présidentielle 2027, telles que recoupées le 23/07/2026.

Référence : CANDIDATS_2027.md dans le coffre OneDrive (liste, recoupements,
divergences). Sources croisées : Wikipédia (agrégateur, consulté le 23/07/2026),
LCP (mis à jour le 10/07/2026), France 24 (08/07/2026) pour Marine Le Pen.

Règles :
  - il n'existe PAS de liste officielle avant la décision du Conseil
    constitutionnel (mars 2027) — statut 'declaree' ou 'primaire' seulement ;
  - chaque ligne pointe une source ; les dates issues du seul agrégateur
    Wikipédia sont marquées « à re-sourcer » dans detail ;
  - Jordan Bardella n'est PAS candidat (Marine Le Pen déclarée le 07/07/2026
    après l'arrêt d'appel) : il n'a pas de ligne candidature, ses données
    restent en base à titre historique.
  - Clémentine Autain a retiré sa candidature le 11/07/2026, après l'échec de
    la primaire de la gauche unitaire (source : recherche du 26/07/2026 sur
    son site de campagne, retrait non mentionné sur le site lui-même — à
    resourcer sur un article de presse dédié). Sa ligne candidature a été
    retirée de la base ; ses données personnelles restent à titre historique.

Usage : python ingestion/seed_candidatures.py [chemin_base]
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

WIKI = ("https://fr.wikipedia.org/wiki/%C3%89lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2027",
        "Wikipédia (agrégateur), consulté le 23/07/2026 — recoupé avec LCP du 10/07/2026")
LCP = ("https://lcp.fr/actualites/presidentielle-2027-la-liste-des-candidats-deja-en-lice-et-des-pretendants-436373",
       "LCP, article mis à jour le 10/07/2026")
F24 = ("https://www.france24.com/fr/france/20260708-marine-le-pen-candidate-en-2027-un-choix-dynastique-du-rn-qui-%C3%A9clipse-jordan-bardella",
       "France 24, 08/07/2026 — déclaration au 20 h de TF1 le 07/07/2026 après l'arrêt d'appel")

RESOURCER = " — date rapportée par agrégateur, à re-sourcer sur document primaire"

# (nom, prénom, slug, statut, date, detail, source)
CANDIDATS = [
    ("Arthaud", "Nathalie", "nathalie-arthaud", "declaree", "2025-12-08", "Lutte ouvrière" + RESOURCER, "wiki"),
    ("Asselineau", "François", "francois-asselineau", "declaree", "2023-08-31", "Union populaire républicaine" + RESOURCER, "wiki"),
    ("Attal", "Gabriel", "gabriel-attal", "declaree", "2026-05-22", "Renaissance — dates Wikipédia et LCP concordantes", "wiki"),
    ("Batho", "Delphine", "delphine-batho", "declaree", "2025-11-25", "Génération écologie" + RESOURCER, "wiki"),
    ("Bertrand", "Xavier", "xavier-bertrand", "declaree", "2024-02-03", "Nous France" + RESOURCER, "wiki"),
    ("Bouamrane", "Karim", "karim-bouamrane", "declaree", "2026-06-09", "Parti socialiste, maire de Saint-Ouen" + RESOURCER, "wiki"),
    ("Cazeneuve", "Bernard", "bernard-cazeneuve", "declaree", "2026-07-16", "La Convention — entretien au Parisien" + RESOURCER, "wiki"),
    ("Dupont-Aignan", "Nicolas", "nicolas-dupont-aignan", "declaree", "2025-03-08", "Debout la France" + RESOURCER, "wiki"),
    ("Egger", "Clara", "clara-egger", "declaree", None, "Solution démocratique — recensée par LCP, date non fournie", "lcp"),
    ("Guedj", "Jérôme", "jerome-guedj", "declaree", "2026-02-05", "Parti socialiste" + RESOURCER, "wiki"),
    ("Kazib", "Anasse", "anasse-kazib", "declaree", "2026-06-01", "Révolution permanente" + RESOURCER, "wiki"),
    ("Labib", "Selma", "selma-labib", "declaree", "2026-06-17", "NPA – Révolutionnaires" + RESOURCER, "wiki"),
    ("Le Pen", "Marine", "marine-le-pen", "declaree", "2026-07-07",
     "Rassemblement national — déclarée le soir de l'arrêt d'appel (peine ramenée à 45 mois "
     "d'inéligibilité dont 30 avec sursis, partie ferme purgée en juin 2026 ; pourvoi en cassation formé)", "f24"),
    ("Mélenchon", "Jean-Luc", "jean-luc-melenchon", "declaree", "2026-05-03",
     "La France insoumise — Wikipédia indique le 03/05, LCP « fin mai » : divergence à trancher sur source primaire", "wiki"),
    ("Mikolajczak", "Antoine", "antoine-mikolajczak", "declaree", None, "Équinoxe — recensé par LCP, date non fournie", "lcp"),
    ("Philippe", "Édouard", "edouard-philippe", "declaree", "2024-09-03", "Horizons — dates Wikipédia et LCP concordantes", "wiki"),
    ("Philippot", "Florian", "florian-philippot", "declaree", "2026-05-09", "Les Patriotes" + RESOURCER, "wiki"),
    ("Retailleau", "Bruno", "bruno-retailleau", "declaree", "2026-04-19", "Les Républicains — LCP « mi-avril », concordant", "wiki"),
    # Candidats à une primaire
    # Autain (LFI/gauche unitaire) retirée le 11/07/2026 — voir note en tête de fichier.
    ("Brun", "Philippe", "philippe-brun", "primaire", "2026-06-30", "Primaire du Parti socialiste" + RESOURCER, "wiki"),
    ("Lisnard", "David", "david-lisnard", "primaire", "2026-03-31", "Nouvelle Énergie" + RESOURCER, "wiki"),
    ("Massard", "Lydie", "lydie-massard", "primaire", "2026-04-02", "Primaire de la gauche unitaire, Union démocratique bretonne" + RESOURCER, "wiki"),
    ("Ruffin", "François", "francois-ruffin", "primaire", "2025-04-01", "Primaire de la gauche unitaire, Debout !" + RESOURCER, "wiki"),
    ("Royal", "Ségolène", "segolene-royal", "primaire", "2026-07-10", "Primaire du Parti socialiste — Wikipédia et LCP concordants", "wiki"),
    ("Tondelier", "Marine", "marine-tondelier", "primaire", "2025-10-22", "Primaire de la gauche unitaire, Les Écologistes" + RESOURCER, "wiki"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    if cur.execute("SELECT COUNT(*) FROM candidatures").fetchone()[0]:
        sys.exit("La table candidatures n'est pas vide — réinitialiser la base avant de re-semer.")

    sources = {}
    for cle, (url, detail) in (("wiki", WIKI), ("lcp", LCP), ("f24", F24)):
        cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?, 'presse', '2026-07-23', ?)",
                    (url, detail))
        sources[cle] = cur.lastrowid

    inseres_personnes = 0
    for nom, prenom, slug, statut, date, detail, src in CANDIDATS:
        ligne = cur.execute("SELECT id FROM personnes WHERE slug = ?", (slug,)).fetchone()
        if ligne:
            pid = ligne[0]
        else:
            cur.execute("INSERT INTO personnes (nom, prenom, slug) VALUES (?,?,?)", (nom, prenom, slug))
            pid = cur.lastrowid
            inseres_personnes += 1
        cur.execute("INSERT INTO candidatures (personne_id, statut, date, detail, source_id) "
                    "VALUES (?,?,?,?,?)", (pid, statut, date, detail, sources[src]))

    cur.execute("INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
                (sources["wiki"], "ingestion/seed_candidatures.py", len(CANDIDATS),
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()
    n_dec = cur.execute("SELECT COUNT(*) FROM candidatures WHERE statut='declaree'").fetchone()[0]
    n_pri = cur.execute("SELECT COUNT(*) FROM candidatures WHERE statut='primaire'").fetchone()[0]
    print(f"Candidatures semées : {n_dec} déclarées + {n_pri} en primaire "
          f"({inseres_personnes} nouvelles personnes). Bardella : volontairement sans candidature.")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

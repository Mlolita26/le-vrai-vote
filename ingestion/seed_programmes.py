"""Sites de campagne ou de programme officiels par candidat, vérifiés par
ouverture directe de chaque site (pas un simple résultat de recherche).

Règles :
  - un lien n'est ajouté que vers un site officiel du candidat ou de son
    parti/mouvement, jamais vers un article de presse ou un résumé tiers ;
  - 'type' vaut 'campagne' (site de campagne 2027 dédié) ou 'parti' (site du
    parti/mouvement, faute de site de campagne personnel identifié) ;
  - aucune ligne pour un candidat sans site vérifié : l'absence s'affiche
    comme telle (« indisponible »), jamais comblée par un lien approximatif.

Usage : python ingestion/seed_programmes.py [chemin_base]
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

# (slug, url, type, note, date de vérification) — vérifié par ouverture directe
# (WebFetch) le 26/07/2026. « aucun trouvé » : pas de ligne, l'absence s'affiche
# comme telle (« indisponible »).
PROGRAMMES = [
    ("nathalie-arthaud", "https://www.lutte-ouvriere.org/", "parti",
     None, "2026-07-26"),
    ("francois-asselineau", "https://upr.fr/", "parti",
     None, "2026-07-26"),
    ("gabriel-attal", "https://attalpresident.fr/", "campagne",
     None, "2026-07-26"),
    ("delphine-batho", "https://www.delphinebatho.fr/", "campagne",
     None, "2026-07-26"),
    ("xavier-bertrand", "https://www.nousfrance.fr/", "parti",
     None, "2026-07-26"),
    ("karim-bouamrane", "https://www.karimbouamrane2027.org/", "campagne",
     None, "2026-07-26"),
    ("bernard-cazeneuve", "https://bc2027.fr/", "campagne",
     "Site en construction : présente une démarche (dialogue, assemblée citoyenne) mais pas encore de programme détaillé.",
     "2026-07-26"),
    ("nicolas-dupont-aignan", "https://www.dupontaignan.fr/", "campagne",
     None, "2026-07-26"),
    ("clara-egger", "https://solutiondemocratique.fr/", "parti",
     None, "2026-07-26"),
    ("jerome-guedj", "http://jeromeguedj2027.fr/", "campagne",
     None, "2026-07-26"),
    ("anasse-kazib", "https://anasse2027.fr/", "campagne",
     "Accès direct bloqué par une protection anti-robot lors de la vérification ; domaine confirmé comme site officiel par Révolution permanente.",
     "2026-07-26"),
    ("selma-labib", "https://npa-revolutionnaires.org/", "parti",
     None, "2026-07-26"),
    ("marine-le-pen", "https://www.marinelepen.com/", "campagne",
     "Site officiel confirmé (« Présidentielles 2027 : Marine Le Pen, Site Officiel de Campagne ») ; au moment de la vérification, propose surtout un formulaire de soutien, le détail du programme n'est pas encore en ligne.",
     "2026-07-26"),
    ("david-lisnard", "https://www.unenouvelleenergie.fr/notre-programme/", "parti",
     None, "2026-07-26"),
    ("antoine-mikolajczak", "https://parti-equinoxe.fr/qui-est-antoine-mikolajczak/", "parti",
     "La page indique elle-même que le programme officiel pour la présidentielle 2027 n'est pas encore publié.",
     "2026-07-26"),
    ("jean-luc-melenchon", "https://melenchon2027.fr/", "campagne",
     None, "2026-07-26"),
    ("edouard-philippe", "https://horizonsleparti.fr/", "parti",
     None, "2026-07-26"),
    ("florian-philippot", "https://les-patriotes.fr/", "parti",
     None, "2026-07-26"),
    ("bruno-retailleau", "https://www.avecretailleau.fr/", "campagne",
     None, "2026-07-26"),
    ("francois-ruffin", "https://debout.fr/", "campagne",
     None, "2026-07-26"),
    ("marine-tondelier", "https://lesecologistes.fr/", "parti",
     "Accès direct bloqué par une protection anti-robot lors de la vérification ; domaine confirmé comme site officiel du parti par des sources tierces.",
     "2026-07-26"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS programmes (
            id          INTEGER PRIMARY KEY,
            personne_id INTEGER NOT NULL UNIQUE REFERENCES personnes(id),
            type        TEXT NOT NULL,
            note        TEXT,
            source_id   INTEGER NOT NULL REFERENCES sources(id)
        )""")

    if not PROGRAMMES:
        con.commit()
        print("Table programmes créée/à jour ; aucune ligne à semer pour l'instant.")
        con.close()
        return

    existants = {slug for (slug,) in cur.execute(
        "SELECT p.slug FROM programmes pr JOIN personnes p ON p.id = pr.personne_id")}

    inseres = 0
    for slug, url, type_, note, verifie_le in PROGRAMMES:
        if slug in existants:
            continue
        pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (slug,)).fetchone()
        if not pid:
            sys.exit(f"Candidat inconnu : {slug}")
        cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?, 'site_officiel', ?, ?)",
                    (url, verifie_le, note))
        src = cur.lastrowid
        cur.execute("INSERT INTO programmes (personne_id, type, note, source_id) VALUES (?,?,?,?)",
                    (pid[0], type_, note, src))
        inseres += 1

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM programmes").fetchone()[0]
    print(f"Semé : {inseres} programme(s) ajouté(s) ({n} au total).")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

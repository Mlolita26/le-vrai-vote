"""Mandats d'eurodéputé des candidats, saisis depuis les fiches OFFICIELLES
du Parlement européen (europarl.europa.eu — historique par législature,
dates au jour). Le référentiel AMO de l'Assemblée ne couvre pas ces mandats,
et le dataset HowTheyVote ne commence qu'en juillet 2019 : cette saisie
éditoriale sourcée comble le trou pour le parcours des candidats.

Les POSITIONS de vote au Parlement européen ne sont pas couvertes ici
(elles nécessitent l'import des votes par appel nominal 2004-2019 — voir
FEUILLE_DE_ROUTE) : les fiches affichent donc le mandat, et l'état
« scrutins du Parlement européen à importer ».

Usage : python ingestion/seed_mandats_europeens.py [chemin_base]
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

# (slug, url fiche officielle, [(debut, fin, détail)])
MANDATS = [
    ("marine-le-pen", "https://www.europarl.europa.eu/meps/fr/28210/MARINE_LE+PEN/history/8", [
        ("2004-07-20", "2009-07-13", "Eurodéputée, 6e législature (circonscription Île-de-France)"),
        ("2009-07-14", "2014-06-30", "Eurodéputée, 7e législature (circonscription Nord-Ouest)"),
        ("2014-07-01", "2017-06-18", "Eurodéputée, 8e législature (circonscription Nord-Ouest) ; "
                                     "mandat quitté après son élection à l'Assemblée nationale"),
    ]),
    ("jean-luc-melenchon", "https://www.europarl.europa.eu/meps/fr/96742/JEAN-LUC_MELENCHON/history/8", [
        ("2009-07-14", "2014-06-30", "Eurodéputé, 7e législature (circonscription Sud-Ouest)"),
        ("2014-07-01", "2017-06-18", "Eurodéputé, 8e législature ; mandat quitté après son élection "
                                     "à l'Assemblée nationale"),
    ]),
    ("florian-philippot", "https://www.europarl.europa.eu/meps/fr/110977/FLORIAN_PHILIPPOT/history/8", [
        ("2014-07-01", "2019-07-01", "Eurodéputé, 8e législature (circonscription Est)"),
    ]),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    inseres = 0
    for slug, url, mandats in MANDATS:
        pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (slug,)).fetchone()
        if not pid:
            sys.exit(f"Personne inconnue : {slug}")
        cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                    (url, "autre", "2026-07-24",
                     "Fiche officielle du député européen (historique par législature), consultée le 24/07/2026"))
        src = cur.lastrowid
        for debut, fin, detail in mandats:
            deja = cur.execute("SELECT COUNT(*) FROM mandats WHERE personne_id=? AND type='eurodepute' "
                               "AND debut=?", (pid[0], debut)).fetchone()[0]
            if deja:
                continue
            cur.execute("INSERT INTO mandats (personne_id, type, debut, fin, detail, precision, source_id) "
                        "VALUES (?, 'eurodepute', ?, ?, ?, 'jour', ?)", (pid[0], debut, fin, detail, src))
            inseres += 1
    con.commit()
    print(f"Semé : {inseres} mandats d'eurodéputé (sources : fiches officielles europarl.europa.eu).")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

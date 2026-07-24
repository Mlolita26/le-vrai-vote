"""Ajoute les identifiants `pe_mep_id` des candidats ayant siégé au Parlement
européen sur la période couverte par les données nominatives (2019+), vérifiés
dans le référentiel HowTheyVote (members.csv), afin que import_votes_cles_pe.py
puisse rattacher leurs positions personnelles.

Aujourd'hui : Lydie Massard (eurodéputée Verts/ALE, 24/09/2023 → 15/07/2024).
Bardella (131580) est déjà seedé par seed_identites.py mais n'est pas candidat.
Le Pen, Mélenchon, Philippot ont quitté le PE avant 2019 : aucun vote nominatif
collectable (cf. notes_projet/SOURCES_SENAT_ET_PE.md) — pas d'ID de collecte.

Idempotent : INSERT OR IGNORE (clé unique personne+système).

Usage : python ingestion/pe/seed_pe_ids.py [chemin_base] [chemin_coffre]
"""
import csv
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
COFFRE_DEFAUT = Path(r"C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles")

# (slug, pe_mep_id, prénom attendu, nom attendu) — vérifiés contre members.csv.
IDS = [
    ("lydie-massard", "249285", "Lydie", "MASSARD"),
]


def seed(base: Path, coffre: Path) -> None:
    hv = coffre / "donnees_brutes" / "Howtheyvote" / "export"
    with open(hv / "members.csv", encoding="utf-8") as f:
        membres = {r["id"]: (r["first_name"], r["last_name"]) for r in csv.DictReader(f)}

    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                ("https://github.com/HowTheyVote/data", "dataset", "2026-07-24",
                 "Identifiant MEP vérifié dans members.csv de l'export HowTheyVote (ODbL)."))
    src = cur.lastrowid

    # Adhésions de groupe (= bornes de mandat, comme pour Bardella dans seed_identites).
    with open(hv / "group_memberships.csv", encoding="utf-8") as f:
        adhesions = [r for r in csv.DictReader(f)]

    ajout_id = ajout_m = 0
    for slug, mep_id, prenom, nom in IDS:
        if membres.get(mep_id) != (prenom, nom):
            sys.exit(f"MEP {mep_id} ne correspond pas à {prenom} {nom} dans members.csv — abandon.")
        pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (slug,)).fetchone()
        if not pid:
            sys.exit(f"Personne inconnue : {slug}")
        pid = pid[0]
        cur.execute("INSERT OR IGNORE INTO identifiants_externes "
                    "(personne_id, systeme, identifiant, source_id) VALUES (?, 'pe_mep_id', ?, ?)",
                    (pid, mep_id, src))
        ajout_id += cur.rowcount
        # Mandat(s) d'eurodéputé, dérivé(s) des adhésions de groupe (sourcé HowTheyVote).
        for a in (x for x in adhesions if x["member_id"] == mep_id):
            deja = cur.execute("SELECT 1 FROM mandats WHERE personne_id=? AND type='eurodepute' AND debut=?",
                               (pid, a["start_date"])).fetchone()
            if deja:
                continue
            cur.execute(
                "INSERT INTO mandats (personne_id, type, debut, fin, detail, precision, source_id) "
                "VALUES (?, 'eurodepute', ?, ?, ?, 'jour', ?)",
                (pid, a["start_date"], a["end_date"] or None,
                 f"Parlement européen, législature {a['term']}, groupe {a['group_code']} "
                 "(bornes = dates d'adhésion au groupe, dataset HowTheyVote)", src))
            ajout_m += 1

    con.commit()
    print(f"Semé : {ajout_id} identifiant(s) pe_mep_id + {ajout_m} mandat(s) d'eurodéputé (idempotent).")
    con.close()


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    coffre = Path(sys.argv[2]) if len(sys.argv) > 2 else COFFRE_DEFAUT
    seed(base, coffre)

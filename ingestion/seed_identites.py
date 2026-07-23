"""Peuple `personnes`, `mandats` et `declarations` pour les cinq candidats suivis,
exclusivement à partir de sources vérifiables présentes dans le coffre de données.

Sources exploitées (aucune valeur « de mémoire ») :
  1. Dataset HowTheyVote.eu (export local du 09/05/2026) — naissance et mandats
     d'eurodéputé de Jordan Bardella (MEP 131580), lus programmatiquement des CSV.
  2. DIA HATVP de Gabriel Attal (déposée le 09/09/2024) — transcription manuelle
     du PDF officiel : naissance, mandat de député, fonctions gouvernementales.
  3. DIA HATVP de Bruno Retailleau (déposée le 09/01/2026) — idem.

Jean-Luc Mélenchon et Édouard Philippe : identité seule (nom, prénom, slug) ;
naissance et mandats restent vides → état « à importer » (règle n° 1 de CLAUDE.md).
Les dates des DIA sont à précision mensuelle : debut = 1er du mois,
fin = dernier jour du mois, colonne precision = 'mois'.

Usage : python ingestion/seed_identites.py [chemin_base] [chemin_coffre]
"""
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
COFFRE_DEFAUT = Path(r"C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles")

BARDELLA_MEP_ID = "131580"  # attention : 197819 est un autre eurodéputé


def fin_de_mois(annee: int, mois: int) -> str:
    if mois == 12:
        return f"{annee}-12-31"
    premier_suivant = datetime(annee + (mois // 12), (mois % 12) + 1, 1)
    from datetime import timedelta
    return (premier_suivant - timedelta(days=1)).strftime("%Y-%m-%d")


def seed(base: Path, coffre: Path) -> None:
    hv = coffre / "donnees_brutes" / "Howtheyvote" / "export"
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    if cur.execute("SELECT COUNT(*) FROM personnes").fetchone()[0]:
        sys.exit("La table personnes n'est pas vide — réinitialiser la base avant de re-semer.")

    # ── Sources ──────────────────────────────────────────────────────────────
    def source(url, type_, collecte, detail):
        cur.execute(
            "INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
            (url, type_, collecte, detail))
        return cur.lastrowid

    s_htv = source(
        "https://github.com/HowTheyVote/data", "dataset", "2026-05-09",
        "Export local : donnees_brutes/Howtheyvote/export (last_updated 2026-05-09, licence ODbL)")
    s_dia_attal = source(
        "https://www.hatvp.fr/consulter-les-declarations/", "declaration_hatvp", "2026-05-11",
        "DIA de Gabriel Attal déposée le 09/09/2024 — PDF local : "
        "donnees_brutes/Gabriel_Attal/attal-gabriel-dia30320-depute-92.pdf")
    s_dia_ret = source(
        "https://www.hatvp.fr/consulter-les-declarations/", "declaration_hatvp", "2026-05-11",
        "DIA de Bruno Retailleau déposée le 09/01/2026 — PDF local : "
        "donnees_brutes/Bruno_Retailleau/retailleau-bruno-dia34773-senateur-85.pdf")

    # ── Bardella : lecture programmatique du dataset HowTheyVote ────────────
    with open(hv / "members.csv", encoding="utf-8") as f:
        membre = next((r for r in csv.DictReader(f) if r["id"] == BARDELLA_MEP_ID), None)
    if membre is None:
        sys.exit(f"MEP {BARDELLA_MEP_ID} introuvable dans members.csv — abandon.")
    if (membre["first_name"], membre["last_name"]) != ("Jordan", "BARDELLA"):
        sys.exit(f"L'ID {BARDELLA_MEP_ID} ne correspond pas à Jordan BARDELLA — abandon.")

    with open(hv / "group_memberships.csv", encoding="utf-8") as f:
        adhesions = [r for r in csv.DictReader(f) if r["member_id"] == BARDELLA_MEP_ID]
    if not adhesions:
        sys.exit("Aucune adhésion de groupe trouvée pour Bardella — abandon.")

    # ── Personnes ────────────────────────────────────────────────────────────
    def personne(nom, prenom, slug, naissance=None, naissance_source=None):
        cur.execute(
            "INSERT INTO personnes (nom, prenom, slug, naissance, naissance_source_id) "
            "VALUES (?,?,?,?,?)", (nom, prenom, slug, naissance, naissance_source))
        return cur.lastrowid

    p_attal = personne("Attal", "Gabriel", "gabriel-attal", "1989-03-16", s_dia_attal)
    p_bardella = personne("Bardella", "Jordan", "jordan-bardella",
                          membre["date_of_birth"] or None,
                          s_htv if membre["date_of_birth"] else None)
    p_melenchon = personne("Mélenchon", "Jean-Luc", "jean-luc-melenchon")   # naissance : à importer
    p_philippe = personne("Philippe", "Édouard", "edouard-philippe")        # naissance : à importer
    p_retailleau = personne("Retailleau", "Bruno", "bruno-retailleau", "1960-11-20", s_dia_ret)

    # ── Mandats ──────────────────────────────────────────────────────────────
    def mandat(pid, type_, debut, fin, detail, precision, src):
        cur.execute(
            "INSERT INTO mandats (personne_id, type, debut, fin, detail, precision, source_id) "
            "VALUES (?,?,?,?,?,?,?)", (pid, type_, debut, fin, detail, precision, src))

    # Bardella — mandats d'eurodéputé dérivés des adhésions de groupe (termes 9 et 10)
    for a in adhesions:
        mandat(p_bardella, "eurodepute", a["start_date"], a["end_date"] or None,
               f"Parlement européen, législature {a['term']}, groupe {a['group_code']} "
               "(bornes = dates d'adhésion au groupe, dataset HowTheyVote)",
               "jour", s_htv)

    # Attal — DIA HATVP du 09/09/2024 (couvre les 5 années précédentes)
    mandat(p_attal, "depute", "2024-07-08", None,
           "Député des Hauts-de-Seine, élu le 08/07/2024 ; en cours au dépôt de la DIA. "
           "Mandat de député antérieur (2017-2022) hors périmètre de cette DIA : à importer (open data AN).",
           "jour", s_dia_attal)
    mandat(p_attal, "secretaire_etat", "2019-01-01", fin_de_mois(2020, 6),
           "Secrétaire d'État, ministère de l'Éducation nationale et de la Jeunesse (01/2019-06/2020)",
           "mois", s_dia_attal)
    mandat(p_attal, "secretaire_etat", "2020-07-01", fin_de_mois(2022, 5),
           "Secrétaire d'État, porte-parole du Gouvernement (07/2020-05/2022)",
           "mois", s_dia_attal)
    mandat(p_attal, "ministre", "2022-07-01", fin_de_mois(2023, 7),
           "Ministre des Comptes publics (07/2022-07/2023)", "mois", s_dia_attal)
    mandat(p_attal, "ministre", "2023-07-01", fin_de_mois(2024, 1),
           "Ministre de l'Éducation nationale et de la Jeunesse (07/2023-01/2024)",
           "mois", s_dia_attal)
    mandat(p_attal, "premier_ministre", "2024-01-01", fin_de_mois(2024, 9),
           "Premier ministre (01/2024-09/2024)", "mois", s_dia_attal)
    mandat(p_attal, "conseiller_municipal", "2019-01-01", None,
           "Conseiller municipal depuis 01/2019, « fonction en cours » au dépôt de la DIA (09/09/2024) ; "
           "commune non précisée dans la DIA", "mois", s_dia_attal)

    # Retailleau — DIA HATVP du 09/01/2026 (couvre les 5 années précédentes)
    mandat(p_retailleau, "senateur", "2019-01-01", fin_de_mois(2024, 10),
           "Sénateur de la Vendée, président de groupe parlementaire (01/2019-10/2024). "
           "Mandats sénatoriaux antérieurs à 2019 hors périmètre de cette DIA : à importer (data.senat.fr).",
           "mois", s_dia_ret)
    mandat(p_retailleau, "ministre", "2024-09-01", fin_de_mois(2025, 10),
           "Ministre de l'Intérieur (09/2024-10/2025)", "mois", s_dia_ret)
    mandat(p_retailleau, "senateur", "2025-11-13", None,
           "Sénateur de la Vendée, élu le 13/11/2025, en cours au dépôt de la DIA", "jour", s_dia_ret)
    mandat(p_retailleau, "conseiller_regional", "2020-01-01", None,
           "Conseiller régional des Pays-de-la-Loire depuis 01/2020, fonction conservée au dépôt de la DIA",
           "mois", s_dia_ret)

    # Mélenchon, Philippe : aucun mandat saisi — aucune source locale vérifiable.
    # Leurs mandats viendront des imports officiels (AN pour Mélenchon, RNE/JO pour Philippe).

    # ── Déclarations (les deux DIA elles-mêmes) ─────────────────────────────
    cur.execute(
        "INSERT INTO declarations (personne_id, type, contenu, date, source_id) VALUES (?,?,?,?,?)",
        (p_attal, "interets",
         "Déclaration d'intérêts et d'activités (DIA) de député, déposée à la HATVP", "2024-09-09", s_dia_attal))
    cur.execute(
        "INSERT INTO declarations (personne_id, type, contenu, date, source_id) VALUES (?,?,?,?,?)",
        (p_retailleau, "interets",
         "Déclaration d'intérêts et d'activités (DIA) de sénateur, déposée à la HATVP", "2026-01-09", s_dia_ret))

    # ── Journal d'import ─────────────────────────────────────────────────────
    maintenant = datetime.now().isoformat(timespec="seconds")
    for src, n in ((s_htv, 1 + len(adhesions)),
                   (s_dia_attal, 1 + 7 + 1),
                   (s_dia_ret, 1 + 4 + 1)):
        cur.execute(
            "INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
            (src, "ingestion/seed_identites.py", n, maintenant))

    con.commit()
    total_m = cur.execute("SELECT COUNT(*) FROM mandats").fetchone()[0]
    print(f"Semé : 5 personnes, {total_m} mandats sourcés, 2 déclarations, 3 sources.")
    print("Sans source locale (état « à importer ») : naissance et mandats de Mélenchon et Philippe ; "
          "mandat de député 2017-2022 d'Attal ; mandats sénatoriaux de Retailleau antérieurs à 2019.")
    con.close()


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    coffre = Path(sys.argv[2]) if len(sys.argv) > 2 else COFFRE_DEFAUT
    seed(base, coffre)

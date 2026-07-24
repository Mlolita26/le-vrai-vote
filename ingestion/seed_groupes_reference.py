"""Rattachement éditorial : candidat → groupe parlementaire de son parti,
par législature. N'est saisi que ce qui est net et vérifiable sur les pages
officielles des groupes (assemblee-nationale.fr) : le parti du candidat
possède un groupe propre à l'Assemblée sur la législature donnée.

Volontairement ABSENTS (pas de groupe rattachable — affiché tel quel) :
  - RN sur la 15e législature (8 députés, non-inscrits) ;
  - Horizons sur la 15e (parti créé en 2021) ;
  - les partis sans groupe : LO, UPR, DLF, Révolution permanente, NPA-R,
    Solution démocratique, Équinoxe, Nouvelle Énergie, La Convention,
    Nous France, Les Patriotes, UDB ;
  - les cas ambigus : Batho (Génération écologie ≠ Les Écologistes),
    Autain et Ruffin (partis récents distincts de LFI — leurs propres votes
    sont en base de toute façon).

Usage : python ingestion/seed_groupes_reference.py [chemin_base]
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

# (slug, législature, groupe_abrege AMO, justification)
RATTACHEMENTS = [
    ("gabriel-attal", "15", "LaREM", "Renaissance (ex-LREM) — groupe La République en Marche"),
    ("gabriel-attal", "16", "RE", "Renaissance — groupe Renaissance"),
    ("gabriel-attal", "17", "EPR", "Renaissance — groupe Ensemble pour la République"),
    ("marine-le-pen", "16", "RN", "Rassemblement national — groupe RN"),
    ("marine-le-pen", "17", "RN", "Rassemblement national — groupe RN"),
    ("jean-luc-melenchon", "15", "FI", "La France insoumise — groupe FI"),
    ("jean-luc-melenchon", "16", "LFI - NUPES", "La France insoumise — groupe LFI-NUPES"),
    ("jean-luc-melenchon", "17", "LFI-NFP", "La France insoumise — groupe LFI-NFP"),
    ("jerome-guedj", "15", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("jerome-guedj", "16", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("jerome-guedj", "17", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("philippe-brun", "15", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("philippe-brun", "16", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("philippe-brun", "17", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("karim-bouamrane", "15", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("karim-bouamrane", "16", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("karim-bouamrane", "17", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("segolene-royal", "15", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("segolene-royal", "16", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("segolene-royal", "17", "SOC", "Parti socialiste — groupe Socialistes et apparentés"),
    ("bruno-retailleau", "15", "LR", "Les Républicains — groupe LR (Assemblée)"),
    ("bruno-retailleau", "16", "LR", "Les Républicains — groupe LR (Assemblée)"),
    ("bruno-retailleau", "17", "DR", "Les Républicains — groupe Droite Républicaine"),
    ("edouard-philippe", "16", "HOR", "Horizons — groupe Horizons et apparentés"),
    ("edouard-philippe", "17", "HOR", "Horizons — groupe Horizons & Indépendants"),
    ("marine-tondelier", "16", "Ecolo - NUPES", "Les Écologistes — groupe Écologiste-NUPES"),
    ("marine-tondelier", "17", "EcoS", "Les Écologistes — groupe Écologiste et Social"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    if cur.execute("SELECT COUNT(*) FROM groupes_reference").fetchone()[0]:
        sys.exit("La table groupes_reference n'est pas vide — la vider avant de re-semer.")

    cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                ("https://www.assemblee-nationale.fr/dyn/instances", "autre", "2026-07-24",
                 "Pages officielles des groupes politiques de l'Assemblée nationale (composition "
                 "et affiliation partisane), croisées avec le référentiel AMO30."))
    src = cur.lastrowid

    abreges_connus = {a for (a,) in cur.execute(
        "SELECT DISTINCT groupe_abrege FROM positions_groupes WHERE groupe_abrege IS NOT NULL")}

    for slug, leg, abrege, detail in RATTACHEMENTS:
        pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (slug,)).fetchone()
        if not pid:
            sys.exit(f"Personne inconnue : {slug}")
        if abrege not in abreges_connus:
            print(f"  [attention] {slug} L{leg} : groupe « {abrege} » absent des scrutins "
                  "des votes clés (normal si le groupe n'existait pas encore à ces dates).")
        cur.execute("INSERT INTO groupes_reference (personne_id, legislature, groupe_abrege, detail, source_id) "
                    "VALUES (?,?,?,?,?)", (pid[0], leg, abrege, detail, src))

    con.commit()
    print(f"Semé : {len(RATTACHEMENTS)} rattachements candidat → groupe (cas nets uniquement).")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

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
    # ── Parlement européen : délégation française du parti (termes 9 et 10) ─────
    # Cas nets uniquement (délégation française = le parti) : RN et LFI. Le
    # candidat n'a pas nécessairement siégé au PE — c'est la position de sa
    # délégation ; l'UI affiche « n'y siégeait pas » le cas échéant.
    ("marine-le-pen", "pe9", "RN",
     "Rassemblement national — délégation française au groupe Identité et démocratie "
     "(PE, 2019-2024). Marine Le Pen n'y siégeait pas (mandat européen achevé en 2017) : "
     "position de la délégation, pas un vote personnel."),
    ("marine-le-pen", "pe10", "RN",
     "Rassemblement national — délégation française au groupe Patriotes pour l'Europe "
     "(PE, depuis 2024). Position de la délégation, pas un vote personnel de Marine Le Pen."),
    ("jean-luc-melenchon", "pe9", "LFI",
     "La France insoumise — délégation française au groupe The Left/GUE-NGL (PE, 2019-2024). "
     "Jean-Luc Mélenchon n'y siégeait pas (mandat européen achevé en 2017) : position de la délégation."),
    ("jean-luc-melenchon", "pe10", "LFI",
     "La France insoumise — délégation française au groupe The Left/GUE-NGL (PE, depuis 2024). "
     "Position de la délégation, pas un vote personnel de Jean-Luc Mélenchon."),
    # Parti socialiste → groupe S&D (délégation française : PS + Place publique).
    ("karim-bouamrane", "pe9", "PS", "Parti socialiste — délégation française du groupe S&D au Parlement européen (2019-2024). Position de la délégation, pas un vote personnel."),
    ("karim-bouamrane", "pe10", "PS", "Parti socialiste — délégation française du groupe S&D au Parlement européen (depuis 2024). Position de la délégation, pas un vote personnel."),
    ("jerome-guedj", "pe9", "PS", "Parti socialiste — délégation française du groupe S&D (2019-2024). Position de la délégation, pas un vote personnel."),
    ("jerome-guedj", "pe10", "PS", "Parti socialiste — délégation française du groupe S&D (depuis 2024). Position de la délégation, pas un vote personnel."),
    ("philippe-brun", "pe9", "PS", "Parti socialiste — délégation française du groupe S&D (2019-2024). Position de la délégation, pas un vote personnel."),
    ("philippe-brun", "pe10", "PS", "Parti socialiste — délégation française du groupe S&D (depuis 2024). Position de la délégation, pas un vote personnel."),
    ("segolene-royal", "pe9", "PS", "Parti socialiste — délégation française du groupe S&D (2019-2024). Position de la délégation, pas un vote personnel."),
    ("segolene-royal", "pe10", "PS", "Parti socialiste — délégation française du groupe S&D (depuis 2024). Position de la délégation, pas un vote personnel."),
    # Les Républicains → groupe PPE (délégation française : LR).
    ("bruno-retailleau", "pe9", "LR", "Les Républicains — délégation française du groupe PPE au Parlement européen (2019-2024). Position de la délégation, pas un vote personnel."),
    ("bruno-retailleau", "pe10", "LR", "Les Républicains — délégation française du groupe PPE (depuis 2024). Position de la délégation, pas un vote personnel."),
    ("david-lisnard", "pe9", "LR", "Les Républicains — délégation française du groupe PPE (2019-2024). Position de la délégation, pas un vote personnel."),
    ("david-lisnard", "pe10", "LR", "Les Républicains — délégation française du groupe PPE (depuis 2024). Position de la délégation, pas un vote personnel."),
    # Renaissance et Horizons → groupe Renew Europe (délégation française commune).
    ("gabriel-attal", "pe9", "RE", "Renaissance — délégation française du groupe Renew Europe au Parlement européen (2019-2024). Position de la délégation (Renaissance, MoDem, Horizons), pas un vote personnel."),
    ("gabriel-attal", "pe10", "RE", "Renaissance — délégation française du groupe Renew Europe (depuis 2024). Position de la délégation, pas un vote personnel."),
    ("edouard-philippe", "pe9", "RE", "Horizons — siège au sein de la délégation française du groupe Renew Europe (2019-2024). Position de la délégation (Renaissance, MoDem, Horizons), pas un vote personnel d'Édouard Philippe."),
    ("edouard-philippe", "pe10", "RE", "Horizons — délégation française du groupe Renew Europe (depuis 2024). Position de la délégation, pas un vote personnel."),
    # Les Écologistes (EELV) → groupe Verts/ALE (délégation française).
    ("marine-tondelier", "pe9", "VERT", "Les Écologistes — délégation française du groupe Verts/ALE au Parlement européen (2019-2024). Position de la délégation, pas un vote personnel."),
    ("marine-tondelier", "pe10", "VERT", "Les Écologistes — délégation française du groupe Verts/ALE (depuis 2024). Position de la délégation, pas un vote personnel."),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # Idempotent : on n'ajoute que les rattachements (personne, législature) absents.
    existants = {(pid, leg) for pid, leg in cur.execute(
        "SELECT personne_id, legislature FROM groupes_reference")}
    abreges_connus = {a for (a,) in cur.execute(
        "SELECT DISTINCT groupe_abrege FROM positions_groupes WHERE groupe_abrege IS NOT NULL")}

    a_ajouter = []
    for slug, leg, abrege, detail in RATTACHEMENTS:
        pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (slug,)).fetchone()
        if not pid:
            sys.exit(f"Personne inconnue : {slug}")
        if (pid[0], leg) in existants:
            continue
        if abrege not in abreges_connus:
            print(f"  [attention] {slug} {leg} : groupe « {abrege} » absent des scrutins "
                  "des votes clés (normal si le groupe/terme n'est pas encore importé).")
        a_ajouter.append((pid[0], leg, abrege, detail))

    if not a_ajouter:
        print("groupes_reference : déjà à jour, rien à ajouter.")
        con.close()
        return

    # Deux sources selon l'échelle (AN vs PE), créées seulement si nécessaires.
    src_an = src_pe = None
    def source_an():
        nonlocal src_an
        if src_an is None:
            cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                        ("https://www.assemblee-nationale.fr/dyn/instances", "autre", "2026-07-24",
                         "Pages officielles des groupes politiques de l'Assemblée nationale "
                         "(composition et affiliation partisane), croisées avec le référentiel AMO30."))
            src_an = cur.lastrowid
        return src_an
    def source_pe():
        nonlocal src_pe
        if src_pe is None:
            cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                        ("https://www.europarl.europa.eu/meps/fr/", "autre", "2026-07-24",
                         "Rattachement éditorial candidat → délégation française de son parti au "
                         "Parlement européen (groupe et terme), fiches officielles europarl.europa.eu."))
            src_pe = cur.lastrowid
        return src_pe

    for pid, leg, abrege, detail in a_ajouter:
        src = source_pe() if leg.startswith("pe") else source_an()
        cur.execute("INSERT INTO groupes_reference (personne_id, legislature, groupe_abrege, detail, source_id) "
                    "VALUES (?,?,?,?,?)", (pid, leg, abrege, detail, src))

    con.commit()
    print(f"Semé : {len(a_ajouter)} rattachement(s) candidat → groupe ajouté(s) "
          f"({sum(1 for r in a_ajouter if r[1].startswith('pe'))} au PE).")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

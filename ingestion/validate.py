"""Valide le schéma et la logique d'affichage à trois états.

Deux volets :
  1. Tests de la vue `couverture` sur une base EN MÉMOIRE peuplée de données
     FICTIVES clairement étiquetées TEST (jamais écrites dans la vraie base) —
     un cas par état : indisponible / non_concerne / position connue / a_importer.
  2. Contrôles d'intégrité et de cohérence sur la vraie base
     (clés étrangères, mandats sourcés, faits attendus des sources locales).

Usage : python ingestion/validate.py [chemin_base]
Sortie : code 0 si tout passe, 1 sinon.
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SCHEMA = RACINE / "db" / "schema.sql"
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

ECHECS = []


def verifier(nom: str, condition: bool, detail: str = ""):
    statut = "OK " if condition else "ÉCHEC"
    print(f"  [{statut}] {nom}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        ECHECS.append(nom)


def test_logique_trois_etats():
    """Base en mémoire, données fictives TEST : un cas par état de la vue."""
    print("1. Logique des trois états (base en mémoire, données fictives TEST)")
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    cur = con.cursor()

    cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES "
                "('https://exemple.invalid/test','autre','2026-01-01','fixture de test')")
    src = cur.lastrowid
    # Quatre personnes fictives
    cur.executemany("INSERT INTO personnes (nom, prenom, slug) VALUES (?,?,?)", [
        ("TEST-JamaisParlementaire", "X", "test-jamais"),
        ("TEST-HorsMandat", "X", "test-hors-mandat"),
        ("TEST-PositionConnue", "X", "test-position"),
        ("TEST-EnPosteSansDonnee", "X", "test-a-importer"),
    ])
    ids = {slug: pid for pid, slug in cur.execute("SELECT id, slug FROM personnes")}
    # Mandats : députée 2020-2024 (hors scrutin de 2025) ; deux députés couvrant 2025
    cur.executemany(
        "INSERT INTO mandats (personne_id, type, debut, fin, detail, precision, source_id) "
        "VALUES (?,?,?,?,?,'jour',?)", [
            (ids["test-hors-mandat"], "depute", "2020-01-01", "2024-06-09", "TEST", src),
            (ids["test-position"], "depute", "2024-07-08", None, "TEST", src),
            (ids["test-a-importer"], "depute", "2024-07-08", None, "TEST", src),
        ])
    # Un scrutin AN fictif en 2025, promu vote clé
    cur.execute("INSERT INTO scrutins (chambre, numero, objet, date, source_id) "
                "VALUES ('an','TEST-1','Scrutin fictif de test','2025-03-15',?)", (src,))
    scrutin = cur.lastrowid
    cur.execute("INSERT INTO thematiques (libelle, ordre) VALUES ('TEST', 1)")
    cur.execute("INSERT INTO votes_cles (scrutin_id, thematique_id, resume, source_resume) "
                "VALUES (?,?, 'Résumé fictif de test', 'https://exemple.invalid/dossier')",
                (scrutin, cur.lastrowid))
    cur.execute("INSERT INTO positions_vote (personne_id, scrutin_id, position) VALUES (?,?,'contre')",
                (ids["test-position"], scrutin))

    etats = dict(cur.execute("SELECT personne_slug, etat FROM couverture"))
    verifier("jamais parlementaire → indisponible", etats.get("test-jamais") == "indisponible", str(etats))
    verifier("mandat clos avant le scrutin → non_concerne", etats.get("test-hors-mandat") == "non_concerne", str(etats))
    verifier("position importée → contre", etats.get("test-position") == "contre", str(etats))
    verifier("en poste sans donnée → a_importer", etats.get("test-a-importer") == "a_importer", str(etats))

    # Garde-fou éditorial : une affaire en cours doit porter la présomption d'innocence
    import sqlite3 as s3
    try:
        cur.execute("INSERT INTO affaires_judiciaires (personne_id, statut, date, detail, presomption, source_id) "
                    "VALUES (?, 'mise_en_examen', '2025-01-01', 'TEST', 0, ?)", (ids["test-jamais"], src))
        verifier("affaire en cours sans présomption rejetée", False)
    except s3.IntegrityError:
        verifier("affaire en cours sans présomption rejetée", True)
    con.close()


def controles_base_reelle(base: Path):
    print(f"2. Contrôles de la base réelle ({base.name})")
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    verifier("intégrité des clés étrangères",
             cur.execute("PRAGMA foreign_key_check").fetchall() == [])
    verifier("aucune donnée fictive TEST dans la base réelle",
             cur.execute("SELECT COUNT(*) FROM personnes WHERE nom LIKE 'TEST-%'").fetchone()[0] == 0)
    verifier("5 personnes suivies",
             cur.execute("SELECT COUNT(*) FROM personnes").fetchone()[0] == 5)
    verifier("toute naissance renseignée est sourcée",
             cur.execute("SELECT COUNT(*) FROM personnes WHERE naissance IS NOT NULL "
                         "AND naissance_source_id IS NULL").fetchone()[0] == 0)

    # Faits attendus des sources locales dépouillées
    verifier("Bardella : eurodéputé actif au 01/01/2020 (terme 9)",
             cur.execute("SELECT COUNT(*) FROM mandats m JOIN personnes p ON p.id = m.personne_id "
                         "WHERE p.slug='jordan-bardella' AND m.type='eurodepute' "
                         "AND m.debut <= '2020-01-01' AND (m.fin IS NULL OR m.fin >= '2020-01-01')"
                         ).fetchone()[0] == 1)
    verifier("Bardella : pas encore eurodéputé au 01/06/2019",
             cur.execute("SELECT COUNT(*) FROM mandats m JOIN personnes p ON p.id = m.personne_id "
                         "WHERE p.slug='jordan-bardella' AND m.type='eurodepute' "
                         "AND m.debut <= '2019-06-01' AND (m.fin IS NULL OR m.fin >= '2019-06-01')"
                         ).fetchone()[0] == 0)
    def mandat_actif(slug, type_, date):
        return cur.execute(
            "SELECT COUNT(*) FROM mandats m JOIN personnes p ON p.id = m.personne_id "
            "WHERE p.slug=? AND m.type=? AND m.debut <= ? "
            "AND (m.fin IS NULL OR m.fin >= ?)", (slug, type_, date, date)).fetchone()[0]

    # Cas de contrôle issus de l'AMO30 historique (mandats officiels datés au jour).
    verifier("Mélenchon : député actif au 01/01/2020 (L15)",
             mandat_actif("jean-luc-melenchon", "depute", "2020-01-01") == 1)
    verifier("Mélenchon : plus député au 16/03/2023 (vote retraites → non concerné)",
             mandat_actif("jean-luc-melenchon", "depute", "2023-03-16") == 0)
    verifier("Philippe : député actif au 01/01/2015 (L14)",
             mandat_actif("edouard-philippe", "depute", "2015-01-01") == 1)
    verifier("Philippe : aucun mandat parlementaire depuis nos premiers scrutins (10/07/2017 → non concerné)",
             mandat_actif("edouard-philippe", "depute", "2017-07-10") == 0
             and mandat_actif("edouard-philippe", "senateur", "2017-07-10") == 0)
    verifier("Attal : député actif au 01/01/2018 (L15, avant son entrée au gouvernement)",
             mandat_actif("gabriel-attal", "depute", "2018-01-01") == 1)
    verifier("Attal : plus député au 16/03/2023 (ministre, siège au suppléant → non concerné)",
             mandat_actif("gabriel-attal", "depute", "2023-03-16") == 0)
    verifier("Retailleau : sénateur actif aujourd'hui (mandat du 13/11/2025, fin NULL)",
             cur.execute("SELECT COUNT(*) FROM mandats m JOIN personnes p ON p.id = m.personne_id "
                         "WHERE p.slug='bruno-retailleau' AND m.type='senateur' AND m.fin IS NULL"
                         ).fetchone()[0] == 1)
    verifier("Retailleau : sénateur sans interruption de 2004 à octobre 2024",
             all(mandat_actif("bruno-retailleau", "senateur", d) == 1
                 for d in ("2005-01-01", "2015-01-01", "2022-01-01")))
    verifier("les 5 naissances sont renseignées et sourcées",
             cur.execute("SELECT COUNT(*) FROM personnes WHERE naissance IS NOT NULL "
                         "AND naissance_source_id IS NOT NULL").fetchone()[0] == 5)

    n_mandats = cur.execute("SELECT COUNT(*) FROM mandats").fetchone()[0]
    n_sources = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    print(f"  Récapitulatif : {n_mandats} mandats, {n_sources} sources, "
          f"{cur.execute('SELECT COUNT(*) FROM declarations').fetchone()[0]} déclarations.")
    con.close()


def controles_scrutins_an(base: Path, dossier_dumps: Path):
    """Contrôles du jalon J2 : volumes contre les dumps, recoupements externes."""
    import zipfile
    print(f"3. Contrôles des scrutins AN (dumps : {dossier_dumps.name})")
    con = sqlite3.connect(base)
    cur = con.cursor()

    if cur.execute("SELECT COUNT(*) FROM scrutins WHERE chambre='an'").fetchone()[0] == 0:
        print("  (aucun scrutin AN importé — contrôles sautés)")
        con.close()
        return

    # Volumes : chaque zip doit être intégralement importé (pas de troncature silencieuse).
    for zip_path in sorted(dossier_dumps.glob("Scrutins*.zip")):
        with zipfile.ZipFile(zip_path) as z:
            entrees = [e for e in z.namelist() if e.endswith(".json")]
            import json as _json
            with z.open(entrees[0]) as f:
                leg = _json.load(f)["scrutin"]["legislature"]
        en_base = cur.execute("SELECT COUNT(*) FROM scrutins WHERE chambre IN ('an','congres') "
                              "AND legislature=?", (leg,)).fetchone()[0]
        verifier(f"législature {leg} intégralement importée ({len(entrees)} scrutins)",
                 en_base == len(entrees), f"base={en_base}, dump={len(entrees)}")

    # Recoupement Datan (contrôle, jamais source) : Attal POUR l'aide à mourir
    # au scrutin solennel de première lecture (27/05/2025).
    rows = cur.execute(
        "SELECT s.date, s.objet, pv.position FROM scrutins s "
        "JOIN positions_vote pv ON pv.scrutin_id = s.id "
        "JOIN personnes p ON p.id = pv.personne_id "
        "WHERE p.slug='gabriel-attal' AND s.legislature='17' "
        "AND s.type_vote LIKE '%solennel%' AND s.objet LIKE '%aide%mourir%'").fetchall()
    verifier("Attal, scrutin solennel « aide à mourir » : position POUR retrouvée (recoupement Datan)",
             any(r[2] == "pour" for r in rows), f"lignes trouvées : {rows}")

    # Présence d'Attal aux scrutins solennels de la 17e législature.
    # Datan affichait 93 % au 11/05/2026 ; nos données vont jusqu'à juillet 2026,
    # on tolère une fourchette large et on affiche la valeur pour revue humaine.
    present, total = cur.execute(
        "SELECT SUM(CASE WHEN pv.position != 'absent' THEN 1 ELSE 0 END), COUNT(*) "
        "FROM positions_vote pv JOIN scrutins s ON s.id = pv.scrutin_id "
        "JOIN personnes p ON p.id = pv.personne_id "
        "WHERE p.slug='gabriel-attal' AND s.legislature='17' AND s.type_vote LIKE '%solennel%'"
    ).fetchone()
    if total:
        taux = 100.0 * present / total
        print(f"  [INFO] Présence d'Attal aux scrutins solennels L17 : {present}/{total} = {taux:.1f} % "
              "(Datan au 11/05/2026 : 93 %)")
        verifier("présence solennels L17 d'Attal dans une fourchette plausible (80-100 %)",
                 80.0 <= taux <= 100.0, f"{taux:.1f} %")
    else:
        verifier("Attal a des positions sur des scrutins solennels L17", False, "aucune ligne")

    # Mélenchon (PA2150) : ses positions L15 doivent exister, et rien après
    # la fin de son mandat de député (21/06/2022).
    verifier("Mélenchon : des positions existent sur la L15",
             cur.execute("SELECT COUNT(*) FROM positions_vote pv "
                         "JOIN personnes p ON p.id = pv.personne_id "
                         "JOIN scrutins s ON s.id = pv.scrutin_id "
                         "WHERE p.slug='jean-luc-melenchon' AND s.legislature='15'"
                         ).fetchone()[0] > 0)
    verifier("Mélenchon : aucune position après la fin de son mandat (21/06/2022)",
             cur.execute("SELECT COUNT(*) FROM positions_vote pv "
                         "JOIN personnes p ON p.id = pv.personne_id "
                         "JOIN scrutins s ON s.id = pv.scrutin_id "
                         "WHERE p.slug='jean-luc-melenchon' AND s.date > '2022-06-21'"
                         ).fetchone()[0] == 0)

    # Cohérence : aucune absence inférée hors période de mandat pertinent
    # (séance AN : député ; Congrès : député ou sénateur).
    orphelines = cur.execute(
        "SELECT COUNT(*) FROM positions_vote pv JOIN scrutins s ON s.id = pv.scrutin_id "
        "WHERE s.chambre IN ('an','congres') AND pv.position = 'absent' AND NOT EXISTS ("
        "  SELECT 1 FROM mandats m WHERE m.personne_id = pv.personne_id "
        "  AND ((s.chambre='an' AND m.type='depute') "
        "    OR (s.chambre='congres' AND m.type IN ('depute','senateur'))) "
        "  AND m.debut <= s.date AND COALESCE(m.fin,'9999-12-31') >= s.date)").fetchone()[0]
    verifier("aucune absence inférée hors période de mandat", orphelines == 0, f"{orphelines} lignes")

    n_pos = cur.execute("SELECT COUNT(*) FROM positions_vote").fetchone()[0]
    n_scr = cur.execute("SELECT COUNT(*) FROM scrutins").fetchone()[0]
    n_abs = cur.execute("SELECT COUNT(*) FROM positions_vote WHERE position='absent'").fetchone()[0]
    print(f"  Récapitulatif : {n_scr} scrutins, {n_pos} positions ({n_abs} absences inférées).")
    con.close()


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    test_logique_trois_etats()
    if base.exists():
        controles_base_reelle(base)
        COFFRE = Path(r"C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles")
        dumps = COFFRE / "donnees_brutes" / "Assemblee_Nationale" / "dump_manuel_2026-07-23"
        if dumps.exists():
            controles_scrutins_an(base, dumps)
    else:
        print(f"2. Base réelle absente ({base}) — contrôles sautés.")
    if ECHECS:
        print(f"\n{len(ECHECS)} contrôle(s) en échec : {ECHECS}")
        sys.exit(1)
    print("\nTous les contrôles passent.")

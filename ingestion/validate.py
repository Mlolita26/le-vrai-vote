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
    for slug in ("edouard-philippe", "jean-luc-melenchon"):
        verifier(f"{slug} : aucun mandat parlementaire saisi (sources locales absentes → indisponible/à importer)",
                 cur.execute("SELECT COUNT(*) FROM mandats m JOIN personnes p ON p.id = m.personne_id "
                             "WHERE p.slug=? AND m.type IN ('depute','senateur','eurodepute')",
                             (slug,)).fetchone()[0] == 0)
    verifier("Retailleau : sénateur actif aujourd'hui (mandat du 13/11/2025, fin NULL)",
             cur.execute("SELECT COUNT(*) FROM mandats m JOIN personnes p ON p.id = m.personne_id "
                         "WHERE p.slug='bruno-retailleau' AND m.type='senateur' AND m.fin IS NULL"
                         ).fetchone()[0] == 1)

    # Point d'attention connu (informative, pas un échec) : le mandat AN 2017-2022
    # d'Attal n'est couvert par aucune source locale — attendu jusqu'au jalon J2.
    attal_2023 = cur.execute(
        "SELECT COUNT(*) FROM mandats m JOIN personnes p ON p.id = m.personne_id "
        "WHERE p.slug='gabriel-attal' AND m.type='depute' "
        "AND m.debut <= '2023-03-16' AND (m.fin IS NULL OR m.fin >= '2023-03-16')").fetchone()[0]
    print(f"  [INFO] Attal député au 16/03/2023 (vote retraites) : {attal_2023} mandat trouvé — "
          "0 attendu tant que l'open data AN (J2) n'est pas importé.")

    n_mandats = cur.execute("SELECT COUNT(*) FROM mandats").fetchone()[0]
    n_sources = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    print(f"  Récapitulatif : {n_mandats} mandats, {n_sources} sources, "
          f"{cur.execute('SELECT COUNT(*) FROM declarations').fetchone()[0]} déclarations.")
    con.close()


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    test_logique_trois_etats()
    if base.exists():
        controles_base_reelle(base)
    else:
        print(f"2. Base réelle absente ({base}) — contrôles sautés.")
    if ECHECS:
        print(f"\n{len(ECHECS)} contrôle(s) en échec : {ECHECS}")
        sys.exit(1)
    print("\nTous les contrôles passent.")

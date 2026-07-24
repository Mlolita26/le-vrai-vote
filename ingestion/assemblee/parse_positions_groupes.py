"""Extrait, pour chaque scrutin promu vote clé, les décomptes officiels
par groupe parlementaire (pour / contre / abstention / non-votant), depuis
les mêmes dumps que les positions individuelles.

Les libellés de groupes viennent du référentiel officiel AMO30 (organes de
type GP). Un organeRef absent du référentiel (ex. groupes du Sénat dans le
scrutin du Congrès) est conservé avec un libellé NULL — l'affichage le
signale au lieu de l'inventer.

Usage : python ingestion/assemblee/parse_positions_groupes.py [chemin_base] [dossier_dumps]
"""
import json
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
COFFRE = Path(r"C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles")
DUMPS_DEFAUT = COFFRE / "donnees_brutes" / "Assemblee_Nationale" / "dump_manuel_2026-07-23"
AMO30 = "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"


def liste(v):
    return v if isinstance(v, list) else ([] if v is None else [v])


def entier(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def importer(base: Path, dossier: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    cibles = {uid: (sid, None) for sid, uid in cur.execute(
        "SELECT s.id, s.uid_officiel FROM votes_cles vc JOIN scrutins s ON s.id = vc.scrutin_id")}
    if not cibles:
        sys.exit("Aucun vote clé en base — exécuter seed_votes_cles.py d'abord.")

    # Référentiel des groupes politiques (AMO30, organes GP).
    groupes = {}
    with zipfile.ZipFile(dossier / AMO30) as z:
        for entree in z.namelist():
            if "/organe/" not in entree or not entree.endswith(".json"):
                continue
            with z.open(entree) as f:
                o = json.load(f).get("organe", {})
            if o.get("codeType") != "GP":
                continue
            uid = o.get("uid")
            uid = uid.get("#text") if isinstance(uid, dict) else uid
            groupes[uid] = (o.get("libelleAbrege"), o.get("libelle"))

    cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                ("https://data.assemblee-nationale.fr", "scrutin_officiel", "2026-07-23",
                 "Décomptes par groupe extraits des dumps Scrutins (mêmes fichiers archivés que "
                 "l'import des positions individuelles) ; libellés de groupes : référentiel AMO30."))
    src = cur.lastrowid

    cur.execute("DELETE FROM positions_groupes")
    inseres, inconnus = 0, set()
    for zip_path in sorted(dossier.glob("Scrutins*.zip")):
        with zipfile.ZipFile(zip_path) as z:
            for entree in [x for x in z.namelist() if x.endswith(".json")]:
                uid_scrutin = entree.split("/")[-1].removesuffix(".json")
                if uid_scrutin not in cibles:
                    continue
                sid = cibles[uid_scrutin][0]
                with z.open(entree) as f:
                    s = json.load(f).get("scrutin", {})
                for organe in liste(s.get("ventilationVotes", {}).get("organe")):
                    for g in liste(organe.get("groupes", {}).get("groupe")):
                        ref = g.get("organeRef")
                        d = g.get("vote", {}).get("decompteVoix", {})
                        abrege, libelle = groupes.get(ref, (None, None))
                        if abrege is None:
                            inconnus.add(ref)
                        cur.execute(
                            "INSERT INTO positions_groupes (scrutin_id, organe_ref, groupe_abrege, "
                            "groupe_libelle, pour, contre, abstention, non_votant, source_id) "
                            "VALUES (?,?,?,?,?,?,?,?,?)",
                            (sid, ref, abrege, libelle, entier(d.get("pour")), entier(d.get("contre")),
                             entier(d.get("abstentions")), entier(d.get("nonVotants")), src))
                        inseres += 1

    cur.execute("INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
                (src, "ingestion/assemblee/parse_positions_groupes.py", inseres,
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()
    print(f"{inseres} lignes de positions de groupes insérées pour {len(cibles)} votes clés.")
    if inconnus:
        print(f"{len(inconnus)} organeRef hors référentiel AMO30 (probablement groupes du Sénat "
              f"au Congrès) — conservés sans libellé : {sorted(inconnus)[:8]}…")
    con.close()


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    dossier = Path(sys.argv[2]) if len(sys.argv) > 2 else DUMPS_DEFAUT
    importer(base, dossier)

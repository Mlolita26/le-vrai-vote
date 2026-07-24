"""Importe les scrutins publics de l'Assemblée nationale (dumps JSON officiels)
et les positions de vote des personnes suivies.

Pour chaque zip Scrutins*.zip du dossier de dumps :
  - crée une entrée `sources` (URL open data + date de collecte + sha256) ;
  - insère TOUS les scrutins de la législature (chambre 'an') ;
  - pour chaque personne suivie disposant d'un UID AN (identifiants_externes) :
      * position explicite du fichier officiel : pour / contre / abstention /
        non_votant (« non votant » = présent mais ne prend pas part au vote) ;
      * position inférée 'absent' : mandat de député actif à la date du
        scrutin ET aucune mention dans le fichier — l'absence n'est jamais
        listée explicitement par l'AN, cette dérivation est documentée ici ;
  - dérive la table `presence` (type 'scrutin') : present si position
    exprimée ou non_votant, absent sinon ;
  - journalise l'import (nombre de lignes) dans imports_journal.

Usage : python ingestion/assemblee/parse_scrutins.py [chemin_base] [dossier_dumps]
"""
import hashlib
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
COLLECTE_MANUELLE = "2026-07-23"

# Les séances ordinaires utilisent des clés au pluriel (pours, contres…),
# le Congrès de Versailles des clés au singulier (pour, abstention…).
POSITIONS = {"pours": "pour", "pour": "pour",
             "contres": "contre", "contre": "contre",
             "abstentions": "abstention", "abstention": "abstention",
             "nonVotants": "non_votant", "nonVotant": "non_votant",
             "nonVotantsVolontaires": "non_votant", "nonVotantVolontaire": "non_votant"}
# Convention AN : « suffrages exprimés » = pour + contre, hors abstentions.
EXPRIMES = {"pour", "contre"}


def liste(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def positions_du_scrutin(scrutin: dict, uids: set):
    """Extrait ({uid suivi: position}, nombre de suffrages exprimés listés)."""
    resultat, n_exprimes_listes = {}, 0
    ventilation = scrutin.get("ventilationVotes", {})
    for organe in liste(ventilation.get("organe")):
        for groupe in liste(organe.get("groupes", {}).get("groupe")):
            decompte = groupe.get("vote", {}).get("decompteNominatif", {})
            if not isinstance(decompte, dict):
                continue
            for cle, position in POSITIONS.items():
                bloc = decompte.get(cle)
                if not isinstance(bloc, dict):
                    continue
                votants = liste(bloc.get("votant"))
                if position in EXPRIMES:
                    n_exprimes_listes += len(votants)
                for votant in votants:
                    uid = votant.get("acteurRef")
                    if uid in uids:
                        resultat[uid] = position
    return resultat, n_exprimes_listes


def importer(base: Path, dossier: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    suivis = dict(cur.execute(
        "SELECT identifiant, personne_id FROM identifiants_externes WHERE systeme = 'an_uid'").fetchall())
    if not suivis:
        sys.exit("Aucun UID AN dans identifiants_externes — exécuter parse_amo.py d'abord.")
    uids = set(suivis)
    # Mandats parlementaires par personne (pour l'inférence d'absence).
    # Séance AN : seuls les députés sont concernés ; Congrès de Versailles :
    # députés et sénateurs votent ensemble.
    mandats = {}
    for pid, type_, debut, fin in cur.execute(
            "SELECT personne_id, type, debut, fin FROM mandats "
            "WHERE type IN ('depute','senateur')").fetchall():
        mandats.setdefault(pid, []).append((type_, debut, fin or "9999-12-31"))

    def concerne(pid, date, chambre):
        types = ("depute", "senateur") if chambre == "congres" else ("depute",)
        return any(t in types and d <= date <= f for t, d, f in mandats.get(pid, []))

    total_scrutins = total_positions = total_absents = 0
    ecarts = []  # (uid_officiel, date, exprimés annoncés, exprimés listés)
    for zip_path in sorted(dossier.glob("Scrutins*.zip")):
        sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        cur.execute(
            "INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
            ("https://data.assemblee-nationale.fr", "scrutin_officiel", COLLECTE_MANUELLE,
             f"Dump des scrutins publics en séance (rubrique Travaux parlementaires / Votes) — "
             f"fichier {zip_path.name}, téléchargé manuellement le {COLLECTE_MANUELLE}, "
             f"archivé : {zip_path}, sha256={sha}"))
        src = cur.lastrowid
        n_scrutins = n_positions = n_absents = 0

        with zipfile.ZipFile(zip_path) as z:
            entrees = [e for e in z.namelist() if e.endswith(".json")]
            for entree in entrees:
                with z.open(entree) as f:
                    s = json.load(f).get("scrutin", {})
                legislature = s.get("legislature")
                numero = s.get("numero")
                uid_officiel = s.get("uid")
                date = s.get("dateScrutin")
                objet = (s.get("titre") or (s.get("objet") or {}).get("libelle") or "").strip()
                type_vote = (s.get("typeVote") or {}).get("libelleTypeVote")
                if not (legislature and numero and date and uid_officiel):
                    sys.exit(f"Format inattendu dans {zip_path.name}/{entree} — import interrompu "
                             "(le parseur échoue bruyamment plutôt que de deviner).")
                # VTANR… = séance de l'Assemblée ; VTCGR… = Congrès de Versailles.
                if uid_officiel.startswith("VTANR"):
                    chambre = "an"
                elif uid_officiel.startswith("VTCGR"):
                    chambre = "congres"
                else:
                    sys.exit(f"Préfixe d'uid inconnu « {uid_officiel} » dans {entree} — import interrompu.")
                cur.execute(
                    "INSERT INTO scrutins (chambre, legislature, numero, uid_officiel, objet, type_vote, date, source_id) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (chambre, legislature, numero, uid_officiel, objet, type_vote, date, src))
                sid = cur.lastrowid
                n_scrutins += 1

                exprimes, n_listes = positions_du_scrutin(s, uids)
                # Détecteur de changement de format : si le scrutin annonce des
                # suffrages exprimés mais que l'extraction nominative ne liste
                # personne, la structure n'est pas celle attendue → arrêt.
                annonce = (s.get("syntheseVote") or {}).get("suffragesExprimes")
                if annonce and int(annonce) > 0 and n_listes == 0:
                    sys.exit(f"Structure de ventilation non reconnue dans {entree} "
                             f"({annonce} suffrages annoncés, 0 votant extrait) — import interrompu.")
                # Écart annoncé/listé (mises au point publiées par l'AN) : les
                # positions explicites restent fiables, mais l'inférence
                # d'absence est désactivée pour ce scrutin — mieux vaut un
                # état « à importer » qu'une absence potentiellement fausse.
                ecart = annonce is not None and n_listes != int(annonce)
                if ecart:
                    ecarts.append((uid_officiel, date, int(annonce), n_listes))
                # Motion de censure : seuls les votes POUR sont enregistrés ;
                # ne pas voter est la manière de ne pas soutenir la censure.
                # Aucune absence ne peut donc en être déduite.
                est_censure = "motion de censure" in objet.lower()
                for uid, position in exprimes.items():
                    pid = suivis[uid]
                    cur.execute("INSERT INTO positions_vote (personne_id, scrutin_id, position) "
                                "VALUES (?,?,?)", (pid, sid, position))
                    cur.execute("INSERT INTO presence (personne_id, type, date, statut, source_id) "
                                "VALUES (?, 'scrutin', ?, 'present', ?)", (pid, date, src))
                    n_positions += 1
                if not ecart and not est_censure:
                    for uid, pid in suivis.items():
                        if uid not in exprimes and concerne(pid, date, chambre):
                            cur.execute("INSERT INTO positions_vote (personne_id, scrutin_id, position) "
                                        "VALUES (?,?, 'absent')", (pid, sid))
                            cur.execute("INSERT INTO presence (personne_id, type, date, statut, source_id) "
                                        "VALUES (?, 'scrutin', ?, 'absent', ?)", (pid, date, src))
                            n_absents += 1

        cur.execute("INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
                    (src, "ingestion/assemblee/parse_scrutins.py", n_scrutins + n_positions + n_absents,
                     datetime.now().isoformat(timespec="seconds")))
        con.commit()
        print(f"{zip_path.name} : {n_scrutins} scrutins, {n_positions} positions exprimées, "
              f"{n_absents} absences inférées.")
        total_scrutins += n_scrutins
        total_positions += n_positions
        total_absents += n_absents

    print(f"TOTAL : {total_scrutins} scrutins, {total_positions} positions, {total_absents} absences.")
    if ecarts:
        print(f"[ATTENTION] {len(ecarts)} scrutins avec écart entre suffrages annoncés et listés "
              "(mises au point ou données source incohérentes) — à examiner :")
        for uid_off, date, annonce, listes in ecarts[:10]:
            print(f"   {uid_off} ({date}) : annoncés={annonce}, listés={listes}")
        if len(ecarts) > 10:
            print(f"   … et {len(ecarts) - 10} autres.")
    con.close()


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    dossier = Path(sys.argv[2]) if len(sys.argv) > 2 else DUMPS_DEFAUT
    importer(base, dossier)

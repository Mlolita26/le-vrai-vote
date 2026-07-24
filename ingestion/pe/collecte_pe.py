"""Collecte les votes par appel nominal du Parlement européen depuis le portail
OFFICIEL data.europarl.europa.eu (API v2) et importe les positions des personnes
suivies disposant d'un identifiant `pe_mep_id`.

PÉRIMÈTRE (vérifié le 24/07/2026, voir notes_projet/SOURCES_SENAT_ET_PE.md) :
  L'API n'expose le détail NOMINATIF (liste des députés par pour/contre/abstention,
  identifiés par `person/<id>`) qu'à partir de la 9e législature (juillet 2019).
  Pour 2004-2019 (mandats de Le Pen, Mélenchon, Philippot), l'endpoint /decisions
  renvoie 404/204 et les annexes XML doceo sont derrière un pare-feu WAF : la
  collecte automatisée officielle est IMPOSSIBLE. Ces mandats restent donc à
  l'état « scrutins du Parlement européen à importer ». Rien n'est inventé.

Source par séance :
  GET /meetings?year=YYYY                       -> liste des séances plénières
  GET /meetings/MTG-PL-YYYY-MM-DD/decisions     -> décisions ; les votes par appel
      nominal ont decision_method ...ROLLCALL et des listes had_voter_favor /
      had_voter_against / had_voter_abstention contenant « person/<id> ».

Chaque réponse JSON de séance est archivée horodatée avant transformation.

Positions : person/<id> présent dans favor->pour, against->contre,
abstention->abstention. Les listes had_voter_intended_* (votes « d'intention »,
non enregistrés) ne sont PAS comptées comme position exprimée.
Absence : inférée « absent » si la personne avait un mandat d'eurodéputé actif à
la date du scrutin ET n'apparaît dans aucune des trois listes exprimées — au PE,
seuls les votants d'un appel nominal sont listés (comme pour l'AN, l'absence n'est
jamais listée explicitement). C'est aussi la définition de présence de HowTheyVote,
d'où la validation de repli (présence de Bardella ≈ 89,8 %).

Usage : python ingestion/pe/collecte_pe.py [chemin_base] [annee_debut] [annee_fin]
Par défaut : 2019 à 2026 (période couverte par le nominatif de l'API).
"""
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
DUMPS = RACINE / "data" / "dumps" / "pe"
API = "https://data.europarl.europa.eu/api/v2"
ENTETES = {"User-Agent": "LeVraiVoteBot/1.0 (+https://github.com/Mlolita26/le-vrai-vote)",
           "Accept": "application/ld+json"}
SOURCE_URL = "https://data.europarl.europa.eu"
# Fenêtre couverte par le nominatif dans l'API (borne basse vérifiée : terme 9).
ANNEE_MIN_NOMINATIF = 2019


def get(url, tries=5):
    for essai in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), timeout=60) as r:
                if r.status == 204:
                    return None
                return r.read()
        except urllib.error.HTTPError as err:
            if err.code in (404, 204):
                return None
            if essai < tries - 1:
                time.sleep(5 * (essai + 1))
            else:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if essai < tries - 1:
                time.sleep(5 * (essai + 1))
            else:
                raise
    return None


def seances_de_annee(annee):
    """Identifiants MTG-PL-YYYY-MM-DD des séances plénières d'une année."""
    raw = get(f"{API}/meetings?year={annee}&format=application/ld%2Bjson&limit=400")
    if not raw:
        return []
    data = json.loads(raw).get("data", [])
    ids = []
    for m in data:
        aid = m.get("activity_id") or ""
        if aid.startswith("MTG-PL-"):
            ids.append(aid)
    return sorted(set(ids))


def liste(v):
    if not v:
        return []
    return v if isinstance(v, list) else [v]


def objet_de(dec):
    lab = dec.get("activity_label")
    if isinstance(lab, dict):
        return (lab.get("fr") or lab.get("en") or lab.get("mul") or "").strip()
    if isinstance(lab, str):
        return lab.strip()
    return ""


def decisions_nominatives(raw):
    """Rend les décisions de type appel nominal, avec leurs listes de votants."""
    data = json.loads(raw).get("data", [])
    out = []
    for d in data:
        methode = d.get("decision_method", "") or ""
        favor = liste(d.get("had_voter_favor"))
        against = liste(d.get("had_voter_against"))
        abst = liste(d.get("had_voter_abstention"))
        if not methode.endswith("ROLLCALL") and not (favor or against or abst):
            continue
        out.append(d)
    return out


def ids_votants(dec, cle):
    return {x.replace("person/", "") for x in liste(dec.get(cle)) if isinstance(x, str)}


def collecte(base, an_debut, an_fin):
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # Personnes suivies disposant d'un identifiant PE.
    suivis = dict(cur.execute(
        "SELECT identifiant, personne_id FROM identifiants_externes "
        "WHERE systeme = 'pe_mep_id'").fetchall())
    if not suivis:
        sys.exit("Aucun pe_mep_id dans identifiants_externes — rien à collecter.")
    # Mandats d'eurodéputé (pour l'inférence d'absence).
    mandats = {}
    for pid, debut, fin in cur.execute(
            "SELECT personne_id, debut, fin FROM mandats WHERE type='eurodepute'").fetchall():
        mandats.setdefault(pid, []).append((debut, fin or "9999-12-31"))

    def concerne(pid, date):
        return any(d <= date <= f for d, f in mandats.get(pid, []))

    # Réimport idempotent : on efface l'existant 'pe'.
    cur.execute("DELETE FROM positions_vote WHERE scrutin_id IN "
                "(SELECT id FROM scrutins WHERE chambre='pe')")
    cur.execute("DELETE FROM presence WHERE source_id IN "
                "(SELECT id FROM sources WHERE url=? AND type='scrutin_officiel')", (SOURCE_URL,))
    cur.execute("DELETE FROM scrutins WHERE chambre='pe'")
    con.commit()

    horodatage = datetime.now().strftime("%Y-%m-%d")
    dossier = DUMPS / horodatage
    dossier.mkdir(parents=True, exist_ok=True)

    cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                (SOURCE_URL, "scrutin_officiel", horodatage,
                 f"Votes par appel nominal du Parlement européen, API v2 officielle "
                 f"(endpoint /meetings/.../decisions), législatures {an_debut}-{an_fin}, "
                 f"archivés dans {dossier}. Détail nominatif disponible à partir de 2019."))
    src = cur.lastrowid

    n_scrutins = n_positions = n_absents = 0
    for annee in range(max(an_debut, ANNEE_MIN_NOMINATIF), an_fin + 1):
        seances = seances_de_annee(annee)
        print(f"{annee} : {len(seances)} séances plénières", flush=True)
        for sid_officiel in seances:
            fichier = dossier / f"{sid_officiel}.json"
            if fichier.exists():
                raw = fichier.read_bytes()
            else:
                raw = get(f"{API}/meetings/{sid_officiel}/decisions?format=application/ld%2Bjson")
                if not raw:
                    continue
                fichier.write_bytes(raw)
                time.sleep(0.3)
            for dec in decisions_nominatives(raw):
                date = dec.get("activity_date")
                uid = dec.get("activity_id")
                objet = objet_de(dec)
                if not (date and uid and objet):
                    continue  # sans identité fiable, on n'insère pas (pas de supposition)
                numero = dec.get("notation_votingId") or uid.split("-")[-1]
                cur.execute(
                    "INSERT OR IGNORE INTO scrutins (chambre, legislature, numero, uid_officiel, objet, "
                    "type_vote, date, sort, total_pour, total_contre, total_abstention, source_id) "
                    "VALUES ('pe', NULL, ?, ?, ?, 'appel nominal', ?, NULL, ?, ?, ?, ?)",
                    (str(numero), uid, objet, date,
                     dec.get("number_of_votes_favor"), dec.get("number_of_votes_against"),
                     dec.get("number_of_votes_abstention"), src))
                row = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
                sid = row[0]
                n_scrutins += 1

                pour = ids_votants(dec, "had_voter_favor")
                contre = ids_votants(dec, "had_voter_against")
                abst = ids_votants(dec, "had_voter_abstention")
                for mep_id, pid in suivis.items():
                    if mep_id in pour:
                        position = "pour"
                    elif mep_id in contre:
                        position = "contre"
                    elif mep_id in abst:
                        position = "abstention"
                    elif concerne(pid, date):
                        position = "absent"          # mandat actif, non listé = n'a pas pris part
                    else:
                        continue                     # pas eurodéputé à cette date : rien
                    cur.execute("INSERT OR IGNORE INTO positions_vote (personne_id, scrutin_id, position) "
                                "VALUES (?,?,?)", (pid, sid, position))
                    statut = "absent" if position == "absent" else "present"
                    cur.execute("INSERT INTO presence (personne_id, type, date, statut, source_id) "
                                "VALUES (?, 'scrutin', ?, ?, ?)", (pid, date, statut, src))
                    if position == "absent":
                        n_absents += 1
                    else:
                        n_positions += 1
            con.commit()

    cur.execute("INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
                (src, "ingestion/pe/collecte_pe.py", n_scrutins + n_positions + n_absents,
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()
    print(f"\nImporté : {n_scrutins} scrutins PE (appels nominaux), "
          f"{n_positions} positions exprimées, {n_absents} absences inférées, "
          f"pour {len(suivis)} député(s) suivi(s).")
    con.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    an_debut = int(sys.argv[2]) if len(sys.argv) > 2 else 2019
    an_fin = int(sys.argv[3]) if len(sys.argv) > 3 else 2026
    collecte(base, an_debut, an_fin)

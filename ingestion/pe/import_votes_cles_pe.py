"""Importe les DONNÉES BRUTES des votes clés du Parlement européen, à partir de
l'export HowTheyVote déjà présent dans le coffre (licence ODbL). Cible une liste
restreinte de scrutins retenus éditorialement (décision : ne collecter que les
votes clés, pas les 24 000 scrutins).

Pour chaque vote clé PE, ce script remplit :
  - `scrutins`  : chambre='pe', legislature='pe9'/'pe10' (dérivée de la date ;
     terme 10 à partir du 16/07/2024), uid_officiel='PE-HTV-<vote_id>' ;
  - `positions_vote` : position PERSONNELLE des personnes suivies disposant d'un
     `pe_mep_id` (aujourd'hui Bardella ; Massard après seed_pe_ids) ;
  - `positions_groupes` : décompte de la DÉLÉGATION FRANÇAISE de chaque parti
     (RN = élus français des groupes ID puis PfE ; LFI = élus français du groupe
     The Left/GUE-NGL) — c'est la mention « son parti a voté Y ».

La légende « son parti » n'est PAS un vote personnel : le rattachement candidat →
délégation est éditorial (seed_groupes_reference.py) et l'UI affiche « n'y siégeait
pas » quand le candidat n'a pas de vote personnel.

Rien n'est inventé : chaque scrutin pointe sa page officielle via howtheyvote.eu
(qui référence le scrutin du PE). Réimport idempotent (efface d'abord le 'pe').

Usage : python ingestion/pe/import_votes_cles_pe.py [chemin_base] [chemin_coffre]
"""
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
COFFRE_DEFAUT = Path(r"C:\Users\mlolita\OneDrive - CGIAR\Documents\presidentielles")
SOURCE_URL = "https://howtheyvote.eu"
DEBUT_TERME_10 = "2024-07-16"  # première séance de la 10e législature

# Sélection éditoriale (clé lisible -> vote_id HowTheyVote). Les titres/résumés
# neutres et la thématique vivent dans seed_votes_cles.py (couche éditoriale).
VOTES_CLES_PE = {
    "salaire_minimum": 147342,
    "co2_voitures_2035": 152544,
    "restauration_nature": 164499,
    "media_freedom_act": 166183,
    "violences_femmes": 168573,
    "pacte_migration": 167531,
    "facilite_ukraine": 164536,
    "soutien_ukraine": 169362,
    # Extension « votes clivants » (positions différentes entre délégations).
    "marche_carbone": 154173,
    "transparence_salariale": 154076,
    "marche_electricite": 167334,
    # Corrigés le 30/07/2026 après audit : l'ancien id 155918 pointait sur la
    # directive « représentants légaux » et non sur le règlement de fond, et
    # l'ancien id 150367 était un amendement sur la Libye, sans rapport avec les
    # logiciels espions (la recommandation PEGA de juin 2023 n'a pas fait l'objet
    # d'un vote nominatif ; on retient la résolution de suivi de novembre 2023).
    "preuves_electroniques": 155928,
    "logiciels_espions": 161873,
    "armes_a_feu": 168301,
    "eurodac": 166929,
    "filtrage_frontieres": 166904,
    "convention_istanbul": 155091,
    "avortement_charte": 168054,
    "egalite_lgbtiq": 164215,
    "elargissement_ue": 186518,
    "etat_droit_hongrie": 168862,
    "reglement_ia": 166051,
    # Urgence climatique et événements extrêmes.
    "urgence_climatique": 110615,
    "loi_climat": 118521,
    "adaptation_climat": 126261,
    "protection_civile": 117083,
    "neutralite_2040": 184178,
    # Fiscalité et travail (thèmes Taxe/impôts et Travail, ajout 25/07/2026).
    "impot_minimum_mondial": 143328,
    "vetos_accord_fiscal": 147044,
    "stages_qualite": 155946,
    "quotas_co2_aviation": 144789,
    # Défense européenne et Proche-Orient (ajout 26/07/2026).
    "gaza_famine_2etats": 179048,
    "livre_blanc_defense_ue": 172867,
    "psdc_rapport_2024": 174053,
    "edip_industrie_defense": 181587,
}

# « Voix 2 » = la DÉLÉGATION FRANÇAISE du groupe européen où siège le parti du
# candidat (entité factuelle : les élus français de ce groupe le jour du vote).
# On l'étiquette par le groupe + le(s) parti(s) français concerné(s) — on ne
# prétend jamais isoler un « vote de parti » quand la délégation en mêle plusieurs.
PARTIS_PE = {
    "RN": {"groupes": ["ID", "PFE"],
           "libelle": "Délégation française du groupe Identité et démocratie puis Patriotes pour l'Europe (Rassemblement national)"},
    "LFI": {"groupes": ["GUE_NGL"],
            "libelle": "Délégation française du groupe The Left/GUE-NGL (La France insoumise et apparentés)"},
    "PS": {"groupes": ["SD"],
           "libelle": "Délégation française du groupe S&D (Parti socialiste, Place publique)"},
    "LR": {"groupes": ["EPP"],
           "libelle": "Délégation française du groupe PPE (Les Républicains)"},
    "RE": {"groupes": ["RENEW"],
           "libelle": "Délégation française du groupe Renew Europe (Renaissance, MoDem, Horizons)"},
    "VERT": {"groupes": ["GREEN_EFA"],
             "libelle": "Délégation française du groupe Verts/ALE (Les Écologistes)"},
}

POS = {"FOR": "pour", "AGAINST": "contre", "ABSTENTION": "abstention"}


def legislature(date_iso):
    return "pe10" if date_iso >= DEBUT_TERME_10 else "pe9"


def sort_officiel(result):
    return {"ADOPTED": "adopté", "REJECTED": "rejeté"}.get((result or "").upper())


def entier(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def importer(base: Path, coffre: Path) -> None:
    hv = coffre / "donnees_brutes" / "Howtheyvote" / "export"
    ids = set(VOTES_CLES_PE.values())

    # Métadonnées des scrutins retenus (votes.csv).
    meta = {}
    with open(hv / "votes.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vid = entier(r["id"])
            if vid in ids:
                meta[vid] = r
    manquants = ids - set(meta)
    if manquants:
        sys.exit(f"vote_id introuvables dans votes.csv : {sorted(manquants)} — abandon.")

    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    suivis = dict(cur.execute(
        "SELECT identifiant, personne_id FROM identifiants_externes WHERE systeme='pe_mep_id'").fetchall())
    mandats = {}
    for pid, debut, fin in cur.execute(
            "SELECT personne_id, debut, fin FROM mandats WHERE type='eurodepute'").fetchall():
        mandats.setdefault(pid, []).append((debut, fin or "9999-12-31"))

    def concerne(pid, date):
        return any(d <= date <= f for d, f in mandats.get(pid, []))

    # Réimport idempotent : on rafraîchit positions et décomptes, mais on NE
    # supprime PAS les scrutins 'pe' (ils peuvent être référencés par votes_cles
    # → FK). Les scrutins sont ré-insérés en INSERT OR IGNORE plus bas.
    cur.execute("DELETE FROM positions_vote WHERE scrutin_id IN "
                "(SELECT id FROM scrutins WHERE chambre='pe')")
    cur.execute("DELETE FROM positions_groupes WHERE scrutin_id IN "
                "(SELECT id FROM scrutins WHERE chambre='pe')")
    cur.execute("DELETE FROM presence WHERE source_id IN "
                "(SELECT id FROM sources WHERE url=? AND type='scrutin_officiel')", (SOURCE_URL,))
    con.commit()

    horodatage = datetime.now().strftime("%Y-%m-%d")
    cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                (SOURCE_URL, "scrutin_officiel", horodatage,
                 "Votes par appel nominal du Parlement européen, votes clés sélectionnés, "
                 "agrégés depuis l'export HowTheyVote (ODbL) du coffre ; chaque scrutin renvoie "
                 "à sa page officielle howtheyvote.eu/votes/<id>."))
    src = cur.lastrowid

    # Scrutins PE.
    sid_par_vote = {}
    for vid, r in meta.items():
        date = r["timestamp"][:10]
        uid = f"PE-HTV-{vid}"
        cur.execute(
            "INSERT OR IGNORE INTO scrutins (chambre, legislature, numero, uid_officiel, objet, type_vote, "
            "date, sort, total_pour, total_contre, total_abstention, source_id) "
            "VALUES ('pe', ?, ?, ?, ?, 'appel nominal', ?, ?, ?, ?, ?, ?)",
            (legislature(date), str(vid), uid, (r.get("display_title") or "").strip(), date,
             sort_officiel(r.get("result")), entier(r.get("count_for")),
             entier(r.get("count_against")), entier(r.get("count_abstention")), src))
        sid_par_vote[vid] = cur.execute(
            "SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()[0]

    # Un seul balayage de member_votes.csv (513 Mo) filtré sur les votes retenus.
    perso = {}                       # (mep_id, vid) -> position
    tallies = {}                     # (vid, parti) -> {pour,contre,abstention,non_votant}
    groupe_vers_parti = {g: p for p, cfg in PARTIS_PE.items() for g in cfg["groupes"]}
    with open(hv / "member_votes.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vid = entier(r["vote_id"])
            if vid not in ids:
                continue
            pos = r["position"]
            mep = r["member_id"]
            if mep in suivis:
                perso[(mep, vid)] = pos
            if r["country_code"] == "FRA":
                parti = groupe_vers_parti.get(r["group_code"])
                if parti:
                    d = tallies.setdefault((vid, parti),
                                           {"pour": 0, "contre": 0, "abstention": 0, "non_votant": 0})
                    if pos == "DID_NOT_VOTE":
                        d["non_votant"] += 1
                    else:
                        d[POS[pos]] += 1

    # positions_vote + presence (personnes suivies).
    n_perso = n_abs = 0
    for mep, pid in suivis.items():
        for vid in ids:
            date = meta[vid]["timestamp"][:10]
            pos = perso.get((mep, vid))
            if pos in POS:
                position = POS[pos]
            elif pos == "DID_NOT_VOTE" or (pos is None and concerne(pid, date)):
                position = "absent"
            else:
                continue  # pas eurodéputé à cette date : rien
            cur.execute("INSERT OR IGNORE INTO positions_vote (personne_id, scrutin_id, position) "
                        "VALUES (?,?,?)", (pid, sid_par_vote[vid], position))
            cur.execute("INSERT INTO presence (personne_id, type, date, statut, source_id) "
                        "VALUES (?, 'scrutin', ?, ?, ?)",
                        (pid, date, "absent" if position == "absent" else "present", src))
            n_abs += position == "absent"
            n_perso += position != "absent"

    # positions_groupes (délégations RN / LFI).
    n_grp = 0
    for (vid, parti), d in tallies.items():
        cur.execute(
            "INSERT INTO positions_groupes (scrutin_id, organe_ref, groupe_abrege, groupe_libelle, "
            "pour, contre, abstention, non_votant, source_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (sid_par_vote[vid], f"PE-{parti}", parti, PARTIS_PE[parti]["libelle"],
             d["pour"], d["contre"], d["abstention"], d["non_votant"], src))
        n_grp += 1

    cur.execute("INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
                (src, "ingestion/pe/import_votes_cles_pe.py", len(meta) + n_perso + n_abs + n_grp,
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()
    print(f"Importé : {len(meta)} scrutins PE (votes clés), {n_perso} positions personnelles "
          f"+ {n_abs} absences ({len(suivis)} suivi(s)), {n_grp} décomptes de délégation.")
    con.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    coffre = Path(sys.argv[2]) if len(sys.argv) > 2 else COFFRE_DEFAUT
    importer(base, coffre)

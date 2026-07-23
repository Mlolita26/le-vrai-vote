"""Importe les acteurs et mandats parlementaires depuis un dump AMO de
l'open data de l'Assemblée nationale (AMO20 « en exercice » ou AMO30 « historique »).

Ce que fait le script, pour les personnes suivies uniquement :
  - apparie chaque personne par nom + prénom (+ contrôle de la date de naissance
    quand la base la connaît déjà — refus en cas de divergence) ;
  - enregistre l'UID officiel (PAxxxx) dans identifiants_externes ;
  - complète la naissance si elle manquait (source = dump AMO) ;
  - importe les mandats ASSEMBLEE (→ depute) et SENAT (→ senateur), datés au jour.

Règle de préséance : pour ces types parlementaires, l'open data AN est le
miroir officiel. Tout mandat de même type provenant d'une DIA HATVP et
chevauchant la période importée est remplacé (la DIA reste source pour ce
que l'AN ne couvre pas : fonctions gouvernementales, mandats locaux).

Les mandats GOUVERNEMENT du dump ne sont PAS importés à ce stade : le fichier
ne distingue pas la fonction exercée (libQualite = « membre »), la DIA reste
la source la plus précise pour ces fonctions. À revoir avec le référentiel
des organes (jalon ultérieur).

Usage : python ingestion/assemblee/parse_amo.py [chemin_base] [chemin_zip_amo]
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
AMO_DEFAUT = (COFFRE / "donnees_brutes" / "Assemblee_Nationale" / "dump_manuel_2026-07-23"
              / "AMO20_dep_sen_min_tous_mandats_et_organes.json.zip")
COLLECTE_MANUELLE = "2026-07-23"  # date du téléchargement manuel sur data.assemblee-nationale.fr

# Personnes suivies : slug -> (nom AMO en majuscules accentuées, prénom)
SUIVIS = {
    "gabriel-attal": ("ATTAL", "Gabriel"),
    "jean-luc-melenchon": ("MÉLENCHON", "Jean-Luc"),
    "edouard-philippe": ("PHILIPPE", "Édouard"),
    "bruno-retailleau": ("RETAILLEAU", "Bruno"),
}
TYPE_ORGANE_VERS_MANDAT = {"ASSEMBLEE": "depute", "SENAT": "senateur"}


def texte(v):
    """Les champs AMO sont parfois {'#text': ...} ou {'@xsi:nil': 'true'}."""
    if isinstance(v, dict):
        return v.get("#text")
    return v


def liste(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def importer(base: Path, zip_amo: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    sha = hashlib.sha256(zip_amo.read_bytes()).hexdigest()
    cur.execute(
        "INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
        ("https://data.assemblee-nationale.fr", "dataset", COLLECTE_MANUELLE,
         f"Dump acteurs/mandats/organes (rubrique Acteurs) — fichier {zip_amo.name}, "
         f"téléchargé manuellement le {COLLECTE_MANUELLE}, archivé : {zip_amo}, sha256={sha}"))
    src_amo = cur.lastrowid

    personnes = {slug: pid for pid, slug in
                 cur.execute("SELECT id, slug FROM personnes").fetchall()}
    naissances = dict(cur.execute("SELECT slug, naissance FROM personnes").fetchall())

    apparies, mandats_inseres, remplaces = {}, 0, 0
    with zipfile.ZipFile(zip_amo) as z:
        fichiers_acteurs = [e for e in z.namelist() if "/acteur/" in e and e.endswith(".json")]
        for entree in fichiers_acteurs:
            with z.open(entree) as f:
                acteur = json.load(f).get("acteur", {})
            ident = acteur.get("etatCivil", {}).get("ident", {})
            nom, prenom = (ident.get("nom") or "").upper(), ident.get("prenom") or ""
            correspondance = [s for s, (n, p) in SUIVIS.items() if n == nom and p == prenom]
            if not correspondance:
                continue
            slug = correspondance[0]
            uid = texte(acteur.get("uid"))
            naiss_amo = texte(acteur.get("etatCivil", {}).get("infoNaissance", {}).get("dateNais"))

            # Contrôle d'identité : si la base connaît la naissance, elle doit coïncider.
            naiss_db = naissances.get(slug)
            if naiss_db and naiss_amo and naiss_db != naiss_amo:
                sys.exit(f"Divergence de naissance pour {slug} : base={naiss_db}, AMO={naiss_amo} "
                         f"(uid {uid}) — appariement refusé, vérifier les homonymes.")
            pid = personnes[slug]
            apparies[slug] = uid

            cur.execute("INSERT OR IGNORE INTO identifiants_externes "
                        "(personne_id, systeme, identifiant, source_id) VALUES (?, 'an_uid', ?, ?)",
                        (pid, uid, src_amo))
            if not naiss_db and naiss_amo:
                cur.execute("UPDATE personnes SET naissance = ?, naissance_source_id = ? WHERE id = ?",
                            (naiss_amo, src_amo, pid))
                print(f"  naissance complétée pour {slug} : {naiss_amo} (source AMO)")

            for m in liste(acteur.get("mandats", {}).get("mandat")):
                type_mandat = TYPE_ORGANE_VERS_MANDAT.get(m.get("typeOrgane"))
                if not type_mandat:
                    continue
                debut, fin = texte(m.get("dateDebut")), texte(m.get("dateFin"))
                if not debut:
                    continue
                legislature = texte(m.get("legislature"))
                # Préséance : retirer les mandats DIA de même type chevauchant la période.
                chevauches = cur.execute(
                    "SELECT m.id FROM mandats m JOIN sources s ON s.id = m.source_id "
                    "WHERE m.personne_id = ? AND m.type = ? AND s.type = 'declaration_hatvp' "
                    "AND m.debut <= COALESCE(?, '9999-12-31') AND COALESCE(m.fin, '9999-12-31') >= ?",
                    (pid, type_mandat, fin, debut)).fetchall()
                for (mid,) in chevauches:
                    cur.execute("DELETE FROM mandats WHERE id = ?", (mid,))
                    remplaces += 1
                deja = cur.execute(
                    "SELECT COUNT(*) FROM mandats WHERE personne_id = ? AND type = ? "
                    "AND debut = ? AND source_id = ?", (pid, type_mandat, debut, src_amo)).fetchone()[0]
                if deja:
                    continue
                detail = (f"Open data AN (AMO), qualité « {m.get('infosQualite', {}).get('libQualite')} »"
                          + (f", législature {legislature}" if legislature else ""))
                cur.execute("INSERT INTO mandats (personne_id, type, debut, fin, detail, precision, source_id) "
                            "VALUES (?,?,?,?,?, 'jour', ?)",
                            (pid, type_mandat, debut, fin, detail, src_amo))
                mandats_inseres += 1

    cur.execute("INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
                (src_amo, "ingestion/assemblee/parse_amo.py", mandats_inseres,
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()

    print(f"Appariés dans {zip_amo.name} : {apparies or 'aucun'}")
    absents = [s for s in SUIVIS if s not in apparies]
    if absents:
        print(f"Non trouvés dans ce dump (normal pour AMO20 si plus en exercice) : {absents}")
    print(f"{mandats_inseres} mandats parlementaires importés (précision jour), "
          f"{remplaces} mandats DIA chevauchants remplacés.")
    con.close()


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    zip_amo = Path(sys.argv[2]) if len(sys.argv) > 2 else AMO_DEFAUT
    importer(base, zip_amo)

"""Exporte les données publiables du site vers web/data.json.

Tout ce qui est exporté provient de la base (elle-même alimentée par des
imports sourcés) : aucune valeur n'est saisie ici. Les personnes sans donnée
gardent leurs états explicites (« à importer », « non concerné »…).

Usage : python ingestion/export_json.py [chemin_base]
"""
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
SORTIE = RACINE / "web" / "data.json"

LIBELLES_MANDAT = {
    "depute": "Député", "senateur": "Sénateur", "eurodepute": "Eurodéputé",
    "ministre": "Ministre", "premier_ministre": "Premier ministre",
    "secretaire_etat": "Secrétaire d'État", "maire": "Maire",
    "conseiller_municipal": "Conseiller municipal",
    "conseiller_regional": "Conseiller régional", "autre": "Autre mandat",
}
# Personnes dont les données parlementaires sont déjà en base
SUIVIS = ["gabriel-attal", "marine-le-pen", "jean-luc-melenchon",
          "edouard-philippe", "bruno-retailleau"]


def exporter(base: Path) -> None:
    con = sqlite3.connect(base)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    candidats = []
    for c in cur.execute(
            "SELECT p.slug, p.prenom, p.nom, c.statut, c.date, c.detail, s.url AS source_url "
            "FROM candidatures c JOIN personnes p ON p.id = c.personne_id "
            "JOIN sources s ON s.id = c.source_id "
            "ORDER BY c.statut, p.nom"):
        candidats.append({
            "slug": c["slug"], "nom": f"{c['prenom']} {c['nom']}",
            "statut": c["statut"], "date_declaration": c["date"],
            "detail": c["detail"], "source": c["source_url"],
            "donnees_disponibles": c["slug"] in SUIVIS,
        })

    profils = {}
    for slug in SUIVIS:
        p = cur.execute("SELECT id, prenom, nom, naissance FROM personnes WHERE slug=?",
                        (slug,)).fetchone()
        mandats = [{
            "libelle": LIBELLES_MANDAT.get(m["type"], m["type"]),
            "debut": m["debut"], "fin": m["fin"], "precision": m["precision"],
            "detail": m["detail"],
        } for m in cur.execute(
            "SELECT type, debut, fin, precision, detail FROM mandats "
            "WHERE personne_id=? ORDER BY debut", (p["id"],))]

        par_position = dict(cur.execute(
            "SELECT position, COUNT(*) FROM positions_vote WHERE personne_id=? GROUP BY position",
            (p["id"],)).fetchall())

        solennels = cur.execute(
            "SELECT SUM(CASE WHEN pv.position != 'absent' THEN 1 ELSE 0 END) AS present, COUNT(*) AS total "
            "FROM positions_vote pv JOIN scrutins s ON s.id = pv.scrutin_id "
            "WHERE pv.personne_id=? AND s.legislature='17' AND s.type_vote LIKE '%solennel%'",
            (p["id"],)).fetchone()

        profils[slug] = {
            "nom": f"{p['prenom']} {p['nom']}",
            "naissance": p["naissance"],
            "mandats": mandats,
            "positions": {
                "exprimees": sum(v for k, v in par_position.items()
                                 if k in ("pour", "contre", "abstention")),
                "non_votant": par_position.get("non_votant", 0),
                "absences_inferees": par_position.get("absent", 0),
                "detail": par_position,
            },
            "solennels_l17": ({"present": solennels["present"], "total": solennels["total"]}
                              if solennels["total"] else None),
        }

    n_scrutins = cur.execute("SELECT COUNT(*) FROM scrutins").fetchone()[0]
    donnees = {
        "meta": {
            "genere_le": date.today().isoformat(),
            "scrutins_en_base": n_scrutins,
            "perimetre_scrutins": "Assemblée nationale et Congrès, législatures 15 à 17 "
                                  "(juillet 2017 → juillet 2026). Sénat et Parlement européen : à importer.",
            "candidats_maj": "2026-07-23",
            "avertissement": "Version de travail. Les déclarations de candidature sont des déclarations "
                             "publiques recensées par la presse : la liste officielle des candidats ne sera "
                             "établie par le Conseil constitutionnel qu'après validation des parrainages, en mars 2027.",
        },
        "candidats": candidats,
        "profils": profils,
        "note_bardella": "Jordan Bardella n'est pas candidat : Marine Le Pen, déclarée le 7 juillet 2026 "
                         "après l'arrêt d'appel, porte la candidature du Rassemblement national.",
    }
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Exporté : {SORTIE} ({len(candidats)} candidats, {len(profils)} profils détaillés)")
    con.close()


if __name__ == "__main__":
    exporter(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

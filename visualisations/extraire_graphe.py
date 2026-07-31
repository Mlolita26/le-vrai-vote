"""Extrait de la base un graphe multi-couches : candidats, votes clés,
thématiques, institutions, groupes parlementaires et sources.

Chaque arête correspond à une relation réellement enregistrée en base — aucune
n'est déduite ni estimée. Le fichier produit (JSON) sert d'entrée au rendu.

Usage : python visualisations/extraire_graphe.py [chemin_base] [sortie.json]
"""
import json
import re
import sqlite3
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
SORTIE_DEFAUT = Path(__file__).resolve().parent / "graphe.json"

# Positions comptées comme un vote exprimé (l'absence n'est pas une position).
EXPRIMEES = ("pour", "contre", "abstention")

# Seuil de comparabilité pour un lien candidat–candidat : en dessous, le taux
# d'accord n'est pas statistiquement lisible et le lien n'est pas tracé.
MIN_SCRUTINS_PARTAGES = 100

CHAMBRES = {
    "an": "Assemblée nationale",
    "senat": "Sénat",
    "pe": "Parlement européen",
    "congres": "Congrès",
}

# Un domaine institutionnel n'est pas une source « tierce » : le portail open data
# de l'Assemblée EST l'Assemblée. Le garder séparé créerait un nœud aspirant relié
# à presque tout, qui écraserait la carte sans rien apprendre. Ces domaines sont
# donc rabattus sur le nœud d'institution correspondant.
DOMAINES_INSTITUTIONNELS = {
    "assemblee-nationale.fr": "an",
    "data.assemblee-nationale.fr": "an",
    "groupe-communiste.assemblee-nationale.fr": "an",
    "senat.fr": "senat",
    "data.senat.fr": "senat",
    "europarl.europa.eu": "pe",
    "hatvp.fr": "hatvp",
}

# Institutions ajoutées hors chambres parlementaires.
INSTITUTIONS_HORS_CHAMBRE = {"hatvp": "HATVP"}


def domaine(url):
    m = re.search(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1).lower() if m else None


def famille_source(type_source):
    return "presse" if type_source == "presse" else "autre"


def construire(base: Path) -> dict:
    con = sqlite3.connect(base)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    noeuds = {}
    aretes = []

    def noeud(cle, **attrs):
        if cle not in noeuds:
            noeuds[cle] = {"id": cle, **attrs}
        return cle

    def arete(a, b, relation, poids=1.0):
        aretes.append({"source": a, "cible": b, "relation": relation, "poids": poids})

    # ------------------------------------------------------------- institutions
    for code, libelle in CHAMBRES.items():
        n = cur.execute("SELECT count(*) FROM scrutins WHERE chambre = ?", (code,)).fetchone()[0]
        if n:
            noeud(f"inst:{code}", type="institution", libelle=libelle, nb_scrutins=n)
    for code, libelle in INSTITUTIONS_HORS_CHAMBRE.items():
        noeud(f"inst:{code}", type="institution", libelle=libelle)

    # ------------------------------------------------------------------ sources
    # Une source par domaine : 212 URLs se ramènent à quelques dizaines
    # d'émetteurs, ce qui est l'échelle lisible sur une carte. Les domaines
    # institutionnels sont rabattus sur leur institution (voir la constante).
    src_vers_noeud = {}
    compte_dom = defaultdict(int)
    type_dom = {}
    for r in cur.execute("SELECT id, url, type FROM sources"):
        dom = domaine(r["url"])
        if not dom:
            continue
        code = DOMAINES_INSTITUTIONNELS.get(dom)
        if code:
            src_vers_noeud[r["id"]] = f"inst:{code}"
            continue
        src_vers_noeud[r["id"]] = f"src:{dom}"
        compte_dom[dom] += 1
        # Le premier type rencontré classe le domaine (ils sont homogènes en base).
        type_dom.setdefault(dom, r["type"])

    for dom, n in compte_dom.items():
        noeud(f"src:{dom}", type="source", libelle=dom,
              famille=famille_source(type_dom[dom]), nb_urls=n)

    def source_de(source_id):
        """Nœud représentant une source, ou None si l'URL n'est pas exploitable."""
        cle = src_vers_noeud.get(source_id)
        return cle if cle in noeuds else None

    def source_url(url):
        """Même résolution, à partir d'une URL brute (colonnes de type texte)."""
        dom = domaine(url)
        if not dom:
            return None
        code = DOMAINES_INSTITUTIONNELS.get(dom)
        cle = f"inst:{code}" if code else f"src:{dom}"
        return cle if cle in noeuds else None

    # --------------------------------------------------------------- thématiques
    for r in cur.execute("SELECT id, libelle FROM thematiques ORDER BY ordre"):
        noeud(f"theme:{r['id']}", type="theme", libelle=r["libelle"])

    # ----------------------------------------------------------------- personnes
    personnes = {}
    for r in cur.execute("SELECT id, nom, prenom, slug FROM personnes"):
        personnes[r["id"]] = r
        noeud(f"cand:{r['id']}", type="candidat",
              libelle=f"{r['prenom']} {r['nom']}", slug=r["slug"])

    # ------------------------------------------- groupes parlementaires déclarés
    for r in cur.execute("""SELECT personne_id, groupe_abrege, legislature, source_id
                            FROM groupes_reference"""):
        g = noeud(f"grp:{r['groupe_abrege']}", type="groupe", libelle=r["groupe_abrege"])
        arete(f"cand:{r['personne_id']}", g, "appartenance_groupe")
        s = source_de(r["source_id"])
        if s:
            arete(g, s, "sourcee_par", 0.3)

    # ------------------------------------------------------------------ mandats
    type_vers_inst = {"depute": "an", "senateur": "senat", "eurodepute": "pe"}
    for r in cur.execute("SELECT personne_id, type, source_id FROM mandats"):
        code = type_vers_inst.get(r["type"])
        if code and f"inst:{code}" in noeuds:
            arete(f"cand:{r['personne_id']}", f"inst:{code}", "mandat")
        s = source_de(r["source_id"])
        if s:
            arete(f"cand:{r['personne_id']}", s, "sourcee_par", 0.3)

    # ------------------------ candidatures, programmes, déclarations → sources
    for table in ("candidatures", "programmes", "declarations"):
        for r in cur.execute(f"SELECT personne_id, source_id FROM {table}"):
            s = source_de(r["source_id"])
            if s:
                arete(f"cand:{r['personne_id']}", s, "sourcee_par", 0.5)

    # ---------------------------------------------------------------- votes clés
    votes = {}
    for r in cur.execute("""SELECT vc.id, vc.titre, vc.thematique_id, vc.source_resume,
                                   s.chambre, s.date, s.source_id
                            FROM votes_cles vc JOIN scrutins s ON s.id = vc.scrutin_id"""):
        v = noeud(f"vote:{r['id']}", type="vote", libelle=r["titre"],
                  chambre=r["chambre"], date=r["date"])
        votes[r["id"]] = r
        if r["thematique_id"]:
            arete(v, f"theme:{r['thematique_id']}", "thematique", 1.2)
        arete(v, f"inst:{r['chambre']}", "chambre", 1.0)
        # Source du scrutin lui-même, puis source du résumé éditorial.
        for s in (source_de(r["source_id"]), source_url(r["source_resume"])):
            if s:
                arete(v, s, "sourcee_par", 0.4)

    # ------------------------ position majoritaire des groupes sur les votes clés
    # Décomptes officiels (pour/contre/abstention) publiés scrutin par scrutin.
    # Un groupe sans libellé abrégé n'est pas rattaché : l'inventer serait faux.
    # Un vote clé peut renvoyer à deux scrutins (lecture AN et lecture Sénat).
    vote_par_scrutin = {}
    for r in cur.execute("SELECT id, scrutin_id, scrutin_senat_id FROM votes_cles"):
        for sid in (r["scrutin_id"], r["scrutin_senat_id"]):
            if sid is not None:
                vote_par_scrutin[sid] = r["id"]

    for r in cur.execute("""SELECT scrutin_id, groupe_abrege, groupe_libelle,
                                   pour, contre, abstention, source_id
                            FROM positions_groupes
                            WHERE groupe_abrege IS NOT NULL"""):
        vid = vote_par_scrutin.get(r["scrutin_id"])
        if vid is None:
            continue
        decompte = {"pour": r["pour"] or 0, "contre": r["contre"] or 0,
                    "abstention": r["abstention"] or 0}
        if not any(decompte.values()):
            continue
        majoritaire = max(decompte, key=decompte.get)
        exprimes = sum(decompte.values())
        g = noeud(f"grp:{r['groupe_abrege']}", type="groupe",
                  libelle=r["groupe_abrege"], detail=r["groupe_libelle"])
        # Poids = netteté de la position du groupe (une position unanime tire plus
        # fort qu'une position partagée).
        arete(g, f"vote:{vid}", f"groupe_{majoritaire}",
              round(decompte[majoritaire] / exprimes, 3))

    # ------------------- justifications éditoriales des positions de groupe
    # C'est par là qu'arrive la couche média : chaque justification cite un
    # article de presse, un communiqué de parti ou un compte rendu de séance.
    for r in cur.execute("""SELECT scrutin_id, groupe_abrege, source_id
                            FROM justifications_groupes"""):
        vid = vote_par_scrutin.get(r["scrutin_id"])
        s = source_de(r["source_id"])
        g = f"grp:{r['groupe_abrege']}"
        if g not in noeuds or not s:
            continue
        arete(g, s, "justification", 0.6)
        if vid is not None:
            arete(f"vote:{vid}", s, "sourcee_par", 0.4)

    # ------------------------------------ source du scrutin de seconde chambre
    for r in cur.execute("""SELECT vc.id AS vote_id, s.source_id
                            FROM votes_cles vc JOIN scrutins s ON s.id = vc.scrutin_senat_id"""):
        s = source_de(r["source_id"])
        if s:
            arete(f"vote:{r['vote_id']}", s, "sourcee_par", 0.4)

    # ------------------------------------------- identités externes → sources
    for r in cur.execute("SELECT personne_id, source_id FROM identifiants_externes"):
        s = source_de(r["source_id"])
        if s:
            arete(f"cand:{r['personne_id']}", s, "sourcee_par", 0.3)

    # --------------------------------------------- positions des candidats votées
    positions = cur.execute(f"""
        SELECT vc.id AS vote_id, pv.personne_id, pv.position
        FROM votes_cles vc
        JOIN positions_vote pv ON pv.scrutin_id = vc.scrutin_id
        WHERE pv.position IN {EXPRIMEES}""").fetchall()
    for p in positions:
        arete(f"cand:{p['personne_id']}", f"vote:{p['vote_id']}",
              f"vote_{p['position']}", 1.0)

    # --------------------------- accord de vote entre candidats (tous scrutins)
    # Calculé sur l'ensemble des scrutins où les deux ont exprimé une position :
    # c'est une mesure, pas une opinion.
    par_personne = defaultdict(dict)
    for r in cur.execute(f"""SELECT personne_id, scrutin_id, position FROM positions_vote
                             WHERE position IN {EXPRIMEES}"""):
        par_personne[r["personne_id"]][r["scrutin_id"]] = r["position"]

    accords = []
    for a, b in combinations(sorted(par_personne), 2):
        va, vb = par_personne[a], par_personne[b]
        communs = va.keys() & vb.keys()
        if len(communs) < MIN_SCRUTINS_PARTAGES:
            continue
        identiques = sum(1 for s in communs if va[s] == vb[s])
        taux = identiques / len(communs)
        accords.append({"a": a, "b": b, "partages": len(communs), "taux": taux})
        arete(f"cand:{a}", f"cand:{b}", "accord_vote", taux)

    con.close()

    # Un nœud sans aucune arête ne dit rien sur la carte et fausse le calcul de
    # position. Il est retiré — et listé, pour que l'omission soit explicite.
    relies = {a["source"] for a in aretes} | {a["cible"] for a in aretes}
    exclus = [noeuds[k]["libelle"] for k in noeuds if k not in relies]
    for k in list(noeuds):
        if k not in relies:
            del noeuds[k]

    return {
        "noeuds": list(noeuds.values()),
        "aretes": aretes,
        "accords": accords,
        "meta": {
            "base": str(base),
            "min_scrutins_partages": MIN_SCRUTINS_PARTAGES,
            "nb_positions_votes_cles": len(positions),
            "noeuds_exclus_sans_lien": sorted(exclus),
        },
    }


def main():
    # La console Windows est en cp1252 par défaut : les libellés français et les
    # flèches du récapitulatif exigent l'UTF-8.
    sys.stdout.reconfigure(encoding="utf-8")
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else SORTIE_DEFAUT
    g = construire(base)

    par_type = defaultdict(int)
    for n in g["noeuds"]:
        par_type[n["type"]] += 1
    par_rel = defaultdict(int)
    for a in g["aretes"]:
        par_rel[a["relation"]] += 1

    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")

    print(f"{len(g['noeuds'])} nœuds, {len(g['aretes'])} arêtes → {sortie}")
    print("\nnœuds par type :")
    for t, n in sorted(par_type.items(), key=lambda x: -x[1]):
        print(f"  {t:14} {n:5}")
    print("\narêtes par relation :")
    for r, n in sorted(par_rel.items(), key=lambda x: -x[1]):
        print(f"  {r:20} {n:5}")
    exclus = g["meta"]["noeuds_exclus_sans_lien"]
    if exclus:
        print(f"\n{len(exclus)} nœuds retirés faute de lien : {', '.join(exclus)}")

    print("\naccords de vote (taux, nb scrutins partagés) :")
    for d in sorted(g["accords"], key=lambda x: -x["taux"])[:12]:
        print(f"  {d['taux']:.0%}  {d['partages']:6}  {d['a']:3} ↔ {d['b']}")
    print(f"  … {len(g['accords'])} paires au total")


if __name__ == "__main__":
    main()

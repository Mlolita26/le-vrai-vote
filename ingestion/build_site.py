"""Génère le site statique complet dans web/ à partir de la base.

Arborescence (docs/arborescence.md) :
  /                    accueil
  /candidats/          liste, recherche
  /candidats/{slug}/   fiche candidat
  /themes/             thématiques (grille de votes clés : en préparation)
  /comparer/           comparateur deux candidats (scrutins communs exprimés)
  /methode/            méthodologie

Tout provient de la base sourcée ; les manques restent des états explicites.
Remplace export_json.py (le data.json du comparateur est généré ici).

Usage : python ingestion/build_site.py [chemin_base]
"""
import html
import json
import sqlite3
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
WEB = RACINE / "web"

LIBELLES_MANDAT = {
    "depute": "Député", "senateur": "Sénateur", "eurodepute": "Eurodéputé",
    "ministre": "Ministre", "premier_ministre": "Premier ministre",
    "secretaire_etat": "Secrétaire d'État", "maire": "Maire",
    "conseiller_municipal": "Conseiller municipal",
    "conseiller_regional": "Conseiller régional", "autre": "Autre mandat",
}
SEUIL_COMPARABLE = 30  # nb minimal de votes exprimés pour entrer au comparateur

# Candidats mis en avant (ordre imposé) : en tête de la liste, de l'accueil et
# du comparateur ; les autres suivent, par ordre alphabétique.
CANDIDATS_PRIORITAIRES = [
    "jean-luc-melenchon", "marine-le-pen", "edouard-philippe",
    "gabriel-attal", "bruno-retailleau", "marine-tondelier",
]

THEME_SLUGS = {
    "Écologie et agriculture": "ecologie-agriculture",
    "Pouvoir d'achat et fiscalité": "pouvoir-achat-fiscalite",
    "Sécurité et justice": "securite-justice",
    "Immigration": "immigration",
    "Questions de société": "societe",
    "Europe et international": "europe-international",
    "Institutions et vie démocratique": "institutions",
}
# Libellé et classe de badge pour chaque état de la vue couverture.
ETATS = {
    "pour": ("pour", "badge-pour"),
    "contre": ("contre", "badge-contre"),
    "abstention": ("abstention", "badge-abstention"),
    "non_votant": ("non-votant", "badge-nonvotant"),
    "absent": ("absent (déduit)", "badge-absent"),
    "non_concerne": ("non concerné", "badge-neutre"),
    "indisponible": ("indisponible", "badge-neutre"),
    "a_importer": ("à importer", "badge-neutre"),
}
ORDRE_ETATS = ["pour", "contre", "abstention", "non_votant", "absent",
               "a_importer", "non_concerne", "indisponible"]

e = html.escape


def badge_etat(etat):
    libelle, classe = ETATS[etat]
    return f'<span class="badge {classe}">{libelle}</span>'


def majorite_groupe(g):
    """Position majoritaire d'un groupe : la plus votée parmi les exprimés ; « partagé » en cas d'égalité."""
    exprimes = [("pour", g["pour"]), ("contre", g["contre"]), ("abstention", g["abstention"])]
    exprimes.sort(key=lambda x: -x[1])
    if exprimes[0][1] == 0 or (len(exprimes) > 1 and exprimes[0][1] == exprimes[1][1]):
        return None
    return exprimes[0][0]


def decompte_groupe(g):
    morceaux = []
    for cle, libelle in (("pour", "pour"), ("contre", "contre"), ("abstention", "abst.")):
        if g[cle]:
            morceaux.append(f"{g[cle]} {libelle}")
    return " · ".join(morceaux) if morceaux else "aucun suffrage exprimé"


def chip_groupe(g, est_censure=False, contour=False):
    # Nom complet du groupe (référentiel officiel) plutôt que le sigle seul.
    nom = g["libelle"] or g["abrege"] or "groupe non identifié (réf. Sénat)"
    # Motion de censure : seuls les votes pour sont enregistrés — on affiche
    # le nombre de voix apportées à la censure, pas une « majorité ».
    if est_censure:
        if g["pour"]:
            return (f'<span class="badge badge-groupe badge-pour">{e(nom)} : {g["pour"]} voix pour la censure</span>')
        return f'<span class="badge badge-groupe badge-neutre">{e(nom)} : aucune voix pour la censure</span>'
    maj = majorite_groupe(g)
    classe = ETATS[maj][1] if maj else "badge-neutre"
    # « contour » : position d'un PARTI/délégation (badge en contour), à distinguer
    # visuellement du badge plein = vote personnel de la personne.
    if contour:
        classe = f"badge-contour {classe}"
    libelle_maj = ETATS[maj][0] if maj else "partagé"
    return (f'<span class="badge badge-groupe {classe}">{e(nom)} : {libelle_maj}</span> '
            f'<span class="decompte-groupe">({e(decompte_groupe(g))})</span>')


def chip_resultat(v):
    """Résultat officiel du scrutin : adopté/rejeté et décompte de synthèse."""
    if v["sort"] not in ("adopté", "rejeté") or v["total_pour"] is None:
        return ""
    if v["est_censure"]:
        if v["sort"] == "rejeté":
            texte = (f"Censure rejetée · {v['total_pour']} voix pour"
                     + (f", {v['suffrages_requis']} requises" if v["suffrages_requis"] else ""))
        else:
            texte = f"Censure adoptée · {v['total_pour']} voix pour"
    else:
        libelle = "Adopté" if v["sort"] == "adopté" else "Rejeté"
        morceaux = [f"{v['total_pour']} pour", f"{v['total_contre']} contre"]
        if v["total_abstention"]:
            morceaux.append(f"{v['total_abstention']} abst.")
        texte = f"{libelle} · {', '.join(morceaux)}"
    return f'<span class="chip-resultat">{e(texte)}</span>'


RAIL_MOT = {"pour": "Pour", "contre": "Contre", "abstention": "Abstention",
            "non_votant": "Non-votant", "absent": "Absent", "non_concerne": "Non concern\u00e9",
            "indisponible": "Indisponible", "a_importer": "\u00c0 importer"}
RAIL_CLS = {"pour": "pour", "contre": "contre", "abstention": "abst", "non_votant": "neutre",
            "absent": "absent", "non_concerne": "neutre", "indisponible": "neutre", "a_importer": "neutre"}


def rail_perso(p, v, etat_v, equiv_senat, est_pe, a_vote_perso):
    """Bandeau dominant : position de la personne (vote perso, ou \u00e9quivalent S\u00e9nat, ou \u00e9tat)."""
    if a_vote_perso or etat_v == "non_votant":
        return RAIL_CLS[etat_v], RAIL_MOT[etat_v], "a vot\u00e9", False
    eq = equiv_senat.get(v["id"])
    if eq:
        ps = eq["positions"].get(p["slug"])
        if ps:
            return RAIL_CLS[ps], RAIL_MOT[ps], "au S\u00e9nat", True
    if est_pe:
        return "neutre", "\u2014", "n'y si\u00e9geait pas", False
    return "neutre", RAIL_MOT.get(etat_v, "\u2014"), "", False


def resultat_texte(v):
    """R\u00e9sultat officiel en texte court (pas de pastille) pour la ligne meta."""
    if v["sort"] not in ("adopt\u00e9", "rejet\u00e9") or v["total_pour"] is None:
        return ""
    if v["est_censure"]:
        if v["sort"] == "rejet\u00e9":
            return (f"Censure rejet\u00e9e \u00b7 {v['total_pour']} voix pour"
                    + (f", {v['suffrages_requis']} requises" if v["suffrages_requis"] else ""))
        return f"Censure adopt\u00e9e \u00b7 {v['total_pour']} voix pour"
    lib = "Adopt\u00e9" if v["sort"] == "adopt\u00e9" else "Rejet\u00e9"
    return f"{lib} {v['total_pour']}\u2013{v['total_contre']}"


def sens_html(v):
    """Ligne « Pour = … · Contre = … » : ce que le vote signifie concrètement.
    Le mot « Pour »/« Contre » porte le sens (jamais la couleur seule — RGAA)."""
    sp, sc = v.get("sens_pour"), v.get("sens_contre")
    if not sp or not sc:
        return ""
    return (f'<p class="sens-vote">'
            f'<span class="sens-part sens-p"><span class="sens-mot">Pour</span> = {e(sp)}</span>'
            f'<span class="sens-part sens-c"><span class="sens-mot">Contre</span> = {e(sc)}</span>'
            f'</p>')


def senat_fiche(vc_id, slug, equiv_senat):
    """Ligne \u00ab Au S\u00e9nat \u00bb sur la fiche : position du candidat sur le texte \u00e9quivalent."""
    eq = equiv_senat.get(vc_id)
    if not eq:
        return ""
    pos = eq["positions"].get(slug)
    if not pos:
        return ""
    lib, classe = ETATS[pos]
    return (f'<p class="ligne-senat">Au S\u00e9nat, sur le m\u00eame texte '
            f'(scrutin du {date_fr(eq["date"])}) : <span class="badge {classe}">{lib}</span></p>')


def senat_theme(vc_id, equiv_senat, par_slug):
    """Ligne \u00ab Au S\u00e9nat \u00bb sur la page th\u00e8me : positions des candidats suivis."""
    eq = equiv_senat.get(vc_id)
    if not eq or not eq["positions"]:
        return ""
    parts = []
    for s, pos in eq["positions"].items():
        if s in par_slug:
            lib, classe = ETATS[pos]
            parts.append(f'<a href="../../candidats/{s}/">{e(par_slug[s])}</a> '
                         f'<span class="badge {classe}">{lib}</span>')
    if not parts:
        return ""
    return (f'<p class="ligne-senat">Au S\u00e9nat, m\u00eame texte (scrutin du {date_fr(eq["date"])}, '
            f'{e(eq["sort"] or "")}) : ' + ", ".join(parts) + "</p>")


def date_fr(iso):
    if not iso:
        return None
    a, m, j = iso.split("-")
    return f"{j}/{m}/{a}"


def nombre_fr(n):
    return f"{n:,}".replace(",", " ")  # espace fine insécable


# ── Collecte des données ─────────────────────────────────────────────────────

def charger(base):
    con = sqlite3.connect(base)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    candidats = []
    lignes = cur.execute(
        "SELECT p.id, p.slug, p.prenom, p.nom, p.naissance, c.statut, c.date, c.detail, "
        "s.url AS source_url FROM candidatures c "
        "JOIN personnes p ON p.id = c.personne_id "
        "JOIN sources s ON s.id = c.source_id ORDER BY p.nom").fetchall()
    for c in lignes:  # fetchall d'abord : le curseur est réutilisé dans la boucle
        pid = c["id"]
        mandats = [dict(m) for m in cur.execute(
            "SELECT type, debut, fin, precision, detail FROM mandats "
            "WHERE personne_id=? ORDER BY debut", (pid,))]
        # Positions ventilées par chambre : l'AN/Congrès et le Sénat ne se
        # mélangent pas (échelles et périodes différentes).
        positions = dict(cur.execute(
            "SELECT position, COUNT(*) FROM positions_vote pv JOIN scrutins s ON s.id = pv.scrutin_id "
            "WHERE pv.personne_id=? AND s.chambre IN ('an','congres') GROUP BY position", (pid,)).fetchall())
        positions_senat = dict(cur.execute(
            "SELECT position, COUNT(*) FROM positions_vote pv JOIN scrutins s ON s.id = pv.scrutin_id "
            "WHERE pv.personne_id=? AND s.chambre='senat' GROUP BY position", (pid,)).fetchall())
        solennels = [dict(r) for r in cur.execute(
            "SELECT s.legislature AS leg, "
            "SUM(CASE WHEN pv.position != 'absent' THEN 1 ELSE 0 END) AS present, COUNT(*) AS total "
            "FROM positions_vote pv JOIN scrutins s ON s.id = pv.scrutin_id "
            "WHERE pv.personne_id=? AND s.type_vote LIKE '%solennel%' "
            "GROUP BY s.legislature ORDER BY s.legislature", (pid,))]
        exprimes = {sid: pos for sid, pos in cur.execute(
            "SELECT scrutin_id, position FROM positions_vote "
            "WHERE personne_id=? AND position IN ('pour','contre','abstention')", (pid,))}
        candidats.append({
            "slug": c["slug"], "nom": f"{c['prenom']} {c['nom']}", "nom_famille": c["nom"],
            "naissance": c["naissance"], "statut": c["statut"],
            "date_declaration": c["date"], "detail": c["detail"],
            "parti": c["detail"].split(" — ")[0].split(",")[0],
            "source": c["source_url"], "mandats": mandats,
            "positions": positions, "positions_senat": positions_senat,
            "solennels": solennels, "exprimes": exprimes,
        })

    themes = [dict(t) for t in cur.execute(
        "SELECT id, libelle, ordre FROM thematiques ORDER BY ordre")]
    votes_cles = [dict(v) for v in cur.execute(
        "SELECT vc.id, vc.thematique_id, vc.titre, vc.resume, vc.source_resume, "
        "vc.contexte, vc.sens_pour, vc.sens_contre, s.date, s.chambre, s.legislature, "
        "s.objet, s.sort, s.total_pour, "
        "s.total_contre, s.total_abstention, s.suffrages_requis, vc.scrutin_id FROM votes_cles vc "
        "JOIN scrutins s ON s.id = vc.scrutin_id ORDER BY vc.thematique_id, s.date")]
    for v in votes_cles:
        v["est_censure"] = "motion de censure" in (v["objet"] or "").lower()
    # Décomptes officiels par groupe parlementaire, par vote clé.
    groupes_par_vote = {}
    for vid, abrege, libelle, pour, contre, abst, nonvot in cur.execute(
            "SELECT vc.id, pg.groupe_abrege, pg.groupe_libelle, pg.pour, pg.contre, "
            "pg.abstention, pg.non_votant FROM positions_groupes pg "
            "JOIN votes_cles vc ON vc.scrutin_id = pg.scrutin_id "
            "ORDER BY (pg.pour + pg.contre + pg.abstention) DESC"):
        groupes_par_vote.setdefault(vid, []).append(
            {"abrege": abrege, "libelle": libelle, "pour": pour,
             "contre": contre, "abstention": abst, "non_votant": nonvot})
    # Rattachement candidat -> groupe de son parti, par législature.
    groupe_du_candidat = {(slug_p, leg): abrege for slug_p, leg, abrege in cur.execute(
        "SELECT p.slug, gr.legislature, gr.groupe_abrege FROM groupes_reference gr "
        "JOIN personnes p ON p.id = gr.personne_id")}
    equiv_senat = {}
    for vc_id, sdate, ssort in cur.execute(
            "SELECT vc.id, s.date, s.sort FROM votes_cles vc "
            "JOIN scrutins s ON s.id = vc.scrutin_senat_id WHERE vc.scrutin_senat_id IS NOT NULL").fetchall():
        pos = dict(cur.execute(
            "SELECT p.slug, pv.position FROM positions_vote pv JOIN personnes p ON p.id = pv.personne_id "
            "JOIN votes_cles vc ON vc.scrutin_senat_id = pv.scrutin_id WHERE vc.id = ?", (vc_id,)).fetchall())
        equiv_senat[vc_id] = {"date": sdate, "sort": ssort, "positions": pos}
    etats = {(slug_p, vid): etat for slug_p, vid, etat in cur.execute(
        "SELECT personne_slug, vote_cle_id, etat FROM couverture")}
    # Concept unifié « justification » : une explication sourcée d'un vote, au
    # niveau d'une PERSONNE ou d'un GROUPE. La vue `justifications` réunit les deux
    # sources de curation (personnes et groupes) — le reste du code, et le site,
    # ne voient plus qu'un seul objet « justification ».
    cur.execute("""CREATE VIEW IF NOT EXISTS justifications AS
        SELECT scrutin_id, personne_id, NULL AS groupe_abrege, texte, source_id FROM nuances
        UNION ALL
        SELECT scrutin_id, NULL AS personne_id, groupe_abrege, texte, source_id FROM justifications_groupes""")
    # Justification d'une personne, par (personne, vote clé).
    nuances = {(slug_p, vid): (texte, url) for slug_p, vid, texte, url in cur.execute(
        "SELECT p.slug, vc.id, j.texte, src.url FROM justifications j "
        "JOIN personnes p ON p.id = j.personne_id "
        "JOIN votes_cles vc ON vc.scrutin_id = j.scrutin_id "
        "JOIN sources src ON src.id = j.source_id WHERE j.personne_id IS NOT NULL")}
    # Justification d'un groupe, par (vote clé, groupe abrégé).
    justifs_groupes = {(vid, ab): (texte, url) for vid, ab, texte, url in cur.execute(
        "SELECT vc.id, j.groupe_abrege, j.texte, src.url FROM justifications j "
        "JOIN votes_cles vc ON vc.scrutin_id = j.scrutin_id "
        "JOIN sources src ON src.id = j.source_id WHERE j.groupe_abrege IS NOT NULL")}

    meta = {
        "genere_le": date.today().isoformat(),
        "n_scrutins": cur.execute("SELECT COUNT(*) FROM scrutins").fetchone()[0],
        "candidats_maj": "23/07/2026",
    }
    con.close()
    return (candidats, themes, votes_cles, etats, nuances, justifs_groupes,
            groupes_par_vote, groupe_du_candidat, equiv_senat, meta)


CHAMBRE_LABEL = {"an": "Assembl\u00e9e nationale", "congres": "Congr\u00e8s du Parlement",
                 "pe": "Parlement europ\u00e9en", "senat": "S\u00e9nat"}
POS_COMPARABLE = ("pour", "contre", "abstention")


def position_perso(slug, v, etats, equiv_senat):
    """Position personnelle exprim\u00e9e (AN/PE via couverture, ou \u00e9quivalent S\u00e9nat)."""
    p = etats.get((slug, v["id"]))
    if p in POS_COMPARABLE:
        return p
    eq = equiv_senat.get(v["id"])
    if eq:
        ps = eq["positions"].get(slug)
        if ps in POS_COMPARABLE:
            return ps
    return None


def position_parti(slug, v, groupes_par_vote, groupe_du_candidat):
    """Position majoritaire du groupe du parti du candidat sur ce vote (ou None)."""
    ab = groupe_du_candidat.get((slug, v["legislature"]))
    if not ab:
        return None, None
    g = next((x for x in groupes_par_vote.get(v["id"], []) if x["abrege"] == ab), None)
    if not g:
        return None, ab
    return majorite_groupe(g), (g["libelle"] or ab)


def positions_comparaison(candidats, votes_cles, etats, nuances, justifs_groupes, equiv_senat,
                          groupes_par_vote, groupe_du_candidat):
    """Pour chaque candidat et chaque vote cl\u00e9 : perso, parti, nom du parti, nuance, justif du parti."""
    out = {}
    for c in candidats:
        slug = c["slug"]
        d = {}
        for v in votes_cles:
            perso = position_perso(slug, v, etats, equiv_senat)
            parti, parti_nom = position_parti(slug, v, groupes_par_vote, groupe_du_candidat)
            nu = nuances.get((slug, v["id"]))
            ab = groupe_du_candidat.get((slug, v["legislature"]))
            jp = justifs_groupes.get((v["id"], ab)) if ab else None
            d[str(v["id"])] = {"perso": perso, "parti": parti, "parti_nom": parti_nom,
                               "nuance": [nu[0], nu[1]] if nu else None,
                               "justif_parti": [jp[0], jp[1]] if jp else None}
        out[slug] = d
    return out


def concordances(candidats):
    """Paires de candidats : accord sur les scrutins où tous deux ont exprimé un vote."""
    resultat = {}
    comparables = [c for c in candidats if len(c["exprimes"]) >= SEUIL_COMPARABLE]
    for a, b in combinations(comparables, 2):
        communs = set(a["exprimes"]) & set(b["exprimes"])
        if len(communs) < SEUIL_COMPARABLE:
            continue
        accord = sum(1 for s in communs if a["exprimes"][s] == b["exprimes"][s])
        cle = "|".join(sorted([a["slug"], b["slug"]]))
        resultat[cle] = {"communs": len(communs), "accord": accord}
    return resultat, [c["slug"] for c in comparables]


# ── Gabarit ──────────────────────────────────────────────────────────────────

def page(titre, actif, contenu, profondeur, meta):
    r = "../" * profondeur
    nav_items = [("", "Accueil"), ("candidats/", "Candidats"),
                 ("comparer/", "Comparer"), ("methode/", "Méthode")]
    nav = "".join(
        f'<a href="{r}{chemin if chemin else "./"}"'
        f'{" aria-current=\"page\"" if libelle == actif else ""}>{libelle}</a>'
        for chemin, libelle in nav_items)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titre)} — Le Vrai Vote</title>
<link rel="stylesheet" href="{r}styles.css">
<script src="{r}theme.js" defer></script>
</head>
<body>
<div class="bandeau-travail" role="status">Version de travail — chaque fait affiché est sourcé ; ce qui n'est pas encore importé est indiqué comme tel.</div>
<header class="entete-nav">
  <a class="marque" href="{r}./">Le Vrai Vote</a>
  <nav aria-label="Navigation principale">{nav}</nav>
</header>
<main>
{contenu}
</main>
<footer class="pied">
<p>Données générées le {e(date_fr(meta['genere_le']))} — {nombre_fr(meta['n_scrutins'])} scrutins en base (Assemblée nationale et Congrès, juillet 2012 → juillet 2026 ; Sénat et Parlement européen à importer). Candidatures mises à jour le {e(meta['candidats_maj'])}.</p>
<p>Données parlementaires : licence ouverte (Assemblée nationale). Contenu : CC BY 4.0. <a href="https://github.com/Mlolita26/le-vrai-vote">Code source</a>.</p>
</footer>
</body>
</html>
"""


def badges_positions(d):
    morceaux = []
    for cle, libelle, classe in (("pour", "pour", "badge-pour"), ("contre", "contre", "badge-contre"),
                                 ("abstention", "abstention", "badge-abstention"),
                                 ("non_votant", "non-votant", "badge-nonvotant"),
                                 ("absent", "absent (déduit)", "badge-absent")):
        if d.get(cle):
            morceaux.append(f'<span class="badge {classe}">{libelle} : {d[cle]:,}</span>'.replace(",", " "))
    return f'<div class="badges">{"".join(morceaux)}</div>' if morceaux else ""


def etat_couverture(p):
    """Phrase d'état honnête selon les données disponibles."""
    exprimables = ("pour", "contre", "abstention")
    n_an = sum(v for k, v in p["positions"].items() if k in exprimables)
    n_senat = sum(v for k, v in p.get("positions_senat", {}).items() if k in exprimables)
    est_senateur = any(m["type"] == "senateur" for m in p["mandats"])
    est_eurodepute = any(m["type"] == "eurodepute" for m in p["mandats"])
    est_depute = any(m["type"] == "depute" for m in p["mandats"])
    a_mandat_parl = est_senateur or est_eurodepute or est_depute
    if n_an >= SEUIL_COMPARABLE:
        return "couvert", f"{n_an:,} votes exprimés à l'Assemblée".replace(",", " ")
    if n_senat >= SEUIL_COMPARABLE:
        return "couvert", f"{n_senat:,} votes exprimés au Sénat".replace(",", " ")
    if est_senateur:
        return "partiel", "sénateur — scrutins du Sénat à importer"
    if est_eurodepute and not est_depute:
        return "partiel", "eurodéputé — scrutins du Parlement européen à importer"
    if a_mandat_parl:
        return "partiel", "mandats antérieurs à la période couverte (2012-2026)"
    return "hors", "jamais parlementaire depuis 1997 (données AN) — positions déclaratives à venir"


# ── Pages ────────────────────────────────────────────────────────────────────

def carte_candidat(p, prefixe):
    etat, phrase = etat_couverture(p)
    declaration = (f"déclaré(e) le {date_fr(p['date_declaration'])}" if p["date_declaration"]
                   else "date de déclaration non fournie par la source")
    lien_statut = "candidature déclarée" if p["statut"] == "declaree" else "en lice pour une primaire"
    return f"""<article class="carte-candidat" data-nom="{e(p['nom'].lower())}">
<div class="carte-tete">{avatar(p, prefixe)}<h3><a href="{prefixe}candidats/{e(p['slug'])}/">{e(p['nom'])}</a></h3></div>
<p class="detail">{e(p['parti'])} · {lien_statut} · {e(declaration)} (<a href="{e(p['source'])}" rel="noopener">source</a>)</p>
<p class="couverture couverture-{etat}">{e(phrase)}</p>
</article>"""


# Explications précises quand le parti d'un candidat n'avait pas de groupe
# à l'Assemblée sur une législature (affichées à la place du message générique).
SANS_GROUPE = {
    ("marine-le-pen", "15"):
        "Le RN n'avait que 8 députés en 2017 — pas assez pour former un groupe "
        "(minimum 15) : ses élus siégeaient parmi les non-inscrits. Il n'existe donc "
        "aucun décompte officiel « groupe RN » pour ce scrutin.",
    ("edouard-philippe", "15"):
        "Horizons n'existait pas encore (parti créé en octobre 2021) : aucun décompte "
        "de groupe ne peut exister pour ce scrutin.",
}

# Pastilles d'état de couverture (design « refonte accueil », 24/07/2026)
PASTILLES = {
    "couvert": ("Votes disponibles", "pastille-ok"),
    "partiel": ("Couverture partielle", "pastille-partiel"),
    "hors": ("Positions déclaratives", "pastille-decl"),
}


def avatar(p, prefixe=""):
    """Portrait libre (Wikimedia, crédité sur la page Méthode) ou initiales."""
    if (WEB / "photos" / f"{p['slug']}.jpg").exists():
        return (f'<img class="cand-avatar cand-photo" src="{prefixe}photos/{e(p["slug"])}.jpg" '
                f'alt="" loading="lazy" width="42" height="42">')
    initiales = (p["nom"].split()[0][0] + p["nom"].split()[1][0]).upper() \
        if len(p["nom"].split()) > 1 else p["nom"][:2].upper()
    return f'<div class="cand-avatar">{e(initiales)}</div>'


def carte_accueil(p):
    etat, phrase = etat_couverture(p)
    libelle, classe = PASTILLES[etat]
    note = phrase[0].upper() + phrase[1:]
    recherche = f"{p['nom']} {p['parti']}".lower()
    return f"""<article class="cand-carte" data-nom="{e(recherche)}">{avatar(p)}<div>
<h3 class="cand-nom"><a href="candidats/{e(p['slug'])}/">{e(p['nom'])}</a></h3>
<div class="cand-parti">{e(p['parti'])}</div>
<span class="pastille {classe}">{libelle}</span>
<div class="cand-note">{e(note)}</div></div></article>"""


def page_accueil(candidats, meta):
    declares = [c for c in candidats if c["statut"] == "declaree"]
    primaires = [c for c in candidats if c["statut"] == "primaire"]
    n_couverts = sum(1 for c in candidats if etat_couverture(c)[0] == "couvert")
    contenu = f"""
<section class="hero">
<p class="hero-eyebrow"><i></i> Présidentielle 2027 · Transparence électorale</p>
<h1>Leurs votes,<br>pas leurs promesses.</h1>
<p class="hero-lead">Pour chaque candidat à la présidentielle, ce qu'il a <strong>réellement voté</strong> au Parlement,
sa présence et son parcours — à partir des données publiques officielles, chaque fait relié à sa source.</p>
<p class="acces">
<a class="bouton" href="#candidats">Voir les candidats</a>
<a class="bouton bouton-second" href="comparer/">Comparer deux candidats</a>
<a class="bouton bouton-second" href="methode/">Lire la méthode</a>
</p>
<div class="stats">
<div><div class="stat-num">{len(candidats)}</div><div class="stat-lbl">candidatures suivies ({len(declares)} déclarées + {len(primaires)} en primaire)</div></div>
<div><div class="stat-num">{n_couverts}</div><div class="stat-lbl">candidats aux votes déjà consultables</div></div>
<div><div class="stat-num accent">100 %</div><div class="stat-lbl">des faits reliés à leur source</div></div>
</div>
</section>

<section class="bloc" id="comment">
<h2>Comment lire ce site</h2>
<p class="intro">Trois gestes suffisent. Le site ne vous dit jamais quoi penser : il vous donne les faits, vous vous faites votre opinion.</p>
<div class="steps">
<div class="step"><div class="step-num">1</div><h3>Choisissez un candidat</h3><p>Parcourez les candidatures déclarées et les personnalités en lice pour une primaire. Une pastille indique d'emblée ce qui est disponible.</p></div>
<div class="step"><div class="step-num">2</div><h3>Lisez ses votes réels</h3><p>Ses positions sur les votes clés, regroupées par thème, chacune accompagnée d'un résumé neutre de la loi et de son assiduité.</p></div>
<div class="step"><div class="step-num">3</div><h3>Comparez deux candidats</h3><p>Mettez deux candidats côte à côte sur les mêmes votes clés et voyez, thème par thème, où ils se rejoignent et où ils s'opposent.</p></div>
</div>
</section>

<section class="bloc" id="candidats">
<h2>Les candidats</h2>
<p class="intro">Déclarations publiques recensées et sourcées — la liste officielle ne sera établie par le Conseil constitutionnel qu'après validation des parrainages, en mars 2027.</p>
<p><label for="recherche" style="font-size:0.9rem;color:var(--encre-douce);">Rechercher :</label>
<input id="recherche" type="search" placeholder="Nom du candidat ou parti" autocomplete="off"></p>
<h3 class="sous-titre">Candidatures déclarées</h3>
<div class="cand-grille" id="grille-declarees">{''.join(carte_accueil(c) for c in declares)}</div>
<h3 class="sous-titre">En lice pour une primaire</h3>
<div class="cand-grille" id="grille-primaire">{''.join(carte_accueil(c) for c in primaires)}</div>
<p class="note-methode">Jordan Bardella n'est pas candidat : Marine Le Pen, déclarée le 7 juillet 2026
après l'arrêt d'appel, porte la candidature du Rassemblement national.</p>
</section>
<script>
document.getElementById("recherche").addEventListener("input", function () {{
  const q = this.value.toLowerCase().trim();
  for (const carte of document.querySelectorAll(".cand-carte"))
    carte.style.display = carte.dataset.nom.includes(q) ? "" : "none";
}});
</script>"""
    return page("Accueil", "Accueil", contenu, 0, meta)


def page_liste(candidats, meta):
    contenu = f"""
<h1>Les candidats</h1>
<p>Recherchez un candidat ; chaque fiche détaille mandats, votes et présence, avec les sources.</p>
<p><label for="recherche">Rechercher :</label>
<input id="recherche" type="search" placeholder="Nom du candidat" autocomplete="off"></p>
<div class="grille-cartes" id="cartes">{''.join(carte_candidat(c, '../') for c in candidats)}</div>
<script>
document.getElementById("recherche").addEventListener("input", function () {{
  const q = this.value.toLowerCase().trim();
  for (const carte of document.querySelectorAll("#cartes .carte-candidat"))
    carte.style.display = carte.dataset.nom.includes(q) ? "" : "none";
}});
</script>"""
    return page("Candidats", "Candidats", contenu, 1, meta)


def fiche_candidat(p, themes, votes_cles, etats, nuances, justifs_groupes, groupes_par_vote, groupe_du_candidat, equiv_senat, meta):
    declaration = (f"le {date_fr(p['date_declaration'])}" if p["date_declaration"]
                   else "(date non fournie par la source)")
    statut = "Candidature déclarée" if p["statut"] == "declaree" else "En lice pour une primaire"
    mandats_html = "".join(
        f"""<li><strong>{e(LIBELLES_MANDAT.get(m['type'], m['type']))}</strong>
<span class="dates"> — {date_fr(m['debut'])} → {date_fr(m['fin']) if m['fin'] else 'en cours'}
{'(précision au mois)' if m['precision'] == 'mois' else ''}</span></li>"""
        for m in p["mandats"]) or "<li>Aucun mandat parlementaire ou gouvernemental depuis 1997 dans les données AN importées.</li>"

    solennels_html = ""
    if p["solennels"]:
        lignes = "".join(
            f"<li>Législature {e(s['leg'])} : {s['present']}/{s['total']} scrutins solennels "
            f"({100 * s['present'] / s['total']:.1f} %)</li>".replace(".", ",")
            for s in p["solennels"])
        solennels_html = f"""<h2>Présence aux scrutins solennels</h2>
<p class="note-methode">Les scrutins solennels sont les votes d'ensemble annoncés à l'avance —
référence usuelle de l'assiduité. La médiane de l'assemblée sera affichée dans une prochaine version.</p>
<ul>{lignes}</ul>"""

    etat, phrase = etat_couverture(p)
    positions_html = badges_positions(p["positions"]) or f'<p class="couverture couverture-{etat}">{e(phrase)}</p>'

    # Votes clés groupés par thème, avec l'état calculé de ce candidat.
    votes_html = ""
    themes_presents = []

    def _vote_present(v):
        """Le candidat OU son parti a-t-il une position sur ce vote clé ?"""
        ev = etats.get((p["slug"], v["id"]), "a_importer")
        if ev in ("pour", "contre", "abstention", "absent", "non_votant"):
            return True
        ab = groupe_du_candidat.get((p["slug"], v["legislature"]))
        if ab and any(x["abrege"] == ab for x in groupes_par_vote.get(v["id"], [])):
            return True
        eqp = equiv_senat.get(v["id"])
        return bool(eqp and eqp["positions"].get(p["slug"]))

    for t in themes:
        votes_t = [v for v in votes_cles if v["thematique_id"] == t["id"]]
        if not votes_t:
            continue
        # Dans chaque thème : d'abord les votes où le candidat/parti était présent,
        # les « non concerné »/vides à la fin (tri stable → ordre d'origine préservé).
        votes_t = sorted(votes_t, key=lambda v: 0 if _vote_present(v) else 1)
        slug_t = THEME_SLUGS[t["libelle"]]
        lignes = ""
        for v in votes_t:
            etat_v = etats.get((p["slug"], v["id"]), "a_importer")
            est_pe = v["chambre"] == "pe"
            nuance = nuances.get((p["slug"], v["id"]))
            nuance_html = (f'<p class="vote-nuance">Justification : {e(nuance[0])} '
                           f'(<a href="{e(nuance[1])}" rel="noopener">source</a>)</p>' if nuance else "")
            # Voix 2 — position du groupe/délégation du parti du candidat (même
            # quand lui-même n'a pas voté). Au PE : badge en contour (≠ vote perso).
            groupe_html = ""
            pos_parti = None   # position majoritaire du groupe/délégation du parti (toutes chambres)
            abrege = groupe_du_candidat.get((p["slug"], v["legislature"]))
            if abrege:
                g = next((x for x in groupes_par_vote.get(v["id"], []) if x["abrege"] == abrege), None)
                if g and est_pe:
                    pos_parti = majorite_groupe(g)
                    groupe_html = (f'<p class="ligne-groupe ligne-pe">Son parti au Parlement européen — '
                                   f'{chip_groupe(g, contour=True)}</p>')
                elif g:
                    pos_parti = majorite_groupe(g)
                    groupe_html = (f'<p class="ligne-groupe">Son parti — groupe '
                                   f'{chip_groupe(g, v["est_censure"])}</p>')
            elif not est_pe and any(cle[0] == p["slug"] for cle in groupe_du_candidat):
                explication = SANS_GROUPE.get(
                    (p["slug"], v["legislature"]),
                    "Son parti n'avait pas de groupe à l'Assemblée sur cette législature : "
                    "aucun décompte officiel de groupe n'existe pour ce scrutin.")
                groupe_html = f'<p class="ligne-groupe ligne-groupe-absente">{e(explication)}</p>'
            # Justification sourcée du groupe du candidat (le « pourquoi » du parti).
            jp = justifs_groupes.get((v["id"], abrege)) if abrege else None
            justif_parti_html = (
                f'<p class="groupe-justif">Justification du groupe : {e(jp[0])} '
                f'(<a href="{e(jp[1])}" rel="noopener">source</a>)</p>' if jp else "")
            senat_html = senat_fiche(v["id"], p["slug"], equiv_senat)
            a_vote_perso = etat_v in ("pour", "contre", "abstention", "absent")
            # Au PE, une carte sans vote personnel ET sans position de parti
            # rattachée n'apporte rien : on ne l'affiche pas (évite le bruit sur
            # les fiches des candidats sans lien avec le Parlement européen).
            if est_pe and not a_vote_perso and not groupe_html:
                continue
            # Voix 1 — vote personnel. Au PE, affichée seulement si vote réel ;
            # sinon ruban « n'y siégeait pas » (on n'affiche pas « non concerné »
            # pour un mandat européen que la personne n'avait pas).
            if est_pe and not a_vote_perso:
                perso_html = f'<span class="mention-absente">{e(p["nom"])} n\'y siégeait pas</span>'
            else:
                perso_html = badge_etat(etat_v)
            resultat_txt = resultat_texte(v)
            rail_cls, rail_mot, rail_sous, rail_from_senat = rail_perso(
                p, v, etat_v, equiv_senat, est_pe, a_vote_perso)
            senat_sec = "" if rail_from_senat else senat_html
            provenance = (f'<span class="provenance provenance-{v["chambre"]}">'
                          f'{e(CHAMBRE_LABEL.get(v["chambre"], v["chambre"]))}</span>')
            meta_html = f'<p class="ap-meta">{e(resultat_txt)}</p>' if resultat_txt else ''
            # Banni\u00e8re : quand la personne n'a pas vot\u00e9 elle-m\u00eame (mandat europ\u00e9en
            # qu'elle n'avait pas, ou pas en poste \u00e0 l'Assembl\u00e9e/au Congr\u00e8s \u00e0 la date)
            # mais que son parti a une position, on l'affiche en teinte douce
            # (vert/rouge) avec la m\u00eame pr\u00e9sentation partout \u2014 label \u00ab Parti \u00bb +
            # mention explicite \u2014 pour ne pas la confondre avec un vote personnel.
            # (Exclu pour les motions de censure : seul le \u00ab pour \u00bb y est compt\u00e9,
            # une banni\u00e8re color\u00e9e serait ambigu\u00eb.)
            if not a_vote_perso and not rail_from_senat and pos_parti and not v["est_censure"]:
                mention_parti = ("n'y si\u00e9geait pas" if est_pe
                                 else "n'\u00e9tait pas en poste" if etat_v == "non_concerne"
                                 else "position de son parti")
                rail_html = (f'<div class="ap-rail rail-parti-{pos_parti}">'
                             f'<span class="pos-parti">Parti</span>'
                             f'<span class="pos">{ETATS[pos_parti][0]}</span>'
                             f'<span class="mini">\u2014 {mention_parti}</span></div>')
            else:
                sous_html = f'<span class="mini">{rail_sous}</span>' if rail_sous else ''
                rail_html = (f'<div class="ap-rail rail-{rail_cls}">'
                             f'<span class="pos">{rail_mot}</span>{sous_html}</div>')
            lignes += f"""<li class="vote-carte">
{rail_html}
<div class="ap-corps">
<p class="ap-titre">{e(v['titre'])} {provenance}</p>
{meta_html}
{sens_html(v)}
{groupe_html}
{justif_parti_html}
{senat_sec}
<p class="ap-resume">{e(v['resume'])} <a href="{e(v['source_resume'])}" rel="noopener">Scrutin officiel \u2192</a></p>
{nuance_html}
{f'<p class="vote-contexte">{e(v["contexte"])}</p>' if v['contexte'] else ''}
</div>
</li>"""
        if lignes:  # thème sans aucune carte à montrer (ex. votes PE tous masqués)
            n_cartes = lignes.count('class="vote-carte"')
            themes_presents.append((slug_t, t["libelle"], n_cartes))
            votes_html += (f'<section class="theme-bloc" data-theme="{slug_t}">'
                           f'<h3>{e(t["libelle"])}</h3>'
                           f'<ul class="votes-cles">{lignes}</ul></section>')

    n_an_expr = sum(v for k, v in p["positions"].items() if k in ("pour", "contre", "abstention"))
    bloc_an = ("<h2>Ensemble des positions de vote \u2014 Assembl\u00e9e nationale, 2012-2026</h2>\n"
               + positions_html) if n_an_expr else ""
    b_sen = badges_positions(p["positions_senat"])
    bloc_senat = ("<h2>Positions de vote \u2014 S\u00e9nat</h2>\n"
                  "<p class=\"note-methode\">Scrutins publics du S\u00e9nat collect\u00e9s sur senat.fr. "
                  "Beaucoup de textes au S\u00e9nat ne font pas l'objet d'un scrutin public : "
                  "cette r\u00e9partition ne couvre que les scrutins publics.</p>\n" + b_sen) if b_sen else ""
    total_votes = sum(n for _, _, n in themes_presents)
    if len(themes_presents) > 1:
        chips = (f'<button class="filtre-chip actif" data-cible="tous" type="button" '
                 f'aria-pressed="true">Tous les th\u00e8mes ({total_votes})</button>')
        for slug_t, lib, n in themes_presents:
            chips += (f'<button class="filtre-chip" data-cible="{slug_t}" type="button" '
                      f'aria-pressed="false">{e(lib)} ({n})</button>')
        filtre_html = (f'<div class="filtres-themes" role="group" '
                       f'aria-label="Filtrer les votes cl\u00e9s par th\u00e8me">{chips}</div>')
    else:
        filtre_html = ""
    note_votes = (
        '<p class="note-methode">S\u00e9lection selon la <a href="../../methode/">grille de crit\u00e8res '
        'publi\u00e9e</a>, identique pour tous les candidats. \u00ab Non concern\u00e9 \u00bb : pas en poste dans la '
        'chambre \u00e0 la date du scrutin ; \u00ab absent (d\u00e9duit) \u00bb : mandat actif mais aucune mention '
        'au scrutin officiel.</p>')
    js_filtre = """<script>
(function() {
  var chips = document.querySelectorAll(".filtres-themes .filtre-chip");
  var blocs = document.querySelectorAll("#votes-themes .theme-bloc");
  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      chips.forEach(function (x) { x.classList.remove("actif"); x.setAttribute("aria-pressed", "false"); });
      c.classList.add("actif"); c.setAttribute("aria-pressed", "true");
      var cible = c.dataset.cible;
      blocs.forEach(function (b) {
        b.style.display = (cible === "tous" || b.dataset.theme === cible) ? "" : "none";
      });
      // Remonter au niveau des filtres : sinon, après un clic en bas de page,
      // la liste raccourcie laisse l'utilisateur bloqué en bas (peu commode).
      var barre = document.querySelector(".filtres-themes");
      if (barre && barre.scrollIntoView) barre.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
})();
</script>"""
    if etat == "hors" and votes_html:
        # Jamais parlementaire : tous les votes cl\u00e9s sont \u00ab indisponible \u00bb.
        # On r\u00e9sume en une phrase et on replie le d\u00e9tail (rien n'est perdu).
        section_votes = (
            f'<h2>Votes cl\u00e9s</h2>'
            f'<p class="note-methode">{e(p["nom"])} n\'a jamais si\u00e9g\u00e9 au Parlement '
            f'(Assembl\u00e9e nationale, S\u00e9nat ou Parlement europ\u00e9en) depuis 1997 : il n\'existe donc '
            f'aucun vote personnel \u00e0 afficher sur les lois cl\u00e9s. Les positions viendront des '
            f'd\u00e9clarations publiques (programme, discours), clairement identifi\u00e9es comme telles.</p>'
            f'<details class="votes-replies"><summary>Voir la liste des lois cl\u00e9s '
            f'(toutes \u00ab indisponible \u00bb pour ce candidat)</summary>{note_votes}{votes_html}</details>')
    else:
        section_votes = (f'<h2>Votes cl\u00e9s par th\u00e8me</h2>{note_votes}{filtre_html}'
                         f'<div id="votes-themes">{votes_html}</div>{js_filtre}')
    contenu = f"""
<nav class="fil"><a href="../">← Tous les candidats</a></nav>
<div class="fiche-tete">{avatar(p, "../../").replace('width="42" height="42"', 'width="72" height="72"')}
<div><h1>{e(p['nom'])}</h1>
<p class="detail">{e(p['detail'])}</p></div></div>
<p>{statut} {e(declaration)} — <a href="{e(p['source'])}" rel="noopener">source de la déclaration</a>.
{f"Né(e) le {date_fr(p['naissance'])} (source : open data officiel)." if p['naissance'] else "Date de naissance : à importer."}</p>
{section_votes}
<h2>Mandats (sources officielles, datés)</h2>
<ul class="mandats">{mandats_html}</ul>
{bloc_an}
{bloc_senat}
{solennels_html}
<h2>Justice</h2>
<p class="note-methode">Volet renseigné manuellement, fait par fait, uniquement sur documents publics sourcés,
après relecture — avec mention systématique de la présomption d'innocence pour toute procédure en cours. À venir.</p>
<h2>Programme</h2>
<p class="note-methode">Positions déclarées (programmes, discours sourcés) : à venir — particulièrement utile
pour les candidats sans mandat parlementaire récent.</p>"""
    return page(p["nom"], "Candidats", contenu, 2, meta)


def page_themes_index(themes, votes_cles, meta):
    cartes = ""
    for t in themes:
        n = sum(1 for v in votes_cles if v["thematique_id"] == t["id"])
        slug_t = THEME_SLUGS[t["libelle"]]
        cartes += f"""<article class="carte-candidat">
<h3><a href="{slug_t}/">{e(t['libelle'])}</a></h3>
<p class="detail">{n} votes clés</p>
</article>"""
    contenu = f"""
<h1>Thèmes</h1>
<p>Chaque thème regroupe des « votes clés » : des scrutins réels, résumés de façon neutre,
avec pour chaque candidat sa position — ou son état : non concerné, indisponible, à importer.
La sélection suit la <a href="../methode/">grille de critères publiée</a>, identique pour tous.</p>
<div class="grille-cartes">{cartes}</div>"""
    return page("Thèmes", "Thèmes", contenu, 1, meta)


def page_theme(t, votes_t, candidats, etats, nuances, justifs_groupes, groupes_par_vote, equiv_senat, meta):
    par_slug = {c["slug"]: c["nom"] for c in candidats}
    blocs = ""
    for v in votes_t:
        groupes = {}
        for c in candidats:
            etat_v = etats.get((c["slug"], v["id"]), "a_importer")
            groupes.setdefault(etat_v, []).append(c["slug"])
        lignes_groupes = ""
        for etat_v in ORDRE_ETATS:
            if etat_v not in groupes:
                continue
            noms = ", ".join(
                f'<a href="../../candidats/{s}/">{e(par_slug[s])}</a>' for s in groupes[etat_v])
            lignes_groupes += f"<li>{badge_etat(etat_v)} {noms}</li>"
        # Nuances attribuées et sourcées pour ce vote.
        lignes_nuances = ""
        for c in candidats:
            nuance = nuances.get((c["slug"], v["id"]))
            if nuance:
                lignes_nuances += (f'<li><strong>{e(par_slug[c["slug"]])}</strong> — {e(nuance[0])} '
                                   f'(<a href="{e(nuance[1])}" rel="noopener">source</a>)</li>')
        nuances_html = (f'<p class="titre-nuances">Justifications (position déclarée, rapportée et sourcée) :</p>'
                        f'<ul class="nuances">{lignes_nuances}</ul>') if lignes_nuances else ""
        # Décomptes officiels par groupe parlementaire, repliés par défaut ;
        # chaque groupe porte, si elle existe, sa justification sourcée.
        groupes_v = groupes_par_vote.get(v["id"], [])
        groupes_html = ""
        if groupes_v:
            lignes_g = ""
            n_just = 0
            for g in groupes_v:
                j = justifs_groupes.get((v["id"], g["abrege"]))
                if j:
                    n_just += 1
                    just_html = (f'<p class="groupe-justif">{e(j[0])} '
                                 f'(<a href="{e(j[1])}" rel="noopener">source</a>)</p>')
                else:
                    just_html = ""
                lignes_g += f"<li>{chip_groupe(g, v['est_censure'])}{just_html}</li>"
            sous_titre = (" · pourquoi, pour les groupes qui l'ont expliqué"
                          if n_just else "")
            groupes_html = (f'<details class="groupes-votes"><summary>Comment ont voté les groupes '
                            f'({len(groupes_v)}){sous_titre}</summary><ul>{lignes_g}</ul></details>')
        res_txt = resultat_texte(v) or "\u2014"
        blocs += f"""<article class="vote-carte vote-carte-theme">
<div class="ap-rail rail-neutre rail-resultat"><span class="pos-res">{e(res_txt)}</span></div>
<div class="ap-corps">
<h2 class="ap-titre">{e(v['titre'])}</h2>
<p class="ap-resume">{e(v['resume'])} <a href="{e(v['source_resume'])}" rel="noopener">Scrutin officiel \u2192</a></p>
{sens_html(v)}
{f'<p class="vote-contexte">{e(v["contexte"])}</p>' if v['contexte'] else ''}
<ul class="groupes-etat">{lignes_groupes}</ul>
{senat_theme(v["id"], equiv_senat, par_slug)}
{groupes_html}
{nuances_html}
</div>
</article>"""
    contenu = f"""
<nav class="fil"><a href="../">← Tous les thèmes</a></nav>
<h1>{e(t['libelle'])}</h1>
<p class="note-methode">Positions issues des scrutins officiels importés. « Non concerné » : pas en poste
dans la chambre à la date du scrutin ; « indisponible » : jamais parlementaire ; « absent (déduit) » :
mandat actif mais aucune mention au scrutin ; « à importer » : donnée pas encore chargée (ex. Sénat).</p>
{blocs}"""
    return page(t["libelle"], "Thèmes", contenu, 2, meta)


def page_comparer(meta):
    # JS en chaîne simple (pas d'f-string) : les accolades sont littérales.
    contenu = """
<h1>Comparer deux candidats</h1>
<p>Sur les <strong>votes clés</strong>, thème par thème — à l'Assemblée, au Sénat et au Parlement
européen. Chaque candidat est comparé <strong>au plus précis</strong> : son vote personnel s'il a voté,
sinon la position de son parti — clairement marquée. Ainsi deux candidats restent comparables même
lorsqu'ils n'ont pas siégé aux mêmes moments.</p>
<div class="comparateur">
  <label>Candidat A <select id="sel-a"></select></label>
  <label>Candidat B <select id="sel-b"></select></label>
</div>
<div class="mode-compare filtre-compare" role="group" aria-label="Filtrer les votes affichés">
  <button type="button" data-filtre="comparable" class="actif" aria-pressed="true">Votes comparables</button>
  <button type="button" data-filtre="tous" aria-pressed="false">Tous les votes clés</button>
</div>
<p class="note-methode" id="note-mode"></p>
<div id="resultat"></div>
<script>
fetch("../data.json").then(function (r) { return r.json(); }).then(function (d) {
  var selA = document.getElementById("sel-a"), selB = document.getElementById("sel-b");
  d.candidats.forEach(function (c) {
    var o = document.createElement("option");
    o.value = c.slug; o.textContent = c.nom;
    selA.appendChild(o.cloneNode(true)); selB.appendChild(o.cloneNode(true));
  });
  selB.selectedIndex = Math.min(1, selB.options.length - 1);
  var filtre = "comparable";
  function brancher(sel, set) {
    var bs = document.querySelectorAll(sel + " button");
    bs.forEach(function (b) {
      b.addEventListener("click", function () {
        set(b.dataset);
        bs.forEach(function (x) { x.classList.remove("actif"); x.setAttribute("aria-pressed", "false"); });
        b.classList.add("actif"); b.setAttribute("aria-pressed", "true");
        rendre();
        var res = document.getElementById("resultat");
        if (res && res.scrollIntoView) res.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }
  brancher(".filtre-compare", function (ds) { filtre = ds.filtre; });

  // Vue unique : pour chaque candidat, le niveau le plus précis disponible —
  // vote personnel s'il a voté, sinon position de son groupe (étiquetée).
  function infoDe(slug, vid) {
    var e = (d.positions[slug] || {})[vid] || {};
    var pos = e.perso || e.parti || null;
    var niveau = e.perso ? "perso" : (e.parti ? "parti" : null);
    // Justification visible dans tous les cas : la nuance personnelle si elle
    // existe, sinon celle du parti (même quand on affiche le vote personnel).
    var just = e.nuance || e.justif_parti || null;
    var justParti = (!e.nuance && !!e.justif_parti);
    return { pos: pos, niveau: niveau, just: just, justParti: justParti };
  }
  var RAILCLS = { pour: "rail-pour", contre: "rail-contre", abstention: "rail-abst" };
  function banniere(surnom, info) {
    var cls = info.pos ? RAILCLS[info.pos] : "rail-neutre";
    var mot = info.pos ? d.libelles[info.pos][0] : "Aucune donnée";
    var tag = (info.niveau === "parti") ? '<span class="cmp-ban-tag">position du parti</span>' : '';
    return '<div class="cmp-ban ' + cls + '"><span class="cmp-ban-qui">' + surnom + tag
      + '</span><span class="cmp-ban-pos">' + mot + '</span></div>';
  }
  function justifDe(surnom, info) {
    if (!info.just) return "";
    var etiq = info.justParti ? (surnom + " — son parti") : surnom;
    return '<p class="cmp-nuance"><strong>' + etiq + '</strong> — ' + info.just[0]
      + ' (<a href="' + info.just[1] + '" rel="noopener">source</a>)</p>';
  }

  function rendre() {
    var a = selA.value, b = selB.value, res = document.getElementById("resultat");
    document.getElementById("note-mode").textContent =
      "Vue unique : chaque candidat au niveau le plus précis disponible — son vote personnel s'il a voté, "
      + "sinon la position majoritaire de son groupe (marquée « position du parti »). "
      + "« Aucune donnée » = ni vote personnel ni parti rattaché pour ce scrutin.";
    res.textContent = "";
    if (a === b) { res.textContent = "Choisissez deux candidats différents."; return; }
    var objA = d.candidats.find(function (c) { return c.slug === a; });
    var objB = d.candidats.find(function (c) { return c.slug === b; });
    var nomA = objA.nom, nomB = objB.nom;
    var surA = objA.nom_famille || nomA, surB = objB.nom_famille || nomB;

    var totComp = 0, totAcc = 0;
    var sections = document.createElement("div");
    d.themes.forEach(function (theme) {
      var votesT = d.votes.filter(function (v) { return v.theme === theme; });
      var comp = 0, acc = 0, cartes = "";
      votesT.forEach(function (v) {
        var ia = infoDe(a, v.id), ib = infoDe(b, v.id);
        var pa = ia.pos, pb = ib.pos;
        var comparable = pa && pb;
        var diverge = comparable && pa !== pb;
        if (comparable) { comp++; if (pa === pb) acc++; }
        if (filtre === "comparable" && !pa && !pb) return;
        // Classe d'etat conservee pour la teinte de la carte, mais sans libelle
        // texte : la concordance pour/contre des deux bannieres suffit (redondant).
        var etat = diverge ? "diverge" : (comparable ? "accord" : "incomp");
        var sens = (v.sens_pour && v.sens_contre)
          ? '<p class="sens-vote"><span class="sens-part sens-p"><span class="sens-mot">Pour</span> = '
            + v.sens_pour + '</span><span class="sens-part sens-c"><span class="sens-mot">Contre</span> = '
            + v.sens_contre + '</span></p>'
          : '';
        cartes += '<article class="cmp-vote ' + etat + '">'
          + '<div class="cmp-tete"><span class="cmp-titre">' + v.titre + '</span>'
          + '<span class="cmp-chambre">' + v.chambre + '</span></div>'
          + '<p class="cmp-desc-texte">' + v.resume + '</p>'
          + sens
          + '<div class="cmp-bannieres">' + banniere(surA, ia) + banniere(surB, ib) + '</div>'
          + justifDe(surA, ia) + justifDe(surB, ib)
          + '</article>';
      });
      totComp += comp; totAcc += acc;
      if (!cartes) return;
      var resume = comp ? (acc + " accord" + (acc > 1 ? "s" : "") + " / " + comp + " comparable" + (comp > 1 ? "s" : "")) : "aucun vote comparable";
      sections.innerHTML += '<section class="cmp-theme"><h2>' + theme + ' <span class="cmp-compte">' + resume + '</span></h2>' + cartes + '</section>';
    });

    var pct = totComp ? Math.round(100 * totAcc / totComp) : 0;
    var entete = document.createElement("div");
    entete.className = "resultat-comparaison";
    entete.innerHTML = '<p><strong>' + nomA + '</strong> et <strong>' + nomB + '</strong> '
      + '(vote personnel ou, à défaut, position du parti) :</p>'
      + (totComp
          ? '<p class="grand-chiffre">' + pct + ' %</p><p>de positions identiques sur <strong>'
            + totComp + '</strong> votes clés comparables (' + totAcc + ' accords).</p>'
          : '<p>Aucun vote clé comparable entre ces deux candidats.</p>')
      + '<p><a href="../candidats/' + a + '/">Fiche ' + nomA + '</a> · <a href="../candidats/' + b + '/">Fiche ' + nomB + '</a></p>';
    res.appendChild(entete);
    res.appendChild(sections);
  }
  selA.addEventListener("change", rendre); selB.addEventListener("change", rendre);
  rendre();
});
</script>"""
    return page("Comparer", "Comparer", contenu, 1, meta)

def page_methode(meta, noms):
    contenu = f"""
<h1>Méthode</h1>
<h2>Trois principes non négociables</h2>
<p>Sur un site qui parle de personnes réelles en campagne, la crédibilité est la seule valeur. Ces règles priment sur tout le reste.</p>
<ul class="methode-liste">
<li><strong>Sources — tout est sourcé.</strong> Chaque fait renvoie à un document officiel vérifiable en un clic. Un fait sans source ne s'affiche pas.</li>
<li><strong>Neutralité — aucune éditorialisation.</strong> Méthodologie publique et identique pour tous. « A voté contre », jamais « a trahi ».</li>
<li><strong>Honnêteté sur les manques.</strong> Des états d'affichage clairs — jamais de vide ambigu, jamais de supposition.</li>
</ul>
<h2>D'où viennent les données</h2>
<ul class="methode-liste">
<li><strong>Scrutins et positions de vote</strong> : dumps officiels de
<a href="https://data.assemblee-nationale.fr">data.assemblee-nationale.fr</a> (licence ouverte),
législatures 14 à 17 (juillet 2012 → juillet 2026), y compris le Congrès de Versailles.
Chaque fichier est archivé avec son empreinte avant transformation ; chaque import est journalisé.</li>
<li><strong>Identités et mandats</strong> : référentiel officiel « acteurs, mandats, organes » de
l'Assemblée nationale (précision au jour), complété par les déclarations HATVP pour les fonctions
non couvertes. Appariement par nom, prénom et date de naissance — jamais par le nom seul.</li>
<li><strong>Candidatures</strong> : déclarations publiques recensées par la presse, recoupées entre
plusieurs sources, chacune datée et reliée à sa source. La liste officielle n'existera qu'après
validation des parrainages par le Conseil constitutionnel (mars 2027).</li>
<li><strong>Sénat et Parlement européen</strong> : à importer — indiqué comme tel sur les fiches concernées.</li>
</ul>
<h2>Les quatre états d'affichage</h2>
<p>Chaque case affiche toujours l'un de ces états — jamais un vide ambigu, jamais une valeur supposée :</p>
<ul class="methode-liste">
<li><strong>Position connue</strong> : pour / contre / abstention / non-votant, telle que publiée au scrutin officiel.</li>
<li><strong>Non concerné</strong> : la personne n'était pas en poste dans la chambre à la date du scrutin.</li>
<li><strong>Indisponible</strong> : la personne n'a jamais été parlementaire — il n'existe pas de vote à afficher.</li>
<li><strong>À importer</strong> : la donnée existe mais n'est pas encore chargée.</li>
</ul>
<h2>Les pastilles des candidats</h2>
<p>Tous les candidats n'ont pas le même historique traçable — un député cumule des milliers de scrutins, un maire n'en a aucun. Sur chaque fiche, une pastille dit d'emblée ce que l'on peut montrer :</p>
<ul class="methode-liste">
<li><span class="pastille pastille-ok">Votes disponibles</span> — le candidat était en poste et a voté : ses positions réelles sont consultables.</li>
<li><span class="pastille pastille-partiel">Couverture partielle</span> — mandats hors de la période couverte, ou chambre pas encore importée (Sénat, Parlement européen).</li>
<li><span class="pastille pastille-decl">Positions déclaratives</span> — jamais parlementaire : ses positions viendront de ses déclarations publiques, clairement identifiées comme telles.</li>
</ul>
<h2>Ce que veulent dire « absent » et « non-votant »</h2>
<p>L'Assemblée nationale ne publie jamais la liste des absents : un élu est compté <strong>absent (déduit)</strong>
si son mandat était actif à la date du scrutin et qu'il n'apparaît dans aucune liste de votants.
Cette déduction est désactivée sur les scrutins dont les totaux publiés présentent un écart avec les
listes nominatives, et sur la partie des scrutins ordinaires de la 14e législature (2012-2017) où
l'Assemblée ne publiait que la position de chaque groupe et les votes dissidents — on importe alors
ces positions explicites, mais on ne déduit ni « suivi du groupe » ni absence. <strong>Non-votant</strong> signifie présent sans prendre part au vote
(par exemple la présidence de séance) — ce n'est pas une absence.</p>
<h2>La position du parti d'un candidat</h2>
<p>Pour chaque vote clé, le site affiche aussi comment a voté le <strong>groupe parlementaire du parti</strong>
du candidat — utile quand le candidat lui-même n'était pas en poste ou n'a pas voté. Cette position n'est
jamais un « oui/non » décrété : c'est la répartition réelle des voix du groupe (pour, contre, abstention),
extraite du même scrutin officiel, avec la tendance majoritaire mise en avant — « partagé » en cas d'égalité.
Cas particulier des motions de censure : l'Assemblée n'enregistre que les voix pour ; ne pas voter est la
manière de ne pas soutenir la censure. On affiche donc le nombre de voix apportées par chaque groupe, et
aucune absence individuelle n'est déduite de ces scrutins.
Le rattachement candidat → groupe suit une table publiée dans le code source (parti → groupe, par
législature) qui ne couvre que les cas nets ; un candidat dont le parti n'a pas de groupe à l'Assemblée
est affiché comme tel, avec l'explication : ainsi le RN, avec 8 députés élus en 2017 — sous le minimum
de 15 requis pour former un groupe —, n'a aucun décompte officiel de groupe sur la législature 2017-2022,
et Horizons n'existait pas avant octobre 2021. Au Congrès de Versailles, les groupes du Sénat ne sont pas encore identifiés dans
notre référentiel et apparaissent comme « non identifiés ».</p>
<h2>Justifications de vote</h2>
<p>Sous certains votes clés figure une <strong>justification</strong> : l'explication du vote telle qu'elle a été
<strong>déclarée et publiée</strong> par l'intéressé ou son groupe (explication de vote officielle, communiqué,
compte rendu de séance, presse). Elle est toujours <strong>reliée à sa source</strong> ; le site la rapporte
sans la juger ni l'endosser. Quand aucune justification publique n'est trouvée, <strong>aucune n'est affichée</strong> —
jamais une explication inventée. Certaines formations en publient beaucoup (fiches de vote détaillées), d'autres
très peu : la couverture est donc, à ce stade, <strong>inégale selon les partis</strong> — un reflet de ce qui est
publiquement disponible, pas un choix éditorial. Pour un vote au Parlement européen où le candidat ne siégeait pas,
la justification affichée est celle de sa <strong>délégation</strong>, indiquée comme telle.</p>
<p>Deux niveaux de justification coexistent : celle d'une <strong>personne</strong> (rare, réservée aux votes
contre-intuitifs) et celle d'un <strong>groupe parlementaire</strong> — pourquoi tel parti a voté pour ou contre.
Cette dernière figure sous « Comment ont voté les groupes » (page d'un thème) et sur la fiche d'un candidat, sous
la position de son parti. Elle vise en priorité les lois où les familles politiques <strong>divergent nettement</strong>,
et couvre, quand la source existe, plusieurs partis — pas seulement les deux qui s'opposent le plus.</p>
<h2>Votes clés : la grille avant les votes</h2>
<p>Aucun vote clé commenté n'est affiché tant que la grille de sélection (critères objectifs, publics,
appliqués identiquement à tous) n'est pas publiée ici. Les résumés seront descriptifs et neutres,
chacun relié au dossier législatif officiel.</p>
<h2>Volet judiciaire</h2>
<p>Renseigné manuellement, fait par fait, uniquement à partir de documents publics sourcés, avec mention
systématique de la présomption d'innocence pour toute procédure en cours. Aucun croisement automatique
de bases judiciaires (les décisions en open data sont pseudonymisées ; ce croisement serait illégal).</p>
<h2>Corrections</h2>
<p>Une donnée vous semble fausse ? Ouvrez un signalement sur
<a href="https://github.com/Mlolita26/le-vrai-vote/issues">le dépôt public</a> avec le lien de la source :
toute correction est tracée.</p>
{credits_photos_html(noms)}"""
    return page("Méthode", "Méthode", contenu, 1, meta)


def credits_photos_html(noms):
    """Crédits des portraits (licences libres Wikimedia — attribution obligatoire)."""
    chemin = WEB / "photos" / "credits.json"
    if not chemin.exists():
        return ""
    credits = json.loads(chemin.read_text(encoding="utf-8"))
    if not credits:
        return ""
    lignes = "".join(
        f'<li>{e(noms.get(slug, slug))} — photo : {e(c["auteur"])}, '
        f'licence {e(c["licence"])} (<a href="{e(c["page"])}" rel="noopener">Wikimedia Commons</a>)</li>'
        for slug, c in sorted(credits.items()))
    return f"""<h2>Crédits des portraits</h2>
<p>Les portraits proviennent de Wikimedia Commons, sous licence libre ; les candidats sans
photographie librement réutilisable sont représentés par leurs initiales.</p>
<ul class="methode-liste credits-photos">{lignes}</ul>"""


# ── Génération ───────────────────────────────────────────────────────────────

def generer(base):
    (candidats, themes, votes_cles, etats, nuances, justifs_groupes,
     groupes_par_vote, groupe_du_candidat, equiv_senat, meta) = charger(base)
    # Ordre stratégique : candidats principaux en tête (se propage à l'accueil,
    # à la liste et au comparateur, qui consomment tous cette liste ordonnée).
    _rang = {slug: i for i, slug in enumerate(CANDIDATS_PRIORITAIRES)}
    candidats.sort(key=lambda c: (_rang.get(c["slug"], len(_rang)), c["nom"]))
    (WEB / "candidats").mkdir(parents=True, exist_ok=True)
    (WEB / "comparer").mkdir(exist_ok=True)
    (WEB / "methode").mkdir(exist_ok=True)

    (WEB / "index.html").write_text(page_accueil(candidats, meta), encoding="utf-8")
    (WEB / "candidats" / "index.html").write_text(page_liste(candidats, meta), encoding="utf-8")
    for p in candidats:
        dossier = WEB / "candidats" / p["slug"]
        dossier.mkdir(exist_ok=True)
        (dossier / "index.html").write_text(
            fiche_candidat(p, themes, votes_cles, etats, nuances, justifs_groupes,
                           groupes_par_vote, groupe_du_candidat, equiv_senat, meta), encoding="utf-8")
    # Les pages « thème » autonomes ont été retirées (juillet 2026) : les thèmes
    # restent comme regroupement sur chaque fiche candidat et dans le comparateur,
    # mais une page thème isolée portait trop d'information sans pouvoir montrer
    # toutes les justifications. Les fonctions page_theme/page_themes_index sont
    # conservées (non appelées) au cas où.
    (WEB / "comparer" / "index.html").write_text(page_comparer(meta), encoding="utf-8")
    (WEB / "methode" / "index.html").write_text(
        page_methode(meta, {c["slug"]: c["nom"] for c in candidats}), encoding="utf-8")

    libelles_themes = {t["id"]: t["libelle"] for t in themes}
    (WEB / "data.json").write_text(json.dumps({
        "candidats": [{"slug": c["slug"], "nom": c["nom"], "nom_famille": c["nom_famille"]}
                      for c in candidats],
        "themes": [t["libelle"] for t in themes],
        "votes": [{"id": str(v["id"]), "titre": v["titre"], "resume": v["resume"],
                   "theme": libelles_themes[v["thematique_id"]],
                   "chambre": CHAMBRE_LABEL.get(v["chambre"], v["chambre"]),
                   "sens_pour": v.get("sens_pour"), "sens_contre": v.get("sens_contre"),
                   "date": v["date"]} for v in votes_cles],
        "positions": positions_comparaison(candidats, votes_cles, etats, nuances, justifs_groupes, equiv_senat,
                                           groupes_par_vote, groupe_du_candidat),
        "libelles": {"pour": ["Pour", "badge-pour"], "contre": ["Contre", "badge-contre"],
                     "abstention": ["Abstention", "badge-abstention"]},
        "meta": meta,
    }, ensure_ascii=False), encoding="utf-8")

    print(f"Site généré : accueil + {len(candidats)} fiches + comparer/methode "
          f"(pages thème retirées). {len(votes_cles)} votes clés. Comparateur : vue unique.")


if __name__ == "__main__":
    generer(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

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


def chip_groupe(g, est_censure=False):
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
        positions = dict(cur.execute(
            "SELECT position, COUNT(*) FROM positions_vote WHERE personne_id=? "
            "GROUP BY position", (pid,)).fetchall())
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
            "slug": c["slug"], "nom": f"{c['prenom']} {c['nom']}",
            "naissance": c["naissance"], "statut": c["statut"],
            "date_declaration": c["date"], "detail": c["detail"],
            "parti": c["detail"].split(" — ")[0].split(",")[0],
            "source": c["source_url"], "mandats": mandats,
            "positions": positions, "solennels": solennels, "exprimes": exprimes,
        })

    themes = [dict(t) for t in cur.execute(
        "SELECT id, libelle, ordre FROM thematiques ORDER BY ordre")]
    votes_cles = [dict(v) for v in cur.execute(
        "SELECT vc.id, vc.thematique_id, vc.titre, vc.resume, vc.source_resume, "
        "vc.contexte, s.date, s.chambre, s.legislature, s.objet, s.sort, s.total_pour, "
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
    etats = {(slug_p, vid): etat for slug_p, vid, etat in cur.execute(
        "SELECT personne_slug, vote_cle_id, etat FROM couverture")}
    # Nuances : explication sourcée d'un vote contre-intuitif, par (personne, vote clé).
    nuances = {(slug_p, vid): (texte, url) for slug_p, vid, texte, url in cur.execute(
        "SELECT p.slug, vc.id, n.texte, src.url FROM nuances n "
        "JOIN personnes p ON p.id = n.personne_id "
        "JOIN votes_cles vc ON vc.scrutin_id = n.scrutin_id "
        "JOIN sources src ON src.id = n.source_id")}

    meta = {
        "genere_le": date.today().isoformat(),
        "n_scrutins": cur.execute("SELECT COUNT(*) FROM scrutins").fetchone()[0],
        "candidats_maj": "23/07/2026",
    }
    con.close()
    return candidats, themes, votes_cles, etats, nuances, groupes_par_vote, groupe_du_candidat, meta


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
    nav_items = [("", "Accueil"), ("candidats/", "Candidats"), ("themes/", "Thèmes"),
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


def badges_positions(p):
    d = p["positions"]
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
    n_expr = sum(v for k, v in p["positions"].items() if k in ("pour", "contre", "abstention"))
    a_mandat_parl = any(m["type"] in ("depute", "senateur", "eurodepute") for m in p["mandats"])
    est_senateur = any(m["type"] == "senateur" for m in p["mandats"])
    est_eurodepute = any(m["type"] == "eurodepute" for m in p["mandats"])
    est_depute = any(m["type"] == "depute" for m in p["mandats"])
    if n_expr >= SEUIL_COMPARABLE:
        return "couvert", f"{n_expr:,} votes exprimés en base".replace(",", " ")
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
<div><div class="stat-num">{nombre_fr(meta['n_scrutins'])}</div><div class="stat-lbl">scrutins officiels en base</div></div>
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

<section class="bloc">
<h2>Trois principes non négociables</h2>
<p class="intro">Sur un site qui parle de personnes réelles en campagne, la crédibilité est la seule valeur. Ces règles priment sur tout le reste.</p>
<div class="principes">
<div class="principe"><div class="principe-num">01 — Sources</div><h3>Tout est sourcé</h3><p>Chaque fait renvoie à un document officiel vérifiable en un clic. Un fait sans source ne s'affiche pas.</p></div>
<div class="principe"><div class="principe-num">02 — Neutralité</div><h3>Aucune éditorialisation</h3><p>Méthodologie publique et identique pour tous. « A voté contre », jamais « a trahi ».</p></div>
<div class="principe"><div class="principe-num">03 — Honnêteté</div><h3>Honnêteté sur les manques</h3><p>Trois états d'affichage clairs — jamais de vide ambigu, jamais de supposition.</p></div>
</div>
</section>

<section class="bloc">
<div class="etats-panel">
<h2>Trois états</h2>
<p>Tous les candidats n'ont pas le même historique traçable — un député cumule des milliers de scrutins, un maire n'en a aucun. Chaque pastille dit exactement ce que l'on sait, et ce que l'on ne sait pas.</p>
<div class="etats-grid">
<div class="etat-item"><span class="pastille pastille-ok">Votes disponibles</span><p>Le candidat était en poste et a voté. Ses positions réelles sont consultables dès maintenant.</p></div>
<div class="etat-item"><span class="pastille pastille-partiel">Couverture partielle</span><p>Mandats hors de la période couverte, ou chambre pas encore importée (Sénat, Parlement européen).</p></div>
<div class="etat-item"><span class="pastille pastille-decl">Positions déclaratives</span><p>Jamais parlementaire : ses positions viendront de ses déclarations publiques, clairement identifiées comme telles.</p></div>
</div>
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


def fiche_candidat(p, themes, votes_cles, etats, nuances, groupes_par_vote, groupe_du_candidat, meta):
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
    positions_html = badges_positions(p) or f'<p class="couverture couverture-{etat}">{e(phrase)}</p>'

    # Votes clés groupés par thème, avec l'état calculé de ce candidat.
    votes_html = ""
    for t in themes:
        votes_t = [v for v in votes_cles if v["thematique_id"] == t["id"]]
        if not votes_t:
            continue
        slug_t = THEME_SLUGS[t["libelle"]]
        lignes = ""
        for v in votes_t:
            etat_v = etats.get((p["slug"], v["id"]), "a_importer")
            nuance = nuances.get((p["slug"], v["id"]))
            nuance_html = (f'<p class="vote-nuance">Nuance : {e(nuance[0])} '
                           f'(<a href="{e(nuance[1])}" rel="noopener">source</a>)</p>' if nuance else "")
            # Position du groupe parlementaire du parti du candidat (même quand
            # lui-même n'a pas voté : absent, non concerné, indisponible…).
            groupe_html = ""
            abrege = groupe_du_candidat.get((p["slug"], v["legislature"]))
            if abrege:
                g = next((x for x in groupes_par_vote.get(v["id"], []) if x["abrege"] == abrege), None)
                if g:
                    groupe_html = (f'<p class="ligne-groupe">Son parti — groupe '
                                   f'{chip_groupe(g, v["est_censure"])}</p>')
            elif any(cle[0] == p["slug"] for cle in groupe_du_candidat):
                explication = SANS_GROUPE.get(
                    (p["slug"], v["legislature"]),
                    "Son parti n'avait pas de groupe à l'Assemblée sur cette législature : "
                    "aucun décompte officiel de groupe n'existe pour ce scrutin.")
                groupe_html = f'<p class="ligne-groupe ligne-groupe-absente">{e(explication)}</p>'
            lignes += f"""<li class="vote-cle">
<div class="vote-tete"><strong>{e(v['titre'])}</strong> {chip_resultat(v)} {badge_etat(etat_v)}</div>
{groupe_html}
<p class="vote-resume">{e(v['resume'])}
<a href="{e(v['source_resume'])}" rel="noopener">scrutin officiel du {date_fr(v['date'])}</a></p>
{nuance_html}
{f'<p class="vote-contexte">{e(v["contexte"])}</p>' if v['contexte'] else ''}
</li>"""
        votes_html += (f'<h3><a href="../../themes/{slug_t}/">{e(t["libelle"])}</a></h3>'
                       f'<ul class="votes-cles">{lignes}</ul>')

    contenu = f"""
<nav class="fil"><a href="../">← Tous les candidats</a></nav>
<div class="fiche-tete">{avatar(p, "../../").replace('width="42" height="42"', 'width="72" height="72"')}
<div><h1>{e(p['nom'])}</h1>
<p class="detail">{e(p['detail'])}</p></div></div>
<p>{statut} {e(declaration)} — <a href="{e(p['source'])}" rel="noopener">source de la déclaration</a>.
{f"Né(e) le {date_fr(p['naissance'])} (source : open data officiel)." if p['naissance'] else "Date de naissance : à importer."}</p>
<h2>Votes clés par thème</h2>
<p class="note-methode">Sélection selon la <a href="../../methode/">grille de critères publiée</a>, identique
pour tous les candidats. « Non concerné » : pas en poste dans la chambre à la date du scrutin ;
« absent (déduit) » : mandat actif mais aucune mention au scrutin officiel.</p>
{votes_html}
<h2>Mandats (sources officielles, datés)</h2>
<ul class="mandats">{mandats_html}</ul>
<h2>Ensemble des positions de vote — Assemblée nationale, 2012-2026</h2>
{positions_html}
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


def page_theme(t, votes_t, candidats, etats, nuances, groupes_par_vote, meta):
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
        nuances_html = (f'<p class="titre-nuances">Nuances (explications de vote rapportées, sourcées) :</p>'
                        f'<ul class="nuances">{lignes_nuances}</ul>') if lignes_nuances else ""
        # Décomptes officiels par groupe parlementaire, repliés par défaut.
        groupes_v = groupes_par_vote.get(v["id"], [])
        groupes_html = ""
        if groupes_v:
            lignes_g = "".join(f"<li>{chip_groupe(g, v['est_censure'])}</li>" for g in groupes_v)
            groupes_html = (f'<details class="groupes-votes"><summary>Comment ont voté les groupes '
                            f'({len(groupes_v)})</summary><ul>{lignes_g}</ul></details>')
        blocs += f"""<article class="vote-cle vote-cle-page">
<h2>{e(v['titre'])}</h2>
<p class="resultat-ligne">{chip_resultat(v)}</p>
<p class="vote-resume">{e(v['resume'])}
<a href="{e(v['source_resume'])}" rel="noopener">scrutin officiel du {date_fr(v['date'])}</a></p>
{f'<p class="vote-contexte">{e(v["contexte"])}</p>' if v['contexte'] else ''}
<ul class="groupes-etat">{lignes_groupes}</ul>
{groupes_html}
{nuances_html}
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
    contenu = """
<h1>Comparer deux candidats</h1>
<p>Sur les scrutins de l'Assemblée nationale où les deux candidats ont exprimé un vote
(pour, contre ou abstention), quelle proportion de positions identiques ?</p>
<p class="note-methode">Seuls les candidats ayant au moins 30 votes exprimés dans la période couverte
apparaissent ici. Le taux est calculé uniquement sur les scrutins communs — il ne dit rien des textes
sur lesquels un seul des deux a voté. Les absences et « non-votant » sont exclus du calcul.</p>
<div class="comparateur">
  <label>Candidat A <select id="sel-a"></select></label>
  <label>Candidat B <select id="sel-b"></select></label>
</div>
<div id="resultat"></div>
<script>
fetch("../data.json").then(r => r.json()).then(d => {
  const selA = document.getElementById("sel-a"), selB = document.getElementById("sel-b");
  for (const sel of [selA, selB])
    for (const slug of d.comparables) {
      const o = document.createElement("option");
      o.value = slug; o.textContent = d.noms[slug];
      sel.appendChild(o.cloneNode(true));
    }
  selB.selectedIndex = Math.min(1, selB.options.length - 1);
  function rendre() {
    const a = selA.value, b = selB.value, res = document.getElementById("resultat");
    res.textContent = "";
    if (a === b) { res.textContent = "Choisissez deux candidats différents."; return; }
    const cle = [a, b].sort().join("|");
    const paire = d.concordances[cle];
    if (!paire) { res.textContent = "Trop peu de scrutins communs pour une comparaison honnête."; return; }
    const pct = (100 * paire.accord / paire.communs).toFixed(1).replace(".", ",");
    const h = document.createElement("div");
    h.className = "resultat-comparaison";
    h.innerHTML = `<p><strong>${d.noms[a]}</strong> et <strong>${d.noms[b]}</strong> ont exprimé un vote
      sur <strong>${paire.communs.toLocaleString("fr-FR")}</strong> scrutins communs.</p>
      <p class="grand-chiffre">${pct} %</p>
      <p>de positions identiques (${paire.accord.toLocaleString("fr-FR")} scrutins sur ${paire.communs.toLocaleString("fr-FR")}).</p>
      <p><a href="../candidats/${a}/">Fiche ${d.noms[a]}</a> · <a href="../candidats/${b}/">Fiche ${d.noms[b]}</a></p>`;
    res.appendChild(h);

    // Détail vote clé par vote clé, divergences signalées.
    const exprimes = new Set(["pour", "contre", "abstention"]);
    const titreVotes = document.createElement("h2");
    titreVotes.textContent = "Vote clé par vote clé";
    res.appendChild(titreVotes);
    const ul = document.createElement("ul");
    ul.className = "votes-cles";
    for (const v of d.votes) {
      const ea = (d.etats[a] || {})[v.id] || "a_importer";
      const eb = (d.etats[b] || {})[v.id] || "a_importer";
      const diverge = exprimes.has(ea) && exprimes.has(eb) && ea !== eb;
      const li = document.createElement("li");
      li.className = "vote-cle" + (diverge ? " divergence" : "");
      li.innerHTML = `<div class="vote-tete"><strong>${v.titre}</strong>
        <span class="detail">${v.theme}</span></div>
        <div class="badges">${badgeHtml(d, ea, d.noms[a])} ${badgeHtml(d, eb, d.noms[b])}</div>`;
      ul.appendChild(li);
    }
    res.appendChild(ul);
  }
  function badgeHtml(d, etat, nom) {
    const [libelle, classe] = d.libelles_etats[etat];
    return `<span class="badge ${classe}">${nom.split(" ").slice(-1)[0]} : ${libelle}</span>`;
  }
  selA.addEventListener("change", rendre); selB.addEventListener("change", rendre);
  rendre();
});
</script>"""
    return page("Comparer", "Comparer", contenu, 1, meta)


def page_methode(meta, noms):
    contenu = f"""
<h1>Méthode</h1>
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
    (candidats, themes, votes_cles, etats, nuances,
     groupes_par_vote, groupe_du_candidat, meta) = charger(base)
    paires, comparables = concordances(candidats)

    (WEB / "candidats").mkdir(parents=True, exist_ok=True)
    (WEB / "themes").mkdir(exist_ok=True)
    (WEB / "comparer").mkdir(exist_ok=True)
    (WEB / "methode").mkdir(exist_ok=True)

    (WEB / "index.html").write_text(page_accueil(candidats, meta), encoding="utf-8")
    (WEB / "candidats" / "index.html").write_text(page_liste(candidats, meta), encoding="utf-8")
    for p in candidats:
        dossier = WEB / "candidats" / p["slug"]
        dossier.mkdir(exist_ok=True)
        (dossier / "index.html").write_text(
            fiche_candidat(p, themes, votes_cles, etats, nuances,
                           groupes_par_vote, groupe_du_candidat, meta), encoding="utf-8")
    (WEB / "themes" / "index.html").write_text(
        page_themes_index(themes, votes_cles, meta), encoding="utf-8")
    for t in themes:
        votes_t = [v for v in votes_cles if v["thematique_id"] == t["id"]]
        dossier = WEB / "themes" / THEME_SLUGS[t["libelle"]]
        dossier.mkdir(exist_ok=True)
        (dossier / "index.html").write_text(
            page_theme(t, votes_t, candidats, etats, nuances, groupes_par_vote, meta), encoding="utf-8")
    (WEB / "comparer" / "index.html").write_text(page_comparer(meta), encoding="utf-8")
    (WEB / "methode" / "index.html").write_text(
        page_methode(meta, {c["slug"]: c["nom"] for c in candidats}), encoding="utf-8")

    libelles_themes = {t["id"]: t["libelle"] for t in themes}
    (WEB / "data.json").write_text(json.dumps({
        "comparables": comparables,
        "noms": {c["slug"]: c["nom"] for c in candidats},
        "concordances": paires,
        "votes": [{"id": v["id"], "titre": v["titre"], "date": v["date"],
                   "theme": libelles_themes[v["thematique_id"]]} for v in votes_cles],
        "etats": {slug: {v["id"]: etats.get((slug, v["id"]), "a_importer") for v in votes_cles}
                  for slug in comparables},
        "libelles_etats": ETATS,
        "meta": meta,
    }, ensure_ascii=False), encoding="utf-8")

    print(f"Site généré : accueil + {len(candidats)} fiches + {len(themes)} pages thème + "
          f"comparer/methode. {len(votes_cles)} votes clés affichés. "
          f"Comparateur : {len(comparables)} candidats, {len(paires)} paires.")


if __name__ == "__main__":
    generer(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

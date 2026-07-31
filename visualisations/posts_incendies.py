"""Carrousel Instagram : les votes sur la prévention des incendies.

Slide 1 : la vue d'ensemble — chaque amendement, chaque candidat, pour ou contre.
Slides suivantes : un amendement par slide, avec ce que « pour » et « contre »
voulaient dire, le résultat du scrutin, et la position de chacun.

Distinction tenue partout, parce qu'elle est le cœur de l'honnêteté du post :

  · pastille pleine    = la personne a voté elle-même
  · pastille cerclée   = aucun vote personnel exprimé (absente, ou pas en
                         poste) ; c'est la position de son parti sur ce
                         scrutin, pas la sienne, et la raison est écrite sous
                         son nom

La règle de repli et le calcul de la position majoritaire sont ceux de
`ingestion/build_site.py` : le post ne peut donc pas contredire le site.

Usage : python visualisations/posts_incendies.py [dossier_sortie]
"""
import sqlite3
import sys
from pathlib import Path

from PIL import ImageDraw

import posts_insta as base
from posts_insta import (ACCENT, BADGES, CARTE, ENCRE, ENCRE_DOUCE, FOND, H, L,
                         LISERE, MARGE, MUTE, capitale, date_fr, entete, fonte,
                         enregistrer, largeur, paragraphe, pied, puce, toile)

SORTIE_DEFAUT = base.DOSSIER / "post_insta" / "incendie"

# Les cinq scrutins de la base portant sur la prévention des incendies, dans
# l'ordre chronologique. Ce sont des amendements — pas des lois : quatre à la
# proposition de loi sur le risque incendie, deux au budget.
VOTES = [129, 130, 131, 132, 133]
CANDIDATS = ["Mélenchon", "Le Pen", "Attal", "Philippe"]

COURT = {"pour": "POUR", "contre": "CONTRE", "abstention": "ABST.",
         "absent": "ABSENT"}
EXPRIMEES = ("pour", "contre", "abstention")


# ------------------------------------------------------------------- lecture
def lire_scrutin(con, vote_id):
    con.row_factory = sqlite3.Row
    return con.execute("""SELECT vc.*, s.id AS sid, s.date, s.sort, s.legislature,
                                 s.chambre, s.objet, t.libelle AS theme
                          FROM votes_cles vc
                          JOIN scrutins s ON s.id = vc.scrutin_id
                          JOIN thematiques t ON t.id = vc.thematique_id
                          WHERE vc.id = ?""", (vote_id,)).fetchone()


def majorite_groupe(compte):
    """Position majoritaire d'un groupe parmi les suffrages exprimés.

    Règle reprise telle quelle de `ingestion/build_site.py`, pour que le post et
    le site ne puissent pas se contredire : la plus votée des trois, et rien du
    tout en cas d'égalité ou d'absence de suffrage exprimé.
    """
    classe = sorted(compte.items(), key=lambda kv: -kv[1])
    if classe[0][1] == 0 or classe[0][1] == classe[1][1]:
        return None
    return classe[0][0]


def etat(con, nom, scrutin):
    """Position à afficher pour une personne sur un scrutin.

    Renvoie (genre, position, parti, motif), genre dans 'perso', 'parti',
    'inconnu'.

    Le site tient qu'une absence n'est pas une position (POS_COMPARABLE) et
    retombe alors sur le groupe du parti — y compris quand la personne était en
    poste mais absente. On applique la même règle, sinon le post afficherait
    « absent » là où le site affiche la position du parti. Le motif garde la
    distinction, pour que la mention écrite sous le nom reste exacte.
    """
    con.row_factory = sqlite3.Row
    ligne = con.execute("""SELECT pv.position FROM positions_vote pv
                           JOIN personnes pe ON pe.id = pv.personne_id
                           WHERE pe.nom = ? AND pv.scrutin_id = ?""",
                        (nom, scrutin["sid"])).fetchone()
    if ligne and ligne["position"] in EXPRIMEES:
        return "perso", ligne["position"], None, None
    motif = "absent" if ligne else "hors"

    groupe = con.execute("""SELECT gr.groupe_abrege FROM groupes_reference gr
                            JOIN personnes pe ON pe.id = gr.personne_id
                            WHERE pe.nom = ? AND gr.legislature = ?""",
                         (nom, str(scrutin["legislature"]))).fetchone()
    if not groupe:
        return "inconnu", None, None, motif
    decompte = con.execute("""SELECT pour, contre, abstention FROM positions_groupes
                              WHERE scrutin_id = ? AND groupe_abrege = ?""",
                           (scrutin["sid"], groupe["groupe_abrege"])).fetchone()
    if not decompte:
        return "inconnu", None, groupe["groupe_abrege"], motif
    compte = {k: decompte[k] or 0 for k in ("pour", "contre", "abstention")}
    position = majorite_groupe(compte)
    if position is None:
        return "inconnu", None, groupe["groupe_abrege"], motif
    return "parti", position, groupe["groupe_abrege"], motif


def nature(scrutin):
    """« Amendement au budget » / « à la loi incendie », d'après l'objet officiel."""
    objet = (scrutin["objet"] or "").lower()
    if "loi de finances" in objet:
        return "Amendement au budget"
    if "risque incendie" in objet or "prévention" in objet:
        return "Amendement à la loi incendie"
    return "Amendement"


# ------------------------------------------------------------------- dessin
def pastille(d, x, y, genre, position, parti, police, hauteur=54, largeur_fixe=None):
    """Pastille de position. Pleine pour un vote personnel, cerclée pour un
    parti, grise pour une absence."""
    if genre == "inconnu":
        fondc, textec, texte = "#f4f4f5", "#3f3f46", "position inconnue"
    else:
        fondc, textec = BADGES[position][0], BADGES[position][1]
        texte = COURT[position] if genre == "perso" else f"{parti} · {COURT[position]}"

    w = largeur_fixe or largeur(d, texte, police) + 40
    if genre == "parti":
        # Cerclée, fond de carte : ce n'est pas le vote de la personne.
        d.rounded_rectangle([x, y, x + w, y + hauteur], radius=10, fill=CARTE,
                            outline=textec, width=2)
    else:
        d.rounded_rectangle([x, y, x + w, y + hauteur], radius=10, fill=fondc)
    d.text((x + 20, y + (hauteur - police.size) // 2 - 1), texte, font=police,
           fill=textec)
    return w


def slide_ensemble(con, scrutins, etats, sortie):
    img, d = toile()
    entete(d, "Écologie et agriculture")
    y = 232
    y = paragraphe(d, "Cinq amendements contre les incendies",
                   fonte(base.SERIF, 68), MARGE, y, L - 2 * MARGE, interligne=1.16)
    y += 12
    d.text((MARGE, y), "Tous rejetés par l'Assemblée nationale.",
           font=fonte(base.SANS_GRAS, 34), fill=ACCENT)
    y += 84

    col = (L - 2 * MARGE - 3 * 16) // 4
    f_tete = fonte(base.SANS_GRAS, 27)
    for i, nom in enumerate(CANDIDATS):
        x = MARGE + i * (col + 16)
        d.rounded_rectangle([x, y, x + col, y + 54], radius=10, fill="#eef0f2")
        d.text((x + 14, y + 15), nom, font=f_tete, fill=ACCENT)
    y += 76

    f_titre, f_date, f_p = (fonte(base.SANS_GRAS, 29), fonte(base.SANS, 24),
                            fonte(base.SANS_GRAS, 22))
    for s in scrutins:
        yb = paragraphe(d, s["titre"].split(" (")[0], f_titre, MARGE, y,
                        L - 2 * MARGE, interligne=1.26)
        d.text((MARGE, yb + 2), f"{nature(s)} · {date_fr(s['date'])}",
               font=f_date, fill=MUTE)
        yb += 40
        for i, nom in enumerate(CANDIDATS):
            genre, position, parti, _ = etats[(s["id"], nom)]
            pastille(d, MARGE + i * (col + 16), yb, genre, position, parti, f_p,
                     hauteur=50, largeur_fixe=col)
        y = yb + 74
        d.line([(MARGE, y - 18), (L - MARGE, y - 18)], fill=LISERE, width=1)

    # Légende : sans elle, une position de parti pourrait passer pour un vote
    # personnel. C'est la précaution la plus importante du post.
    y += 6
    f_l = fonte(base.SANS, 25)
    pastille(d, MARGE, y, "perso", "pour", None, fonte(base.SANS_GRAS, 22), hauteur=44)
    d.text((MARGE + 130, y + 11), "a voté ainsi", font=f_l, fill=ENCRE_DOUCE)
    pastille(d, MARGE + 380, y, "parti", "pour", "LFI", fonte(base.SANS_GRAS, 22),
             hauteur=44)
    d.text((MARGE + 380 + 190, y + 11),
           "position de son parti, faute de vote personnel",
           font=f_l, fill=ENCRE_DOUCE)
    pied(img, d, appel=f"Le détail de chaque vote sur {base.SITE}")
    enregistrer(img, sortie / "01_ensemble.jpg")


def slide_detail(con, s, etats, numero, sortie):
    img, d = toile()
    entete(d, "Écologie et agriculture")
    y = 226
    f = fonte(base.SANS_GRAS, 27)
    w, h = puce(d, MARGE, y, f"{nature(s).upper()} · REJETÉ", f, "#fef2f2", "#7f1d1d")
    y += h + 34
    y = paragraphe(d, s["titre"].split(" (")[0], fonte(base.SERIF, 58), MARGE, y,
                   L - 2 * MARGE, interligne=1.16)
    y += 12
    d.text((MARGE, y), f"Assemblée nationale · {date_fr(s['date'])}",
           font=fonte(base.SANS, 28), fill=MUTE)
    y += 62

    # Le bloc des positions est de hauteur connue : on le réserve d'abord, et le
    # texte se répartit dans ce qui reste. Sans cette réservation, les
    # descriptions les plus longues poussaient les noms hors du cadre.
    haut_positions = 40 + sum(
        96 if etats[(s["id"], nom)][0] == "parti" else 76 for nom in CANDIDATS)
    plancher = H - MARGE - 196
    dispo = plancher - haut_positions - y - 24

    d.text((MARGE, y), "Ce que dit l'amendement",
           font=fonte(base.SANS_GRAS, 28), fill=ACCENT)
    y += 46
    y = base.paragraphe_ajuste(d, s["resume"], base.SANS, MARGE, y,
                               L - 2 * MARGE, dispo * 0.42,
                               couleur=ENCRE_DOUCE)
    y += 30

    # Ce que chaque camp voulait dire.
    for etiquette, texte, fondc, textec, part in (
            ("Voter POUR", capitale(s["sens_pour"]), "#e9f4ec", "#14532d", 0.26),
            ("Voter CONTRE", capitale(s["sens_contre"]), "#fef2f2", "#7f1d1d", 0.15)):
        d.rounded_rectangle([MARGE, y, L - MARGE, y + 4], radius=2, fill=fondc)
        y += 20
        d.text((MARGE, y), etiquette, font=fonte(base.SANS_GRAS, 27), fill=textec)
        y += 42
        y = base.paragraphe_ajuste(d, texte, base.SERIF_REG, MARGE, y,
                                   L - 2 * MARGE, dispo * part,
                                   tailles=(38, 36, 34, 32, 30, 28))
        y += 26

    y = plancher - haut_positions
    d.line([(MARGE, y), (L - MARGE, y)], fill=LISERE, width=2)
    y += 40

    f_nom, f_p = fonte(base.SERIF, 38), fonte(base.SANS_GRAS, 24)
    complet = {r["nom"]: r["entier"] for r in con.execute(
        "SELECT nom, prenom || ' ' || nom AS entier FROM personnes")}
    for nom in CANDIDATS:
        genre, position, parti, motif = etats[(s["id"], nom)]
        d.text((MARGE, y + 8), complet.get(nom, nom), font=f_nom, fill=ENCRE)
        pastille(d, L - MARGE - 300, y, genre, position, parti, f_p,
                 hauteur=52, largeur_fixe=300)
        if genre == "parti":
            raison = ("absent ce jour-là" if motif == "absent"
                      else "n'était pas en poste")
            d.text((MARGE, y + 56), f"{raison} — position de son parti",
                   font=fonte(base.SANS, 23), fill=MUTE)
            y += 96
        else:
            y += 76
    pied(img, d, source=s["source_resume"].replace("https://www.", ""))
    enregistrer(img, sortie / f"{numero:02d}_{s['id']}.jpg")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE_DEFAUT
    sortie.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(base.BASE)

    scrutins = [lire_scrutin(con, v) for v in VOTES]
    scrutins.sort(key=lambda s: s["date"])
    etats = {}
    print("état retenu pour chaque couple (scrutin, personne) :")
    for s in scrutins:
        print(f"  #{s['id']} {s['date']} {s['titre'][:44]}")
        for nom in CANDIDATS:
            e = etat(con, nom, s)
            etats[(s["id"], nom)] = e
            print(f"     {nom:11} {e[0]:8} {str(e[1]):11} {e[2] or ''}")

    print()
    slide_ensemble(con, scrutins, etats, sortie)
    for i, s in enumerate(scrutins, start=2):
        slide_detail(con, s, etats, i, sortie)
    con.close()
    print(f"\n{len(scrutins) + 1} slides de {L} × {H} px → {sortie}")


if __name__ == "__main__":
    main()

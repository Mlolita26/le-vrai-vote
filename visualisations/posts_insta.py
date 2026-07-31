"""Génère des posts Instagram éditoriaux à partir de la base.

Trois formats, tous alimentés par des requêtes — aucun texte n'est saisi ici :

  1. quiz         : « qui a voté pour ? », révélation en deuxième slide
  2. vote         : « un vote, une loi » — fiche pédagogique
  3. comparaison  : deux parlementaires face à face sur une thématique

La charte reprend celle du site (fond ivoire, titres sérif, badges de position),
pour que le post et la page se reconnaissent.

Usage : python visualisations/posts_insta.py [dossier_sortie]
"""
import sqlite3
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
BASE = RACINE / "data" / "levraivote.sqlite"
LOGO = RACINE / "web" / "assets" / "logo.png"
SORTIE_DEFAUT = DOSSIER / "post_insta"

L, H = 1440, 1800          # portrait 4:5, le format le plus haut du fil
MARGE = 96
QUALITE = 97
SITE = "levraivote.fr"

# --- Charte reprise de web/styles.css ---------------------------------------
FOND = "#f6f4ef"
CARTE = "#ffffff"
ENCRE = "#211f1b"
ENCRE_DOUCE = "#5c574c"
LISERE = "#e4dfd5"
MUTE = "#8a8474"
ACCENT = "#1f3a52"

BADGES = {
    "pour": ("#e9f4ec", "#14532d", "A voté pour"),
    "contre": ("#fef2f2", "#7f1d1d", "A voté contre"),
    "abstention": ("#fefce8", "#713f12", "S'est abstenu"),
    "absent": ("#f4f4f5", "#3f3f46", "Absent"),
}
LIBELLE_COURT = {"pour": "Pour", "contre": "Contre",
                 "abstention": "Abstention", "absent": "Absent"}

# Le site utilise Spectral (sérif) et Libre Franklin (sans). À défaut, les
# équivalents système les plus proches.
SERIF = ("Spectral-Bold.ttf", "georgiab.ttf", "georgia.ttf", "DejaVuSerif-Bold.ttf")
SERIF_REG = ("Spectral-Regular.ttf", "georgia.ttf", "DejaVuSerif.ttf")
SANS = ("LibreFranklin-Regular.ttf", "segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")
SANS_GRAS = ("LibreFranklin-SemiBold.ttf", "segoeuib.ttf", "arialbd.ttf",
             "DejaVuSans-Bold.ttf")


def fonte(familles, taille):
    for nom in familles:
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------- primitives
def largeur(dessin, texte, police):
    return dessin.textlength(texte, font=police)


def replier(dessin, texte, police, largeur_max):
    """Découpe un texte en lignes tenant dans `largeur_max`."""
    mots, ligne, lignes = texte.split(), "", []
    for mot in mots:
        essai = f"{ligne} {mot}".strip()
        if largeur(dessin, essai, police) <= largeur_max:
            ligne = essai
        else:
            lignes.append(ligne)
            ligne = mot
    if ligne:
        lignes.append(ligne)
    return lignes


def paragraphe(dessin, texte, police, x, y, largeur_max, interligne=1.42,
               couleur=ENCRE, hauteur_ligne=None):
    """Écrit un texte replié à la largeur donnée. Renvoie le y final."""
    saut = hauteur_ligne or int(police.size * interligne)
    for ligne in replier(dessin, texte, police, largeur_max):
        dessin.text((x, y), ligne, font=police, fill=couleur)
        y += saut
    return y


def paragraphe_ajuste(dessin, texte, familles, x, y, largeur_max, hauteur_max,
                      tailles=(36, 34, 32, 30, 28, 26, 24), interligne=1.36,
                      couleur=ENCRE):
    """Écrit un texte à la plus grande taille qui tienne dans `hauteur_max`.

    Les textes venant de la base vont de 300 à 600 caractères selon le vote :
    une taille fixe déborderait sur les plus longs et laisserait du vide sur les
    plus courts.
    """
    for taille in tailles:
        police = fonte(familles, taille)
        lignes = replier(dessin, texte, police, largeur_max)
        saut = int(taille * interligne)
        if len(lignes) * saut <= hauteur_max:
            break
    for ligne in lignes:
        dessin.text((x, y), ligne, font=police, fill=couleur)
        y += saut
    return y


def puce(dessin, x, y, texte, police, couleur_fond, couleur_texte, rayon=None):
    """Étiquette arrondie. Renvoie sa largeur."""
    pad_x, pad_y = 22, 12
    w = largeur(dessin, texte, police) + 2 * pad_x
    h = police.size + 2 * pad_y
    r = rayon if rayon is not None else h // 2
    dessin.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=couleur_fond)
    dessin.text((x + pad_x, y + pad_y - 1), texte, font=police, fill=couleur_texte)
    return w, h


def toile():
    img = Image.new("RGB", (L, H), FOND)
    return img, ImageDraw.Draw(img)


def entete(dessin, thematique=None):
    """Marque en haut à gauche, thématique à droite."""
    f_marque = fonte(SERIF, 40)
    dessin.text((MARGE, MARGE - 8), "Le Vrai Vote", font=f_marque, fill=ACCENT)
    if thematique:
        f = fonte(SANS_GRAS, 26)
        w, _ = puce(dessin, 0, 0, thematique.upper(), f, FOND, FOND)  # mesure
        puce(dessin, L - MARGE - w, MARGE - 4, thematique.upper(), f,
             "#eef0f2", "#55606b")
    dessin.line([(MARGE, MARGE + 62), (L - MARGE, MARGE + 62)], fill=LISERE, width=2)


def pied(img, dessin, source=None, appel=f"{SITE} — les votes réels, pas les promesses"):
    y = H - MARGE - 40
    f = fonte(SANS, 25)
    if source:
        dessin.text((MARGE, y - 46), f"Source : {source}", font=f, fill=MUTE)
    dessin.text((MARGE, y), appel, font=fonte(SANS_GRAS, 27), fill=ACCENT)
    # Logo en bas à droite : dessiné pour un fond clair, il s'utilise tel quel.
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        logo = logo.crop(logo.getbbox())
        w = 210
        logo = logo.resize((w, round(w * logo.height / logo.width)), Image.LANCZOS)
        img.paste(logo, (L - MARGE - w, H - MARGE - logo.height + 10), logo)


def enregistrer(img, chemin):
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=42, threshold=3))
    img.save(chemin, "JPEG", quality=QUALITE, subsampling=0, optimize=True,
             progressive=True)
    print(f"  {chemin.name}  {chemin.stat().st_size // 1024} ko")


# ------------------------------------------------------------------ requêtes
EXPRIMEES = ("pour", "contre", "abstention")


def lire_vote(con, vote_id):
    con.row_factory = sqlite3.Row
    v = con.execute("""SELECT vc.*, t.libelle theme, s.date, s.chambre, s.sort
                       FROM votes_cles vc
                       JOIN thematiques t ON t.id = vc.thematique_id
                       JOIN scrutins s ON s.id = vc.scrutin_id
                       WHERE vc.id = ?""", (vote_id,)).fetchone()
    positions = con.execute(f"""
        SELECT pe.prenom || ' ' || pe.nom AS nom, pv.position
        FROM positions_vote pv
        JOIN personnes pe ON pe.id = pv.personne_id
        WHERE pv.scrutin_id = ? AND pv.position IN {EXPRIMEES}
        ORDER BY CASE pv.position WHEN 'pour' THEN 0 WHEN 'contre' THEN 1 ELSE 2 END,
                 pe.nom""", (v["scrutin_id"],)).fetchall()
    return v, positions


def lire_comparaison(con, nom_a, nom_b, theme):
    con.row_factory = sqlite3.Row
    return con.execute(f"""
        SELECT vc.titre, s.date,
               MAX(CASE WHEN pe.nom = ? THEN pv.position END) AS a,
               MAX(CASE WHEN pe.nom = ? THEN pv.position END) AS b
        FROM votes_cles vc
        JOIN thematiques t ON t.id = vc.thematique_id
        JOIN scrutins s ON s.id = vc.scrutin_id
        JOIN positions_vote pv ON pv.scrutin_id = vc.scrutin_id
             AND pv.position IN {EXPRIMEES}
        JOIN personnes pe ON pe.id = pv.personne_id
        WHERE t.libelle = ? AND pe.nom IN (?, ?)
        GROUP BY vc.id HAVING a IS NOT NULL AND b IS NOT NULL
        ORDER BY s.date""", (nom_a, nom_b, theme, nom_a, nom_b)).fetchall()


def capitale(texte):
    """Première lettre en majuscule, le reste intact.

    str.capitalize() abaisse tout le reste, ce qui écrasait « Constitution »,
    « Corse » ou « République » en minuscules.
    """
    return texte[:1].upper() + texte[1:] if texte else texte


def date_fr(iso):
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
            "août", "septembre", "octobre", "novembre", "décembre"]
    a, m, j = iso.split("-")
    return f"{int(j)} {mois[int(m) - 1]} {a}"


CHAMBRES = {"an": "Assemblée nationale", "senat": "Sénat",
            "pe": "Parlement européen", "congres": "Congrès"}


# -------------------------------------------------------------- format 1 : quiz
def post_quiz(con, vote_id, sortie):
    v, positions = lire_vote(con, vote_id)
    # Ordre alphabétique sur le nom de famille : trié par position, la liste
    # livrait la réponse avant la révélation.
    noms = sorted((p["nom"] for p in positions),
                  key=lambda n: n.split()[-1].lower())

    # --- slide 1 : la question, sans les réponses
    img, d = toile()
    entete(d, v["theme"])
    y = 260
    d.text((MARGE, y), "Qui a voté pour ?", font=fonte(SERIF, 92), fill=ENCRE)
    y += 150
    y = paragraphe(d, capitale(v["sens_pour"]), fonte(SERIF_REG, 46), MARGE, y,
                   L - 2 * MARGE, couleur=ENCRE)
    y += 40
    d.text((MARGE, y), f"{CHAMBRES[v['chambre']]} · {date_fr(v['date'])}",
           font=fonte(SANS, 30), fill=MUTE)

    y += 110
    d.text((MARGE, y), f"Parmi ces {len(noms)} parlementaires :",
           font=fonte(SANS_GRAS, 32), fill=ENCRE_DOUCE)
    y += 66
    f_nom = fonte(SERIF, 44)
    for nom in noms:
        d.text((MARGE + 12, y), nom, font=f_nom, fill=ENCRE)
        y += 68

    y = H - MARGE - 230
    d.rounded_rectangle([MARGE, y, L - MARGE, y + 96], radius=14, fill="#eef0f2")
    d.text((MARGE + 30, y + 28), "Réponse dans la slide suivante  →",
           font=fonte(SANS_GRAS, 34), fill=ACCENT)
    pied(img, d, appel=SITE)
    enregistrer(img, sortie / "quiz_1.jpg")

    # --- slide 2 : la révélation
    img, d = toile()
    entete(d, v["theme"])
    y = 250
    d.text((MARGE, y), "La réponse", font=fonte(SERIF, 92), fill=ENCRE)
    y += 156
    f_nom, f_badge = fonte(SERIF, 46), fonte(SANS_GRAS, 27)
    # Colonne des noms calée sur le badge le plus large : sinon le bord gauche
    # des noms est en dents de scie.
    colonne = MARGE + 44 + max(largeur(d, LIBELLE_COURT[p["position"]].upper(),
                                      f_badge) for p in positions) + 44
    for p in positions:
        fondc, textec, _ = BADGES[p["position"]]
        puce(d, MARGE, y, LIBELLE_COURT[p["position"]].upper(), f_badge,
             fondc, textec)
        d.text((colonne, y + 4), p["nom"], font=f_nom, fill=ENCRE)
        y += 104

    y += 30
    d.line([(MARGE, y), (L - MARGE, y)], fill=LISERE, width=2)
    y += 44
    y = paragraphe(d, f"Résultat du scrutin : texte {v['sort']}.",
                   fonte(SERIF_REG, 40), MARGE, y, L - 2 * MARGE,
                   couleur=ENCRE_DOUCE)
    pied(img, d, source=v["source_resume"].replace("https://www.", ""))
    enregistrer(img, sortie / "quiz_2.jpg")

    # --- slide 3 : ce que ça dit, et l'invitation
    img, d = toile()
    entete(d)
    y = 300
    y = paragraphe(d, "Un vote au Parlement ne se réécrit pas.",
                   fonte(SERIF, 76), MARGE, y, L - 2 * MARGE, interligne=1.22)
    y += 70
    y = paragraphe(d,
                   "Les alignements ne suivent pas toujours les étiquettes. "
                   "C'est pour ça qu'on publie les votes eux-mêmes, un par un, "
                   "avec la source officielle en face.",
                   fonte(SERIF_REG, 44), MARGE, y, L - 2 * MARGE)
    y += 80
    for ligne in (f"{len(noms)} positions vérifiées sur ce scrutin",
                  "22 082 scrutins dans notre base",
                  "Une source officielle derrière chaque fait"):
        d.ellipse([MARGE + 4, y + 16, MARGE + 18, y + 30], fill=ACCENT)
        d.text((MARGE + 44, y), ligne, font=fonte(SANS, 36), fill=ENCRE_DOUCE)
        y += 68
    pied(img, d)
    enregistrer(img, sortie / "quiz_3.jpg")


# ------------------------------------------------- format 2 : un vote, une loi
def post_vote(con, vote_id, sortie):
    v, positions = lire_vote(con, vote_id)

    img, d = toile()
    entete(d, v["theme"])
    y = 250
    f = fonte(SANS_GRAS, 30)
    w, h = puce(d, MARGE, y, "UN VOTE, UNE LOI", f, "#eef0f2", ACCENT)
    y += h + 46
    y = paragraphe(d, v["titre"], fonte(SERIF, 78), MARGE, y, L - 2 * MARGE,
                   interligne=1.2)
    y += 34
    d.text((MARGE, y), f"{CHAMBRES[v['chambre']]} · {date_fr(v['date'])} · "
                       f"texte {v['sort']}", font=fonte(SANS, 30), fill=MUTE)
    y += 96
    d.line([(MARGE, y), (L - MARGE, y)], fill=LISERE, width=2)
    y += 54

    d.text((MARGE, y), "Ce que voter « pour » signifiait",
           font=fonte(SANS_GRAS, 32), fill=ACCENT)
    y += 62
    y = paragraphe(d, capitale(v["sens_pour"]) + ".", fonte(SERIF_REG, 46),
                   MARGE, y, L - 2 * MARGE)
    y += 70
    y = paragraphe(d, (v["resume"] or "")[:300].rsplit(" ", 1)[0] + "…",
                   fonte(SANS, 34), MARGE, y, L - 2 * MARGE, couleur=ENCRE_DOUCE)
    pied(img, d, source=v["source_resume"].replace("https://www.", ""))
    enregistrer(img, sortie / "vote_1.jpg")

    # --- slide 2 : les positions
    img, d = toile()
    entete(d, v["theme"])
    y = 250
    y = paragraphe(d, "Qui a voté quoi", fonte(SERIF, 84), MARGE, y,
                   L - 2 * MARGE)
    y += 60
    f_nom, f_badge = fonte(SERIF, 46), fonte(SANS_GRAS, 27)
    for p in positions:
        fondc, textec, _ = BADGES[p["position"]]
        d.rounded_rectangle([MARGE, y, L - MARGE, y + 86], radius=12, fill=CARTE,
                            outline=LISERE, width=2)
        d.text((MARGE + 28, y + 18), p["nom"], font=f_nom, fill=ENCRE)
        etiquette = LIBELLE_COURT[p["position"]].upper()
        w = largeur(d, etiquette, f_badge) + 44
        puce(d, L - MARGE - 28 - w, y + 20, etiquette, f_badge, fondc, textec)
        y += 100
    y += 30
    y = paragraphe(d, "Les autres candidats suivis n'étaient pas en poste à "
                      "cette date, ou n'ont jamais été parlementaires. "
                      "Le site le précise cas par cas.",
                   fonte(SANS, 32), MARGE, y, L - 2 * MARGE, couleur=MUTE)
    pied(img, d)
    enregistrer(img, sortie / "vote_2.jpg")


# ------------------------------------------------- format 3 : la comparaison
def post_comparaison(con, nom_a, nom_b, theme, sortie):
    lignes = lire_comparaison(con, nom_a, nom_b, theme)
    ecarts = sum(1 for r in lignes if r["a"] != r["b"])
    complet = {r["nom"]: r["entier"] for r in con.execute(
        "SELECT nom, prenom || ' ' || nom AS entier FROM personnes WHERE nom IN (?, ?)",
        (nom_a, nom_b))}
    entier_a, entier_b = complet.get(nom_a, nom_a), complet.get(nom_b, nom_b)

    img, d = toile()
    entete(d, theme)
    y = 232
    y = paragraphe(d, f"{entier_a} face à {entier_b}", fonte(SERIF, 62), MARGE, y,
                   L - 2 * MARGE, interligne=1.18)
    y += 18
    d.text((MARGE, y), f"{len(lignes)} votes en commun · "
                       f"{ecarts} position{'s' if ecarts > 1 else ''} différente"
                       f"{'s' if ecarts > 1 else ''}",
           font=fonte(SANS_GRAS, 32), fill=ACCENT)
    y += 78

    col = (L - 2 * MARGE - 40) // 2
    # Têtes de colonne, en haut : il faut savoir qui est où avant de lire.
    f_tete = fonte(SANS_GRAS, 30)
    for i, nom in enumerate((entier_a, entier_b)):
        x = MARGE + i * (col + 40)
        d.rounded_rectangle([x, y, x + col, y + 62], radius=10, fill="#eef0f2")
        d.text((x + 20, y + 16), nom, font=f_tete, fill=ACCENT)
    y += 92

    f_titre, f_badge, f_date = fonte(SANS_GRAS, 30), fonte(SANS_GRAS, 26), fonte(SANS, 25)
    # Place disponible avant le pied de page. Ce qui ne rentre pas n'est pas
    # tronqué en silence : le nombre de votes omis est écrit.
    plancher = H - MARGE - 150
    affichees = 0
    for r in lignes:
        hauteur_ligne = 42 + 54 + 78 + f_titre.size  # titre + date + badges + jeu
        if y + hauteur_ligne > plancher:
            break
        affichees += 1
        titre = r["titre"].split(" (")[0]
        yb = paragraphe(d, titre, f_titre, MARGE, y, L - 2 * MARGE,
                        couleur=ENCRE, interligne=1.28)
        d.text((MARGE, yb + 2), date_fr(r["date"]), font=f_date, fill=MUTE)
        yb += 42
        for i, position in enumerate((r["a"], r["b"])):
            fondc, textec, _ = BADGES[position]
            x = MARGE + i * (col + 40)
            d.rounded_rectangle([x, yb, x + col, yb + 54], radius=10, fill=fondc)
            d.text((x + 20, yb + 13), LIBELLE_COURT[position].upper(),
                   font=f_badge, fill=textec)
        y = yb + 78
        d.line([(MARGE, y - 20), (L - MARGE, y - 20)], fill=LISERE, width=1)

    restants = len(lignes) - affichees
    if restants:
        d.text((MARGE, y + 4),
               f"+ {restants} autre{'s' if restants > 1 else ''} vote"
               f"{'s' if restants > 1 else ''} sur cette thématique, sur le site",
               font=fonte(SANS, 30), fill=MUTE)

    pied(img, d, appel=f"Comparez vous-même sur {SITE}")
    enregistrer(img, sortie / "comparaison_1.jpg")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE_DEFAUT
    sortie.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BASE)

    print("quiz — autonomie de la Corse :")
    post_quiz(con, 68, sortie)
    print("un vote, une loi — loi d'urgence agricole :")
    post_vote(con, 127, sortie)
    print("comparaison — Batho / Le Pen sur l'écologie :")
    post_comparaison(con, "Batho", "Le Pen", "Écologie et agriculture", sortie)

    con.close()
    print(f"\n{L} × {H} px par image → {sortie}")


if __name__ == "__main__":
    main()

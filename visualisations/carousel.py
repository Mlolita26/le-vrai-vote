"""Découpe la pièce plastique en un carrousel Instagram de trois slides.

  · slides 1 et 2 : une même bande de l'image, coupée en deux — elles se suivent
    sans couture quand on fait défiler ;
  · slide 3 : le réseau complet.

La bande n'est pas choisie à la main : le programme retient la fenêtre qui
concentre le plus de matière lumineuse, ce qui évite de cadrer sur du vide.

Les trois slides ont exactement le même format, condition d'Instagram — sinon la
plateforme recadre chaque image séparément et la continuité est perdue.

Usage : python visualisations/carousel.py [source.png] [dossier] [paysage|portrait|carre]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

DOSSIER = Path(__file__).resolve().parent
RACINE_DEPOT = DOSSIER.parent
SOURCE_DEFAUT = DOSSIER / "neurones.png"
SORTIE_DEFAUT = DOSSIER / "carousel"

# Formats disponibles. Instagram cale l'image sur la largeur de l'écran : à
# largeur égale, un portrait occupe donc bien plus de hauteur qu'un paysage.
# Le 4:5 est le format le plus haut accepté dans le fil, donc le plus grand à
# l'affichage. On téléverse à 1440 px de large, la limite au-delà de laquelle
# Instagram ré-échantillonne de toute façon.
FORMATS = {
    # 5300 n'est pas divisible par 3 : trois slides égales font 5298 px.
    "paysage": (1766, 1350),
    "portrait": (1440, 1800),
    "carre": (1440, 1440),
}
FORMAT_DEFAUT = "paysage"
LARGEUR_SLIDE, HAUTEUR_SLIDE = FORMATS[FORMAT_DEFAUT]
NB_SLIDES = 3

FOND = (5, 6, 10)          # même noir que le rendu
QUALITE_JPEG = 97
# Après réduction, une image perd du micro-contraste : un masque flou léger le
# rend, ce qui compte d'autant plus qu'Instagram recompresse derrière.
NETTETE = dict(radius=1.15, percent=58, threshold=2)
# Part de la largeur source retenue pour la bande panoramique. À 1,0 le cadre
# embarquait le bord droit, presque vide.
ZOOM_BANDE = 0.78
# Part de la masse lumineuse que doit contenir le cadre du réseau complet. Le
# reste — la frange la plus ténue — sort du cadre.
PART_MATIERE = 0.985
# Noms posés au maximum sur chaque slide de zoom. Au-delà, l'image redevient un
# schéma légendé — ce que la pièce refuse d'être.
NB_NOMS = 1
# Sur la vue d'ensemble, plusieurs noms : c'est la slide où le lecteur cherche à
# comprendre ce qu'il regarde.
NB_NOMS_COMPLET = 5
# Ordre de préférence pour les noms affichés : les figures que le public
# reconnaît d'abord. Le cadrage de la bande est choisi pour en faire tomber un
# dans chaque moitié. Réordonner cette liste change les noms visibles.
#
# Jordan Bardella en est écarté volontairement : il ne siège qu'au Parlement
# européen, dont la base ne compte que 37 scrutins contre 18 310 pour
# l'Assemblée. Ses 31 votes exprimés mesurent l'état de la collecte, pas son
# assiduité — affichés à côté des 2 034 d'Attal, ils induiraient en erreur.
NOMS_PRIORITAIRES = (
    "Marine Le Pen",
    "Jean-Luc Mélenchon",
    "Gabriel Attal",
    "Édouard Philippe",
    "François Ruffin",
    "Delphine Batho",
    "Bruno Retailleau",
)
# Marges intérieures avant qu'un nom soit considéré comme coupé par le bord.
MARGE_NOM_X, MARGE_NOM_Y = 330, 130
# Pas de la recherche de cadrage, en pixels source.
PAS_RECHERCHE = 48
# Opacités du texte sur 255. Volontairement basses : le nom doit se lire sans
# devenir une étiquette de schéma posée sur l'image.
OPACITE_NOM = 150
OPACITE_DETAIL = 92
OPACITE_TRAIT = 72

# Signature en bas à droite. La marque existe en deux déclinaisons ; on prend
# celle dessinée pour un fond sombre (filaments pâles), sans retouche.
LOGO = RACINE_DEPOT / "web" / "assets" / "logo-fond-sombre.png"
LARGEUR_LOGO = 0.17      # part de la largeur de la slide
OPACITE_LOGO = 240
MARGE_LOGO = 0.028       # part de la largeur de la slide
# Voile sombre sous la signature. La marque est une rosace de filaments rouges
# et bleus posée sur une image faite de filaments rouges et bleus : sans fond
# assombri elle se camoufle, sur l'éventail rouge du coin en particulier. Le
# voile atteint donc sa pleine opacité sur toute l'emprise du logo, puis
# s'éteint vers l'intérieur de l'image sur la largeur des marges ci-dessous.
OPACITE_VOILE = 190
FONDU_VOILE_X = 1.05     # part de la largeur du logo
FONDU_VOILE_Y = 1.70     # part de la hauteur du logo


def fenetre_la_plus_dense(lum, taille, axe):
    """Position de la fenêtre de `taille` qui capte le plus de lumière sur `axe`."""
    profil = lum.sum(axis=1 - axe)
    cumul = np.concatenate([[0.0], np.cumsum(profil)])
    total = cumul[taille:] - cumul[:-taille]
    return int(np.argmax(total))


def bande_panoramique(img, largeur_cible, hauteur_cible, ancrages=(),
                      nb_slides=2):
    """Recadre une bande au format demandé, puis la met à l'échelle.

    Le cadrage ne cherche pas seulement la matière : il cherche d'abord à placer
    dans chaque moitié un des parlementaires les plus connus, faute de quoi les
    noms affichés seraient ceux que personne ne reconnaît. La densité lumineuse
    ne sert plus qu'à départager les cadrages qui couvrent les mêmes noms.
    """
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    h, l = arr.shape
    rapport = largeur_cible / hauteur_cible

    # La bande ne prend pas toute la largeur : en couvrant les 8 400 px, elle
    # embarquait le bord droit presque vide.
    largeur_bande = int(round(l * ZOOM_BANDE))
    hauteur_bande = int(round(largeur_bande / rapport))
    if hauteur_bande > h:
        hauteur_bande = h
        largeur_bande = int(round(hauteur_bande * rapport))

    echelle = largeur_cible / largeur_bande
    # Marges converties en pixels source : un nom trop près du bord serait coupé.
    marge_x, marge_y = MARGE_NOM_X / echelle, MARGE_NOM_Y / echelle
    largeur_moitie = largeur_bande / nb_slides
    rang = {nom: i for i, nom in enumerate(NOMS_PRIORITAIRES)}

    # Intégrale d'image : la densité d'une fenêtre quelconque en temps constant.
    cumul = arr.cumsum(axis=0).cumsum(axis=1)
    cumul = np.pad(cumul, ((1, 0), (1, 0)))

    def densite(x, y):
        return float(cumul[y + hauteur_bande, x + largeur_bande]
                     - cumul[y, x + largeur_bande]
                     - cumul[y + hauteur_bande, x] + cumul[y, x])

    def couverture(x, y):
        """Meilleur rang de priorité atteint dans chaque moitié (None si aucun)."""
        trouves = []
        for k in range(nb_slides):
            x0 = x + k * largeur_moitie
            meilleurs = [rang[a["nom"]] for a in ancrages
                         if a["nom"] in rang
                         and x0 + marge_x < a["x"] < x0 + largeur_moitie - marge_x
                         and y + marge_y < a["y"] < y + hauteur_bande - marge_y]
            trouves.append(min(meilleurs) if meilleurs else None)
        return trouves

    meilleur = None
    for x in range(0, l - largeur_bande + 1, PAS_RECHERCHE):
        for y in range(0, h - hauteur_bande + 1, PAS_RECHERCHE):
            trouves = couverture(x, y)
            nb = sum(t is not None for t in trouves)
            # Priorité absolue au nombre de moitiés nommées, puis à la notoriété
            # (rang faible = nom mieux connu), puis seulement à la densité.
            qualite = -sum(t for t in trouves if t is not None)
            score = (nb, qualite, densite(x, y))
            if meilleur is None or score > meilleur[0]:
                meilleur = (score, x, y)

    _, x, y = meilleur
    decoupe = img.crop((x, y, x + largeur_bande, y + hauteur_bande))
    return (decoupe.resize((largeur_cible, hauteur_cible), Image.LANCZOS),
            (x, y, largeur_bande, hauteur_bande, echelle))


def emprise_matiere(img, part=PART_MATIERE):
    """Rectangle contenant `part` de la masse lumineuse.

    Un simple seuil par pixel ne marche pas ici : quelques filaments isolés
    touchent les bords de la toile, si bien que l'emprise couvrait tout. On
    raisonne donc en masse cumulée et on laisse dehors la frange la plus ténue.
    """
    arr = np.asarray(img.convert("L"), dtype=np.float64)
    marge = (1.0 - part) / 2

    def bornes(profil):
        cumul = np.cumsum(profil) / profil.sum()
        return (int(np.searchsorted(cumul, marge)),
                int(np.searchsorted(cumul, 1 - marge)) + 1)

    y0, y1 = bornes(arr.sum(axis=1))
    x0, x1 = bornes(arr.sum(axis=0))
    return x0, y0, x1, y1


def entier_dans_cadre(img, largeur, hauteur):
    """L'œuvre entière, recadrée sur son emprise, mise à l'échelle sans rien
    couper, centrée sur le fond.

    Renvoie aussi la transformation source → slide, sans laquelle il serait
    impossible de replacer les noms sur cette vue.
    """
    x0, y0, x1, y1 = emprise_matiere(img)
    print(f"emprise de la matière : ({x0}, {y0}) → ({x1}, {y1})")
    cadre = Image.new("RGB", (largeur, hauteur), FOND)
    copie = img.crop((x0, y0, x1, y1))
    copie.thumbnail((largeur, hauteur), Image.LANCZOS)
    echelle = copie.width / (x1 - x0)
    ox, oy = (largeur - copie.width) // 2, (hauteur - copie.height) // 2
    cadre.paste(copie, (ox, oy))

    def vers_slide(a):
        return (a["x"] - x0) * echelle + ox, (a["y"] - y0) * echelle + oy

    return cadre, vers_slide


def police(taille):
    """Sans-serif du système, avec repli sur la police par défaut de Pillow."""
    for nom in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def se_chevauchent(a, b, jeu=10):
    return not (a[2] + jeu < b[0] or b[2] + jeu < a[0]
                or a[3] + jeu < b[1] or b[3] + jeu < a[1])


def etiqueter(slide, ancrages, vers_slide, maxi=NB_NOMS, taille_nom=34,
              marges=None):
    """Pose au plus `maxi` noms, placés vers l'extérieur de la composition.

    `vers_slide` convertit les coordonnées d'un ancrage (pixels de l'image
    source) en pixels de cette slide — le zoom et la vue d'ensemble n'ont pas la
    même transformation.

    Les étiquettes fuient le centre : sur la vue d'ensemble, où les quatorze
    ancrages sont resserrés, les poser au hasard les ferait se chevaucher.
    """
    marge_x, marge_y = marges or (MARGE_NOM_X, MARGE_NOM_Y)
    dedans = []
    for a in ancrages:
        x, y = vers_slide(a)
        if (marge_x < x < slide.width - marge_x
                and marge_y < y < slide.height - marge_y):
            dedans.append((a, x, y))
    # La notoriété passe devant la taille de la touffe : un nom inconnu
    # n'apprend rien au lecteur, même si sa touffe est la plus grande.
    rang = {nom: i for i, nom in enumerate(NOMS_PRIORITAIRES)}
    dedans.sort(key=lambda t: (rang.get(t[0]["nom"], len(rang)),
                               -t[0]["portee"]))
    dedans = dedans[:maxi]
    if not dedans:
        return slide, []

    calque = Image.new("RGBA", slide.size, (0, 0, 0, 0))
    dessin = ImageDraw.Draw(calque)
    f_nom, f_detail = police(taille_nom), police(int(taille_nom * 0.74))
    saut = int(taille_nom * 1.24)
    cx, cy = slide.width / 2, slide.height / 2
    occupes, poses = [], []

    for a, x, y in dedans:
        nom = a["nom"].upper()
        detail = f"{a['positions_exprimees']:,} votes exprimés".replace(",", " ")
        largeur = max(dessin.textlength(nom, font=f_nom),
                      dessin.textlength(detail, font=f_detail))
        hauteur = saut * 2

        # Le nom se lit mieux au-dessus du point : on essaie donc le dessus en
        # premier, des deux côtés, et le dessous seulement ensuite. Chaque
        # candidat est retenu s'il tient dans le cadre et ne recouvre personne.
        dehors = x >= cx          # côté qui éloigne du centre
        candidats = []
        for en_haut in (True, False):
            for a_droite in (dehors, not dehors):
                candidats.append((a_droite, en_haut, 0))
        # En dernier recours, des décalages verticaux croissants.
        for pas in range(1, 9):
            for en_haut in (True, False):
                for a_droite in (dehors, not dehors):
                    candidats.append((a_droite, en_haut,
                                      -pas * saut if en_haut else pas * saut))

        retenu = None
        for a_droite, en_haut, dy in candidats:
            tx = x + 68 if a_droite else x - 68 - largeur
            ty = (y - 30 - hauteur if en_haut else y + 46) + dy
            if not (20 < tx and tx + largeur < slide.width - 20
                    and 20 < ty and ty + hauteur < slide.height - 20):
                continue
            boite = (tx, ty, tx + largeur, ty + hauteur)
            if any(se_chevauchent(boite, b) for b in occupes):
                continue
            retenu = (a_droite, en_haut, tx, ty)
            break
        if retenu is None:
            # Aucune place libre : on pose au-dessus, quitte à se superposer.
            a_droite, en_haut = dehors, True
            tx = x + 68 if a_droite else x - 68 - largeur
            ty = y - 30 - hauteur
        else:
            a_droite, en_haut, tx, ty = retenu
        occupes.append((tx, ty, tx + largeur, ty + hauteur))

        # Trait de rappel : il désigne le point sans le toucher.
        ancre_x = tx - 14 if a_droite else tx + largeur + 14
        ancre_y = ty + hauteur - saut * 0.35 if en_haut else ty + saut * 0.35
        vx, vy = x - ancre_x, y - ancre_y
        norme = max((vx * vx + vy * vy) ** 0.5, 1e-6)
        dessin.line([(ancre_x, ancre_y),
                     (x - vx / norme * 15, y - vy / norme * 15)],
                    fill=(255, 255, 255, OPACITE_TRAIT), width=2)

        dessin.text((tx, ty), nom, font=f_nom,
                    fill=(255, 255, 255, OPACITE_NOM))
        dessin.text((tx, ty + saut), detail, font=f_detail,
                    fill=(255, 255, 255, OPACITE_DETAIL))
        poses.append(a["nom"])

    return Image.alpha_composite(slide.convert("RGBA"), calque).convert("RGB"), poses


def enregistrer(img, chemin):
    """Netteté de finition puis JPEG progressif, sans sous-échantillonnage
    chroma — les filaments fins sont exactement ce que la compression abîme."""
    img = img.filter(ImageFilter.UnsharpMask(**NETTETE))
    img.save(chemin, "JPEG", quality=QUALITE_JPEG, subsampling=0,
             optimize=True, progressive=True)


def poser_logo(slide, chemin=LOGO):
    """Compose la signature en bas à droite, dans sa déclinaison fond sombre."""
    if not Path(chemin).exists():
        print(f"! logo introuvable : {chemin}")
        return slide

    logo = Image.open(chemin).convert("RGBA")
    logo = logo.crop(logo.getbbox())          # retire la marge transparente

    a = np.asarray(logo).astype(np.float32)
    a[..., 3:] *= OPACITE_LOGO / 255
    logo = Image.fromarray(a.astype(np.uint8), "RGBA")

    largeur = int(slide.width * LARGEUR_LOGO)
    logo = logo.resize((largeur, max(1, round(largeur * logo.height / logo.width))),
                       Image.LANCZOS)
    marge = int(slide.width * MARGE_LOGO)
    x0 = slide.width - largeur - marge
    y0 = slide.height - logo.height - marge

    # Voile : pleine opacité sur l'emprise du logo, fondu vers l'intérieur de
    # l'image sur `pad`, pour qu'aucune arête ne se voie. Une rampe qui partirait
    # du bord de l'image ne monterait qu'à un dixième d'opacité sous le logo.
    pad_x, pad_y = int(largeur * FONDU_VOILE_X), int(logo.height * FONDU_VOILE_Y)
    bx0, by0 = max(0, x0 - pad_x), max(0, y0 - pad_y)
    lv, hv = slide.width - bx0, slide.height - by0
    fx = np.clip((np.arange(lv) - (x0 - bx0 - pad_x)) / max(pad_x, 1), 0, 1)[None, :]
    fy = np.clip((np.arange(hv) - (y0 - by0 - pad_y)) / max(pad_y, 1), 0, 1)[:, None]
    # Lissage en cosinus : ni arête, ni cassure de pente au raccord.
    doux = lambda f: (1 - np.cos(np.pi * f)) / 2
    voile = doux(fx) * doux(fy) * OPACITE_VOILE
    plaque = np.zeros((hv, lv, 4), dtype=np.uint8)
    plaque[..., :3] = FOND
    plaque[..., 3] = voile.astype(np.uint8)

    calque = Image.new("RGBA", slide.size, (0, 0, 0, 0))
    calque.paste(Image.fromarray(plaque, "RGBA"), (bx0, by0))
    calque.paste(logo, (x0, y0), logo)
    return Image.alpha_composite(slide.convert("RGBA"), calque).convert("RGB")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE_DEFAUT
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else SORTIE_DEFAUT
    nom_format = sys.argv[3] if len(sys.argv) > 3 else FORMAT_DEFAUT
    if nom_format not in FORMATS:
        sys.exit(f"format inconnu : {nom_format} (au choix : {', '.join(FORMATS)})")
    global LARGEUR_SLIDE, HAUTEUR_SLIDE
    LARGEUR_SLIDE, HAUTEUR_SLIDE = FORMATS[nom_format]
    print(f"format {nom_format} : {LARGEUR_SLIDE} × {HAUTEUR_SLIDE} px par slide")
    sortie.mkdir(parents=True, exist_ok=True)

    img = Image.open(source).convert("RGB")
    print(f"source : {img.width} × {img.height} px")

    fiche = source.with_suffix(".ancrages.json")
    ancrages = []
    if fiche.exists():
        ancrages = json.loads(fiche.read_text(encoding="utf-8"))["ancrages"]
    else:
        print(f"! {fiche.name} absent : les slides sortiront sans nom")

    # --- slides 1 et 2 : une bande continue, coupée en deux
    largeur_bande = LARGEUR_SLIDE * (NB_SLIDES - 1)
    bande, (x, y, lb, hb, echelle) = bande_panoramique(
        img, largeur_bande, HAUTEUR_SLIDE, ancrages, NB_SLIDES - 1)
    print(f"bande retenue : {lb} × {hb} px à partir de ({x}, {y}) "
          f"→ {bande.width} × {bande.height}")

    chemins = []
    for i in range(NB_SLIDES - 1):
        slide = bande.crop((i * LARGEUR_SLIDE, 0,
                            (i + 1) * LARGEUR_SLIDE, HAUTEUR_SLIDE))
        # Le recadrage dans la bande décale l'origine d'autant de slides.
        origine_x = x + i * LARGEUR_SLIDE / echelle
        slide, poses = etiqueter(
            slide, ancrages,
            lambda a, ox=origine_x: ((a["x"] - ox) * echelle,
                                     (a["y"] - y) * echelle))
        print(f"  slide {i + 1} : {', '.join(poses) if poses else 'aucun nom'}")
        slide = poser_logo(slide)
        chemin = sortie / f"slide_{i + 1}.jpg"
        enregistrer(slide, chemin)
        chemins.append(chemin)

    # --- slide 3 : le réseau complet, avec plusieurs noms
    complet, vers_slide = entier_dans_cadre(img, LARGEUR_SLIDE, HAUTEUR_SLIDE)
    complet, poses = etiqueter(complet, ancrages, vers_slide,
                               maxi=NB_NOMS_COMPLET, taille_nom=26,
                               marges=(40, 40))
    print(f"  slide {NB_SLIDES} : {', '.join(poses) if poses else 'aucun nom'}")
    complet = poser_logo(complet)
    chemin = sortie / f"slide_{NB_SLIDES}.jpg"
    enregistrer(complet, chemin)
    chemins.append(chemin)

    # --- planche de contrôle : les trois slides bout à bout, séparées d'un filet
    planche = Image.new("RGB", (LARGEUR_SLIDE * NB_SLIDES + 2 * 8, HAUTEUR_SLIDE),
                        (255, 255, 255))
    for i, c in enumerate(chemins):
        planche.paste(Image.open(c), (i * (LARGEUR_SLIDE + 8), 0))
    planche.save(sortie / "apercu_carousel.jpg", "JPEG", quality=88, optimize=True)

    print(f"\ncarrousel : {NB_SLIDES} × {LARGEUR_SLIDE} × {HAUTEUR_SLIDE} px "
          f"= {LARGEUR_SLIDE * NB_SLIDES} px de large")
    for c in chemins:
        print(f"  {c.name}  {c.stat().st_size / 1024:.0f} ko")
    print(f"  apercu_carousel.jpg (planche de contrôle)")


if __name__ == "__main__":
    main()

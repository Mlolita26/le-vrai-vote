#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère les déclinaisons de la marque (favicons, icône d'en-tête, image de
partage) à partir des sources dans visualisations/marque/.

Le symbole est une rosace de filaments très fins : à 32 px, une simple
réduction de l'export 1080 px efface les traits. Les icônes sont donc
rasterisées directement depuis le SVG, avec une épaisseur de trait relevée
d'autant que la taille est petite (« boost »). Tout ce qui comporte du texte
(logotype horizontal) est repris de l'export PNG fourni, pour ne pas dépendre
de la police Archivo.

Usage :  python visualisations/genere_marque.py
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "visualisations" / "marque"   # sources, non déployées
SORTIE = RACINE / "web" / "assets"              # déclinaisons servies

# Fond des tuiles opaques (favicons, image de partage) : le crème du site.
CREME = (246, 244, 239)
BLANC = (255, 255, 255)

# Étendue réelle du dessin dans le repère du SVG (viewBox 0 0 200 200) : les
# filaments partent du centre (100, 100) et s'arrêtent vers 22 / 178.
CENTRE = 100.0
ETENDUE = 156.0

SURECHANTILLONNAGE = 4


# ── Rasterisation du symbole ─────────────────────────────────────────────────

def lit_svg(chemin: Path):
    """Extrait les courbes et le disque central du SVG (format connu, régulier)."""
    svg = chemin.read_text(encoding="utf-8")
    courbes = []
    motif = re.compile(
        r'<path d="M([\d.]+) ([\d.]+)Q([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)"'
        r' stroke="(#[0-9a-fA-F]{6})" stroke-width="([\d.]+)"')
    for m in motif.finditer(svg):
        x0, y0, cx, cy, x1, y1 = (float(g) for g in m.groups()[:6])
        courbes.append(((x0, y0), (cx, cy), (x1, y1), m.group(7), float(m.group(8))))
    if not courbes:
        raise ValueError(f"aucune courbe lue dans {chemin.name}")

    disque = re.search(
        r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="(#[0-9a-fA-F]{6})"', svg)
    if not disque:
        raise ValueError(f"disque central introuvable dans {chemin.name}")
    cx, cy, r = (float(disque.group(i)) for i in (1, 2, 3))
    return courbes, (cx, cy, r, disque.group(4))


def rvb(hexa: str):
    return tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))


def bezier(p0, p1, p2, n):
    """Points d'une courbe de Bézier quadratique."""
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1])
            for t in (i / n for i in range(n + 1))]


def rasterise_symbole(source: Path, taille: int, boost: float = 1.0,
                      marge: float = 0.06, fond=None, rayon_coins: float = 0.0):
    """Dessine le symbole à `taille` px.

    boost        multiplicateur d'épaisseur des filaments (>1 aux petites tailles)
    marge        part de la largeur laissée vide autour du dessin
    fond         couleur RVB de la tuile, ou None pour un fond transparent
    rayon_coins  arrondi de la tuile, en part de la largeur (ignoré si fond None)
    """
    courbes, (dcx, dcy, dr, dfill) = lit_svg(source)

    s = SURECHANTILLONNAGE
    grand = taille * s
    echelle = grand * (1 - 2 * marge) / ETENDUE
    decalage = grand / 2 - CENTRE * echelle

    def pt(p):
        return (p[0] * echelle + decalage, p[1] * echelle + decalage)

    img = Image.new("RGBA", (grand, grand), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    for p0, p1, p2, couleur, epaisseur in courbes:
        w = max(1.0, epaisseur * echelle * boost)
        pts = [pt(p) for p in bezier(p0, p1, p2, 48)]
        col = rvb(couleur) + (255,)
        d.line(pts, fill=col, width=round(w), joint="curve")
        # Pillow coupe les extrémités à l'équerre : on referme les bouts ronds.
        for x, y in (pts[0], pts[-1]):
            d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col)

    r = dr * echelle * min(boost, 1.6)
    cx, cy = pt((dcx, dcy))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rvb(dfill) + (255,))

    if fond is None:
        return img.resize((taille, taille), Image.LANCZOS)

    tuile = Image.new("RGBA", (grand, grand), fond + (255,))
    tuile = Image.alpha_composite(tuile, img)
    if rayon_coins > 0:
        masque = Image.new("L", (grand, grand), 0)
        ImageDraw.Draw(masque).rounded_rectangle(
            (0, 0, grand - 1, grand - 1), radius=round(grand * rayon_coins), fill=255)
        tuile.putalpha(masque)
    return tuile.resize((taille, taille), Image.LANCZOS)


# ── Logotype horizontal (comporte du texte : repris de l'export PNG) ─────────

def rogne(img: Image.Image) -> Image.Image:
    boite = img.getbbox()
    return img.crop(boite) if boite else img


def logotype(variante: str) -> Image.Image:
    return Image.open(SOURCE / f"horizontal-{variante}.png").convert("RGBA")


def image_partage(largeur=1200, hauteur=630, part=0.74, fond=CREME) -> Image.Image:
    """Carte de partage : logotype centré sur un fond opaque.

    La composition se fait avant réduction : redimensionner du RVBA à bords
    transparents ferait baver du noir sur le crème.
    """
    logo = logotype("fond-clair")
    plaque = Image.new("RGBA", logo.size, fond + (255,))
    plaque = rogne_opaque(Image.alpha_composite(plaque, logo), logo, fond)

    cible_l = round(largeur * part)
    cible_h = round(cible_l * plaque.height / plaque.width)
    if cible_h > hauteur * 0.62:
        cible_h = round(hauteur * 0.62)
        cible_l = round(cible_h * plaque.width / plaque.height)
    plaque = plaque.resize((cible_l, cible_h), Image.LANCZOS)

    carte = Image.new("RGB", (largeur, hauteur), fond)
    carte.paste(plaque.convert("RGB"),
                ((largeur - cible_l) // 2, (hauteur - cible_h) // 2))
    return carte


def rogne_opaque(composee: Image.Image, original: Image.Image, fond) -> Image.Image:
    """Rogne `composee` sur la boîte englobante des pixels visibles d'`original`."""
    boite = original.getbbox()
    return composee.crop(boite) if boite else composee


# ── Production ───────────────────────────────────────────────────────────────

def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    clair = SOURCE / "symbole-fond-clair.svg"
    sombre = SOURCE / "symbole-fond-sombre.svg"

    # Favicons : tuile opaque crème, arrondie. Un fond transparent rendrait le
    # marine invisible sur les onglets sombres.
    fabriques = [
        ("favicon-16.png", rasterise_symbole(clair, 16, boost=3.8, marge=0.04,
                                             fond=CREME, rayon_coins=0.16)),
        ("favicon-32.png", rasterise_symbole(clair, 32, boost=2.9, marge=0.05,
                                             fond=CREME, rayon_coins=0.16)),
        ("favicon-192.png", rasterise_symbole(clair, 192, boost=1.55, marge=0.07,
                                              fond=CREME, rayon_coins=0.16)),
        ("favicon-512.png", rasterise_symbole(clair, 512, boost=1.25, marge=0.07,
                                              fond=CREME, rayon_coins=0.16)),
        # iOS applique son propre masque : la tuile doit être pleine, sans
        # arrondi ni transparence (sinon les coins ressortent en noir).
        ("apple-touch-icon.png", rasterise_symbole(clair, 180, boost=1.6, marge=0.15,
                                                   fond=BLANC, rayon_coins=0.0)),
        # Icône d'en-tête : fond transparent, une déclinaison par thème.
        ("marque-clair.png", rasterise_symbole(clair, 96, boost=2.1, marge=0.02)),
        ("marque-sombre.png", rasterise_symbole(sombre, 96, boost=2.1, marge=0.02)),
    ]
    for nom, img in fabriques:
        img.save(SORTIE / nom, "PNG", optimize=True)
        print(f"  {nom:24} {img.size[0]}×{img.size[1]}")

    # Logotype horizontal, fond transparent : utilisé par les visuels réseaux
    # sociaux (carousel.py, posts_insta.py), qui éclaircissent le marine.
    for nom, variante in (("logo.png", "fond-clair"),
                          ("logo-fond-sombre.png", "fond-sombre")):
        img = rogne(logotype(variante))
        img.save(SORTIE / nom, "PNG", optimize=True)
        print(f"  {nom:24} {img.size[0]}×{img.size[1]}")

    carte = image_partage()
    carte.save(SORTIE / "og-image.png", "PNG", optimize=True)
    print(f"  {'og-image.png':24} {carte.size[0]}×{carte.size[1]}")


if __name__ == "__main__":
    main()

"""Télécharge les portraits des candidats depuis Wikimedia Commons
(image principale de leur page Wikipédia francophone), avec licence libre
et attribution obligatoire.

- Requêtes groupées (une pour les 25 pages, une pour les 25 fichiers) et
  en-têtes conformes à la politique Wikimedia — pas de martèlement.
- Chaque photo est enregistrée dans web/photos/{slug}.jpg (largeur 256 px).
- Crédits (fichier, auteur, licence, lien) dans web/photos/credits.json,
  affichés sur la page Méthode par build_site.
- Un candidat sans page ou sans image sous licence libre est ignoré :
  le site garde l'avatar à initiales (jamais de photo non libre).

Usage : python ingestion/telecharge_photos.py
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
PHOTOS = RACINE / "web" / "photos"
ENTETES = {"User-Agent": "LeVraiVoteBot/1.0 (https://mlolita26.github.io/le-vrai-vote/; "
                         "https://github.com/Mlolita26/le-vrai-vote)"}

# slug -> titre exact de la page Wikipédia francophone (homonymes désambiguïsés)
TITRES = {
    "nathalie-arthaud": "Nathalie Arthaud",
    "francois-asselineau": "François Asselineau",
    "gabriel-attal": "Gabriel Attal",
    "clementine-autain": "Clémentine Autain",
    "delphine-batho": "Delphine Batho",
    "xavier-bertrand": "Xavier Bertrand",
    "karim-bouamrane": "Karim Bouamrane",
    "philippe-brun": "Philippe Brun (homme politique)",
    "bernard-cazeneuve": "Bernard Cazeneuve",
    "nicolas-dupont-aignan": "Nicolas Dupont-Aignan",
    "clara-egger": "Clara Egger",
    "jerome-guedj": "Jérôme Guedj",
    "anasse-kazib": "Anasse Kazib",
    "selma-labib": "Selma Labib",
    "marine-le-pen": "Marine Le Pen",
    "david-lisnard": "David Lisnard",
    "lydie-massard": "Lydie Massard",
    "jean-luc-melenchon": "Jean-Luc Mélenchon",
    "antoine-mikolajczak": "Antoine Mikolajczak",
    "edouard-philippe": "Édouard Philippe",
    "florian-philippot": "Florian Philippot",
    "bruno-retailleau": "Bruno Retailleau",
    "segolene-royal": "Ségolène Royal",
    "francois-ruffin": "François Ruffin",
    "marine-tondelier": "Marine Tondelier",
}

LICENCES_LIBRES = ("cc", "public domain", "pd", "attribution")


def requete(url):
    for tentative in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as err:
            if err.code == 429 and tentative < 2:
                time.sleep(20)
                continue
            raise
    return None


def api_json(url):
    return json.loads(requete(url))


def sans_html(v):
    return re.sub(r"<[^>]+>", "", v or "").strip()


def principal():
    PHOTOS.mkdir(parents=True, exist_ok=True)

    # 1. Une seule requête : image principale de chacune des 25 pages.
    titres = list(TITRES.values())
    q = urllib.parse.quote("|".join(titres))
    d = api_json("https://fr.wikipedia.org/w/api.php?action=query&format=json"
                 f"&prop=pageimages&piprop=name&titles={q}&redirects=1")
    redirections = {r["to"]: r["from"] for r in d.get("query", {}).get("redirects", [])}
    titre_vers_slug = {t: s for s, t in TITRES.items()}
    fichiers = {}   # slug -> nom de fichier Commons
    for p in d.get("query", {}).get("pages", {}).values():
        titre = p.get("title", "")
        titre_origine = redirections.get(titre, titre)
        slug = titre_vers_slug.get(titre_origine) or titre_vers_slug.get(titre)
        if slug and p.get("pageimage"):
            fichiers[slug] = p["pageimage"]
    sans_image = sorted(set(TITRES) - set(fichiers))
    if sans_image:
        print(f"[sans image principale] {sans_image}")

    # 2. Une seule requête : licences et vignettes des fichiers Commons.
    noms = sorted(set(fichiers.values()))
    q = urllib.parse.quote("|".join(f"File:{n}" for n in noms))
    d = api_json("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                 f"&titles={q}&prop=imageinfo&iiprop=extmetadata|url&iiurlwidth=256")
    infos = {}
    normalises = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
    for p in d.get("query", {}).get("pages", {}).values():
        titre_fichier = normalises.get(p.get("title"), p.get("title", ""))
        nom = titre_fichier.removeprefix("File:").removeprefix("Fichier:")
        for ii in p.get("imageinfo", []):
            meta = ii.get("extmetadata", {})
            infos[nom.replace("_", " ")] = {
                "vignette": ii.get("thumburl") or ii.get("url"),
                "page": ii.get("descriptionurl"),
                "auteur": sans_html(meta.get("Artist", {}).get("value")) or "auteur non renseigné",
                "licence": sans_html(meta.get("LicenseShortName", {}).get("value")),
            }

    # 3. Téléchargement (licences libres uniquement), une image par seconde.
    credits = {}
    for slug, nom in sorted(fichiers.items()):
        i = infos.get(nom.replace("_", " ")) or infos.get(nom)
        if not i or not i["vignette"]:
            print(f"  [sans infos] {slug} ({nom})")
            continue
        if not any(m in (i["licence"] or "").lower() for m in LICENCES_LIBRES):
            print(f"  [licence non libre — ignoré] {slug} : {i['licence']}")
            continue
        try:
            (PHOTOS / f"{slug}.jpg").write_bytes(requete(i["vignette"]))
        except Exception as err:
            print(f"  [échec téléchargement — ignoré] {slug} : {err}")
            continue
        credits[slug] = {"fichier": nom, "auteur": i["auteur"],
                         "licence": i["licence"], "page": i["page"]}
        print(f"  [ok] {slug} — {i['licence']} — {i['auteur'][:55]}")
        time.sleep(1)

    (PHOTOS / "credits.json").write_text(
        json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(credits)} portraits téléchargés, crédits dans web/photos/credits.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    principal()

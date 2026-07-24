"""Collecte les scrutins publics du Sénat depuis senat.fr et importe les
positions de Bruno Retailleau (matricule 04033B), la seule personne suivie
qui y a siégé.

Le Sénat ne publie pas de dump : on récupère chaque scrutin page par page
(listing annuel /scrutin-public/scrYYYY.html → détail scrYYYY-NNN.html).
Chaque page de détail est archivée horodatée avant transformation.

Structure d'une page de détail (vérifiée le 24/07/2026) :
  - résultat global : « Le Sénat a adopté / n'a pas adopté », votants,
    suffrages exprimés, pour, contre ;
  - « Analyse détaillée » : par groupe, des listes « Pour : / Contre : /
    Abstention : / N'ont pas pris part au vote : » suivies des noms.
  La position d'un sénateur = dernier en-tête de liste (suivi d'un nom)
  précédant son entrée, sur le TEXTE NETTOYÉ (les balises trompent le brut).

Usage : python ingestion/senat/collecte_senat.py [chemin_base] [annee_debut] [annee_fin]
Par défaut : 2011 à 2025 (période couverte par senat.fr).
"""
import hashlib
import html as htmllib
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"
DUMPS = RACINE / "data" / "dumps" / "senat"
ENTETES = {"User-Agent": "LeVraiVoteBot/1.0 (https://mlolita26.github.io/le-vrai-vote/; "
                         "https://github.com/Mlolita26/le-vrai-vote)"}
MATRICULE = "04033"          # Retailleau (le suffixe lettre varie en casse)
SLUG_SUIVI = "bruno-retailleau"
MOIS = {"janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12}


def get(url):
    for essai in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=ENTETES), timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            if essai < 4:
                time.sleep(5 * (essai + 1))
            else:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError) as err:
            # coupure réseau / reset : backoff progressif puis on réessaie
            if essai < 4:
                time.sleep(5 * (essai + 1))
            else:
                raise
    return None


def nettoie(fragment):
    return re.sub(r'\s+', ' ', htmllib.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()


def scrutins_de_annee(annee):
    """(numero, objet, date_iso) pour chaque scrutin listé dans la session.

    Structure senat.fr : un <div class="list-group-subtitle">DATE</div> précède
    les scrutins du jour ; chaque scrutin = <a ...scrYYYY-N.html>Scrutin N°N</a>
    suivi de « : OBJET - <a>consulter le dossier</a>. <span badge>Adoption</span> ».
    """
    html = get(f"https://www.senat.fr/scrutin-public/scr{annee}.html")
    if not html:
        return []
    resultats, date_courante = [], None
    motif = re.compile(
        r'<div class="list-group-subtitle">\s*(?P<date>\d{1,2}\s+(?:' + "|".join(MOIS) + r')\s+\d{4})'
        r'|scr' + str(annee) + r'-(?P<num>\d+)\.html">[^<]*</a>(?P<objet>.*?)'
        r'(?:<span|</p>)', re.S)
    for m in motif.finditer(html):
        if m.group("date"):
            j, mois, a = htmllib.unescape(m.group("date")).split()
            date_courante = f"{a}-{MOIS[mois]:02d}-{int(j):02d}"
        else:
            objet = nettoie(m.group("objet"))
            objet = re.sub(r'^:\s*', '', objet)
            # retire le suffixe « - consulter le dossier législatif . »
            objet = re.sub(r'\s*-?\s*consulter\s+le\s+dossier\s+l\w+\s*\.?\s*$', '', objet).strip(" .-")
            resultats.append((m.group("num"), objet or "(objet non précisé)", date_courante))
    return resultats


def parse_detail(html):
    txt = nettoie(html)
    def n(motif):
        mm = re.search(motif, txt)
        return int(mm.group(1)) if mm else None
    sort = ("adopté" if "Le Sénat a adopté" in txt
            else "rejeté" if "n'a pas adopté" in txt else None)
    resultat = {"sort": sort, "votants": n(r'(\d+)\s+votants'),
                "exprimes": n(r'(\d+)\s+suffrages exprimés'),
                "pour": n(r'(\d+)\s+pour\b'), "contre": n(r'(\d+)\s+contre\b')}
    # Position de Retailleau : dernier en-tête de liste avant son nom.
    pos = None
    if MATRICULE in html:
        ret = txt.find("Retailleau")
        if ret >= 0:
            entetes = list(re.finditer(
                r"(Pour|Contre|Abstention|N'ont pas pris part au vote)\s*:\s*"
                r"(?=(?:MM?\.|Mme|[A-ZÉÈ]))", txt[:ret]))
            if entetes:
                pos = {"Pour": "pour", "Contre": "contre", "Abstention": "abstention",
                       "N'ont pas pris part au vote": "non_votant"}[entetes[-1].group(1)]
    return resultat, pos


def collecte(base, an_debut, an_fin):
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()
    pid = cur.execute("SELECT id FROM personnes WHERE slug=?", (SLUG_SUIVI,)).fetchone()
    if not pid:
        sys.exit("Retailleau introuvable en base.")
    pid = pid[0]

    # Repart propre : on efface les scrutins Sénat existants (réimport idempotent).
    cur.execute("DELETE FROM positions_vote WHERE scrutin_id IN "
                "(SELECT id FROM scrutins WHERE chambre='senat')")
    cur.execute("DELETE FROM presence WHERE source_id IN "
                "(SELECT id FROM sources WHERE url='https://www.senat.fr/scrutin-public/')")
    cur.execute("DELETE FROM scrutins WHERE chambre='senat'")
    con.commit()

    horodatage = datetime.now().strftime("%Y-%m-%d")
    dossier = DUMPS / horodatage
    dossier.mkdir(parents=True, exist_ok=True)

    cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?,?,?,?)",
                ("https://www.senat.fr/scrutin-public/", "scrutin_officiel", horodatage,
                 f"Scrutins publics du Sénat collectés page par page depuis senat.fr "
                 f"(sessions {an_debut} à {an_fin}), archivés dans {dossier}"))
    src = cur.lastrowid

    n_scrutins = n_positions = 0
    for annee in range(an_debut, an_fin + 1):
        liste = scrutins_de_annee(annee)
        print(f"Session {annee} : {len(liste)} scrutins listés")
        for numero, objet, date in liste:
            fichier = dossier / f"scr{annee}-{numero}.html"
            if fichier.exists():                       # cache local : pas de re-téléchargement
                html = fichier.read_text(encoding="utf-8")
            else:
                html = get(f"https://www.senat.fr/scrutin-public/{annee}/scr{annee}-{numero}.html")
                if not html:
                    continue
                fichier.write_text(html, encoding="utf-8")
                time.sleep(0.5)
            resultat, pos = parse_detail(html)
            if not date:
                continue  # sans date fiable, on n'insère pas (pas de supposition)
            uid = f"SEN-{annee}-{numero}"
            cur.execute(
                "INSERT OR IGNORE INTO scrutins (chambre, legislature, numero, uid_officiel, objet, "
                "type_vote, date, sort, total_pour, total_contre, total_abstention, source_id) "
                "VALUES ('senat', NULL, ?, ?, ?, 'scrutin public', ?, ?, ?, ?, NULL, ?)",
                (f"{annee}-{numero}", uid, objet, date, resultat["sort"],
                 resultat["pour"], resultat["contre"], src))
            sid = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()[0]
            n_scrutins += 1
            if pos:
                cur.execute("INSERT OR IGNORE INTO positions_vote (personne_id, scrutin_id, position) "
                            "VALUES (?,?,?)", (pid, sid, pos))
                statut = "present" if pos != "non_votant" else "present"
                cur.execute("INSERT INTO presence (personne_id, type, date, statut, source_id) "
                            "VALUES (?, 'scrutin', ?, ?, ?)", (pid, date, statut, src))
                n_positions += 1
        con.commit()

    cur.execute("INSERT INTO imports_journal (source_id, script, lignes, execute_le) VALUES (?,?,?,?)",
                (src, "ingestion/senat/collecte_senat.py", n_scrutins + n_positions,
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()
    print(f"\nImporté : {n_scrutins} scrutins Sénat, {n_positions} positions de Retailleau.")
    con.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    an_debut = int(sys.argv[2]) if len(sys.argv) > 2 else 2011
    an_fin = int(sys.argv[3]) if len(sys.argv) > 3 else 2025
    collecte(base, an_debut, an_fin)

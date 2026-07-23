"""Couche éditoriale : thématiques et votes clés, selon la grille publiée
(docs/grille-selection.md) et la sélection validée le 23/07/2026
(coffre : notes_projet/PROPOSITION_VOTES_CLES.md).

Règles appliquées :
  - chaque vote clé pointe un scrutin réellement importé (uid officiel) ;
  - résumé descriptif neutre : dit ce que fait le texte, ne juge pas ;
  - source_resume : page officielle du scrutin sur assemblee-nationale.fr
    (format vérifié : /dyn/{législature}/scrutins/{numéro}) ; le scrutin du
    Congrès, sans page propre, renvoie à LCP (chaîne parlementaire) ;
  - les qualifications partisanes n'apparaissent qu'attribuées, en contexte.

Usage : python ingestion/seed_votes_cles.py [chemin_base]
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

THEMES = [
    ("ecologie-agriculture", "Écologie et agriculture"),
    ("pouvoir-achat-fiscalite", "Pouvoir d'achat et fiscalité"),
    ("securite-justice", "Sécurité et justice"),
    ("immigration", "Immigration"),
    ("societe", "Questions de société"),
    ("europe-international", "Europe et international"),
]

URL_CONGRES_IVG = "https://lcp.fr/actualites/apres-le-vote-du-congres-la-france-devient-le-premier-pays-au-monde-a-inscrire-l-ivg"

# (uid_officiel, thème, titre court, résumé neutre, contexte ou None)
VOTES = [
    # ── Écologie et agriculture ──────────────────────────────────────────────
    ("VTANR5L15V139", "ecologie-agriculture", "Fin des hydrocarbures (2017)",
     "Met fin progressivement à la recherche et à l'exploitation des hydrocarbures sur le territoire français à l'horizon 2040.",
     None),
    ("VTANR5L15V3738", "ecologie-agriculture", "Loi Climat et résilience (2021)",
     "Traduit une partie des propositions de la Convention citoyenne pour le climat : rénovation énergétique des logements, encadrement de la publicité, lutte contre l'artificialisation des sols.",
     "Première lecture, scrutin solennel du 4 mai 2021."),
    ("VTANR5L16V823", "ecologie-agriculture", "Accélération des énergies renouvelables (2023)",
     "Vise à accélérer le déploiement des énergies renouvelables : planification territoriale des zones d'implantation, simplification des procédures, développement de l'agrivoltaïsme.",
     None),
    ("VTANR5L17V2957", "ecologie-agriculture", "Loi sur les contraintes agricoles, dite « loi Duplomb » (2025)",
     "Lève plusieurs contraintes à l'exercice du métier d'agriculteur, dont la réintroduction à titre dérogatoire d'un insecticide néonicotinoïde interdit en France depuis 2018.",
     None),

    # ── Pouvoir d'achat et fiscalité ─────────────────────────────────────────
    ("VTANR5L16V186", "pouvoir-achat-fiscalite", "Mesures d'urgence pouvoir d'achat (2022)",
     "Ensemble de mesures face à l'inflation : revalorisation de prestations sociales, plafonnement de la hausse des loyers, prime de partage de la valeur.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L16V1240", "pouvoir-achat-fiscalite", "Réforme des retraites : motion de censure (2023)",
     "Motion de censure transpartisane déposée après l'engagement de responsabilité du Gouvernement (article 49.3) sur la réforme portant l'âge légal de départ à la retraite de 62 à 64 ans.",
     "La réforme n'a pas fait l'objet d'un vote direct à l'Assemblée. Voter pour la motion revenait à s'opposer à l'adoption du texte ; son rejet, à neuf voix près, a entraîné l'adoption définitive de la réforme. La position affichée est le vote sur la motion de censure."),
    ("VTANR5L17V881", "pouvoir-achat-fiscalite", "Impôt plancher sur les très hauts patrimoines (2025)",
     "Instaure un impôt plancher de 2 % sur le patrimoine des contribuables les plus fortunés (proposition dite « taxe Zucman », première lecture).",
     None),
    ("VTANR5L17V6319", "pouvoir-achat-fiscalite", "Lutte contre les fraudes sociales et fiscales (2026)",
     "Renforce les moyens de détection et de sanction des fraudes sociales et fiscales.",
     "Vote sur le texte issu de la commission mixte paritaire."),

    # ── Sécurité et justice ──────────────────────────────────────────────────
    ("VTANR5L15V138", "securite-justice", "Sécurité intérieure et lutte contre le terrorisme (2017)",
     "Transpose dans le droit commun plusieurs mesures de l'état d'urgence : périmètres de protection, fermeture de lieux de culte, mesures individuelles de contrôle administratif et de surveillance.",
     None),
    ("VTANR5L15V3254", "securite-justice", "Loi « sécurité globale » (2020)",
     "Élargit les compétences des polices municipales et de la sécurité privée, développe la vidéosurveillance et encadre la diffusion d'images des forces de l'ordre.",
     None),
    ("VTANR5L17V1473", "securite-justice", "Loi contre le narcotrafic (2025)",
     "Renforce les moyens d'enquête contre la criminalité organisée et crée un parquet national dédié ainsi qu'un régime de détention spécifique pour les trafiquants les plus dangereux.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L17V7987", "securite-justice", "Présomption de légitime défense des forces de l'ordre (2026)",
     "Reconnaît une présomption de légitime défense au bénéfice des membres des forces de l'ordre faisant usage de leur arme dans l'exercice de leurs fonctions.",
     "Adoptée en première lecture le 7 juillet 2026 ; la navette parlementaire se poursuit au Sénat. Ses opposants qualifient le texte de « permis de tuer », ses partisans de protection nécessaire des agents — qualifications rapportées, que le site ne reprend pas à son compte."),

    # ── Immigration ──────────────────────────────────────────────────────────
    ("VTANR5L15V578", "immigration", "Loi asile et immigration (2018)",
     "Réduit les délais d'examen des demandes d'asile, allonge la durée maximale de rétention administrative et facilite l'éloignement des personnes déboutées.",
     None),
    ("VTANR5L16V3213", "immigration", "Loi immigration (2023)",
     "Modifie les conditions d'entrée, de séjour, de regroupement familial et d'accès aux prestations sociales des étrangers, et instaure une régularisation encadrée dans les métiers en tension.",
     "Vote sur le texte issu de la commission mixte paritaire ; le Conseil constitutionnel a ensuite censuré une large partie de ses articles (janvier 2024)."),
    ("VTANR5L17V1308", "immigration", "Conditions d'accès à la nationalité (2025)",
     "Renforce les conditions d'accès à la nationalité française.",
     None),
    ("VTANR5L17V7405", "immigration", "Sécurité et rétention administrative (2026)",
     "Renforce les dispositifs de sécurité et étend les possibilités de rétention administrative des étrangers en instance d'éloignement.",
     "Texte transversal sécurité/immigration, rattaché ici à son objet principal (règle « un vote = un thème »)."),

    # ── Questions de société ─────────────────────────────────────────────────
    ("VTANR5L15V2146", "societe", "Bioéthique : PMA pour toutes (2019)",
     "Ouvre la procréation médicalement assistée aux couples de femmes et aux femmes seules, et réforme l'accès aux origines des enfants nés de dons.",
     "Première lecture ; le texte a été définitivement adopté en 2021."),
    ("VTCGR5L16V1", "societe", "IVG dans la Constitution (Congrès, 2024)",
     "Inscrit dans la Constitution la liberté garantie de la femme de recourir à l'interruption volontaire de grossesse.",
     "Adopté par le Parlement réuni en Congrès à Versailles par 780 voix pour et 72 contre : seul vote de la base où députés et sénateurs sont directement comparables."),
    ("VTANR5L17V5728", "societe", "Accompagnement et soins palliatifs (2026)",
     "Vise à garantir l'égal accès de tous à l'accompagnement et aux soins palliatifs.",
     "Deuxième lecture ; texte examiné conjointement avec la proposition de loi sur l'aide à mourir."),
    ("VTANR5L17V8280", "societe", "Droit à l'aide à mourir (2026)",
     "Crée un droit à l'aide à mourir, sous conditions strictes, pour les personnes majeures atteintes d'une affection grave et incurable engageant le pronostic vital.",
     "Lecture définitive du 15 juillet 2026, au terme de quatre lectures à l'Assemblée."),

    # ── Europe et international ──────────────────────────────────────────────
    ("VTANR5L15V2059", "europe-international", "Ratification du CETA (2019)",
     "Autorise la ratification de l'accord économique et commercial global (CETA) entre l'Union européenne et le Canada.",
     "Rattaché au thème Europe et international (accord commercial), bien que ses effets agricoles aient marqué le débat."),
    ("VTANR5L16V652", "europe-international", "Soutien à l'Ukraine (2022)",
     "Résolution affirmant le soutien de l'Assemblée nationale à l'Ukraine et condamnant l'agression menée par la Russie.",
     None),
    ("VTANR5L17V456", "europe-international", "Accord UE-Mercosur : déclaration du Gouvernement (2024)",
     "Vote sur la déclaration du Gouvernement relative aux négociations de l'accord d'association entre l'Union européenne et le Mercosur.",
     "Vote au titre de l'article 50-1 de la Constitution : il exprime la position formelle de l'Assemblée, sans effet législatif direct."),
    ("VTANR5L17V988", "europe-international", "Renforcement du soutien à l'Ukraine (2025)",
     "Résolution européenne appelant au renforcement du soutien de la France et de l'Union européenne à l'Ukraine.",
     None),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    if cur.execute("SELECT COUNT(*) FROM votes_cles").fetchone()[0]:
        sys.exit("La table votes_cles n'est pas vide — la vider avant de re-semer.")

    ids_theme = {}
    for ordre, (slug, libelle) in enumerate(THEMES, start=1):
        cur.execute("INSERT INTO thematiques (libelle, ordre) VALUES (?,?)", (libelle, ordre))
        ids_theme[slug] = cur.lastrowid

    ordre_par_theme = {}
    for uid, theme, titre, resume, contexte in VOTES:
        scrutin = cur.execute(
            "SELECT id, legislature, numero, chambre FROM scrutins WHERE uid_officiel = ?",
            (uid,)).fetchone()
        if scrutin is None:
            sys.exit(f"Scrutin {uid} introuvable en base — la sélection doit pointer des scrutins importés.")
        sid, leg, numero, chambre = scrutin
        if chambre == "congres":
            url = URL_CONGRES_IVG
        else:
            url = f"https://www.assemblee-nationale.fr/dyn/{leg}/scrutins/{numero}"
        ordre_par_theme[theme] = ordre_par_theme.get(theme, 0) + 1
        cur.execute(
            "INSERT INTO votes_cles (scrutin_id, thematique_id, titre, resume, source_resume, contexte, ordre) "
            "VALUES (?,?,?,?,?,?,?)",
            (sid, ids_theme[theme], titre, resume, url, contexte, ordre_par_theme[theme]))

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM votes_cles").fetchone()[0]
    couv = cur.execute("SELECT COUNT(*) FROM couverture").fetchone()[0]
    print(f"Semé : {len(THEMES)} thématiques, {n} votes clés. Vue couverture : {couv} états calculés.")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

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
    ("institutions", "Institutions et vie démocratique"),
]

URL_CONGRES_IVG = "https://lcp.fr/actualites/apres-le-vote-du-congres-la-france-devient-le-premier-pays-au-monde-a-inscrire-l-ivg"

# (uid_officiel, thème, titre court, résumé neutre, contexte ou None)
# Les résumés décrivent le contenu en langage courant, sans reprendre le
# vocabulaire des promoteurs ni celui des opposants du texte.
VOTES = [
    # ── Écologie et agriculture ──────────────────────────────────────────────
    ("VTANR5L15V139", "ecologie-agriculture", "Fin des hydrocarbures (2017)",
     "Interdit progressivement, d'ici 2040, de rechercher et d'extraire du pétrole et du gaz sur le territoire français.",
     None),
    ("VTANR5L15V3738", "ecologie-agriculture", "Loi Climat et résilience (2021)",
     "Traduit une partie des propositions de la Convention citoyenne pour le climat : rénovation énergétique des logements, encadrement de la publicité, limitation de la bétonisation des sols.",
     "Première lecture, scrutin solennel du 4 mai 2021."),
    ("VTANR5L16V823", "ecologie-agriculture", "Accélération des énergies renouvelables (2023)",
     "Facilite l'installation d'éoliennes, de panneaux solaires et d'autres énergies renouvelables : zones d'implantation définies par les communes, procédures accélérées.",
     None),
    ("VTANR5L17V2957", "ecologie-agriculture", "Loi agricole dite « loi Duplomb » (2025)",
     "Autorise de nouveau, par dérogation, l'acétamipride — un insecticide néonicotinoïde interdit en France mais autorisé ailleurs en Europe, réclamé par une partie des filières agricoles — et facilite certains stockages d'eau pour l'irrigation ainsi que des agrandissements d'élevages.",
     "Texte soutenu par la FNSEA et la Coordination rurale, combattu par la Confédération paysanne, les apiculteurs et des associations de santé et d'environnement. Une pétition record (plus de deux millions de signatures) a demandé son abrogation, et le Conseil constitutionnel a censuré la réintroduction de l'acétamipride en août 2025 — après ce scrutin."),

    # ── Pouvoir d'achat et fiscalité ─────────────────────────────────────────
    ("VTANR5L16V186", "pouvoir-achat-fiscalite", "Mesures d'urgence pouvoir d'achat (2022)",
     "Série de mesures face à l'inflation : revalorisation des pensions et prestations sociales, plafonnement temporaire des hausses de loyer, primes versées par les employeurs.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L16V1240", "pouvoir-achat-fiscalite", "Réforme des retraites : motion de censure (2023)",
     "Motion de censure transpartisane déposée après l'engagement de responsabilité du Gouvernement (article 49.3) sur la réforme portant l'âge légal de départ à la retraite de 62 à 64 ans.",
     "La réforme n'a pas fait l'objet d'un vote direct à l'Assemblée. Voter pour la motion revenait à s'opposer à l'adoption du texte ; son rejet, à neuf voix près, a entraîné l'adoption définitive de la réforme. La position affichée est le vote sur la motion de censure."),
    ("VTANR5L17V881", "pouvoir-achat-fiscalite", "Impôt plancher sur les très hauts patrimoines (2025)",
     "Crée un impôt minimal annuel de 2 % sur le patrimoine des foyers possédant plus de 100 millions d'euros (proposition dite « taxe Zucman »).",
     "Proposition d'origine parlementaire, adoptée en première lecture à l'Assemblée ; elle n'était pas devenue loi à la date de mise à jour du site."),
    ("VTANR5L17V6319", "pouvoir-achat-fiscalite", "Lutte contre les fraudes sociales et fiscales (2026)",
     "Renforce les contrôles et les sanctions contre la fraude aux prestations sociales et la fraude fiscale.",
     "Vote sur le texte issu de la commission mixte paritaire."),

    # ── Sécurité et justice ──────────────────────────────────────────────────
    ("VTANR5L15V138", "securite-justice", "Sécurité intérieure et lutte contre le terrorisme (2017)",
     "Fait entrer dans le droit commun plusieurs pouvoirs jusque-là réservés à l'état d'urgence : périmètres de sécurité, fermeture administrative de lieux de culte, mesures individuelles de contrôle et de surveillance.",
     None),
    ("VTANR5L15V3254", "securite-justice", "Loi « sécurité globale » (2020)",
     "Donne davantage de pouvoirs aux polices municipales et à la sécurité privée, développe la vidéosurveillance (dont les drones) et crée un délit de diffusion d'images de policiers avec intention de nuire.",
     None),
    ("VTANR5L17V1473", "securite-justice", "Loi contre le narcotrafic (2025)",
     "Crée un parquet national dédié à la criminalité organisée, des quartiers de détention de haute sécurité pour les trafiquants jugés les plus dangereux, et étend les pouvoirs d'enquête et de renseignement.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L17V7987", "securite-justice", "Présomption de légitime défense des forces de l'ordre (2026)",
     "Instaure une présomption : lorsqu'un policier ou un gendarme fait usage de son arme en service, la justice doit partir du principe qu'il était en état de légitime défense, à charge pour l'accusation de démontrer le contraire.",
     "Adoptée en première lecture le 7 juillet 2026 ; la navette parlementaire se poursuit au Sénat. Ses opposants qualifient le texte de « permis de tuer », ses partisans de protection nécessaire des agents — qualifications rapportées, que le site ne reprend pas à son compte."),

    # ── Immigration ──────────────────────────────────────────────────────────
    ("VTANR5L15V578", "immigration", "Loi asile et immigration (2018)",
     "Réduit les délais pour demander l'asile et contester un refus, porte la durée maximale de rétention administrative de 45 à 90 jours et facilite les éloignements.",
     None),
    ("VTANR5L16V3213", "immigration", "Loi immigration (2023)",
     "Durcit les conditions de regroupement familial et d'accès aux prestations sociales des étrangers, facilite les expulsions, et crée une régularisation encadrée pour les métiers en manque de main-d'œuvre.",
     "Vote sur le texte issu de la commission mixte paritaire ; le Conseil constitutionnel a ensuite censuré une large partie de ses articles (janvier 2024)."),
    ("VTANR5L17V1308", "immigration", "Conditions d'accès à la nationalité (2025)",
     "Restreint les conditions d'accès à la nationalité française.",
     None),
    ("VTANR5L17V7405", "immigration", "Sécurité et rétention administrative (2026)",
     "Allonge et élargit les possibilités de placer en rétention les étrangers visés par une mesure d'éloignement.",
     "Texte transversal sécurité/immigration, rattaché ici à son objet principal (règle « un vote = un thème »)."),

    # ── Questions de société ─────────────────────────────────────────────────
    ("VTANR5L15V2146", "societe", "Bioéthique : PMA pour toutes (2019)",
     "Ouvre la procréation médicalement assistée (PMA) aux couples de femmes et aux femmes seules, avec prise en charge par la Sécurité sociale, et permet aux enfants nés d'un don d'accéder à leurs origines.",
     "Première lecture ; le texte a été définitivement adopté en 2021."),
    ("VTCGR5L16V1", "societe", "IVG dans la Constitution (Congrès, 2024)",
     "Inscrit dans la Constitution la liberté garantie de la femme de recourir à l'interruption volontaire de grossesse.",
     "Adopté par le Parlement réuni en Congrès à Versailles par 780 voix pour et 72 contre : seul vote de la base où députés et sénateurs sont directement comparables."),
    ("VTANR5L17V5728", "societe", "Accompagnement et soins palliatifs (2026)",
     "Organise le développement des soins palliatifs et de l'accompagnement de la fin de vie sur l'ensemble du territoire.",
     "Deuxième lecture ; texte examiné conjointement avec la proposition de loi sur l'aide à mourir."),
    ("VTANR5L17V8280", "societe", "Droit à l'aide à mourir (2026)",
     "Crée un droit à l'aide à mourir — la possibilité, très encadrée, de recevoir ou de s'administrer une substance létale — pour les personnes majeures atteintes d'une affection grave et incurable engageant le pronostic vital.",
     "Lecture définitive du 15 juillet 2026, au terme de quatre lectures à l'Assemblée."),

    # ── Europe et international ──────────────────────────────────────────────
    ("VTANR5L15V2059", "europe-international", "Ratification du CETA (2019)",
     "Autorise la ratification de l'accord de libre-échange entre l'Union européenne et le Canada (CETA), qui supprime l'essentiel des droits de douane entre les deux zones.",
     "Tous les candidats suivis alors en poste ont voté contre, pour des motifs différents selon les groupes : impacts sur l'élevage, normes sanitaires et climat à gauche, souveraineté au RN et à DLF. Le Sénat a ensuite rejeté le texte (2024) ; l'accord reste appliqué à titre provisoire."),
    ("VTANR5L16V652", "europe-international", "Soutien à l'Ukraine (2022)",
     "Résolution affirmant le soutien de l'Assemblée nationale à l'Ukraine et condamnant l'agression menée par la Russie.",
     None),
    ("VTANR5L17V456", "europe-international", "Accord UE-Mercosur : déclaration du Gouvernement (2024)",
     "Vote sur la déclaration par laquelle le Gouvernement exprimait l'opposition de la France à l'accord commercial UE-Mercosur en l'état des négociations : voter « pour » soutenait cette opposition.",
     "Vote au titre de l'article 50-1 de la Constitution : il exprime la position formelle de l'Assemblée, sans effet législatif direct."),
    ("VTANR5L17V988", "europe-international", "Renforcement du soutien à l'Ukraine (2025)",
     "Résolution européenne appelant à renforcer le soutien à l'Ukraine, notamment en mobilisant les avoirs russes gelés, et à faciliter le processus d'adhésion de l'Ukraine à l'Union européenne.",
     None),

    # ── Extension 14e législature (2012-2017), validée le 24/07/2026 ────────
    ("VTANR5L14V511", "societe", "Mariage pour tous (2013)",
     "Ouvre le mariage et l'adoption aux couples de personnes de même sexe.",
     "Deuxième lecture du 23 avril 2013 — dernier vote d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V1070", "societe", "Fin de vie : loi Claeys-Leonetti (2015)",
     "Crée un droit à la sédation profonde et continue jusqu'au décès pour les malades en phase terminale et rend contraignantes les directives anticipées.",
     "Première lecture ; le texte a été définitivement adopté début 2016. C'est le cadre que la loi sur l'aide à mourir de 2026 est venue compléter."),
    ("VTANR5L14V726", "pouvoir-achat-fiscalite", "Réforme des retraites Touraine (2013)",
     "Allonge progressivement la durée de cotisation jusqu'à 43 annuités et crée le compte personnel de prévention de la pénibilité.",
     "Nouvelle lecture du 26 novembre 2013 — dernier scrutin public d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V1270", "pouvoir-achat-fiscalite", "Loi travail (El Khomri) : motion de censure (2016)",
     "Motion de censure déposée après l'engagement de responsabilité du Gouvernement (article 49.3) sur la loi travail : accords d'entreprise prioritaires sur les accords de branche, encadrement du licenciement économique.",
     "Comme pour les retraites en 2023, le texte n'a pas fait l'objet d'un vote direct : voter pour la motion revenait à s'opposer à son adoption ; son rejet a permis l'adoption de la loi."),
    ("VTANR5L14V1109", "securite-justice", "Loi renseignement (2015)",
     "Légalise et encadre des techniques de surveillance élargies pour les services de renseignement (traitement algorithmique des connexions, IMSI-catchers), sous le contrôle d'une nouvelle autorité, la CNCTR.",
     "Votée quelques mois après les attentats de janvier 2015."),
    ("VTANR5L14V1191", "securite-justice", "Prorogation de l'état d'urgence (2015)",
     "Proroge de trois mois l'état d'urgence déclaré après les attentats du 13 novembre 2015 et en renforce les mesures (perquisitions administratives, assignations à résidence).",
     None),
    ("VTANR5L14V994", "immigration", "Réforme de l'asile (2014)",
     "Réorganise l'examen des demandes d'asile : procédures accélérées, recours suspensif généralisé, hébergement directif des demandeurs.",
     None),
    ("VTANR5L14V1237", "immigration", "Déchéance de nationalité — « protection de la Nation » (2016)",
     "Révision constitutionnelle inscrivant l'état d'urgence dans la Constitution et permettant la déchéance de nationalité des personnes condamnées pour terrorisme.",
     "Première lecture. La révision a été abandonnée en mars 2016 faute d'accord entre l'Assemblée et le Sénat : le Congrès n'a jamais été réuni."),
    ("VTANR5L14V1120", "ecologie-agriculture", "Transition énergétique (2015)",
     "Fixe les grands objectifs énergétiques : part du nucléaire ramenée à 50 % de l'électricité, division par deux de la consommation d'énergie d'ici 2050, interdiction des sacs plastique à usage unique.",
     "Nouvelle lecture du 26 mai 2015 — dernier scrutin public d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V30", "europe-international", "Ratification du traité budgétaire européen (TSCG, 2012)",
     "Autorise la ratification du traité européen sur la stabilité, la coordination et la gouvernance (TSCG), qui impose la « règle d'or » de limitation des déficits structurels.",
     None),
    ("VTANR5L14V594", "institutions", "Transparence de la vie publique (2013)",
     "Crée la Haute Autorité pour la transparence de la vie publique (HATVP) et impose aux membres du Gouvernement et aux élus des déclarations de patrimoine et d'intérêts publiques.",
     "Adoptée après l'affaire Cahuzac (lecture définitive). Ce sont ces déclarations HATVP que le présent site utilise pour la partie « parcours » des candidats."),
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

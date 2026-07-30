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
    ("pouvoir-achat-fiscalite", "Économie"),
    ("securite-justice", "Sécurité et justice"),
    ("immigration", "Immigration"),
    ("societe", "Questions de société"),
    ("europe-international", "Europe et international"),
    ("institutions", "Institutions et vie démocratique"),
    ("sante", "Santé"),
    ("education", "Éducation"),
    ("taxe-impots", "Taxe et impôts"),
    ("budget", "Budget"),
    ("travail", "Travail"),
    ("logement", "Logement"),
    ("defense", "Défense"),
    ("femmes", "Droits des femmes"),
]

# Thème « Budget » : lu par AXES de questions, pas vote par vote. Chaque axe
# regroupe des amendements emblématiques des lois de finances (PLF/PLFSS). L'ordre
# et les libellés d'affichage vivent aussi dans build_site.py (AXES_BUDGET) ; ici,
# on ne stocke que le slug de l'axe et le « sens de l'axe » sur chaque vote clé.
#   {uid : (slug_axe, position qui va dans le sens de l'axe)}
# sens_axe = 'pour'  -> voter POUR ce scrutin va dans le sens de l'axe
#            'contre'-> voter CONTRE ce scrutin va dans le sens de l'axe
# (ex. amendement « supprimer telle taxe » : voter CONTRE = taxer davantage).
AXES = {
    # Axe « capital » : voter POUR = taxer davantage le capital / les hauts patrimoines.
    "VTANR5L17V3300": ("capital", "pour"),   # taxe Zucman
    "VTANR5L17V3242": ("capital", "pour"),   # super-dividendes
    "VTANR5L17V3187": ("capital", "pour"),   # multinationales 25 %
    "VTANR5L17V3199": ("capital", "pour"),   # doublement taxe GAFAM
    "VTANR5L17V3149": ("capital", "pour"),   # surtaxe grandes entreprises
    "VTANR5L16V325": ("capital", "pour"),     # rétablissement de l'ISF
    "VTANR5L17V3335": ("capital", "pour"),    # suppression du PFU
    "VTANR5L17V3336": ("capital", "pour"),    # relèvement du taux du PFU
    # Axe « pouvoir-achat » : voter POUR = alléger l'impôt des ménages modestes.
    "VTANR5L17V3096": ("pouvoir-achat", "pour"),  # indexation du barème sur l'inflation
    "VTANR5L17V10": ("pouvoir-achat", "pour"),    # nouvelles tranches, reste à vivre
    # Axe « ecologie-fiscale » : voter POUR = taxer la pollution.
    "VTANR5L17V3848": ("ecologie-fiscale", "pour"),  # taxe sur les jets privés
    # ── Défense : sections (axe = section ; pas de sens_axe, pas de posture) ──
    "VTANR5L16V2256": ("budget-defense", None),
    # Sous-section « incendies » du thème Écologie et agriculture.
    "VTANR5L16V133": ("incendies", None),
    "VTANR5L16V1509": ("incendies", None),
    "VTANR5L16V1545": ("incendies", None),
    "VTANR5L16V1556": ("incendies", None),
    "VTANR5L17V4114": ("incendies", None),
    # Sous-section « climat-energie » du thème Écologie et agriculture.
    "VTANR5L15V139": ("climat-energie", None),
    "VTANR5L15V3738": ("climat-energie", None),
    "VTANR5L16V823": ("climat-energie", None),
    "VTANR5L14V1120": ("climat-energie", None),
    "PE-HTV-152544": ("climat-energie", None),
    "PE-HTV-164499": ("climat-energie", None),
    "PE-HTV-154173": ("climat-energie", None),
    "PE-HTV-110615": ("climat-energie", None),
    "PE-HTV-118521": ("climat-energie", None),
    "PE-HTV-126261": ("climat-energie", None),
    "PE-HTV-117083": ("climat-energie", None),
    "PE-HTV-184178": ("climat-energie", None),
    "VTANR5L16V1533": ("climat-energie", None),
    "VTANR5L16V2721": ("climat-energie", None),
    "PE-HTV-144789": ("climat-energie", None),
    "VTANR5L16V1989": ("climat-energie", None),
    # Sous-section « agriculture-alimentation » du thème Écologie et agriculture.
    "VTANR5L15V729": ("agriculture-alimentation", None),
    "VTANR5L17V8427": ("agriculture-alimentation", None),
    # Sous-section « élevage » du thème Écologie et agriculture.
    "VTANR5L16V3750": ("elevage", None),
    "VTANR5L17V3217": ("elevage", None),
    "VTANR5L16V1370": ("elevage", None),
    "VTANR5L16V1377": ("elevage", None),
    "VTANR5L16V3782": ("elevage", None),
    "VTANR5L17V2957": ("agriculture-alimentation", None),   # loi Duplomb, déjà en base
    # Sous-section « fiscalité de l'énergie » du thème Écologie et agriculture.
    "VTANR5L16V517": ("fiscalite-energie", None),
    "VTANR5L17V110": ("fiscalite-energie", None),
    "VTANR5L17V3958": ("fiscalite-energie", None),
    "VTANR5L17V4046": ("fiscalite-energie", None),
    "VTANR5L17V144": ("fiscalite-energie", None),
    "VTANR5L17V3830": ("fiscalite-energie", None),
    "PE-HTV-172867": ("budget-defense", None),
    "PE-HTV-174053": ("budget-defense", None),
    "PE-HTV-181587": ("budget-defense", None),
    "VTANR5L16V652": ("ukraine", None),
    "VTANR5L17V988": ("ukraine", None),
    "PE-HTV-164536": ("ukraine", None),
    "PE-HTV-169362": ("ukraine", None),
    "PE-HTV-179048": ("proche-orient", None),
    "VTANR5L17V683": ("proche-orient", None),
    "VTANR5L16V1456": ("proche-orient", None),
    "VTANR5L14V510": ("engagements", None),
    "VTANR5L14V998": ("engagements", None),
    "VTANR5L14V1195": ("engagements", None),
    "VTANR5L16V650": ("engagements", None),
    "VTANR5L16V1483": ("engagements", None),
}

URL_CONGRES_IVG = "https://lcp.fr/actualites/apres-le-vote-du-congres-la-france-devient-le-premier-pays-au-monde-a-inscrire-l-ivg"

# (uid_officiel, thème, titre court, résumé neutre, contexte ou None)
# Les résumés décrivent le contenu en langage courant, sans reprendre le
# vocabulaire des promoteurs ni celui des opposants du texte.
VOTES = [
    # ── Écologie et agriculture ──────────────────────────────────────────────
    ("VTANR5L15V139", "ecologie-agriculture", "Fin des hydrocarbures (2017)",
     "Interdit progressivement, d'ici 2040, de rechercher et d'extraire du pétrole et du gaz sur le sol français : plus aucun nouveau permis, et les permis existants ne sont pas prolongés au-delà de cette date. La France produisant très peu d'hydrocarbures, l'effet sur l'approvisionnement est limité : l'enjeu porte surtout sur le signal d'une sortie programmée des énergies fossiles.",
     None),
    ("VTANR5L15V3738", "ecologie-agriculture", "Loi Climat et résilience (2021)",
     "Traduit dans la loi une partie des propositions de la Convention citoyenne pour le climat (150 citoyens tirés au sort). Principales mesures : rénovation des logements mal isolés, avec interdiction progressive de louer les plus énergivores ; encadrement de la publicité pour les produits polluants ; objectif de « zéro artificialisation nette » pour freiner la bétonisation des terres ; zones à faibles émissions dans les grandes villes. L'enjeu : réduire les émissions de la France en agissant sur le logement, la consommation et l'aménagement du territoire.",
     "Première lecture, scrutin solennel du 4 mai 2021."),
    ("VTANR5L16V823", "ecologie-agriculture", "Accélération des énergies renouvelables (2023)",
     "Facilite et accélère l'installation d'énergies renouvelables (éoliennes, panneaux solaires) : les communes délimitent des « zones d'accélération » prioritaires et les procédures d'autorisation sont raccourcies. L'enjeu : produire plus vite une électricité bas-carbone et moins dépendante des importations, la question débattue étant l'équilibre entre rapidité des projets et pouvoir de décision des habitants sur leur implantation.",
     None),
    ("VTANR5L17V2957", "ecologie-agriculture", "Loi agricole dite « loi Duplomb » (2025)",
     "Réautorise, par dérogation, l'acétamipride (un insecticide de la famille des néonicotinoïdes, réputés dangereux pour les abeilles, interdit en France depuis 2018 mais encore autorisé ailleurs en Europe), réclamé par une partie des agriculteurs (betteraves, noisettes) faute d'alternative jugée efficace. Le texte facilite aussi la création de réserves d'eau pour l'irrigation et l'agrandissement de certains élevages. L'enjeu : la compétitivité de ces filières face à la concurrence européenne, mise en balance avec la protection des pollinisateurs, de l'eau et de la santé.",
     "Texte soutenu par la FNSEA et la Coordination rurale, combattu par la Confédération paysanne, les apiculteurs et des associations de santé et d'environnement. Une pétition record (plus de deux millions de signatures) a demandé son abrogation, et le Conseil constitutionnel a censuré la réintroduction de l'acétamipride en août 2025, après ce scrutin."),
    ("VTANR5L17V8427", "ecologie-agriculture", "Loi d'urgence pour la protection et la souveraineté agricoles (2026)",
     "Vise à soutenir l'agriculture française face aux crises climatiques et à la concurrence internationale : facilite les réserves d'eau pour l'irrigation, renforce les contrôles sur les denrées importées aux frontières et interdit l'achat de produits non-européens pour la restauration collective publique, réduit les délais de négociation entre agriculteurs et premiers acheteurs, et permet aux porteurs de certains projets (agricoles, énergétiques, d'infrastructure) d'obtenir réparation en cas de recours jugé abusif contre leur projet. Autorise aussi, à titre dérogatoire et via une procédure d'évaluation accélérée (60 jours, contre 12 mois habituellement), la réintroduction de produits phytosanitaires interdits en France dont l'acétamipride, un insecticide de la famille des néonicotinoïdes. L'enjeu : la compétitivité de l'agriculture française, mise en balance avec la protection de l'eau, des pollinisateurs et de la santé.",
     "Adopté une première fois le 2 juin 2026 (scrutin n°7259 : 369 pour, 178 contre, 15 abstentions), puis, sur le texte de compromis de la commission mixte paritaire, le 20 juillet 2026 (scrutin n°8427 : 296 pour, 224 contre, 41 abstentions) : c'est ce second vote, définitif à l'Assemblée, qui est affiché ici. Reprend, sur les pesticides, un dispositif proche de celui de la loi Duplomb (2025), partiellement censuré par le Conseil constitutionnel après son adoption. Le Conseil, de nouveau saisi le 24 juillet 2026, ne s'était pas prononcé à la date de mise à jour du site : cette disposition est un candidat plausible à une nouvelle censure."),

    # ── Incendies et prévention des feux de forêt (sous-section, ajout 27/07/2026) ──
    ("VTANR5L16V133", "ecologie-agriculture", "Recrutement de pompiers professionnels (2022)",
     "Amendement au budget rectificatif 2022 visant à financer la création d'un programme de recrutement de pompiers professionnels supplémentaires. L'enjeu : renforcer les effectifs de la sécurité civile face à l'intensification des feux de forêt, le débat portant sur le coût budgétaire de la mesure.",
     None),
    ("VTANR5L16V1509", "ecologie-agriculture", "Plan d'adaptation de la forêt au changement climatique (2023)",
     "Amendement à la proposition de loi sur le risque incendie visant à élaborer un plan d'adaptation de la forêt cohérent avec la Stratégie nationale bas-carbone (SNBC), en lien avec le Haut Conseil pour le climat. L'enjeu : anticiper l'évolution des essences et des peuplements forestiers face à un climat plus propice aux incendies.",
     None),
    ("VTANR5L16V1545", "ecologie-agriculture", "Entretien des chemins forestiers contre les incendies (2023)",
     "Amendement à la proposition de loi sur le risque incendie visant à lutter contre la perte de chemins forestiers, jugés nécessaires à la circulation des services de secours et à la prévention des feux. L'enjeu : l'entretien de ces accès, financé notamment par les propriétaires forestiers et les collectivités.",
     None),
    ("VTANR5L16V1556", "ecologie-agriculture", "Pare-feux d'arbres feuillus (2023)",
     "Amendement à la proposition de loi sur le risque incendie visant à imposer la mise en place de pare-feux d'arbres feuillus entre les parcelles de résineux, plus inflammables. L'enjeu : ralentir la propagation des flammes dans les massifs forestiers, la question débattue étant la contrainte imposée aux propriétaires et exploitants forestiers.",
     None),
    ("VTANR5L17V4114", "ecologie-agriculture", "Contribution des assurances au financement des pompiers (2025)",
     "Amendement au budget 2026 visant à relever la part départementale de la taxe sur les conventions d'assurance (TSCA) pour financer les services départementaux d'incendie et de secours (SDIS). L'enjeu : donner aux pompiers des moyens supplémentaires face à des feux plus fréquents et plus intenses, en faisant contribuer davantage les sociétés d'assurance, mis en balance avec le coût pour les assurés.",
     None),

    # ── Élevage et bien-être animal (sous-section, ajout 27/07/2026) ──────────
    ("VTANR5L16V3750", "ecologie-agriculture", "Moratoire sur les nouveaux élevages en cage (2024)",
     "Amendement à la loi d'orientation agricole visant à instaurer un moratoire sur la construction de nouveaux bâtiments d'élevage en cage. L'enjeu : le bien-être animal dans les élevages, mis en balance avec les conséquences pour les filières concernées (poules pondeuses, lapins notamment).",
     None),
    ("VTANR5L17V3217", "ecologie-agriculture", "Impôt sur les sociétés renforcé pour les élevages classés à risque (2025)",
     "Amendement au budget 2026 visant à rétablir un taux d'impôt sur les sociétés de 35 % pour les élevages soumis au régime d'autorisation environnementale (installations classées, généralement les plus grandes). L'enjeu : décourager fiscalement l'agrandissement des élevages industriels, mis en balance avec la compétitivité de ces filières.",
     None),
    ("VTANR5L16V1370", "ecologie-agriculture", "Option végétarienne quotidienne en restauration collective (2023)",
     "Amendement visant à imposer une option végétarienne quotidienne dans la restauration collective (cantines scolaires, administrations). L'enjeu : diversifier l'offre alimentaire et réduire la consommation de viande, mis en balance avec la liberté de gestion des collectivités et le coût de mise en œuvre.",
     None),
    ("VTANR5L16V1377", "ecologie-agriculture", "Interdiction progressive des additifs nitrés dans la charcuterie (2023)",
     "Amendement visant à rétablir l'interdiction progressive des additifs nitrés (nitrites et nitrates) dans les produits de charcuterie, soupçonnés d'augmenter le risque de cancer colorectal. L'enjeu : la santé publique, mis en balance avec les difficultés techniques et économiques invoquées par la filière charcutière pour s'en passer.",
     None),
    ("VTANR5L16V3782", "ecologie-agriculture", "Développement de l'élevage en pâturage et plein air (2024)",
     "Amendement à la loi d'orientation agricole appelant au développement de l'élevage en pâturage et plein air, alternative à l'élevage en bâtiment fermé. L'enjeu : promouvoir des modes d'élevage jugés plus respectueux du bien-être animal, sans y contraindre les exploitants.",
     None),

    # ── Fiscalité de l'énergie et du carbone (sous-section, ajout 27/07/2026) ──
    ("VTANR5L16V517", "ecologie-agriculture", "Taxe carbone sur les vols en jet privé (2022)",
     "Amendement au second budget rectificatif pour 2022 visant à créer une taxe sur la circulation des aéronefs privés au-dessus de l'espace aérien national, assise sur leurs émissions de dioxyde de carbone, au taux de 44,60 euros par tonne émise ; les aéronefs individuels de plaisance en sont exclus. L'enjeu : faire contribuer ces vols à la transition écologique, mis en balance avec l'activité du secteur de l'aviation d'affaires.",
     None),
    ("VTANR5L17V110", "ecologie-agriculture", "Suppression de la niche fiscale sur le kérosène aérien (2024)",
     "Amendement au budget 2025 visant à supprimer l'exonération de taxe intérieure de consommation dont bénéficie le kérosène utilisé par l'aviation. L'enjeu : aligner la fiscalité du transport aérien sur celle des autres carburants, mis en balance avec la compétitivité du secteur aérien français face à la concurrence internationale.",
     None),
    ("VTANR5L17V3958", "ecologie-agriculture", "Fin de la taxation réduite du charbon pour les entreprises énergo-intensives (2025)",
     "Amendement au budget 2026 visant à mettre fin au tarif réduit de taxation du charbon dont bénéficient les entreprises grandes consommatrices d'énergie. L'enjeu : renchérir l'usage d'une énergie fossile très émettrice, mis en balance avec la compétitivité de ces industries.",
     None),
    ("VTANR5L17V4046", "ecologie-agriculture", "TVA à 5,5 % sur les transports en commun (2025)",
     "Amendement au budget 2026 visant à abaisser à 5,5 % (taux réduit) la TVA sur les titres de transports en commun, aujourd'hui taxés à 10 %. L'enjeu : rendre les transports collectifs plus abordables pour inciter à leur usage, mis en balance avec la perte de recettes pour l'État.",
     None),
    ("VTANR5L17V144", "ecologie-agriculture", "TVA à 5,5 % sur le gaz, l'électricité, le fioul et les carburants (2024)",
     "Amendement au budget 2025, déposé par un député du Rassemblement national, visant à abaisser à 5,5 % la TVA sur le gaz, l'électricité, le fioul domestique et les carburants. L'enjeu : le pouvoir d'achat des ménages face au coût de l'énergie, mis en balance avec la perte de recettes pour l'État et l'incitation à réduire sa consommation d'énergies fossiles.",
     None),
    ("VTANR5L17V3830", "ecologie-agriculture", "Suppression du malus écologique sur les véhicules (2025)",
     "Amendement au budget 2026 visant à supprimer le malus écologique, une taxe appliquée à l'achat des véhicules neufs les plus émetteurs de CO2. L'enjeu : le pouvoir d'achat des ménages achetant un véhicule thermique, mis en balance avec l'incitation à acheter des véhicules moins polluants.",
     None),

    # ── Écologie et agriculture : hors sous-section ───────────────────────────
    ("VTANR5L16V1989", "ecologie-agriculture", "Réserver 1 % de l'enveloppe d'artificialisation aux pistes cyclables (2023)",
     "Amendement réservant, au sein des schémas de cohérence territoriale, 1 % de l'enveloppe d'artificialisation des sols à la création ou à l'extension de pistes cyclables intercommunales, mobilisable en priorité par les communes peu denses et très peu denses ; les conditions techniques limitant l'impact sur la biodiversité seraient fixées par décret en Conseil d'État. L'enjeu : permettre le développement de réseaux cyclables en zone rurale sans que ces aménagements soient bloqués par l'objectif de « zéro artificialisation nette ».",
     None),

    # ── Pouvoir d'achat et fiscalité ─────────────────────────────────────────
    ("VTANR5L16V186", "pouvoir-achat-fiscalite", "Mesures d'urgence pouvoir d'achat (2022)",
     "Ensemble de mesures adoptées face à la forte inflation de 2022 : revalorisation anticipée des retraites et de plusieurs prestations sociales, plafonnement temporaire de la hausse des loyers, et primes exonérées de cotisations que les employeurs peuvent verser à leurs salariés. L'enjeu : soutenir rapidement le pouvoir d'achat des ménages, le débat portant sur l'ampleur de ces mesures et leur coût pour les finances publiques.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L16V1240", "travail", "Réforme des retraites : motion de censure (2023)",
     "Motion de censure déposée par plusieurs groupes après que le Gouvernement a engagé sa responsabilité (article 49.3) pour faire adopter, sans vote des députés, la réforme repoussant l'âge légal de départ à la retraite de 62 à 64 ans. Dans ce cas, la motion de censure est le seul moyen de rejeter le texte : si elle est adoptée, le Gouvernement tombe et la loi est abandonnée. L'enjeu affiché était l'équilibre financier des retraites, face à l'allongement de la durée de travail.",
     "La réforme n'a pas fait l'objet d'un vote direct à l'Assemblée. Voter pour la motion revenait à s'opposer à l'adoption du texte ; son rejet, à neuf voix près, a entraîné l'adoption définitive de la réforme. La position affichée est le vote sur la motion de censure."),
    ("VTANR5L17V881", "taxe-impots", "Impôt plancher sur les très hauts patrimoines (2025)",
     "Crée un impôt minimum : les foyers dont le patrimoine dépasse 100 millions d'euros devraient payer chaque année au moins 2 % de ce patrimoine en impôt (proposition dite « taxe Zucman », du nom de l'économiste). L'idée de départ est que certaines très grandes fortunes paient aujourd'hui, en proportion, moins d'impôt que le reste de la population. L'enjeu : de nouvelles recettes et davantage de progressivité de l'impôt, mis en regard du risque d'exil fiscal et de la difficulté à taxer un patrimoine qui n'a pas été vendu.",
     "Proposition d'origine parlementaire, adoptée en première lecture à l'Assemblée ; elle n'était pas devenue loi à la date de mise à jour du site."),
    ("VTANR5L17V3290", "taxe-impots", "Restriction d'une taxe sur les holdings patrimoniales (2025)",
     "Amendement au budget 2026 qui restreint une taxe sur les holdings patrimoniales (des sociétés utilisées par certains grands patrimoines pour loger leurs actifs) : la trésorerie et les actifs financiers sortent de l'assiette, réduite à une liste de biens non professionnels (véhicules de tourisme, aéronefs, objets d'art et de collection, biens de chasse et de pêche, logements et résidences). En contrepartie, le taux passe de 2 % à 20 % sur ce périmètre réduit, et le seuil de détention par une personne physique au-delà duquel une holding entre dans le champ de la taxe passe de 33,33 % à 50 %. L'enjeu : le texte discuté avant cet amendement prévoyait une assiette et un champ plus larges ; l'adopter réduit le nombre de sociétés et d'actifs taxés, tout en alourdissant le taux sur les seuls biens visés.",
     "Amendement porté par un député du groupe Droite Républicaine, adopté le 31 octobre 2025 par le Rassemblement national, Ensemble pour la République et la Droite Républicaine, contre les groupes de gauche."),
    ("VTANR5L17V6319", "taxe-impots", "Lutte contre les fraudes sociales et fiscales (2026)",
     "Renforce les contrôles et les sanctions contre deux types de fraude : la fraude aux prestations sociales (aides perçues indûment) et la fraude fiscale (impôts non payés). L'enjeu : récupérer des sommes dues à la collectivité et faire respecter l'égalité devant l'impôt et les aides, le débat portant sur les moyens consacrés à chacune de ces deux fraudes et sur l'étendue des contrôles.",
     "Vote sur le texte issu de la commission mixte paritaire."),

    # ── Sécurité et justice ──────────────────────────────────────────────────
    ("VTANR5L15V138", "securite-justice", "Sécurité intérieure et lutte contre le terrorisme (2017)",
     "Fait entrer dans le droit ordinaire, de façon permanente, plusieurs pouvoirs qui n'existaient que pendant l'état d'urgence antiterroriste : périmètres de protection lors d'événements, fermeture administrative de lieux de culte, et mesures de surveillance de personnes visées, décidées par l'administration. L'enjeu : disposer d'outils antiterroristes en temps normal, ce qui pose la question du contrôle du juge sur des mesures qui touchent aux libertés.",
     None),
    ("VTANR5L15V3254", "securite-justice", "Loi « sécurité globale » (2020)",
     "Élargit les pouvoirs des polices municipales et des agents de sécurité privée, développe la vidéosurveillance et encadre l'usage des drones par les forces de l'ordre, et crée un délit de diffusion d'images de policiers ou de gendarmes dans l'intention de leur nuire. L'enjeu : renforcer la sécurité du quotidien ; la mesure sur les images des forces de l'ordre a fait débat sur la liberté d'informer et de filmer leur action.",
     None),
    ("VTANR5L17V1473", "securite-justice", "Loi contre le narcotrafic (2025)",
     "Crée un parquet national spécialisé dans la criminalité organisée (sur le modèle du parquet antiterroriste), des quartiers de prison de haute sécurité pour les trafiquants considérés comme les plus dangereux, et étend les pouvoirs d'enquête et de renseignement (surveillance, protection des informateurs, gel des avoirs). L'enjeu : mieux combattre un trafic de drogue de plus en plus violent, l'équilibre débattu étant celui entre efficacité des enquêtes et protection des libertés individuelles.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L17V7987", "securite-justice", "Présomption de légitime défense des forces de l'ordre (2026)",
     "Instaure une présomption de légitime défense pour les policiers et gendarmes qui font usage de leur arme en service : la justice partirait du principe qu'ils étaient en état de légitime défense, à charge pour l'accusation de prouver le contraire, l'inverse de la règle actuelle. L'enjeu : mieux protéger des agents qui doivent parfois décider en une fraction de seconde, mis en balance avec le contrôle exercé sur l'usage d'une arme pouvant donner la mort.",
     "Adoptée en première lecture le 7 juillet 2026 ; la navette parlementaire se poursuit au Sénat. Ses opposants qualifient le texte de « permis de tuer », ses partisans de protection nécessaire des agents. Ce sont des qualifications rapportées, que le site ne reprend pas à son compte."),

    # ── Immigration ──────────────────────────────────────────────────────────
    ("VTANR5L15V578", "immigration", "Loi asile et immigration (2018)",
     "Raccourcit les délais pour déposer une demande d'asile et pour contester un refus, double la durée maximale de rétention administrative (de 45 à 90 jours) et facilite l'éloignement des personnes déboutées. La rétention administrative est l'enfermement, hors prison, d'un étranger en attente d'expulsion. L'enjeu : accélérer le traitement des demandes et les expulsions, mis en regard des droits et des garanties des demandeurs d'asile.",
     None),
    ("VTANR5L16V3213", "immigration", "Loi immigration (2023)",
     "Durcit plusieurs règles applicables aux étrangers : conditions du regroupement familial, accès à certaines prestations sociales, et expulsions facilitées ; en contrepartie, elle ouvre une régularisation encadrée pour les travailleurs sans papiers employés dans des métiers qui manquent de main-d'œuvre. L'enjeu : l'équilibre entre maîtrise de l'immigration et droits des personnes étrangères, un sujet de fortes tensions politiques.",
     "Vote sur le texte issu de la commission mixte paritaire ; le Conseil constitutionnel a ensuite censuré une large partie de ses articles (janvier 2024)."),
    ("VTANR5L17V1308", "immigration", "Accès à la nationalité française à Mayotte (2025)",
     "Durcit, à Mayotte uniquement, les conditions dans lesquelles un enfant né sur place de parents étrangers peut devenir français. Jusqu'alors, il suffisait qu'au moins un des deux parents réside régulièrement en France depuis plus de trois mois à la date de la naissance ; le texte exige désormais que les deux parents y résident régulièrement depuis au moins un an (un seul parent si la filiation n'est établie qu'à son égard). Il impose aussi la présentation d'un titre de séjour accompagné d'un passeport biométrique. L'enjeu : la pression migratoire et démographique à Mayotte, mise en balance avec le droit du sol et l'égalité devant la loi.",
     "Texte de la commission mixte paritaire. Promulgué le 12 mai 2025 (loi n° 2025-412) après validation par le Conseil constitutionnel, assortie d'une réserve d'interprétation : le passeport biométrique ne peut être exigé des ressortissants d'États qui n'en délivrent pas."),
    ("VTANR5L17V7405", "immigration", "Sécurité et rétention administrative (2026)",
     "Allonge la durée et élargit les cas dans lesquels un étranger visé par une mesure d'éloignement peut être placé en rétention administrative (l'enfermement, hors prison, en attendant l'expulsion). L'enjeu : donner plus de temps à l'administration pour organiser les expulsions, mis en balance avec la privation de liberté que représente la rétention.",
     "Texte transversal sécurité/immigration, rattaché ici à son objet principal (règle « un vote = un thème »)."),

    # ── Questions de société ─────────────────────────────────────────────────
    ("VTANR5L15V2146", "femmes", "Bioéthique : PMA pour toutes (2019)",
     "Ouvre la procréation médicalement assistée (PMA : les techniques médicales pour concevoir un enfant, comme l'insémination ou la fécondation in vitro) aux couples de femmes et aux femmes seules, alors qu'elle était réservée aux couples femme-homme, avec prise en charge par la Sécurité sociale. Le texte permet aussi aux enfants nés d'un don d'accéder, à leur majorité, à l'identité du donneur. L'enjeu : l'égalité d'accès à la parentalité, face à des débats éthiques sur la filiation et l'accès aux origines.",
     "Première lecture ; le texte a été définitivement adopté en 2021."),
    ("VTCGR5L16V1", "femmes", "IVG dans la Constitution (Congrès, 2024)",
     "Inscrit dans la Constitution la « liberté garantie » de la femme de recourir à l'avortement (IVG). L'avortement était déjà légal depuis la loi Veil de 1975 ; l'inscrire dans la Constitution le protège d'un retour en arrière, car modifier la Constitution suppose une très large majorité. L'enjeu : rendre ce droit beaucoup plus difficile à remettre en cause à l'avenir. La France est le premier pays au monde à l'avoir fait.",
     "Adopté par le Parlement réuni en Congrès à Versailles par 780 voix pour et 72 contre : seul vote de la base où députés et sénateurs sont directement comparables."),
    ("VTANR5L17V5728", "sante", "Accompagnement et soins palliatifs (2026)",
     "Organise le développement, partout sur le territoire, des soins palliatifs (les soins qui soulagent la douleur et accompagnent les personnes en fin de vie sans chercher à guérir) et garantit le droit d'y accéder. L'enjeu : réduire les fortes inégalités d'accès à ces soins selon les régions et les établissements.",
     "Deuxième lecture ; texte examiné conjointement avec la proposition de loi sur l'aide à mourir."),
    ("VTANR5L17V8280", "sante", "Droit à l'aide à mourir (2026)",
     "Crée un « droit à l'aide à mourir » : la possibilité, très encadrée, pour une personne majeure atteinte d'une maladie grave et incurable engageant son pronostic vital, de recevoir ou de s'administrer elle-même une substance létale. Chaque demande doit être libre, répétée et validée par une équipe médicale. L'enjeu : pouvoir choisir sa fin de vie face à des souffrances jugées insupportables, mis en regard des inquiétudes éthiques sur la protection des personnes les plus vulnérables.",
     "Lecture définitive du 15 juillet 2026, au terme de quatre lectures à l'Assemblée."),

    # ── Europe et international ──────────────────────────────────────────────
    ("VTANR5L15V2059", "europe-international", "Ratification du CETA (2019)",
     "Autorise la France à ratifier le CETA, l'accord de libre-échange entre l'Union européenne et le Canada, qui supprime la quasi-totalité des droits de douane entre les deux zones et facilite donc le commerce dans les deux sens. L'enjeu : de nouveaux débouchés pour les exportateurs européens, mis en balance avec les craintes des éleveurs et d'associations sur la concurrence de produits agricoles soumis à d'autres normes et sur l'impact climatique des échanges transatlantiques.",
     "Tous les candidats suivis alors en poste ont voté contre, pour des motifs différents selon les groupes : impacts sur l'élevage, normes sanitaires et climat à gauche, souveraineté au RN et à DLF. Le Sénat a ensuite rejeté le texte (2024) ; l'accord reste appliqué à titre provisoire."),
    ("VTANR5L16V652", "defense", "Soutien à l'Ukraine (2022)",
     "Résolution par laquelle l'Assemblée nationale affirme son soutien à l'Ukraine et condamne l'invasion menée par la Russie depuis février 2022. Une résolution exprime une position politique solennelle, mais sans portée juridique contraignante. L'enjeu : marquer le soutien de la France à un pays agressé et à la sécurité de l'Europe.",
     None),
    ("VTANR5L17V456", "europe-international", "Accord UE-Mercosur : déclaration du Gouvernement (2024)",
     "Le Mercosur est un accord de libre-échange en négociation entre l'Union européenne et des pays d'Amérique du Sud (Brésil, Argentine, Uruguay, Paraguay) qui augmenterait les échanges, notamment les importations agricoles (bœuf, volaille, sucre). Sur ce vote, le Gouvernement demandait aux députés d'approuver l'opposition de la France à l'accord en l'état : voter « pour » revenait donc à soutenir ce refus. L'enjeu : les agriculteurs européens redoutent une concurrence de produits soumis à des règles sanitaires et environnementales moins strictes, quand les partisans de l'accord mettent en avant de nouveaux marchés.",
     "Vote au titre de l'article 50-1 de la Constitution : il exprime la position formelle de l'Assemblée, sans effet législatif direct."),
    ("VTANR5L17V988", "defense", "Renforcement du soutien à l'Ukraine (2025)",
     "Résolution appelant à renforcer le soutien à l'Ukraine, notamment en utilisant les avoirs russes gelés en Europe pour la financer, et à faciliter le processus d'adhésion de l'Ukraine à l'Union européenne. Comme toute résolution, elle exprime une position sans créer d'obligation juridique. L'enjeu : l'ampleur et les moyens du soutien européen à l'Ukraine dans la durée.",
     None),

    # ── Extension 14e législature (2012-2017), validée le 24/07/2026 ────────
    ("VTANR5L14V511", "societe", "Mariage pour tous (2013)",
     "Ouvre le mariage civil et l'adoption aux couples de personnes de même sexe, jusque-là réservés aux couples femme-homme. L'enjeu : l'égalité des droits entre couples hétérosexuels et homosexuels, un texte qui a donné lieu à d'importantes mobilisations, pour comme contre.",
     "Deuxième lecture du 23 avril 2013 : dernier vote d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V1070", "societe", "Fin de vie : loi Claeys-Leonetti (2015)",
     "Crée un droit à la « sédation profonde et continue » jusqu'au décès pour les malades en phase terminale dont les souffrances ne peuvent être soulagées, et rend contraignantes les « directives anticipées » (les volontés écrites à l'avance sur sa propre fin de vie, que les médecins doivent alors respecter). Le texte n'autorise ni l'euthanasie ni le suicide assisté. L'enjeu : mieux accompagner la fin de vie sans légaliser l'aide active à mourir.",
     "Première lecture ; le texte a été définitivement adopté début 2016. C'est le cadre que la loi sur l'aide à mourir de 2026 est venue compléter."),
    ("VTANR5L14V726", "travail", "Réforme des retraites Touraine (2013)",
     "Allonge progressivement la durée de cotisation nécessaire pour une retraite à taux plein, jusqu'à 43 ans (172 trimestres) pour les générations nées à partir de 1973, et crée un compte permettant de partir plus tôt après un métier pénible. L'enjeu : équilibrer le financement des retraites en faisant cotiser plus longtemps, sans toucher à l'âge légal (alors 62 ans).",
     "Nouvelle lecture du 26 novembre 2013 : dernier scrutin public d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V1270", "travail", "Loi travail (El Khomri) : motion de censure (2016)",
     "Motion de censure déposée après que le Gouvernement a engagé sa responsabilité (article 49.3) pour adopter, sans vote, la « loi travail ». Celle-ci faisait notamment primer les accords d'entreprise sur les accords de branche (les règles négociées entreprise par entreprise pouvant être moins favorables que celles du secteur) et assouplissait le licenciement économique. Voter la motion revenait à s'opposer à la loi. L'enjeu : la flexibilité du marché du travail face aux protections des salariés.",
     "Comme pour les retraites en 2023, le texte n'a pas fait l'objet d'un vote direct : voter pour la motion revenait à s'opposer à son adoption ; son rejet a permis l'adoption de la loi."),
    ("VTANR5L14V1109", "securite-justice", "Loi renseignement (2015)",
     "Encadre par la loi des techniques de surveillance élargies pour les services de renseignement : analyse automatisée des données de connexion pour détecter des menaces (les « boîtes noires »), fausses antennes-relais captant les téléphones (IMSI-catchers), le tout sous le contrôle d'une nouvelle autorité indépendante, la CNCTR. L'enjeu : donner des moyens modernes à la lutte antiterroriste tout en encadrant la surveillance des citoyens.",
     "Votée quelques mois après les attentats de janvier 2015."),
    ("VTANR5L14V1191", "securite-justice", "Prorogation de l'état d'urgence (2015)",
     "Prolonge de trois mois l'état d'urgence déclaré après les attentats du 13 novembre 2015 et en renforce les mesures : perquisitions décidées par l'administration (sans autorisation préalable d'un juge) et assignations à résidence. L'état d'urgence est un régime exceptionnel qui élargit temporairement les pouvoirs de police. L'enjeu : répondre à une menace terroriste immédiate, au prix de restrictions temporaires des libertés.",
     None),
    ("VTANR5L14V994", "immigration", "Réforme de l'asile (2014)",
     "Réorganise l'examen des demandes d'asile : création de procédures accélérées, généralisation d'un recours qui suspend l'éloignement le temps de son examen, et répartition dirigée des demandeurs dans des hébergements sur tout le territoire. L'enjeu : traiter les demandes plus vite et mieux répartir l'accueil, tout en garantissant les droits des demandeurs.",
     None),
    ("VTANR5L14V1237", "immigration", "Déchéance de nationalité : « protection de la Nation » (2016)",
     "Projet de révision de la Constitution qui voulait y inscrire l'état d'urgence et permettre de retirer la nationalité française à des personnes condamnées pour terrorisme, y compris à des Français de naissance disposant d'une autre nationalité. L'enjeu portait sur la réponse à apporter au terrorisme après les attentats de 2015 et sur l'égalité entre Français selon qu'ils possèdent une ou deux nationalités.",
     "Première lecture. La révision a été abandonnée en mars 2016 faute d'accord entre l'Assemblée et le Sénat : le Congrès n'a jamais été réuni."),
    ("VTANR5L14V1120", "ecologie-agriculture", "Transition énergétique (2015)",
     "Fixe les grands objectifs énergétiques de la France : ramener la part du nucléaire à 50 % de l'électricité (contre environ 75 %), diviser par deux la consommation d'énergie d'ici 2050, développer les renouvelables et interdire les sacs plastique à usage unique. L'enjeu : engager la transition vers une énergie moins carbonée et moins gaspilleuse, en fixant des caps de long terme dont dépendront les politiques suivantes.",
     "Nouvelle lecture du 26 mai 2015 : dernier scrutin public d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V30", "europe-international", "Ratification du traité budgétaire européen (TSCG, 2012)",
     "Autorise la ratification du traité budgétaire européen (TSCG), négocié après la crise de la zone euro, qui engage les États à limiter strictement leurs déficits, la « règle d'or » des finances publiques. L'enjeu : la discipline budgétaire commune en Europe, mise en balance avec la marge de manœuvre des États pour mener leur propre politique économique.",
     None),
    ("VTANR5L14V594", "institutions", "Transparence de la vie publique (2013)",
     "Crée la Haute Autorité pour la transparence de la vie publique (HATVP) et impose aux membres du Gouvernement, aux parlementaires et à de nombreux élus et responsables publics de déclarer leur patrimoine et leurs intérêts (activités, revenus, liens pouvant créer des conflits d'intérêts). Les déclarations d'intérêts sont rendues publiques. Les déclarations de patrimoine ne le sont que pour les membres du Gouvernement : celles des parlementaires sont seulement consultables en préfecture par les électeurs de leur département, leur publication étant sanctionnée. L'enjeu : prévenir la corruption et les conflits d'intérêts, le degré de publicité du patrimoine des parlementaires ayant été le principal point de désaccord entre l'Assemblée et le Sénat.",
     "Adoptée après l'affaire Cahuzac (lecture définitive). Ce sont les déclarations d'intérêts publiées par la HATVP que le présent site utilise pour la partie « parcours » des candidats."),

    # ── Parlement européen (uid PE-HTV-<vote_id>, importés par ingestion/pe) ────
    # Pour la plupart des candidats, aucun vote personnel n'est disponible (mandat
    # européen achevé avant 2019) : c'est la position de la DÉLÉGATION de leur parti
    # qui s'affiche, clairement étiquetée « n'y siégeait pas ». Sélection symétrique.
    ("PE-HTV-147342", "travail", "Salaire minimum européen (2022)",
     "Directive fixant un cadre pour des salaires minimaux « adéquats » dans l'Union : les États dotés d'un salaire minimum légal doivent le fixer selon des critères communs (niveau de vie, salaires médians) et la négociation collective est encouragée, sans montant unique imposé à l'échelle européenne. L'enjeu : relever le niveau des bas salaires en Europe tout en laissant chaque pays fixer son propre montant.",
     "Vote d'ensemble au Parlement européen, septembre 2022 (9e législature)."),
    ("PE-HTV-152544", "ecologie-agriculture", "Fin des voitures thermiques neuves en 2035 (2023)",
     "Fixe la fin de la vente de voitures et utilitaires neufs émettant du CO₂ à partir de 2035 dans l'Union : les constructeurs ne pourront plus vendre que des véhicules neufs à zéro émission. L'enjeu : réduire les émissions du transport routier, mis en balance avec les effets sur l'industrie automobile, l'emploi et le coût des véhicules pour les ménages.",
     "Normes CO₂ pour voitures et véhicules utilitaires légers, vote de février 2023."),
    ("PE-HTV-164499", "ecologie-agriculture", "Loi sur la restauration de la nature (2024)",
     "Impose aux États des objectifs de restauration des milieux naturels dégradés (zones humides, forêts, rivières, terres agricoles, milieux marins) pour enrayer le déclin de la biodiversité. L'enjeu : reconstituer des écosystèmes affaiblis, la question débattue étant l'articulation entre ces objectifs et les usages agricoles et économiques des terres.",
     "Vote d'adoption de février 2024, sur le texte négocié avec les États membres."),
    ("PE-HTV-166183", "institutions", "Liberté des médias dans l'Union (2024)",
     "Règlement européen sur la liberté des médias : protège l'indépendance éditoriale, impose la transparence sur la propriété des médias, encadre la publicité des pouvoirs publics dans les médias et renforce la protection des journalistes et de leurs sources. L'enjeu : préserver le pluralisme et l'indépendance de la presse face aux pressions politiques ou économiques.",
     "European Media Freedom Act, vote d'adoption de mars 2024."),
    ("PE-HTV-168573", "femmes", "Lutte contre les violences faites aux femmes (2024)",
     "Première directive européenne dédiée à la lutte contre les violences faites aux femmes et les violences domestiques : elle harmonise certaines infractions et sanctions (notamment les cyberviolences) et renforce la protection, l'accompagnement et l'accès à la justice des victimes dans toute l'Union. L'enjeu : un socle commun de protection, le débat ayant porté sur le périmètre des infractions harmonisées.",
     "Directive sur la lutte contre la violence à l'égard des femmes et la violence domestique, vote d'avril 2024."),
    ("PE-HTV-167531", "immigration", "Pacte européen sur l'asile et la migration (2024)",
     "Pièce centrale du Pacte sur la migration et l'asile : le règlement sur la gestion de l'asile et de la migration réforme la répartition des demandeurs entre États membres et instaure un mécanisme dit de solidarité (accueil de demandeurs ou contribution financière). L'enjeu : répartir la charge de l'asile entre les pays de l'Union : un compromis critiqué à la fois comme trop contraignant et comme insuffisamment protecteur.",
     "Volet « gestion de l'asile et de la migration » du Pacte, vote d'avril 2024."),
    ("PE-HTV-164536", "defense", "Facilité pour l'Ukraine : 50 milliards (2024)",
     "Crée la « facilité pour l'Ukraine » : un soutien financier de l'Union doté de 50 milliards d'euros sur 2024-2027 (prêts et subventions) pour le fonctionnement de l'État ukrainien, sa reconstruction et ses réformes. L'enjeu : assurer à l'Ukraine en guerre un financement européen pluriannuel et prévisible.",
     "Établissement de la facilité pour l'Ukraine, vote de février 2024."),
    ("PE-HTV-169362", "defense", "Soutien continu à l'Ukraine (2024)",
     "Résolution appelant l'Union et les États membres à maintenir et renforcer leur soutien financier et militaire à l'Ukraine face à l'invasion russe. Une résolution exprime une position politique, sans portée juridiquement contraignante. L'enjeu : la constance et l'ampleur du soutien européen dans la durée.",
     "Résolution sur la nécessité d'un soutien continu de l'UE à l'Ukraine, vote de juillet 2024 (10e législature)."),

    # ── Extension : votes européens CLIVANTS (positions différentes) ───────────
    ("PE-HTV-154173", "ecologie-agriculture", "Réforme du marché carbone européen (2023)",
     "Renforce le « marché carbone » de l'Union : les industries et les producteurs d'électricité doivent acheter des quotas pour leurs émissions de CO₂, dont le nombre total diminue chaque année. La réforme accélère cette baisse, étend le système (transport maritime notamment) et supprime progressivement les quotas gratuits accordés à l'industrie. L'enjeu : renchérir les émissions pour les faire baisser plus vite, la question débattue étant le coût pour les entreprises et son effet sur les prix.",
     "Pièce maîtresse du paquet climat « Fit for 55 », vote d'avril 2023."),
    ("PE-HTV-154076", "travail", "Transparence des salaires (2023)",
     "Directive obligeant les entreprises à plus de transparence sur les rémunérations pour réduire l'écart de salaire entre femmes et hommes : indication des salaires dès l'offre d'emploi, droit pour un salarié de connaître les rémunérations moyennes à poste équivalent, et publication par les grandes entreprises de leurs écarts de salaire. L'enjeu : rendre visibles, et corriger, les inégalités de salaire à travail égal.",
     "Directive sur la transparence des rémunérations, vote de mars 2023."),
    ("PE-HTV-167334", "pouvoir-achat-fiscalite", "Réforme du marché de l'électricité (2024)",
     "Réorganise le marché européen de l'électricité après la flambée des prix de 2022 : développe les contrats de long terme pour stabiliser les prix, renforce la protection des consommateurs (contre les coupures et la volatilité) et vise à rendre les factures moins dépendantes du prix des énergies fossiles. L'enjeu : limiter l'envolée des factures d'électricité, le débat portant sur le degré d'intervention publique sur les prix.",
     "Directive sur l'organisation du marché de l'électricité, vote d'avril 2024."),
    ("PE-HTV-155928", "securite-justice", "Preuves électroniques en matière pénale (2023)",
     "Permet à la justice d'un pays de l'Union d'adresser directement à un fournisseur établi dans un autre pays de l'Union une injonction de remise ou de conservation de preuves numériques (données d'abonné, de connexion, contenus), avec des délais de réponse encadrés (dix jours, huit heures en urgence). Pour les données de connexion et de contenu, les autorités du pays où se trouve le fournisseur sont notifiées en même temps et peuvent s'y opposer dans un délai de dix jours, notamment en cas d'atteinte aux droits fondamentaux ou d'immunité. L'enjeu : accélérer les enquêtes pénales transfrontalières, mis en balance avec la protection des données et les garanties pour les personnes concernées.",
     "Règlement sur les preuves électroniques (« e-evidence »), vote du 13 juin 2023 ; une directive distincte, votée le même jour, oblige les fournisseurs à désigner un représentant légal dans l'Union."),
    ("PE-HTV-161873", "securite-justice", "Logiciels espions : réclamer une législation européenne (2023)",
     "Résolution constatant que la Commission n'a pas donné de suite législative aux conclusions de la commission d'enquête du Parlement sur l'usage de logiciels espions (type Pegasus) contre des journalistes, des opposants et des magistrats dans plusieurs États membres. Le texte demande des règles européennes encadrant la vente et l'usage de ces outils, ainsi que des garanties pour les personnes surveillées. L'enjeu : les libertés et l'État de droit face à la surveillance numérique par les pouvoirs publics.",
     "Résolution de suivi de la commission d'enquête PEGA, novembre 2023. La recommandation PEGA elle-même (juin 2023) a été adoptée sans vote nominatif : les positions individuelles n'y sont pas publiques."),
    ("PE-HTV-168301", "securite-justice", "Contrôle du commerce des armes à feu (2024)",
     "Renforce le contrôle de l'importation, de l'exportation et du transit des armes à feu civiles : traçabilité, autorisations, lutte contre le trafic et contre la transformation d'armes d'alarme en armes létales. L'enjeu : réduire la circulation illégale d'armes à feu, tout en encadrant les usages légaux (tir sportif, chasse, collection).",
     "Règlement sur les mesures d'importation et d'exportation des armes à feu, vote d'avril 2024."),
    ("PE-HTV-166929", "immigration", "Fichier européen d'empreintes des migrants : Eurodac (2024)",
     "Étend la base de données Eurodac, qui enregistre empreintes et données des demandeurs d'asile et des personnes en situation irrégulière : abaissement de l'âge d'enregistrement à six ans, conservation de l'image du visage et accès élargi pour les forces de l'ordre. L'enjeu : mieux suivre les parcours migratoires et éviter les demandes multiples, mis en balance avec la protection des données personnelles, y compris des mineurs.",
     "Volet Eurodac du Pacte migration et asile, vote d'avril 2024."),
    ("PE-HTV-166904", "immigration", "Filtrage aux frontières extérieures (2024)",
     "Instaure un « filtrage » obligatoire des personnes entrées irrégulièrement : identification, contrôle de sécurité et de santé, enregistrement, pendant lesquels la personne est juridiquement considérée comme pas encore entrée sur le territoire. L'enjeu : trier rapidement, aux frontières, entre demandes d'asile et personnes à éloigner, un dispositif jugé trop expéditif par les uns, insuffisant par les autres.",
     "Règlement « filtrage » du Pacte migration et asile, vote d'avril 2024."),
    ("PE-HTV-155091", "femmes", "Adhésion de l'UE à la Convention d'Istanbul (2023)",
     "Approuve l'adhésion de l'Union à la Convention d'Istanbul, le traité du Conseil de l'Europe qui engage à prévenir et combattre les violences faites aux femmes et les violences domestiques (protection des victimes, poursuite des auteurs, prévention). L'enjeu : lier juridiquement l'Union à ce cadre, alors que plusieurs États membres refusent de le ratifier.",
     "Vote d'approbation de l'adhésion de l'UE (mai 2023), à distinguer de la directive de 2024 sur le même thème, où les positions ont pu différer."),
    ("PE-HTV-168054", "femmes", "Droit à l'avortement dans la Charte de l'UE (2024)",
     "Résolution demandant d'inscrire le droit à l'avortement dans la Charte des droits fondamentaux de l'Union. Une résolution exprime une position politique : elle ne modifie pas elle-même les traités, ce qui exigerait l'accord unanime des États membres. L'enjeu : ériger l'accès à l'avortement en droit fondamental à l'échelle européenne.",
     "Résolution du 11 avril 2024, sans effet juridique contraignant."),
    ("PE-HTV-164215", "societe", "Stratégie de l'UE pour l'égalité des personnes LGBTIQ (2024)",
     "Rapport dressant le bilan de la stratégie européenne 2020-2025 pour l'égalité des personnes LGBTIQ et appelant à la prolonger : lutte contre les discriminations, reconnaissance des familles d'un pays à l'autre, protection contre les violences et les discours de haine. L'enjeu : l'égalité des droits des personnes LGBTIQ dans l'Union, un sujet sur lequel des États membres s'opposent.",
     "Rapport de mise en œuvre de la stratégie LGBTIQ, vote de février 2024."),
    ("PE-HTV-186518", "europe-international", "Stratégie d'élargissement de l'Union (2026)",
     "Position du Parlement sur l'élargissement de l'Union : soutien à l'adhésion, à terme, de pays candidats (Ukraine, Moldavie, Balkans occidentaux…) sous condition de réformes, et débat sur les réformes internes que l'Union devrait mener pour pouvoir accueillir de nouveaux membres. L'enjeu : l'avenir géographique et politique de l'Union, entre ouverture et capacité d'intégration.",
     "Résolution sur la stratégie d'élargissement, vote de mars 2026 (10e législature)."),
    ("PE-HTV-168862", "institutions", "État de droit en Hongrie : passer à l'article 7(2) (2024)",
     "Résolution constatant la persistance d'atteintes à l'État de droit en Hongrie (indépendance de la justice, corruption et conflits d'intérêts, liberté des médias, système électoral, société civile). Elle condamne la loi de « protection de la souveraineté nationale » et le bureau de surveillance qu'elle crée, constate que la procédure de l'article 7, paragraphe 1, est bloquée au Conseil depuis 2018 et demande de passer au paragraphe 2, étape où le Conseil européen peut constater une violation grave et persistante des valeurs de l'Union, préalable à la suspension de certains droits dont le droit de vote au Conseil. Elle demande aussi à la Commission de revenir sur le déblocage de 10,2 milliards d'euros de fonds gelés. L'enjeu : la réponse de l'Union face à un État membre accusé de s'éloigner des valeurs démocratiques communes, alors que la Hongrie devait présider le Conseil au second semestre 2024.",
     "Résolution du 24 avril 2024 sur les auditions au titre de l'article 7, paragraphe 1, et leurs implications budgétaires. Sans effet juridique contraignant."),
    ("PE-HTV-166051", "institutions", "Règlement européen sur l'intelligence artificielle (2024)",
     "Premier cadre juridique complet au monde sur l'intelligence artificielle : classe les usages selon leur niveau de risque, interdit certaines pratiques (notation sociale, manipulation) et impose des obligations renforcées aux systèmes « à haut risque » (santé, justice, emploi…). L'enjeu : encadrer l'IA pour protéger les droits sans freiner l'innovation, l'équilibre entre les deux étant au cœur des débats.",
     "Règlement sur l'intelligence artificielle (« AI Act »), vote d'adoption de mars 2024."),

    # ── Urgence climatique et événements extrêmes (canicules, incendies…) ──────
    ("PE-HTV-110615", "ecologie-agriculture", "Déclaration d'urgence climatique (2019)",
     "Résolution par laquelle le Parlement européen déclare l'« urgence climatique et environnementale » et appelle l'Union et les États à aligner leurs politiques sur l'objectif de limiter le réchauffement à 1,5 °C. Une résolution exprime une position politique solennelle, sans effet juridique contraignant en soi. L'enjeu : reconnaître officiellement l'urgence climatique et en faire une priorité de l'action publique.",
     "Résolution du 28 novembre 2019, à la veille de la conférence climat de Madrid (COP25)."),
    ("PE-HTV-118521", "ecologie-agriculture", "Loi européenne sur le climat (2020)",
     "Inscrit dans la loi l'objectif de neutralité carbone de l'Union en 2050 (ne plus émettre plus de gaz à effet de serre que ce que l'on peut absorber) et rehausse l'objectif intermédiaire de réduction des émissions d'ici 2030, avec un suivi régulier des progrès des États. L'enjeu : rendre juridiquement contraignante la trajectoire de baisse des émissions, le débat portant sur l'ampleur des objectifs et leur coût.",
     "Position du Parlement sur la loi européenne sur le climat, octobre 2020."),
    ("PE-HTV-126261", "ecologie-agriculture", "Stratégie d'adaptation au changement climatique (2020)",
     "Position du Parlement sur la stratégie européenne d'adaptation au changement climatique : préparer les territoires aux effets déjà en cours et à venir (canicules, sécheresses, inondations, montée des eaux, incendies) par la prévention des risques, l'aménagement, l'agriculture et la protection des populations. L'enjeu : réduire les dégâts humains et matériels des événements climatiques extrêmes, en complément de la baisse des émissions.",
     "Résolution sur la stratégie d'adaptation au changement climatique, décembre 2020."),
    ("PE-HTV-117083", "ecologie-agriculture", "Mécanisme de protection civile de l'UE (2020)",
     "Renforce le mécanisme européen de protection civile (rescEU) : réserves communes de moyens (avions bombardiers d'eau, matériel médical, abris…) et coordination de l'aide entre États lors de catastrophes : incendies de forêt, inondations, séismes, épidémies. L'enjeu : mieux répondre ensemble à des catastrophes de plus en plus fréquentes, la question débattue étant le degré de mutualisation des moyens et le budget.",
     "Position du Parlement sur la révision du mécanisme de protection civile de l'Union, septembre 2020."),
    ("PE-HTV-184178", "ecologie-agriculture", "Cadre pour la neutralité climatique : objectif 2040 (2026)",
     "Fixe un objectif intermédiaire de réduction des émissions de gaz à effet de serre de l'Union à l'horizon 2040, sur la trajectoire vers la neutralité carbone en 2050, et en précise le rythme et les moyens (dont d'éventuelles souplesses réclamées par certains secteurs). L'enjeu : la vitesse de la transition climatique d'ici 2040, entre ambition environnementale et coût pour l'économie et les ménages.",
     "Vote sur le cadre pour la neutralité climatique (objectif 2040), février 2026 (10e législature)."),

    # ── Extension : lois où LFI et RN divergent nettement (ajout 25/07/2026) ────
    # Sélectionnées pour éclairer les différences d'orientation entre familles
    # politiques ; chaque groupe porte une justification déclarée, sourcée
    # (table justifications_groupes, seed dédié).
    ("VTANR5L16V1533", "ecologie-agriculture", "Relance du nucléaire (2023)",
     "Accélère et simplifie les procédures administratives pour construire de nouveaux réacteurs nucléaires à proximité de centrales existantes : délais raccourcis, autorisations facilitées. L'enjeu : permettre une relance rapide de la construction nucléaire pour produire une électricité bas-carbone, mis en balance avec les questions de sûreté, de gestion des déchets et le choix, de long terme, de miser sur cette énergie.",
     "Vote sur le texte issu de la commission mixte paritaire. Adopté largement ; seuls les groupes LFI et Écologiste ont voté contre, les Socialistes s'abstenant."),
    ("VTANR5L16V2721", "ecologie-agriculture", "Loi industrie verte (2023)",
     "Vise à accélérer l'implantation d'usines en France, en particulier dans les technologies de la transition (batteries, panneaux solaires, pompes à chaleur) : procédures raccourcies, sites « clés en main », commande publique et financements orientés vers les produits plus vertueux. L'enjeu : réindustrialiser tout en verdissant la production, le débat portant sur l'ampleur réelle des moyens et sur l'équilibre entre rapidité des projets et exigences environnementales.",
     "Vote sur le texte issu de la commission mixte paritaire. LFI et les Écologistes ont voté contre, jugeant les moyens insuffisants ; le RN a voté pour."),
    ("VTANR5L17V6184", "pouvoir-achat-fiscalite", "Simplification de la vie économique (2026)",
     "Allège des obligations administratives pesant sur les entreprises, accélère certains projets industriels et supprime les zones à faibles émissions (ZFE), ces périmètres urbains où les véhicules les plus polluants sont progressivement interdits. L'enjeu : réduire les contraintes sur l'activité économique, mis en balance avec les objectifs de qualité de l'air et de protection de l'environnement.",
     "Vote sur le texte issu de la commission mixte paritaire. Fait notable : une partie du groupe macroniste (EPR) a voté contre le texte final, après le maintien de la suppression des ZFE ; le RN a voté pour, LFI contre. Le Conseil constitutionnel a ensuite censuré la suppression des ZFE (2026)."),
    ("VTANR5L17V1624", "securite-justice", "Justice des mineurs : loi Attal (2025)",
     "Durcit la réponse pénale à la délinquance des mineurs : comparution immédiate possible dès 16 ans, atténuation plus limitée de la peine du fait de la minorité (l'« excuse de minorité »), et amende civile pour les parents ne répondant pas aux convocations du juge. L'enjeu : sanctionner plus vite et plus fermement les mineurs délinquants, mis en balance avec un principe propre à la justice des mineurs : la primauté de l'éducation sur la répression.",
     "Texte porté par Gabriel Attal, adopté sur le texte de la commission mixte paritaire. Toute la gauche a voté contre, le RN pour. Le Conseil constitutionnel a ensuite censuré plusieurs de ces mesures (juin 2025)."),
    ("VTANR5L16V3045", "societe", "Société du bien vieillir (2023)",
     "Mesures sur le grand âge : repérage des personnes âgées fragiles et isolées, lutte contre la maltraitance, création d'une carte professionnelle pour les aides à domicile, sans la « loi grand âge » ni le financement de l'autonomie longtemps annoncés. L'enjeu : améliorer l'accompagnement du vieillissement, la critique portant sur l'absence de moyens jugés à la hauteur du défi démographique.",
     "Première lecture. LFI et le groupe GDR (dont le PCF) ont voté contre, jugeant le texte insuffisant ; le RN a voté pour ; le groupe Les Républicains n'a pas pris part au vote."),
    ("VTANR5L17V7454", "institutions", "Autonomie de la Corse (2026)",
     "Révision de la Constitution inscrivant un statut d'autonomie pour la Corse au sein de la République : l'île pourrait adapter certaines lois et règlements à ses spécificités, dans des domaines et des limites définis. L'enjeu : reconnaître les particularités corses par une forme de pouvoir normatif propre, une question qui touche au caractère unitaire de la République et à l'égalité entre les territoires.",
     "Première lecture. Une révision constitutionnelle doit ensuite être votée dans les mêmes termes par le Sénat, puis approuvée par le Congrès ou par référendum. Les positions habituelles s'y sont inversées : LFI a voté pour, le RN contre."),
    ("VTANR5L16V3725", "institutions", "Corps électoral en Nouvelle-Calédonie (2024)",
     "Révision de la Constitution élargissant le corps électoral pour les élections au congrès et aux assemblées de province de Nouvelle-Calédonie : pourraient voter les personnes inscrites sur la liste électorale générale qui sont nées en Nouvelle-Calédonie ou qui y sont domiciliées de façon continue depuis au moins dix ans. Jusqu'alors, ce corps électoral était limité aux personnes inscrites avant l'accord de Nouméa de novembre 1998 et à leurs descendants, limite « gelée » par la révision constitutionnelle de 2007. L'enjeu : faire voter des habitants aujourd'hui écartés de ces scrutins, mis en balance avec l'équilibre politique issu des accords sur l'avenir de l'archipel entre indépendantistes et non-indépendantistes.",
     "Première lecture. Le RN a voté pour, LFI contre. Le processus a ensuite été suspendu à la suite des tensions survenues sur l'archipel."),
    ("VTANR5L17V1303", "institutions", "Parité dans les petites communes (2025)",
     "Étend le scrutin de liste, à la proportionnelle et paritaire (autant de femmes que d'hommes), aux communes de moins de 1 000 habitants, qui élisaient jusqu'ici leurs conseillers au scrutin majoritaire, sans obligation de parité. L'enjeu : renforcer la représentation des femmes dans les conseils municipaux des petites communes, la question débattue étant la difficulté à constituer des listes complètes et paritaires dans les villages.",
     "Adoptée en première lecture, 206 voix contre 181, puis promulguée le 21 mai 2025 pour les municipales de 2026. Les positions habituelles s'y sont inversées : la gauche (dont LFI) a voté pour, le RN contre."),

    # ── Santé (thème créé le 25/07/2026) ─────────────────────────────────────
    ("VTANR5L14V1200", "sante", "Modernisation du système de santé : loi Touraine (2016)",
     "Réforme d'ensemble du système de santé : généralisation du tiers payant (ne plus avancer les frais chez le médecin), paquet de cigarettes neutre, ouverture de salles de consommation de drogue à moindre risque, renforcement de la prévention. L'enjeu : faciliter l'accès aux soins et agir sur la santé publique, le tiers payant généralisé étant vivement contesté par une partie des médecins.",
     None),
    ("VTANR5L16V875", "sante", "Accès direct aux paramédicaux : loi Rist (2023)",
     "Ouvre l'accès direct à certains professionnels de santé (kinésithérapeutes, orthophonistes, infirmiers en pratique avancée) sans passer d'abord par un médecin, pour raccourcir les délais. L'enjeu : désengorger l'accès aux soins face au manque de médecins, la question débattue étant la coordination des soins autour du médecin traitant.",
     None),
    ("VTANR5L17V1607", "sante", "Déserts médicaux : régulation de l'installation (2025)",
     "Encadre l'installation des médecins : dans les zones déjà bien pourvues, un nouveau médecin ne pourrait s'installer qu'en remplaçant un départ. L'enjeu : lutter contre les « déserts médicaux » en répartissant mieux les médecins sur le territoire, une régulation combattue par une partie de la profession au nom de la liberté d'installation.",
     None),
    ("VTANR5L15V2760", "sante", "Programmation pour l'hôpital public (2020)",
     "Proposition de loi prévoyant un plan pluriannuel d'investissement, de créations de postes et de revalorisations à l'hôpital public, au sortir de la première vague de Covid. L'enjeu : redonner des moyens à l'hôpital public, le débat portant sur le coût et le calendrier de tels engagements.",
     None),
    ("VTANR5L17V600", "sante", "Ratios de soignants par patient (2025)",
     "Instaure un nombre minimum de soignants par patient dans les établissements de santé (ratios), pour garantir un niveau de personnel au chevet des malades. L'enjeu : la sécurité des patients et les conditions de travail des soignants, mis en balance avec le coût et la pénurie de personnel disponible.",
     None),
    ("VTANR5L15V4414", "sante", "Allongement du délai d'IVG à 14 semaines (2022)",
     "Allonge de 12 à 14 semaines de grossesse le délai légal pour recourir à une interruption volontaire de grossesse (IVG). Le texte supprime aussi le délai de réflexion de deux jours après l'entretien psychosocial et autorise les sages-femmes à réaliser des IVG instrumentales en établissement de santé. L'enjeu : l'accès effectif à l'IVG pour les femmes hors délai (qui devaient jusque-là se rendre à l'étranger), face à des objections d'ordre médical et éthique.",
     None),
    ("VTANR5L17V3656", "sante", "Interdiction des dépassements d'honoraires sur les consultations de santé sexuelle (2025)",
     "Amendement au budget de la Sécurité sociale 2026 visant à interdire les dépassements d'honoraires sur les consultations de prévention, de dépistage des infections sexuellement transmissibles, de contraception et de suivi gynécologique. L'enjeu : l'accès financier à la santé sexuelle, mis en balance avec la liberté de fixation des honoraires médicaux.",
     None),
    ("VTANR5L17V7261", "sante", "Reconnaissance de la responsabilité de l'État et indemnisation des victimes du chlordécone",
     "Reconnaît la responsabilité de l'État dans le préjudice sanitaire, moral, écologique et économique subi par la Guadeloupe et la Martinique et leurs populations, résultant de l'autorisation du chlordécone (un insecticide utilisé dans les bananeraies antillaises jusqu'en 1993, alors que sa toxicité et sa persistance dans les sols et l'eau étaient déjà documentées) et de son usage prolongé. Donne un an au Gouvernement pour proposer au Parlement les modalités d'indemnisation des victimes, notamment via une extension possible du fonds existant pour les victimes de pesticides. L'enjeu : la réparation d'un préjudice sanitaire de long terme (le chlordécone, un perturbateur endocrinien, reste présent dans les sols antillais pour plusieurs siècles), le débat portant sur l'ampleur et le financement de cette indemnisation.",
     "Adopté une première fois par l'Assemblée le 29 février 2024 (scrutin n°3382 : 100 pour, 1 contre, 80 abstentions), modifié par le Sénat le 12 juin 2025, puis adopté définitivement et à l'unanimité par l'Assemblée le 2 juin 2026 (scrutin n°7261 : 236 pour) : c'est ce second vote qui est affiché ici. Promulguée le 12 juin 2026 (loi n° 2026-491)."),
    ("VTANR5L17V7303", "sante", "Contamination au cadmium des engrais et de l'alimentation (2026)",
     "Abaisse la teneur maximale en cadmium (un métal lourd toxique) autorisée dans les engrais phosphatés : de 90 mg/kg actuellement à 40 mg/kg au 1ᵉʳ janvier 2027, puis 20 mg/kg au 1ᵉʳ janvier 2030. L'enjeu : réduire la contamination des sols agricoles et, à terme, de la chaîne alimentaire, mis en balance avec le coût pour les fabricants d'engrais et les agriculteurs d'une mise aux normes plus rapide.",
     "Adopté en première lecture le 3 juin 2026 (144 pour, 22 contre, 4 abstentions), avis défavorable du Gouvernement. Le texte doit encore être examiné par le Sénat."),
    ("VTANR5L17V852", "sante", "Interdiction des PFAS, les « polluants éternels » (2025)",
     "Interdit progressivement la fabrication, l'importation et la vente de produits contenant des PFAS (substances per- et polyfluoroalkylées) dans plusieurs secteurs (textiles d'habillement, cosmétiques, farts de ski) en raison de leur persistance dans l'environnement et de leurs effets sanitaires suspectés. Crée aussi une contribution des industriels rejetant des PFAS, destinée à financer la dépollution de l'eau. L'enjeu : réduire l'exposition à ces polluants durables, mis en balance avec les délais et coûts de reconversion pour les filières concernées.",
     "Adoption définitive en deuxième lecture le 20 février 2025 (231 pour, 51 contre, 7 abstentions). En première lecture (avril 2024), un amendement avait exempté les ustensiles de cuisine antiadhésifs du champ de l'interdiction."),
    ("VTANR5L17V4515", "sante", "Nutri-Score obligatoire sur les emballages alimentaires (2025)",
     "Aurait rendu obligatoire l'affichage du Nutri-Score (l'étiquetage nutritionnel simplifié, noté de A à E) sur les emballages alimentaires ; il est aujourd'hui facultatif, en France comme dans le reste de l'Union européenne. L'enjeu : mieux informer les consommateurs sur la qualité nutritionnelle des produits, mis en balance avec les contraintes pour les industriels et les réticences de certaines filières.",
     "Amendement au budget de la Sécurité sociale 2026 : adopté une première fois en première lecture, supprimé par le Sénat, puis son rétablissement a été rejeté de justesse en nouvelle lecture le 3 décembre 2025 (117 pour, 120 contre, 6 abstentions)."),

    # ── Éducation (thème créé le 25/07/2026) ─────────────────────────────────
    ("VTANR5L15V351", "education", "Parcoursup : accès à l'université (loi ORE, 2018)",
     "Crée la plateforme Parcoursup et autorise les universités à examiner les dossiers des lycéens (« attendus », prérequis) pour l'accès aux filières, surtout celles très demandées. L'enjeu : mieux orienter et réduire l'échec en licence, la critique portant sur l'instauration d'une forme de sélection à l'entrée de l'université.",
     None),
    ("VTANR5L15V3188", "education", "Programmation de la recherche 2021-2030 (LPR)",
     "Fixe une trajectoire budgétaire pluriannuelle pour la recherche publique jusqu'en 2030 et modifie les carrières scientifiques (nouveaux contrats, « chaires de professeur junior »). L'enjeu : le niveau et la prévisibilité des moyens de la recherche, le débat portant sur une hausse jugée trop lente et sur la précarité de certains nouveaux contrats.",
     None),
    ("VTANR5L17V7397", "education", "Bourses étudiantes et précarité (2026)",
     "Réforme les bourses sur critères sociaux (revalorisation, élargissement des bénéficiaires) et prévoit des mesures contre la précarité étudiante. L'enjeu : les conditions de vie et le pouvoir d'achat des étudiants, mis en balance avec le coût pour les finances publiques.",
     None),
    ("VTANR5L17V2880", "education", "Antisémitisme dans l'enseignement supérieur (2025)",
     "Renforce la lutte contre l'antisémitisme dans les universités : signalement des actes, sanctions disciplinaires, formation et sensibilisation des étudiants. L'enjeu : protéger les étudiants face aux actes antisémites, la question débattue étant l'articulation de ces mesures avec la liberté d'expression et le militantisme sur les campus.",
     None),
    ("VTANR5L17V1550", "education", "Scolarisation des élèves handicapés (2025)",
     "Réorganise l'accompagnement des élèves en situation de handicap : création de « pôles d'appui à la scolarité » et évolution du rôle des accompagnants (AESH). L'enjeu : mieux scolariser les enfants handicapés, la critique portant sur les moyens réels et sur le statut des accompagnants.",
     None),
    ("VTANR5L17V840", "education", "Égalité des chances pour les écoles de service public (2025)",
     "Prolonge un dispositif d'aide (classes préparatoires intégrées, accompagnement) permettant à des jeunes de milieux modestes de préparer les concours d'accès aux écoles de service public (administration, magistrature…). L'enjeu : diversifier le recrutement de la haute fonction publique, la mesure étant contestée par ses opposants comme une forme de traitement préférentiel.",
     None),
    ("VTANR5L17V5845", "education", "Enseignement de la défense nationale à l'école (2026)",
     "Renforce l'enseignement des enjeux de défense nationale dans le « parcours de citoyenneté » des collégiens et lycéens (lien armée-Nation, connaissance des menaces). L'enjeu : sensibiliser les jeunes aux questions de défense, un contenu jugé par ses opposants trop orienté vers l'« esprit de défense ».",
     None),

    # ── Taxe et impôts (thème créé le 25/07/2026) ────────────────────────────
    ("VTANR5L15V272", "taxe-impots", "Budget 2018 : fin de l'ISF et « flat tax » (2017)",
     "Premier budget du quinquennat Macron. Il supprime l'impôt de solidarité sur la fortune (ISF) : l'impôt annuel qui frappait l'ensemble du patrimoine (biens immobiliers, placements financiers, etc.) au-delà d'environ 1,3 million d'euros. Il le remplace par l'impôt sur la fortune immobilière (IFI), limité au seul patrimoine immobilier : les placements financiers ne sont donc plus taxés. Il instaure aussi un prélèvement forfaitaire unique, la « flat tax » de 30 %, sur les revenus du capital (dividendes, intérêts). L'enjeu : alléger la fiscalité du capital, présenté par ses promoteurs comme un encouragement à l'investissement et par ses opposants comme un avantage fiscal aux plus fortunés.",
     None),
    ("VTANR5L15V1536", "taxe-impots", "Taxe carbone et « gilets jaunes » : déclaration (2018)",
     "Déclaration du Gouvernement, en plein mouvement des « gilets jaunes », sur la fiscalité écologique et ses conséquences sur le pouvoir d'achat. Le Premier ministre y annonce la suspension pour six mois des hausses de taxes sur les carburants et l'énergie prévues au 1ᵉʳ janvier 2019, et indique que le Gouvernement ne proposera pas de les rétablir dans le projet de loi de finances. Voter pour revenait à approuver cette position. L'enjeu : concilier le signal-prix climatique et le pouvoir d'achat des ménages, la hausse de la taxe carbone ayant déclenché la contestation.",
     None),
    ("PE-HTV-143328", "taxe-impots", "Impôt minimum mondial de 15 % (UE, 2022)",
     "Transposition dans l'Union de l'accord international (OCDE) instaurant un taux d'imposition minimum de 15 % sur les bénéfices des grandes multinationales, pour limiter l'évitement fiscal. L'enjeu : réduire la concurrence fiscale entre pays et faire contribuer les groupes qui délocalisent leurs profits.",
     "Vote d'ensemble au Parlement européen. Les six délégations françaises ont voté pour."),
    ("PE-HTV-147044", "taxe-impots", "Blocages nationaux de l'impôt mondial (UE, 2022)",
     "Résolution adoptée après le véto de la Hongrie, en juin 2022, sur la directive transposant l'impôt minimum mondial de 15 % (l'unanimité étant requise en matière fiscale dans l'Union). Le Parlement invite la Commission à recourir, le cas échéant, à l'article 116 du traité, qui permet de statuer à la majorité qualifiée, et à explorer d'autres voies comme la coopération renforcée ; il demande de ne pas approuver le plan de relance hongrois tant que tous les critères ne sont pas remplis. L'enjeu : appliquer l'accord fiscal international malgré un blocage national, ce qui touche à la souveraineté fiscale des États.",
     "Résolution du 6 juillet 2022. Côté français : 52 élus pour et 16 contre, à savoir les élus du RN (groupe Identité et démocratie) et deux non-inscrits élus sur une liste RN, Nicolas Bay et Maxette Pirbakas."),

    # ── Travail (thème créé le 25/07/2026) ───────────────────────────────────
    ("VTANR5L15V106", "travail", "Réforme du code du travail par ordonnances (2017)",
     "Autorise le Gouvernement à réformer le code du travail par ordonnances : plafonnement des indemnités prud'homales en cas de licenciement jugé abusif, fusion des instances représentatives du personnel (comité social et économique), place accrue des accords d'entreprise. L'enjeu : assouplir le droit du travail pour, selon le Gouvernement, favoriser l'embauche, au prix, pour ses opposants, d'une baisse des protections des salariés.",
     None),
    ("VTANR5L16V236", "travail", "Réforme de l'assurance chômage (2022)",
     "Permet de moduler les règles de l'assurance chômage selon la conjoncture (durée d'indemnisation réduite quand le chômage est bas). L'enjeu : inciter au retour à l'emploi lorsque le marché est favorable, une logique contestée comme une baisse des droits des demandeurs d'emploi.",
     None),
    ("VTANR5L16V2965", "travail", "France Travail : RSA sous condition d'activité (2023)",
     "Crée France Travail (en remplacement de Pôle emploi) et conditionne le versement du RSA à 15 à 20 heures hebdomadaires d'activité ou d'accompagnement. L'enjeu : favoriser le retour à l'emploi des allocataires, une mesure jugée par ses opposants comme une contrainte pénalisant les plus précaires.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L16V2112", "travail", "Partage de la valeur en entreprise (ANI, 2023)",
     "Transpose un accord entre syndicats et patronat pour développer l'intéressement, la participation et les primes dans les entreprises, y compris les plus petites. L'enjeu : mieux associer les salariés aux résultats de leur entreprise, la critique portant sur le choix de primes ponctuelles plutôt que de hausses de salaire.",
     None),
    ("PE-HTV-155946", "travail", "Stages de qualité dans l'Union (2023)",
     "Position du Parlement européen pour un cadre garantissant des stages de qualité : lutte contre les stages non ou mal rémunérés et contre les stages répétés se substituant à un véritable emploi. L'enjeu : protéger les jeunes en stage contre la précarité, la question débattue étant le degré de contrainte imposé aux employeurs.",
     "Position adoptée au Parlement européen ; la délégation du RN a voté contre."),
    ("VTANR5L17V3690", "travail", "Création du congé supplémentaire de naissance (2025)",
     "Crée un congé indemnisé qui s'ajoute aux congés de maternité, de paternité et d'adoption existants : un ou deux mois pour chacun des deux parents, fractionnable en deux périodes d'un mois, l'un des deux mois ne pouvant être pris simultanément par les deux parents. Le droit est ouvert aux actifs (salariés, indépendants, agriculteurs, fonctionnaires) qui remplissent les conditions d'affiliation déjà applicables aux indemnités journalières de maternité, soit six mois d'affiliation à la Sécurité sociale et une durée minimale d'activité. L'indemnisation est dégressive, son niveau étant renvoyé à un décret (fixé depuis à 70 % du revenu net le premier mois et 60 % le second, dans la limite d'un plafond). L'enjeu : allonger le temps passé auprès d'un nouveau-né et mieux répartir ce temps entre les parents, mis en balance avec le coût pour la Sécurité sociale (estimé de 0,3 milliard d'euros la première année à 0,6 milliard à terme) et l'organisation des entreprises.",
     "Vote sur l'article 42 du budget de la Sécurité sociale pour 2026, en première lecture, après l'adoption d'amendements autorisant le fractionnement du congé. Tous les groupes ont voté pour, sauf Les Républicains (majoritairement contre) et Horizons (divisé). L'article a été adopté de nouveau en nouvelle lecture (220 voix contre 2) ; il figure à l'article 99 de la loi du 30 décembre 2025."),
    ("VTANR5L17V3686", "travail", "Congé de naissance réservé aux couples dont un parent est français (2025)",
     "Amendement au budget de la Sécurité sociale 2026 visant à n'ouvrir le congé supplémentaire de naissance qu'« aux personnes d'un couple dont au moins l'un des membres est de nationalité française ». Son exposé des motifs avance qu'il est « légitime que cet effort soit prioritairement orienté vers les familles qui ont un lien stable, durable et reconnu avec la communauté nationale ». L'enjeu : conditionner l'accès à une prestation sociale à la nationalité.",
     "Amendement déposé par la députée Angélique Ranc et cosigné par l'ensemble du groupe Rassemblement national (123 signataires), rejeté par 147 voix contre 68 : il a été soutenu par le Rassemblement national, l'Union des droites pour la République et deux députés non inscrits, tous les autres groupes votant contre. Un second amendement du même groupe, subordonnant le congé à des conditions d'affiliation et d'activité, a également été rejeté (scrutin n°3687), la rapporteure et la ministre le jugeant déjà satisfait : le congé étant une prestation contributive, il est déjà soumis aux conditions d'affiliation des indemnités journalières de maternité."),

    # ── Ajouts du 25/07/2026 (cancer, transports, femmes, handicap) ──────────
    ("VTANR5L17V6572", "sante", "Médicaments contre les cancers de l'enfant (2026)",
     "Crée un cadre pour développer les médicaments contre les cancers et les maladies rares de l'enfant (recherche, disponibilité), financé notamment par une contribution des laboratoires pharmaceutiques. L'enjeu : répondre au manque de traitements pédiatriques, faute de rentabilité pour l'industrie ; texte porté de façon transpartisane, salué par les associations de familles.",
     "Adopté très largement (98 voix contre 22). Fait notable : le RN est le seul groupe à avoir voté contre."),
    ("PE-HTV-144789", "ecologie-agriculture", "Quotas CO₂ pour l'aviation (UE, 2022)",
     "Position de négociation du Parlement sur le marché carbone européen appliqué à l'aviation : fin des quotas d'émission gratuits dont bénéficiaient les compagnies aériennes dès 2025, soit deux ans plus tôt que ce que proposait la Commission, et extension du système à tous les vols au départ d'un aéroport de l'Espace économique européen, y compris vers des destinations situées hors de cet espace. Les compagnies devraient donc payer davantage pour leurs émissions de CO₂. L'enjeu : faire contribuer le transport aérien à la baisse des émissions, mis en balance avec le coût pour les compagnies et le prix des billets.",
     "Vote du 8 juin 2022 fixant la position de négociation du Parlement. Côté français : 52 élus pour et 15 contre, à savoir les élus du RN (groupe Identité et démocratie), à l'exception de Thierry Mariani qui s'est abstenu, ainsi que deux non-inscrits élus sur la liste RN, Nicolas Bay et Jérôme Rivière."),
    ("VTANR5L15V619", "societe", "Violences sexuelles et sexistes : loi Schiappa (2018)",
     "Renforce la lutte contre les violences sexuelles et sexistes : allongement à trente ans du délai de prescription des crimes sexuels sur mineurs, création de l'« outrage sexiste » (verbalisation du harcèlement de rue), répression du cyberharcèlement en meute. L'enjeu : mieux protéger les victimes, le débat portant sur l'absence de seuil d'âge clair du consentement et sur le risque de juger certains viols comme de simples agressions sexuelles.",
     "Première lecture. La gauche a voté contre, jugeant le texte insuffisant sur ces points."),
    ("VTANR5L16V1843", "femmes", "Accès des femmes aux responsabilités dans la fonction publique (parité, 2023)",
     "Renforce la place des femmes aux postes de direction de la fonction publique. Le taux de primo-nominations de personnes de chaque sexe est porté à 50 % pour les emplois à la décision du Gouvernement, les cabinets ministériels et la Présidence de la République ; le dispositif de nominations équilibrées est étendu à de nouveaux emplois et employeurs publics (Conseil d'État, Cour des comptes, Conseil économique, social et environnemental, fonction publique parlementaire), avec un plancher de 40 %. Le texte avance aussi l'entrée en vigueur de l'index d'égalité professionnelle. L'enjeu : accélérer l'égalité femmes-hommes aux responsabilités, la question débattue étant le recours aux quotas et le calendrier.",
     None),
    ("VTANR5L15V2865", "travail", "Insertion par l'activité économique et « territoires zéro chômeur » (2020)",
     "Réforme les parcours d'insertion par l'activité économique : l'agrément préalable de Pôle emploi est supprimé et remplacé par un examen de l'éligibilité par les structures d'insertion elles-mêmes ; un contrat à durée indéterminée d'inclusion est créé pour les personnes de 57 ans et plus ; un « contrat passerelle » est expérimenté pour faciliter le passage vers une entreprise classique. Le texte prolonge de cinq ans l'expérimentation « territoire zéro chômeur de longue durée » et l'étend à 60 territoires. L'enjeu : ramener vers l'emploi des personnes qui en sont durablement éloignées.",
     "Adopté à l'unanimité des votants."),

    # ── Ajouts issus de l'étude de la base AN (26/07/2026) ───────────────────
    ("VTANR5L15V3421", "securite-justice", "Loi contre le séparatisme : principes de la République (2021)",
     "Renforce le contrôle de l'État sur les associations et les lieux de culte (subventions conditionnées à un « contrat d'engagement républicain », fermetures administratives facilitées), encadre strictement l'instruction en famille (désormais soumise à autorisation) et étend l'obligation de neutralité religieuse aux salariés chargés d'une mission de service public. L'enjeu : lutter contre l'islamisme radical et le « séparatisme », mis en balance avec le risque d'atteinte aux libertés d'association, de culte et d'enseignement.",
     "Projet de loi présenté après l'assassinat de Samuel Paty ; adopté en première lecture le 16 février 2021. Il a été critiqué à la fois par une partie de la gauche (atteinte aux libertés) et par la droite et l'extrême droite (jugé insuffisant)."),
    ("VTANR5L16V1305", "securite-justice", "JO 2024 : vidéosurveillance algorithmique (2023)",
     "Loi d'organisation des Jeux olympiques et paralympiques de Paris 2024, dont la mesure la plus débattue autorise, à titre expérimental, la vidéosurveillance « algorithmique » : des caméras couplées à une intelligence artificielle qui repère automatiquement des situations à risque (mouvements de foule, bagage abandonné…) dans l'espace public. C'est la première fois qu'un tel dispositif est légalisé en France. L'enjeu : sécuriser un événement de masse, mis en balance avec le risque d'une surveillance généralisée.",
     "Première lecture, 28 mars 2023. Le recours à la reconnaissance faciale a été explicitement exclu du texte."),
    ("VTANR5L16V2796", "institutions", "Loi SREN : réguler l'espace numérique (2023)",
     "Encadre plusieurs usages d'internet : vérification de l'âge sur les sites pornographiques, peine de « bannissement » des réseaux sociaux pour les auteurs de cyberharcèlement, filtre « anti-arnaque » dans les navigateurs, et nouvelles obligations pour les grandes plateformes et l'hébergement de données. L'enjeu : mieux protéger les internautes, en particulier les mineurs, face aux craintes pour l'anonymat en ligne et la liberté d'expression.",
     "Première lecture, 17 octobre 2023. Plusieurs dispositions ont été ajustées pour rester compatibles avec le règlement européen sur les services numériques (DSA)."),
    ("VTANR5L15V1209", "pouvoir-achat-fiscalite", "Loi PACTE : entreprises et privatisations (2018)",
     "Vaste loi sur les entreprises : elle simplifie leur création et leur croissance, réforme l'épargne salariale et l'épargne-retraite, et autorise la privatisation d'Aéroports de Paris (ADP) et de la Française des jeux (FDJ) ainsi que la réduction de la participation de l'État dans Engie. L'enjeu : faciliter le financement et l'investissement des entreprises, la privatisation d'actifs publics stratégiques étant, elle, très contestée.",
     "Première lecture, 9 octobre 2018. La privatisation d'Aéroports de Paris a déclenché une tentative de référendum d'initiative partagée (RIP), qui n'a pas réuni assez de soutiens ; ce projet de privatisation a finalement été abandonné."),
    ("VTANR5L15V729", "ecologie-agriculture", "Loi EGalim : revenu agricole et alimentation (2018)",
     "Cherche à mieux rémunérer les agriculteurs : les prix payés aux producteurs doivent davantage tenir compte de leurs coûts de production, les promotions en supermarché sont encadrées et le seuil de revente à perte est relevé. Le texte comporte aussi des mesures sur l'alimentation (produits bio et locaux dans les cantines, bien-être animal). L'enjeu : le revenu paysan, alors que l'effet réel de la loi sur les prix a été jugé décevant.",
     "Première lecture, 30 mai 2018 (loi « pour l'équilibre des relations commerciales dans le secteur agricole et alimentaire et une alimentation saine et durable », dite EGalim)."),
    ("VTANR5L14V981", "europe-international", "Reconnaissance de l'État de Palestine (résolution, 2014)",
     "Résolution (un texte qui exprime une position solennelle de l'Assemblée, sans valeur juridique contraignante) invitant le gouvernement français à reconnaître l'État de Palestine, dans la perspective d'un règlement du conflit israélo-palestinien fondé sur la coexistence de deux États. L'enjeu : un geste diplomatique symbolique, sujet redevenu très sensible depuis la guerre déclenchée en 2023.",
     "Adoptée le 2 décembre 2014. Une résolution n'engage pas juridiquement le gouvernement, seul compétent pour reconnaître un État."),
    ("VTANR5L16V1361", "logement", "Loi anti-squat : occupation illicite des logements (2023)",
     "Triple les peines encourues pour le squat d'un logement et accélère les procédures d'expulsion, y compris pour les locataires qui cessent de payer leur loyer, dont le bail peut être résilié plus rapidement. L'enjeu : mieux protéger les propriétaires face aux occupations illégales et aux impayés, mis en balance avec la protection des locataires en difficulté et le droit au logement.",
     "Deuxième lecture, 4 avril 2023 (proposition de loi dite « Kasbarian-Bergé »). Des associations de lutte contre le mal-logement ont dénoncé un texte fragilisant les locataires modestes."),
    ("VTANR5L15V928", "logement", "Loi ELAN : logement et urbanisme (2018)",
     "Réforme du logement visant à « construire plus, plus vite et moins cher » : allègement de normes (dans les immeubles d'habitation collectifs neufs, la part de logements devant être accessibles aux personnes handicapées passe de la totalité à un dixième, les autres devant être « évolutifs », c'est-à-dire rendus accessibles par des travaux simples), encadrement des locations touristiques de courte durée (type Airbnb) et réorganisation du logement social. L'enjeu : relancer la construction, le recul des normes d'accessibilité ayant été vivement critiqué par les associations de personnes handicapées.",
     "Première lecture, 12 juin 2018 (loi portant évolution du logement, de l'aménagement et du numérique). Le seuil d'un dixième voté à ce stade a ensuite été porté à 20 % en commission mixte paritaire ; c'est cette proportion qui figure dans la loi promulguée le 23 novembre 2018."),
    ("VTANR5L17V2262", "logement", "Encadrement des loyers dans les outre-mer (2025)",
     "Ouvre, pour cinq ans et à titre expérimental, un plafonnement des loyers dans les collectivités régies par l'article 73 de la Constitution (Guadeloupe, Guyane, Martinique, La Réunion, Mayotte), que l'expérimentation métropolitaine créée par la loi Élan de 2018 avait laissées de côté. Les collectivités volontaires disposent de deux ans pour se porter candidates ; le loyer ne peut alors dépasser un loyer de référence majoré, et aucun complément de loyer ne peut être appliqué à un logement qui n'est pas décent. Un second volet adapte les normes des matériaux de construction aux contraintes locales. L'enjeu : le coût du logement dans les outre-mer, face au risque de décourager la mise en location.",
     "Texte d'origine sénatoriale, adopté sans modification par l'Assemblée le 5 juin 2025 : ce vote a donc valu adoption définitive, sans aucune voix contre. Promulgué le 13 juin 2025 (loi n° 2025-534)."),
    ("VTANR5L16V491", "logement", "Aide à la rénovation des passoires thermiques mises en location (2022)",
     "Amendement au budget 2023 transférant 1,1 milliard d'euros des crédits ferroviaires vers l'accompagnement de la transition énergétique, afin de financer une rénovation sans reste à charge, par l'intermédiaire de l'Anah, pour les propriétaires bailleurs aux revenus modestes possédant un logement classé F ou G. L'enjeu : permettre à ces bailleurs de réaliser les travaux avant les échéances d'interdiction de location prévues par la loi Climat et résilience, mis en balance avec le coût pour les finances publiques et la baisse des crédits ferroviaires.",
     None),
    ("VTANR5L16V2256", "defense", "Loi de programmation militaire 2024-2030 (2023)",
     "Fixe le budget et les priorités des armées pour 2024-2030 : 413 milliards d'euros, en forte hausse, pour moderniser la dissuasion nucléaire, les drones, le cyber et le renseignement, et reconstituer les stocks de munitions, dans le contexte de la guerre en Ukraine. L'enjeu : le réarmement et la souveraineté de défense de la France, mis en regard du poids de cet effort pour les finances publiques.",
     "Texte issu de la commission mixte paritaire, adopté le 12 juillet 2023."),

    # ── Budget (thème créé le 25/07/2026) : amendements du PLF 2026 ───────────
    # Lus par AXES (voir AXES ci-dessus et AXES_BUDGET dans build_site.py).
    # Positions de vote RÉELLES : la plupart de ces amendements de la 1re partie
    # du PLF 2026 ont été rendus caducs par le rejet global des recettes
    # (21 novembre 2025) puis l'adoption via l'article 49.3 : c'est dit dans
    # chaque contexte. Scrutins nominatifs vérifiés un à un contre le dump officiel.
    ("VTANR5L17V3300", "budget", "Taxe Zucman sur les très hauts patrimoines (budget 2026)",
     "Amendement au budget 2026 créant un impôt minimum de 2 % par an sur les patrimoines de plus de 100 millions d'euros (proposition dite « taxe Zucman »). L'enjeu : faire contribuer davantage les plus grandes fortunes, mis en regard du risque d'exil fiscal et de la difficulté à taxer un patrimoine qui n'a pas été vendu.",
     "Première partie du projet de loi de finances pour 2026, examen prioritaire du 31 octobre 2025. Rejeté (172 pour, 228 contre) : la gauche a voté pour, le Rassemblement national et le bloc central contre."),
    ("VTANR5L17V3242", "budget", "Taxe sur les super-dividendes (budget 2026)",
     "Amendement au budget 2026 instaurant une taxe sur les « super-dividendes » : chez les entreprises réalisant plus de 750 millions d'euros de chiffre d'affaires, la part des dividendes dépassant 1,25 fois la moyenne versée sur les exercices 2017 à 2019 serait taxée de 20 % à 33 % selon l'ampleur du dépassement, jusqu'à fin 2027. L'enjeu : capter une part des versements exceptionnels aux actionnaires.",
     "Première partie du PLF 2026. Adopté (71 pour, 63 contre, 40 abstentions) grâce à l'abstention du Rassemblement national, avant d'être rendu caduc par le rejet global de la partie recettes (21 novembre 2025). La gauche a voté pour, le bloc central contre."),
    ("VTANR5L17V3187", "budget", "Taxe sur les multinationales selon leur activité en France (budget 2026)",
     "Amendement au budget 2026 taxant les bénéfices des entreprises ayant une activité en France à proportion de la part de leur chiffre d'affaires réalisée en France, dès lors que les bénéfices qu'elles y déclarent sont proportionnellement plus faibles, pour limiter le transfert de bénéfices vers des pays à faible imposition. L'enjeu : faire contribuer les groupes qui logent leurs profits ailleurs.",
     "Première partie du PLF 2026. Adopté largement (207 pour, 89 contre) par la gauche et le Rassemblement national ensemble, le bloc central votant contre ; rendu caduc par le rejet global de la partie recettes."),
    ("VTANR5L17V3199", "budget", "Taxe sur les géants du numérique : taux doublé, seuil relevé (budget 2026)",
     "Amendement au budget 2026 doublant le taux de la « taxe GAFAM » sur les services numériques (de 3 % à 6 % des sommes encaissées en France) et relevant en même temps le seuil d'assujettissement : seules les entreprises dont le chiffre d'affaires numérique mondial dépasse 2 milliards d'euros seraient taxées, au lieu de 750 millions. L'enjeu : faire davantage contribuer les plus grands groupes du numérique, en sortant de la taxe les acteurs de taille intermédiaire.",
     "Première partie du PLF 2026. Adopté très largement (296 pour, 58 contre) sur presque tous les bancs (gauche, Rassemblement national et une partie du bloc central), puis rendu caduc par le rejet global de la partie recettes."),
    ("VTANR5L17V3149", "budget", "Surtaxe sur les bénéfices des grandes entreprises (budget 2026)",
     "Amendement du Gouvernement au budget 2026 reconduisant et réajustant la contribution exceptionnelle sur les bénéfices des grandes entreprises : allègement pour les entreprises intermédiaires, alourdissement pour les plus grandes (chiffre d'affaires supérieur à 3 milliards d'euros). L'enjeu : la contribution des grands groupes au redressement des comptes publics.",
     "Article 4 du PLF 2026, première lecture (27 octobre 2025). Adopté (196 pour, 149 contre). La gauche et le centre (MoDem, LIOT) ont voté pour l'alourdissement du taux supérieur, le Rassemblement national contre ; Renaissance et Les Républicains étaient partagés."),
    ("VTANR5L17V3096", "budget", "Indexation du barème de l'impôt sur le revenu (budget 2026)",
     "Amendement au budget 2026 indexant le barème de l'impôt sur le revenu sur l'inflation. Sans indexation (le « gel » du barème), la hausse des prix rend imposables des ménages jusque-là non imposables et augmente mécaniquement l'impôt de chacun. L'enjeu : protéger le pouvoir d'achat des ménages face à l'inflation, au prix de moindres recettes pour l'État.",
     "Article 2 du PLF 2026, première lecture (25 octobre 2025). Adopté (226 pour, 104 contre) contre l'avis du Gouvernement, par une large coalition (Rassemblement national, La France insoumise, Les Républicains, une partie de Renaissance) ; les Socialistes ont voté contre. Rendu caduc par le rejet global de la partie recettes."),
    ("VTANR5L17V3848", "budget", "Taxe sur les jets privés (budget 2026)",
     "Amendement au budget 2026 supprimant l'avantage fiscal sur le carburant (kérosène) des jets privés et de l'aviation d'affaires, la recette étant affectée aux transports en commun d'Île-de-France. L'enjeu : rapprocher la fiscalité du transport aérien privé de celle des autres carburants, un sujet à forte charge symbolique.",
     "Article 15 du PLF 2026, première lecture (17 novembre 2025). Adopté (137 pour, 107 contre) par la gauche et une majorité du Rassemblement national, contre le bloc central et Les Républicains ; rendu caduc par le rejet global de la partie recettes."),
    ("VTANR5L17V10", "budget", "Réforme du barème de l'impôt sur le revenu pour augmenter le reste à vivre (2024)",
     "Amendement au budget 2025 créant de nouvelles tranches d'imposition sur le revenu pour alléger l'impôt des foyers aux revenus modestes et moyens (moins de 4 000 € net par mois) et augmenter leur reste à vivre après impôt. L'enjeu : rendre l'impôt sur le revenu plus progressif, le débat portant sur le coût pour les finances publiques et la compensation par d'autres tranches.",
     None),
    ("VTANR5L16V325", "budget", "Rétablissement de l'impôt de solidarité sur la fortune (2022)",
     "Amendement au budget 2023 visant à rétablir l'impôt de solidarité sur la fortune (ISF), supprimé en 2017 et remplacé par l'impôt sur la fortune immobilière (IFI). L'enjeu : taxer à nouveau le patrimoine financier des plus grandes fortunes, mis en balance avec le risque d'exil fiscal invoqué par ses opposants.",
     None),
    ("VTANR5L17V3335", "budget", "Suppression du prélèvement forfaitaire unique sur les revenus du capital (2025)",
     "Amendement au budget 2026 visant à supprimer le prélèvement forfaitaire unique (PFU, ou « flat tax »), taxé à 30 %, pour réintégrer les revenus du capital (dividendes, intérêts, plus-values) au barème progressif de l'impôt sur le revenu, comme les revenus du travail. L'enjeu : une même règle fiscale pour tous les types de revenus, mis en balance avec le risque d'une moindre attractivité de l'épargne et de l'investissement en actions.",
     None),
    ("VTANR5L17V3336", "budget", "Relèvement du taux du prélèvement forfaitaire unique (2025)",
     "Amendement au budget 2026 relevant, sans le supprimer, le taux du volet impôt sur le revenu du prélèvement forfaitaire unique (PFU) sur les revenus du capital, de 12,8 % à 15,8 %. L'enjeu : le même que pour le PFU dans son ensemble, mais par un relèvement du taux plutôt que par sa suppression complète.",
     None),
    # ── Défense : ajouts issus de l'étude AN + PE (26/07/2026) ───────────────
    ("VTANR5L14V510", "defense", "Intervention militaire au Mali : opération Serval (2013)",
     "Déclaration du Gouvernement (article 35 de la Constitution) autorisant la prolongation de l'intervention militaire française au Mali, lancée en janvier 2013 (opération Serval) pour stopper l'avancée de groupes jihadistes vers Bamako. L'enjeu : engager durablement l'armée française dans la lutte antiterroriste au Sahel.",
     "Vote quasi unanime : union nationale sur l'engagement des troupes."),
    ("VTANR5L14V998", "defense", "Engagement des forces françaises en Irak contre Daech (2015)",
     "Déclaration du Gouvernement (article 35) autorisant la prolongation de l'engagement des forces françaises en Irak au sein de la coalition internationale contre l'organisation État islamique (Daech). L'enjeu : la participation de la France à la guerre contre Daech.",
     "Vote quasi unanime."),
    ("VTANR5L14V1195", "defense", "Frappes aériennes en Syrie contre Daech (2015)",
     "Autorisation de prolonger les frappes aériennes françaises au-dessus de la Syrie contre l'organisation État islamique, engagées à l'automne 2015 après les attentats. L'enjeu : étendre l'intervention anti-Daech au territoire syrien.",
     "Vote quasi unanime."),
    ("VTANR5L16V650", "defense", "Soutien à l'Arménie face à l'Azerbaïdjan (2022)",
     "Résolution (sans valeur juridique contraignante) exigeant la fin de l'agression de l'Azerbaïdjan contre l'Arménie et appelant à des sanctions. L'enjeu : le soutien de la France à l'Arménie dans le conflit du Haut-Karabakh.",
     "Adoptée à l'unanimité des votants."),
    ("VTANR5L16V1483", "defense", "Classer le groupe Wagner comme organisation terroriste (2023)",
     "Résolution appelant la France et l'Union européenne à inscrire le groupe paramilitaire russe Wagner sur la liste des organisations terroristes, en raison de ses exactions en Afrique et en Ukraine. L'enjeu : la réponse à l'influence militaire russe.",
     "Adoptée à l'unanimité des votants."),
    ("VTANR5L17V683", "defense", "Condamnation de la répression du régime iranien (2025)",
     "Résolution condamnant l'oppression imposée aux femmes iraniennes et la répression du régime de Téhéran, et réaffirmant le soutien de la France au mouvement pour la liberté en Iran. L'enjeu : la position de la France face au régime iranien.",
     "Adoptée à l'unanimité des votants."),
    ("VTANR5L16V1456", "defense", "Conflit israélo-palestinien : résolution « deux États » (2023)",
     "Résolution d'origine parlementaire, sans valeur contraignante, réaffirmant la nécessité d'une solution à deux États et condamnant la politique menée par l'État d'Israël envers les Palestiniens. Le texte employait le terme, très contesté, d'« apartheid ». L'enjeu : la position de la France sur le conflit israélo-palestinien.",
     "Rejetée (71 pour, 199 contre). Le vocabulaire du texte et son origine (La France insoumise) ont concentré l'opposition d'une large partie de l'hémicycle."),
    ("PE-HTV-179048", "defense", "Gaza : famine, otages et solution à deux États (PE, 2025)",
     "Résolution du Parlement européen sur la guerre à Gaza : lutter contre la famine, obtenir la libération des otages détenus par le Hamas et avancer vers une solution à deux États. L'enjeu : la position de l'Union européenne sur la guerre entre Israël et le Hamas.",
     None),
    ("PE-HTV-172867", "defense", "Livre blanc sur l'avenir de la défense européenne (PE, 2025)",
     "Rapport du Parlement européen sur l'avenir de la défense européenne (« Livre blanc ») : renforcer les capacités militaires communes et l'autonomie stratégique de l'Union. L'enjeu : jusqu'où intégrer la défense à l'échelle européenne plutôt que de la garder strictement nationale.",
     None),
    ("PE-HTV-174053", "defense", "Politique de sécurité et de défense commune de l'UE (PE, 2025)",
     "Rapport annuel du Parlement européen sur la politique de sécurité et de défense commune (PSDC) de l'Union. L'enjeu : le bilan et l'orientation de la coopération militaire européenne.",
     None),
    ("PE-HTV-181587", "defense", "Programme pour l'industrie de défense européenne : EDIP (PE, 2025)",
     "Programme européen (EDIP) destiné à financer et coordonner la production d'armement au niveau de l'Union, dans le prolongement du plan « ReArm Europe ». L'enjeu : bâtir une base industrielle de défense européenne commune.",
     None),

    # ── Droits des femmes (thème créé le 27/07/2026) ──────────────────────────
    ("VTANR5L17V3061", "femmes", "Inscription du consentement dans la définition pénale du viol (2025)",
     "Proposition de loi modifiant la définition pénale du viol et des agressions sexuelles pour y inscrire l'absence de consentement, la définition actuelle reposant sur la notion de violence, contrainte, menace ou surprise. L'enjeu : mieux qualifier juridiquement les situations de sidération ou d'emprise, la question débattue étant les conséquences pratiques pour la preuve et l'instruction des affaires.",
     None),
    ("VTANR5L17V3620", "femmes", "Rapport sur la prise en charge des protections périodiques après 26 ans (2025)",
     "Amendement au budget de la Sécurité sociale 2026 demandant au Gouvernement un rapport, dans les six mois, évaluant l'impact financier d'une prise en charge des protections périodiques réutilisables au-delà de 26 ans. Cette prise en charge est aujourd'hui réservée aux assurées de moins de 26 ans et, sans limite d'âge, aux bénéficiaires de la complémentaire santé solidaire. L'enjeu : la précarité menstruelle après 26 ans. Le vote ne crée pas l'extension, il en demande l'évaluation chiffrée.",
     None),
    ("VTANR5L17V4613", "femmes", "Rétablissement de la prise en charge des protections périodiques réutilisables (2025)",
     "Amendement au budget de la Sécurité sociale 2026 visant à rétablir un article prévoyant la prise en charge des protections périodiques réutilisables pour les moins de 26 ans en situation de précarité, supprimé lors d'une étape antérieure de l'examen du texte. L'enjeu : la lutte contre la précarité menstruelle, mis en balance avec le coût pour l'Assurance maladie.",
     None),
    ("VTANR5L16V2137", "femmes", "Renforcement de l'accès des femmes aux responsabilités dans la fonction publique (2023)",
     "Proposition de loi (texte de la commission mixte paritaire) visant à renforcer l'accès des femmes aux postes de direction et de responsabilité dans les trois versants de la fonction publique. L'enjeu : l'égalité professionnelle dans l'emploi public, la question débattue étant le rythme et les sanctions associées aux objectifs de nominations équilibrées.",
     None),
    ("VTANR5L17V3077", "femmes", "Option d'imposition séparée pour les couples mariés ou pacsés (2025)",
     "Amendement au budget 2026 créant une option d'imposition séparée des revenus pour les couples mariés ou pacsés, aujourd'hui imposés obligatoirement ensemble (foyer fiscal commun). L'enjeu : présenté par ses partisans comme un moyen de renforcer l'autonomie financière au sein du couple, mis en balance avec la simplicité du système actuel et ses effets sur le calcul d'autres prestations.",
     None),
    ("VTANR5L16V2814", "femmes", "Extension de la prise en charge de la contraception masculine (2023)",
     "Amendement au budget de la Sécurité sociale 2024 visant à étendre la prise en charge à des méthodes de contraception masculine (thermique, notamment). L'enjeu : partager davantage la responsabilité contraceptive entre les partenaires, la question débattue étant le nombre restreint de méthodes disponibles et leur niveau de preuve scientifique.",
     None),
    ("VTANR5L16V2815", "femmes", "Extension de la prise en charge des préservatifs internes (2023)",
     "Amendement au budget de la Sécurité sociale 2024 visant à étendre la prise en charge aux préservatifs internes (dits féminins), jusque-là moins accessibles que les préservatifs externes. L'enjeu : élargir les moyens de prévention disponibles, notamment pour les personnes qui ne souhaitent pas ou ne peuvent pas utiliser un préservatif externe.",
     None),
    ("VTANR5L16V2259", "femmes", "Formation des magistrats aux violences intrafamiliales (2023)",
     "Amendement à la loi de programmation du ministère de la justice 2023-2027 visant à inscrire explicitement la prise en charge des violences intrafamiliales dans le champ de la formation des magistrats. L'enjeu : mieux outiller les juges face à ce contentieux spécifique.",
     None),
    ("VTANR5L16V1014", "femmes", "Renforcement des pénalités pour les entreprises ne respectant pas l'égalité salariale (2023)",
     "Amendement au budget rectificatif de la Sécurité sociale 2023 visant à augmenter la pénalité financière applicable aux entreprises qui ne respectent pas leurs objectifs de réduction des écarts de rémunération entre les femmes et les hommes (index de l'égalité professionnelle). L'enjeu : renforcer la portée dissuasive de la sanction, mis en balance avec son impact sur les entreprises déjà engagées dans une démarche de correction.",
     None),
]


# Équivalents au Sénat (MÊME texte, même lecture) : {uid vote clé AN : uid scrutin Sénat}.
# Appariements vérifiés le 24/07/2026 sur l'objet et la date. Les faux amis ont été
# écartés (nationalité Sénat = texte spécifique Mayotte ; « Duplomb » Sénat = projet
# agricole 2026 distinct ; pas de CMP soins palliatifs isolable). NULL sinon.
EQUIV_SENAT = {
    "VTANR5L16V3213": "SEN-2023-109",   # immigration 2023 (CMP, même jour)
    "VTANR5L16V186": "SEN-2021-152",    # pouvoir d'achat 2022 (CMP, même jour)
    "VTANR5L17V6319": "SEN-2025-250",   # fraudes sociales et fiscales (CMP)
    "VTANR5L17V1473": "SEN-2024-262",   # narcotrafic (CMP ; Retailleau ministre → sans position)
    "VTANR5L17V7405": "SEN-2025-308",   # sécurité / rétention administrative (CMP)
}


# Sens concret du vote : {uid : (ce que voter POUR signifie, ce que voter CONTRE signifie)}.
# Formulations neutres, à la 3e personne implicite (« … »), décrivant l'effet du vote,
# jamais le motif (le motif relève des nuances/justifications). Pour les motions de
# censure, « pour » = adopter la censure ; « contre » = ne pas censurer.
SENS = {
    # ── Écologie et agriculture ──
    "VTANR5L14V1120": ("adopter ces objectifs : ramener le nucléaire à 50 % de l'électricité, diviser par deux la consommation d'énergie, développer les renouvelables",
                       "rejeter cette trajectoire énergétique"),
    "VTANR5L15V139": ("interdire progressivement, d'ici 2040, la recherche et l'extraction de pétrole et de gaz en France",
                      "ne pas interdire cette exploitation"),
    "PE-HTV-110615": ("déclarer l'« urgence climatique » et en faire une priorité de l'action de l'Union",
                      "refuser cette déclaration d'urgence"),
    "PE-HTV-117083": ("renforcer les moyens européens communs (avions bombardiers d'eau, matériel) face aux catastrophes",
                      "s'opposer à ce renforcement"),
    "PE-HTV-118521": ("rendre juridiquement contraignant l'objectif de neutralité carbone en 2050",
                      "refuser des objectifs climatiques contraignants"),
    "PE-HTV-126261": ("préparer les territoires aux effets du changement climatique (canicules, inondations, incendies)",
                      "s'opposer à cette stratégie d'adaptation"),
    "VTANR5L15V3738": ("adopter la loi Climat (rénovation des logements, zones à faibles émissions, frein à la bétonisation)",
                       "rejeter le texte"),
    "VTANR5L16V823": ("faciliter et accélérer l'installation d'éoliennes et de panneaux solaires",
                      "rejeter le texte"),
    "VTANR5L16V133": ("créer un programme de recrutement de pompiers professionnels supplémentaires",
                      "rejeter cet amendement"),
    "VTANR5L16V1509": ("adopter un plan d'adaptation de la forêt cohérent avec la SNBC",
                       "rejeter cet amendement"),
    "VTANR5L16V1545": ("agir contre la perte de chemins forestiers nécessaires aux secours",
                       "rejeter cet amendement"),
    "VTANR5L16V1556": ("imposer des pare-feux d'arbres feuillus entre parcelles de résineux",
                       "rejeter cet amendement"),
    "VTANR5L17V4114": ("relever la taxe sur les conventions d'assurance pour financer les SDIS",
                       "rejeter cet amendement"),
    "PE-HTV-152544": ("interdire la vente de voitures neuves à moteur thermique à partir de 2035",
                      "refuser cette interdiction"),
    "PE-HTV-154173": ("renforcer le marché carbone (quotas d'émission payants, baisse accélérée, fin des quotas gratuits)",
                      "rejeter cette réforme"),
    "VTANR5L16V1533": ("accélérer et faciliter la construction de nouveaux réacteurs nucléaires",
                       "s'opposer à cette relance du nucléaire"),
    "VTANR5L16V2721": ("adopter la loi (accélérer l'implantation d'usines, dont les technologies de la transition)",
                       "rejeter le texte"),
    "PE-HTV-164499": ("imposer aux États des objectifs de restauration des milieux naturels dégradés",
                      "refuser ces objectifs"),
    "VTANR5L17V2957": ("adopter la loi (réautoriser l'acétamipride, faciliter réserves d'eau et agrandissements d'élevages)",
                       "rejeter le texte"),
    "VTANR5L17V8427": ("adopter la loi (réintroduction dérogatoire de pesticides interdits dont l'acétamipride, réserves d'eau, contrôles aux frontières)",
                       "rejeter le texte"),
    "PE-HTV-184178": ("fixer l'objectif européen de réduction des émissions à l'horizon 2040",
                      "refuser cet objectif intermédiaire"),
    # ── Pouvoir d'achat et fiscalité ──
    "VTANR5L14V726": ("allonger la durée de cotisation nécessaire (jusqu'à 43 ans) pour une retraite à taux plein",
                      "refuser cet allongement"),
    "VTANR5L14V1270": ("voter la censure : s'opposer à la loi travail et faire tomber le Gouvernement",
                       "ne pas censurer : laisser la loi travail être adoptée"),
    "VTANR5L16V186": ("adopter le paquet pouvoir d'achat (revalorisations, plafond des loyers, primes)",
                      "rejeter le texte"),
    "PE-HTV-147342": ("établir un cadre européen pour des salaires minimaux « adéquats »",
                      "s'opposer à ce cadre"),
    "VTANR5L16V1240": ("voter la censure : rejeter la réforme des retraites (64 ans) et faire tomber le Gouvernement",
                       "ne pas censurer : laisser la réforme des retraites s'appliquer"),
    "PE-HTV-154076": ("obliger les entreprises à la transparence sur les salaires (écarts femmes-hommes)",
                      "s'opposer à cette obligation"),
    "PE-HTV-167334": ("adopter la réforme du marché européen de l'électricité",
                      "rejeter cette réforme"),
    "VTANR5L17V881": ("instaurer un impôt minimum de 2 % par an sur les patrimoines de plus de 100 millions d'euros",
                      "refuser cet impôt plancher"),
    "VTANR5L17V6184": ("adopter la loi (alléger les normes des entreprises, supprimer les zones à faibles émissions)",
                       "rejeter le texte"),
    "VTANR5L17V6319": ("renforcer les contrôles et sanctions contre les fraudes sociales et fiscales",
                       "rejeter le texte"),
    # ── Sécurité et justice ──
    "VTANR5L14V1109": ("autoriser des techniques de surveillance élargies pour les services de renseignement",
                       "s'y opposer"),
    "VTANR5L14V1191": ("prolonger l'état d'urgence et renforcer ses mesures (perquisitions administratives, assignations)",
                       "refuser la prolongation"),
    "VTANR5L15V138": ("faire entrer dans le droit ordinaire des pouvoirs jusque-là réservés à l'état d'urgence",
                      "s'y opposer"),
    "VTANR5L15V3254": ("adopter la loi « sécurité globale » (pouvoirs de police, vidéosurveillance, drones, délit d'images)",
                       "rejeter le texte"),
    "PE-HTV-161873": ("demander une législation européenne encadrant les logiciels espions",
                      "s'opposer à cette demande"),
    "PE-HTV-155928": ("permettre l'accès direct, d'un pays à l'autre de l'Union, aux preuves numériques",
                      "s'y opposer"),
    "PE-HTV-168301": ("renforcer le contrôle du commerce des armes à feu civiles",
                      "s'y opposer"),
    "VTANR5L17V1473": ("adopter la loi (parquet spécialisé, prisons de haute sécurité, pouvoirs d'enquête élargis)",
                       "rejeter le texte"),
    "VTANR5L17V1624": ("durcir la réponse pénale aux mineurs délinquants (comparution immédiate dès 16 ans, excuse de minorité limitée)",
                       "s'opposer à ce durcissement"),
    "VTANR5L17V7987": ("instaurer une présomption de légitime défense pour les policiers et gendarmes qui font usage de leur arme",
                       "refuser cette présomption"),
    # ── Immigration ──
    "VTANR5L14V994": ("adopter la réforme de l'asile (procédures accélérées, recours suspensif, hébergement dirigé)",
                      "rejeter le texte"),
    "VTANR5L14V1237": ("adopter la révision (inscrire l'état d'urgence dans la Constitution, permettre la déchéance de nationalité pour terrorisme)",
                       "rejeter la révision"),
    "VTANR5L15V578": ("adopter la loi (délais d'asile raccourcis, rétention doublée, éloignements facilités)",
                      "rejeter le texte"),
    "VTANR5L16V3213": ("adopter la loi immigration (durcissements et régularisation des métiers en tension)",
                       "rejeter le texte"),
    "PE-HTV-167531": ("adopter le règlement (répartition des demandeurs, mécanisme « accueil ou contribution »)",
                      "rejeter le texte"),
    "PE-HTV-166929": ("étendre le fichier européen d'empreintes des migrants (Eurodac)",
                      "s'y opposer"),
    "PE-HTV-166904": ("instaurer un filtrage obligatoire (identité, sécurité, santé) aux frontières extérieures",
                      "s'y opposer"),
    "VTANR5L17V1308": ("durcir les conditions d'accès à la nationalité pour les enfants nés à Mayotte de parents étrangers",
                       "refuser ce durcissement"),
    "VTANR5L17V7405": ("allonger et élargir la rétention administrative avant expulsion",
                       "s'y opposer"),
    # ── Questions de société ──
    "VTANR5L14V511": ("ouvrir le mariage civil et l'adoption aux couples de même sexe",
                      "s'y opposer"),
    "VTANR5L14V1070": ("créer la sédation profonde en fin de vie et rendre les directives anticipées contraignantes",
                       "s'y opposer"),
    "VTANR5L15V2146": ("ouvrir la PMA aux couples de femmes et aux femmes seules",
                       "s'y opposer"),
    "PE-HTV-155091": ("approuver l'adhésion de l'Union à la Convention d'Istanbul (violences faites aux femmes)",
                      "s'y opposer"),
    "VTANR5L16V3045": ("adopter la loi « bien vieillir » (repérage des fragilités, lutte contre la maltraitance, carte des aides à domicile)",
                       "rejeter le texte"),
    "PE-HTV-164215": ("soutenir la stratégie européenne pour l'égalité des personnes LGBTIQ",
                      "s'y opposer"),
    "VTCGR5L16V1": ("inscrire dans la Constitution la liberté de recourir à l'avortement (IVG)",
                    "s'y opposer"),
    "PE-HTV-168054": ("demander l'inscription du droit à l'avortement dans la Charte des droits fondamentaux de l'Union",
                      "s'y opposer"),
    "PE-HTV-168573": ("adopter la directive de lutte contre les violences faites aux femmes",
                      "s'y opposer"),
    "VTANR5L17V5728": ("adopter la loi garantissant l'accès aux soins palliatifs partout sur le territoire",
                       "rejeter le texte"),
    "VTANR5L17V8280": ("créer un droit, très encadré, à l'aide à mourir",
                       "s'y opposer"),
    # ── Europe et international ──
    "VTANR5L14V30": ("ratifier le traité budgétaire européen (TSCG, « règle d'or » des déficits)",
                     "refuser la ratification"),
    "VTANR5L15V2059": ("ratifier l'accord de libre-échange entre l'Union et le Canada (CETA)",
                       "refuser la ratification"),
    "VTANR5L16V652": ("affirmer le soutien de la France à l'Ukraine et condamner l'invasion russe",
                      "refuser d'adopter cette résolution"),
    "PE-HTV-164536": ("accorder à l'Ukraine 50 milliards d'euros d'aide européenne sur 2024-2027",
                      "s'y opposer"),
    "PE-HTV-169362": ("appeler à maintenir et renforcer le soutien de l'Union à l'Ukraine",
                      "s'y opposer"),
    "VTANR5L17V456": ("soutenir la déclaration du Gouvernement, c'est-à-dire dire non à l'accord Mercosur en l'état",
                      "refuser de voter cette déclaration du Gouvernement (ce qui, ici, ne signifie pas soutenir l'accord)"),
    "VTANR5L17V988": ("renforcer le soutien à l'Ukraine (avoirs russes gelés, adhésion à l'Union)",
                      "s'y opposer"),
    "PE-HTV-186518": ("soutenir l'élargissement de l'Union (Ukraine, Moldavie, Balkans) sous condition de réformes",
                      "s'y opposer"),
    # ── Institutions et vie démocratique ──
    "VTANR5L14V594": ("créer la Haute Autorité pour la transparence (HATVP) et obliger les élus à déclarer patrimoine et intérêts",
                      "s'y opposer"),
    "PE-HTV-166183": ("adopter le règlement protégeant l'indépendance et le pluralisme des médias",
                      "s'y opposer"),
    "PE-HTV-166051": ("adopter le cadre européen encadrant l'intelligence artificielle (« AI Act »)",
                      "s'y opposer"),
    "PE-HTV-168862": ("demander le passage à l'étape suivante de l'article 7 contre la Hongrie et le retour sur le déblocage des fonds européens",
                      "s'y opposer"),
    "VTANR5L16V3725": ("élargir le corps électoral aux natifs et aux résidents installés depuis au moins dix ans",
                       "maintenir le corps électoral gelé sur la référence de 1998"),
    "VTANR5L17V1303": ("étendre le scrutin de liste paritaire (autant de femmes que d'hommes) aux communes de moins de 1 000 habitants",
                       "conserver le mode de scrutin actuel, sans parité obligatoire, dans ces communes"),
    "VTANR5L17V7454": ("inscrire dans la Constitution un statut d'autonomie pour la Corse au sein de la République",
                       "refuser ce statut d'autonomie"),
    # ── Santé ──
    "VTANR5L14V1200": ("adopter la réforme (tiers payant généralisé, paquet de cigarettes neutre, salles de consommation à moindre risque)",
                       "rejeter le texte"),
    "VTANR5L16V875": ("autoriser l'accès direct à certains paramédicaux, sans passer d'abord par un médecin",
                      "s'opposer à cet accès direct"),
    "VTANR5L17V1607": ("réguler l'installation des médecins (la limiter dans les zones déjà bien dotées)",
                       "refuser cette régulation de l'installation"),
    "VTANR5L15V2760": ("adopter le plan d'investissement et d'embauches pour l'hôpital public",
                       "rejeter cette proposition"),
    "VTANR5L17V600": ("imposer un nombre minimum de soignants par patient",
                      "ne pas imposer ces ratios"),
    "VTANR5L15V4414": ("allonger le délai légal de l'IVG de 12 à 14 semaines",
                       "maintenir le délai à 12 semaines"),
    "VTANR5L17V7261": ("reconnaître la responsabilité de l'État et engager l'indemnisation des victimes du chlordécone",
                       "rejeter le texte"),
    # ── Éducation ──
    "VTANR5L15V351": ("adopter Parcoursup et l'examen des dossiers pour l'accès à l'université",
                      "rejeter ce dispositif (jugé comme une sélection à l'entrée de la fac)"),
    "VTANR5L15V3188": ("adopter la programmation budgétaire de la recherche et la réforme des carrières",
                       "rejeter le texte"),
    "VTANR5L17V7397": ("adopter la réforme des bourses et les mesures contre la précarité étudiante",
                       "rejeter le texte"),
    "VTANR5L17V2880": ("adopter ces mesures de lutte contre l'antisémitisme à l'université",
                       "s'y opposer"),
    "VTANR5L17V1550": ("adopter cette réorganisation de l'accompagnement des élèves handicapés",
                       "s'y opposer"),
    "VTANR5L17V840": ("prolonger ce dispositif d'accès des jeunes défavorisés aux écoles de service public",
                      "refuser cette prolongation"),
    "VTANR5L17V5845": ("renforcer l'enseignement de la défense nationale à l'école",
                       "s'y opposer"),
    # ── Taxe et impôts ──
    "VTANR5L15V272": ("adopter le budget 2018 (suppression de l'ISF, « flat tax » sur les revenus du capital)",
                      "rejeter ce budget"),
    "VTANR5L15V1536": ("approuver la déclaration du Gouvernement, qui annonce la suspension pour six mois des hausses de taxes sur les carburants et l'énergie",
                       "ne pas approuver cette déclaration"),
    "PE-HTV-143328": ("instaurer un impôt minimum de 15 % sur les bénéfices des multinationales",
                      "s'y opposer"),
    "PE-HTV-147044": ("dénoncer les vétos nationaux et pousser à appliquer l'impôt mondial de 15 %",
                      "défendre le droit de véto national en matière fiscale"),
    # ── Travail ──
    "VTANR5L15V106": ("autoriser la réforme du code du travail par ordonnances (plafonnement prud'hommes, fusion des instances)",
                      "refuser cette réforme"),
    "VTANR5L16V236": ("permettre de moduler l'assurance chômage selon la conjoncture",
                      "s'opposer à cette modulation"),
    "VTANR5L16V2965": ("créer France Travail et conditionner le RSA à 15-20 h d'activité",
                       "s'y opposer"),
    "VTANR5L16V2112": ("développer l'intéressement, la participation et les primes en entreprise",
                       "s'y opposer"),
    "PE-HTV-155946": ("soutenir un encadrement des stages contre la précarité",
                      "s'y opposer"),
    "VTANR5L17V3690": ("créer un congé indemnisé d'un à deux mois par parent après une naissance",
                       "rejeter la création de ce congé"),
    "VTANR5L17V3686": ("réserver ce congé aux couples dont au moins un parent est de nationalité française",
                       "ouvrir ce congé sans condition de nationalité"),
    # ── Ajouts (cancer, transports, femmes, handicap) ──
    "VTANR5L17V6572": ("adopter le cadre de soutien aux médicaments contre les cancers de l'enfant (financé par une contribution des laboratoires)",
                       "rejeter le texte"),
    "PE-HTV-144789": ("faire payer davantage l'aviation pour ses émissions de CO₂ (fin des quotas gratuits)",
                      "s'y opposer"),
    "VTANR5L15V619": ("adopter la loi Schiappa (prescription allongée, outrage sexiste, cyberharcèlement)",
                      "rejeter le texte"),
    "VTANR5L16V1843": ("renforcer la parité aux postes de direction de la fonction publique",
                       "s'y opposer"),
    "VTANR5L15V2865": ("adopter la réforme de l'insertion par l'activité économique et l'extension de l'expérimentation « territoire zéro chômeur »",
                       "rejeter le texte"),
    # ── Ajouts (étude base AN, 26/07/2026) ──
    "VTANR5L15V3421": ("adopter la loi (contrôle renforcé des associations et des cultes, encadrement de l'instruction en famille, neutralité des services publics)",
                       "rejeter le texte"),
    "VTANR5L16V1305": ("adopter la loi et autoriser, à titre expérimental, la vidéosurveillance algorithmique pour les JO 2024",
                       "rejeter le texte / refuser cette surveillance"),
    "VTANR5L16V2796": ("adopter la loi (vérification d'âge sur les sites pornographiques, bannissement des cyberharceleurs, filtre anti-arnaque)",
                       "rejeter le texte"),
    "VTANR5L15V1209": ("adopter la loi PACTE (simplifications pour les entreprises, épargne, privatisations d'ADP et de la FDJ)",
                       "rejeter le texte / s'opposer aux privatisations"),
    "VTANR5L15V729": ("adopter la loi EGalim (meilleure rémunération des agriculteurs, encadrement des promotions, alimentation durable)",
                      "rejeter le texte"),
    "VTANR5L14V981": ("inviter la France à reconnaître l'État de Palestine",
                      "s'opposer à cette reconnaissance"),
    "VTANR5L16V1361": ("adopter la loi (sanctions accrues contre le squat, expulsions facilitées, y compris pour impayés)",
                       "rejeter le texte"),
    "VTANR5L15V928": ("adopter la loi ELAN (faciliter la construction, encadrer les locations touristiques, réformer le logement social)",
                      "rejeter le texte"),
    "VTANR5L17V2262": ("ouvrir aux outre-mer l'expérimentation du plafonnement des loyers",
                       "s'opposer à cet encadrement"),
    "VTANR5L16V2256": ("adopter la programmation militaire 2024-2030 (413 Md€, hausse du budget des armées)",
                       "rejeter le texte"),
    # ── Budget (amendements PLF 2026) ──
    "VTANR5L17V3300": ("instaurer un impôt plancher de 2 % par an sur les patrimoines de plus de 100 millions d'euros",
                       "refuser cet impôt sur les très hauts patrimoines"),
    "VTANR5L17V3242": ("taxer les « super-dividendes » exceptionnels versés par les grandes entreprises",
                       "refuser cette taxe sur les dividendes exceptionnels"),
    "VTANR5L17V3187": ("taxer les bénéfices des multinationales à proportion de leur activité réalisée en France",
                       "refuser cette taxation des multinationales"),
    "VTANR5L17V3199": ("doubler le taux de la taxe sur les géants du numérique (3 % à 6 %) et la réserver aux groupes de plus de 2 milliards d'euros de chiffre d'affaires mondial",
                       "refuser ce doublement de la taxe sur les géants du numérique"),
    "VTANR5L17V3149": ("alourdir la contribution exceptionnelle sur les bénéfices des plus grandes entreprises",
                       "refuser cet alourdissement de l'impôt des grandes entreprises"),
    "VTANR5L17V3096": ("indexer le barème de l'impôt sur le revenu sur l'inflation, ce qui évite que la seule hausse des prix rende des ménages imposables",
                       "refuser cette indexation (le « gel » du barème)"),
    "VTANR5L17V3848": ("supprimer l'avantage fiscal sur le carburant des jets privés et affecter la recette aux transports d'Île-de-France",
                       "conserver cet avantage fiscal sur le carburant des jets privés"),
    # ── Défense : ajouts ──
    "VTANR5L14V510": ("autoriser la prolongation de l'intervention militaire au Mali", "s'y opposer"),
    "VTANR5L14V998": ("autoriser l'engagement des forces françaises en Irak contre Daech", "s'y opposer"),
    "VTANR5L14V1195": ("autoriser les frappes françaises en Syrie contre Daech", "s'y opposer"),
    "VTANR5L16V650": ("exiger la fin de l'agression azerbaïdjanaise et soutenir l'Arménie", "s'y opposer"),
    "VTANR5L16V1483": ("demander le classement de Wagner comme organisation terroriste", "s'y opposer"),
    "VTANR5L17V683": ("condamner la répression du régime iranien et soutenir le mouvement pour la liberté", "s'y opposer"),
    "VTANR5L16V1456": ("adopter la résolution (solution à deux États, condamnation de la politique israélienne)", "rejeter la résolution"),
    "PE-HTV-179048": ("adopter la résolution (lutte contre la famine à Gaza, libération des otages, solution à deux États)", "rejeter la résolution"),
    "PE-HTV-172867": ("soutenir le renforcement de la défense européenne commune", "s'y opposer"),
    "PE-HTV-174053": ("approuver l'orientation de la politique de défense commune de l'UE", "s'y opposer"),
    "PE-HTV-181587": ("financer une industrie de défense européenne commune", "s'y opposer"),

    # ── Incendies / élevage / fiscalité énergie (sous-sections, 27/07/2026) ──
    "VTANR5L16V133": ("créer un programme de recrutement de pompiers professionnels supplémentaires", "rejeter cet amendement"),
    "VTANR5L16V1509": ("adopter un plan d'adaptation de la forêt cohérent avec la SNBC", "rejeter cet amendement"),
    "VTANR5L16V1545": ("agir contre la perte de chemins forestiers nécessaires aux secours", "rejeter cet amendement"),
    "VTANR5L16V1556": ("imposer des pare-feux d'arbres feuillus entre parcelles de résineux", "rejeter cet amendement"),
    "VTANR5L17V4114": ("relever la taxe sur les conventions d'assurance pour financer les SDIS", "rejeter cet amendement"),
    "VTANR5L16V3750": ("instaurer un moratoire sur les nouveaux élevages en cage", "rejeter ce moratoire"),
    "VTANR5L17V3217": ("relever l'impôt sur les sociétés pour les élevages classés à risque", "rejeter cet amendement"),
    "VTANR5L16V1370": ("imposer une option végétarienne quotidienne en restauration collective", "rejeter cette obligation"),
    "VTANR5L16V1377": ("rétablir l'interdiction progressive des additifs nitrés", "rejeter cette interdiction"),
    "VTANR5L16V3782": ("appeler au développement du pâturage et du plein air", "rejeter cet amendement"),
    "VTANR5L16V517": ("créer une taxe carbone sur les vols en jet privé", "rejeter cette taxe"),
    "VTANR5L17V110": ("supprimer la niche fiscale sur le kérosène aérien", "maintenir cette niche fiscale"),
    "VTANR5L17V3958": ("mettre fin au tarif réduit de taxation du charbon", "maintenir ce tarif réduit"),
    "VTANR5L17V4046": ("abaisser la TVA sur les transports en commun à 5,5 %", "rejeter cette baisse de TVA"),
    "VTANR5L17V144": ("abaisser à 5,5 % la TVA sur le gaz, l'électricité, le fioul et les carburants", "rejeter cette baisse de TVA"),
    "VTANR5L17V3830": ("supprimer le malus écologique sur les véhicules", "maintenir ce malus"),
    "VTANR5L16V1989": ("réserver une part de l'enveloppe d'artificialisation à la création de pistes cyclables",
                       "rejeter cet amendement"),
    "VTANR5L16V491": ("financer cette aide à la rénovation par un prélèvement sur les crédits ferroviaires",
                      "rejeter ce redéploiement de crédits"),
    "VTANR5L17V7303": ("abaisser la teneur en cadmium autorisée dans les engrais phosphatés", "maintenir le seuil actuel de 90 mg/kg"),
    "VTANR5L17V852": ("interdire progressivement les PFAS dans les produits concernés", "s'opposer à cette interdiction"),
    "VTANR5L17V4515": ("rendre le Nutri-Score obligatoire sur les emballages alimentaires", "ne pas le rendre obligatoire"),

    # ── Fiscalité du capital et des hauts patrimoines (27/07/2026) ──
    "VTANR5L17V10": ("créer de nouvelles tranches d'impôt sur le revenu pour augmenter le reste à vivre des ménages modestes", "rejeter cette réforme du barème"),
    "VTANR5L16V325": ("rétablir l'impôt de solidarité sur la fortune", "rejeter ce rétablissement"),
    "VTANR5L17V3335": ("supprimer le prélèvement forfaitaire unique sur les revenus du capital", "maintenir le PFU"),
    "VTANR5L17V3336": ("relever le taux du prélèvement forfaitaire unique", "maintenir le taux actuel"),
    "VTANR5L17V3290": ("restreindre l'assiette et le champ de la taxe sur les holdings patrimoniales, en alourdissant son taux",
                       "maintenir une assiette et un champ plus larges pour cette taxe"),

    # ── Droits des femmes (27/07/2026) ──
    "VTANR5L17V3061": ("inscrire l'absence de consentement dans la définition pénale du viol", "rejeter cette nouvelle définition"),
    "VTANR5L17V3620": ("étudier l'extension de la prise en charge des protections périodiques au-delà de 26 ans", "rejeter cette demande de rapport"),
    "VTANR5L17V4613": ("rétablir la prise en charge des protections périodiques réutilisables", "rejeter ce rétablissement"),
    "VTANR5L17V3656": ("interdire les dépassements d'honoraires sur les consultations de santé sexuelle", "rejeter cette interdiction"),
    "VTANR5L16V2137": ("renforcer l'accès des femmes aux responsabilités dans la fonction publique", "rejeter le texte"),
    "VTANR5L17V3077": ("créer une option d'imposition séparée pour les couples mariés ou pacsés", "rejeter cette option"),
    "VTANR5L16V2814": ("étendre la prise en charge à la contraception masculine", "rejeter cette extension"),
    "VTANR5L16V2815": ("étendre la prise en charge aux préservatifs internes", "rejeter cette extension"),
    "VTANR5L16V2259": ("inscrire la formation des magistrats aux violences intrafamiliales", "rejeter cet amendement"),
    "VTANR5L16V1014": ("augmenter les pénalités pour non-respect de l'égalité salariale", "rejeter cette hausse"),
}


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # Colonnes sens_pour / sens_contre ajoutées après coup : les créer si la base
    # a été initialisée avant leur ajout au schéma (ALTER TABLE idempotent maison).
    cols = {r[1] for r in cur.execute("PRAGMA table_info(votes_cles)")}
    if "sens_pour" not in cols:
        cur.execute("ALTER TABLE votes_cles ADD COLUMN sens_pour TEXT")
    if "sens_contre" not in cols:
        cur.execute("ALTER TABLE votes_cles ADD COLUMN sens_contre TEXT")
    if "axe_budget" not in cols:
        cur.execute("ALTER TABLE votes_cles ADD COLUMN axe_budget TEXT")
    if "sens_axe" not in cols:
        cur.execute("ALTER TABLE votes_cles ADD COLUMN sens_axe TEXT")

    # Idempotent : thématiques créées à la demande (libellé unique), votes clés
    # ajoutés seulement s'ils n'existent pas déjà (permet d'ajouter le PE après coup).
    ids_theme = {}
    for ordre, (slug, libelle) in enumerate(THEMES, start=1):
        cur.execute("INSERT OR IGNORE INTO thematiques (libelle, ordre) VALUES (?,?)", (libelle, ordre))
        ids_theme[slug] = cur.execute(
            "SELECT id FROM thematiques WHERE libelle=?", (libelle,)).fetchone()[0]

    # Ordre d'affichage par thème : on repart du maximum déjà présent.
    ordre_par_theme = {}
    for tid, mx in cur.execute("SELECT thematique_id, MAX(ordre) FROM votes_cles GROUP BY thematique_id"):
        ordre_par_theme[tid] = mx or 0

    ajout = deplaces = 0
    for uid, theme, titre, resume, contexte in VOTES:
        scrutin = cur.execute(
            "SELECT id, legislature, numero, chambre FROM scrutins WHERE uid_officiel = ?",
            (uid,)).fetchone()
        if scrutin is None:
            sys.exit(f"Scrutin {uid} introuvable en base : la sélection doit pointer des scrutins importés.")
        sid, leg, numero, chambre = scrutin
        tid = ids_theme[theme]
        if chambre == "congres":
            url = URL_CONGRES_IVG
        elif chambre == "pe":
            url = f"https://howtheyvote.eu/votes/{numero}"
        else:
            url = f"https://www.assemblee-nationale.fr/dyn/{leg}/scrutins/{numero}"
        deja = cur.execute("SELECT id, thematique_id FROM votes_cles WHERE scrutin_id=?", (sid,)).fetchone()
        if deja:
            # Déjà en base : la liste VOTES fait foi ; on synchronise thème,
            # titre, résumé, source et contexte (permet de déplacer un vote ou
            # de corriger un libellé). Idempotent.
            if deja[1] != tid:
                deplaces += 1
            cur.execute("UPDATE votes_cles SET thematique_id=?, titre=?, resume=?, source_resume=?, "
                        "contexte=? WHERE scrutin_id=?", (tid, titre, resume, url, contexte, sid))
            continue
        ordre_par_theme[tid] = ordre_par_theme.get(tid, 0) + 1
        sid_senat = None
        if uid in EQUIV_SENAT:
            r = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (EQUIV_SENAT[uid],)).fetchone()
            if r is None:
                sys.exit(f"Équivalent Sénat {EQUIV_SENAT[uid]} introuvable : collecter le Sénat d'abord.")
            sid_senat = r[0]
        cur.execute(
            "INSERT INTO votes_cles (scrutin_id, thematique_id, titre, resume, source_resume, contexte, "
            "ordre, scrutin_senat_id) VALUES (?,?,?,?,?,?,?,?)",
            (sid, tid, titre, resume, url, contexte, ordre_par_theme[tid], sid_senat))
        ajout += 1

    # Sens concret du vote (pour / contre) : appliqué à TOUS les votes de SENS,
    # y compris ceux déjà en base : idempotent, réexécutable pour corriger un libellé.
    maj_sens = 0
    for uid, (spour, scontre) in SENS.items():
        r = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
        if r is None:
            continue
        maj_sens += cur.execute(
            "UPDATE votes_cles SET sens_pour=?, sens_contre=? WHERE scrutin_id=?",
            (spour, scontre, r[0])).rowcount

    # Rattachement aux axes du thème Budget (idempotent, réexécutable).
    maj_axe = 0
    for uid, (axe, sens_axe) in AXES.items():
        r = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
        if r is None:
            continue
        maj_axe += cur.execute(
            "UPDATE votes_cles SET axe_budget=?, sens_axe=? WHERE scrutin_id=?",
            (axe, sens_axe, r[0])).rowcount

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM votes_cles").fetchone()[0]
    sans_sens = cur.execute("SELECT COUNT(*) FROM votes_cles WHERE sens_pour IS NULL").fetchone()[0]
    couv = cur.execute("SELECT COUNT(*) FROM couverture").fetchone()[0]
    print(f"Semé : {len(THEMES)} thématiques, +{ajout} vote(s) clé(s) ajouté(s) ({n} au total), "
          f"{deplaces} déplacé(s) de thème ; sens (pour/contre) sur {maj_sens} vote(s), {sans_sens} sans sens ; "
          f"axe budget sur {maj_axe} vote(s). "
          f"Vue couverture : {couv} états calculés.")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

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
     "Interdit progressivement, d'ici 2040, de rechercher et d'extraire du pétrole et du gaz sur le sol français : plus aucun nouveau permis, et les permis existants ne sont pas prolongés au-delà de cette date. La France produisant très peu d'hydrocarbures, l'effet sur l'approvisionnement est limité : l'enjeu porte surtout sur le signal d'une sortie programmée des énergies fossiles.",
     None),
    ("VTANR5L15V3738", "ecologie-agriculture", "Loi Climat et résilience (2021)",
     "Traduit dans la loi une partie des propositions de la Convention citoyenne pour le climat (150 citoyens tirés au sort). Principales mesures : rénovation des logements mal isolés, avec interdiction progressive de louer les plus énergivores ; encadrement de la publicité pour les produits polluants ; objectif de « zéro artificialisation nette » pour freiner la bétonisation des terres ; zones à faibles émissions dans les grandes villes. L'enjeu : réduire les émissions de la France en agissant sur le logement, la consommation et l'aménagement du territoire.",
     "Première lecture, scrutin solennel du 4 mai 2021."),
    ("VTANR5L16V823", "ecologie-agriculture", "Accélération des énergies renouvelables (2023)",
     "Facilite et accélère l'installation d'énergies renouvelables (éoliennes, panneaux solaires) : les communes délimitent des « zones d'accélération » prioritaires et les procédures d'autorisation sont raccourcies. L'enjeu : produire plus vite une électricité bas-carbone et moins dépendante des importations, la question débattue étant l'équilibre entre rapidité des projets et pouvoir de décision des habitants sur leur implantation.",
     None),
    ("VTANR5L17V2957", "ecologie-agriculture", "Loi agricole dite « loi Duplomb » (2025)",
     "Réautorise, par dérogation, l'acétamipride — un insecticide de la famille des néonicotinoïdes, réputés dangereux pour les abeilles, interdit en France depuis 2018 mais encore autorisé ailleurs en Europe —, réclamé par une partie des agriculteurs (betteraves, noisettes) faute d'alternative jugée efficace. Le texte facilite aussi la création de réserves d'eau pour l'irrigation et l'agrandissement de certains élevages. L'enjeu : la compétitivité de ces filières face à la concurrence européenne, mise en balance avec la protection des pollinisateurs, de l'eau et de la santé.",
     "Texte soutenu par la FNSEA et la Coordination rurale, combattu par la Confédération paysanne, les apiculteurs et des associations de santé et d'environnement. Une pétition record (plus de deux millions de signatures) a demandé son abrogation, et le Conseil constitutionnel a censuré la réintroduction de l'acétamipride en août 2025 — après ce scrutin."),

    # ── Pouvoir d'achat et fiscalité ─────────────────────────────────────────
    ("VTANR5L16V186", "pouvoir-achat-fiscalite", "Mesures d'urgence pouvoir d'achat (2022)",
     "Ensemble de mesures adoptées face à la forte inflation de 2022 : revalorisation anticipée des retraites et de plusieurs prestations sociales, plafonnement temporaire de la hausse des loyers, et primes exonérées de cotisations que les employeurs peuvent verser à leurs salariés. L'enjeu : soutenir rapidement le pouvoir d'achat des ménages, le débat portant sur l'ampleur de ces mesures et leur coût pour les finances publiques.",
     "Vote sur le texte issu de la commission mixte paritaire."),
    ("VTANR5L16V1240", "pouvoir-achat-fiscalite", "Réforme des retraites : motion de censure (2023)",
     "Motion de censure déposée par plusieurs groupes après que le Gouvernement a engagé sa responsabilité (article 49.3) pour faire adopter, sans vote des députés, la réforme repoussant l'âge légal de départ à la retraite de 62 à 64 ans. Dans ce cas, la motion de censure est le seul moyen de rejeter le texte : si elle est adoptée, le Gouvernement tombe et la loi est abandonnée. L'enjeu affiché était l'équilibre financier des retraites, face à l'allongement de la durée de travail.",
     "La réforme n'a pas fait l'objet d'un vote direct à l'Assemblée. Voter pour la motion revenait à s'opposer à l'adoption du texte ; son rejet, à neuf voix près, a entraîné l'adoption définitive de la réforme. La position affichée est le vote sur la motion de censure."),
    ("VTANR5L17V881", "pouvoir-achat-fiscalite", "Impôt plancher sur les très hauts patrimoines (2025)",
     "Crée un impôt minimum : les foyers dont le patrimoine dépasse 100 millions d'euros devraient payer chaque année au moins 2 % de ce patrimoine en impôt (proposition dite « taxe Zucman », du nom de l'économiste). L'idée de départ est que certaines très grandes fortunes paient aujourd'hui, en proportion, moins d'impôt que le reste de la population. L'enjeu : de nouvelles recettes et davantage de progressivité de l'impôt, mis en regard du risque d'exil fiscal et de la difficulté à taxer un patrimoine qui n'a pas été vendu.",
     "Proposition d'origine parlementaire, adoptée en première lecture à l'Assemblée ; elle n'était pas devenue loi à la date de mise à jour du site."),
    ("VTANR5L17V6319", "pouvoir-achat-fiscalite", "Lutte contre les fraudes sociales et fiscales (2026)",
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
     "Instaure une présomption de légitime défense pour les policiers et gendarmes qui font usage de leur arme en service : la justice partirait du principe qu'ils étaient en état de légitime défense, à charge pour l'accusation de prouver le contraire — l'inverse de la règle actuelle. L'enjeu : mieux protéger des agents qui doivent parfois décider en une fraction de seconde, mis en balance avec le contrôle exercé sur l'usage d'une arme pouvant donner la mort.",
     "Adoptée en première lecture le 7 juillet 2026 ; la navette parlementaire se poursuit au Sénat. Ses opposants qualifient le texte de « permis de tuer », ses partisans de protection nécessaire des agents — qualifications rapportées, que le site ne reprend pas à son compte."),

    # ── Immigration ──────────────────────────────────────────────────────────
    ("VTANR5L15V578", "immigration", "Loi asile et immigration (2018)",
     "Raccourcit les délais pour déposer une demande d'asile et pour contester un refus, double la durée maximale de rétention administrative (de 45 à 90 jours) et facilite l'éloignement des personnes déboutées. La rétention administrative est l'enfermement, hors prison, d'un étranger en attente d'expulsion. L'enjeu : accélérer le traitement des demandes et les expulsions, mis en regard des droits et des garanties des demandeurs d'asile.",
     None),
    ("VTANR5L16V3213", "immigration", "Loi immigration (2023)",
     "Durcit plusieurs règles applicables aux étrangers : conditions du regroupement familial, accès à certaines prestations sociales, et expulsions facilitées ; en contrepartie, elle ouvre une régularisation encadrée pour les travailleurs sans papiers employés dans des métiers qui manquent de main-d'œuvre. L'enjeu : l'équilibre entre maîtrise de l'immigration et droits des personnes étrangères, un sujet de fortes tensions politiques.",
     "Vote sur le texte issu de la commission mixte paritaire ; le Conseil constitutionnel a ensuite censuré une large partie de ses articles (janvier 2024)."),
    ("VTANR5L17V1308", "immigration", "Conditions d'accès à la nationalité (2025)",
     "Durcit les conditions requises pour obtenir la nationalité française. L'enjeu : réserver la nationalité à une intégration jugée plus aboutie, une question qui touche à la définition de l'appartenance à la communauté nationale et aux droits qui y sont attachés.",
     None),
    ("VTANR5L17V7405", "immigration", "Sécurité et rétention administrative (2026)",
     "Allonge la durée et élargit les cas dans lesquels un étranger visé par une mesure d'éloignement peut être placé en rétention administrative — l'enfermement, hors prison, en attendant l'expulsion. L'enjeu : donner plus de temps à l'administration pour organiser les expulsions, mis en balance avec la privation de liberté que représente la rétention.",
     "Texte transversal sécurité/immigration, rattaché ici à son objet principal (règle « un vote = un thème »)."),

    # ── Questions de société ─────────────────────────────────────────────────
    ("VTANR5L15V2146", "societe", "Bioéthique : PMA pour toutes (2019)",
     "Ouvre la procréation médicalement assistée (PMA) — les techniques médicales pour concevoir un enfant, comme l'insémination ou la fécondation in vitro — aux couples de femmes et aux femmes seules, alors qu'elle était réservée aux couples femme-homme, avec prise en charge par la Sécurité sociale. Le texte permet aussi aux enfants nés d'un don d'accéder, à leur majorité, à l'identité du donneur. L'enjeu : l'égalité d'accès à la parentalité, face à des débats éthiques sur la filiation et l'accès aux origines.",
     "Première lecture ; le texte a été définitivement adopté en 2021."),
    ("VTCGR5L16V1", "societe", "IVG dans la Constitution (Congrès, 2024)",
     "Inscrit dans la Constitution la « liberté garantie » de la femme de recourir à l'avortement (IVG). L'avortement était déjà légal depuis la loi Veil de 1975 ; l'inscrire dans la Constitution le protège d'un retour en arrière, car modifier la Constitution suppose une très large majorité. L'enjeu : rendre ce droit beaucoup plus difficile à remettre en cause à l'avenir — la France est le premier pays au monde à l'avoir fait.",
     "Adopté par le Parlement réuni en Congrès à Versailles par 780 voix pour et 72 contre : seul vote de la base où députés et sénateurs sont directement comparables."),
    ("VTANR5L17V5728", "societe", "Accompagnement et soins palliatifs (2026)",
     "Organise le développement, partout sur le territoire, des soins palliatifs — les soins qui soulagent la douleur et accompagnent les personnes en fin de vie sans chercher à guérir — et garantit le droit d'y accéder. L'enjeu : réduire les fortes inégalités d'accès à ces soins selon les régions et les établissements.",
     "Deuxième lecture ; texte examiné conjointement avec la proposition de loi sur l'aide à mourir."),
    ("VTANR5L17V8280", "societe", "Droit à l'aide à mourir (2026)",
     "Crée un « droit à l'aide à mourir » : la possibilité, très encadrée, pour une personne majeure atteinte d'une maladie grave et incurable engageant son pronostic vital, de recevoir ou de s'administrer elle-même une substance létale. Chaque demande doit être libre, répétée et validée par une équipe médicale. L'enjeu : pouvoir choisir sa fin de vie face à des souffrances jugées insupportables, mis en regard des inquiétudes éthiques sur la protection des personnes les plus vulnérables.",
     "Lecture définitive du 15 juillet 2026, au terme de quatre lectures à l'Assemblée."),

    # ── Europe et international ──────────────────────────────────────────────
    ("VTANR5L15V2059", "europe-international", "Ratification du CETA (2019)",
     "Autorise la France à ratifier le CETA, l'accord de libre-échange entre l'Union européenne et le Canada, qui supprime la quasi-totalité des droits de douane entre les deux zones et facilite donc le commerce dans les deux sens. L'enjeu : de nouveaux débouchés pour les exportateurs européens, mis en balance avec les craintes des éleveurs et d'associations sur la concurrence de produits agricoles soumis à d'autres normes et sur l'impact climatique des échanges transatlantiques.",
     "Tous les candidats suivis alors en poste ont voté contre, pour des motifs différents selon les groupes : impacts sur l'élevage, normes sanitaires et climat à gauche, souveraineté au RN et à DLF. Le Sénat a ensuite rejeté le texte (2024) ; l'accord reste appliqué à titre provisoire."),
    ("VTANR5L16V652", "europe-international", "Soutien à l'Ukraine (2022)",
     "Résolution par laquelle l'Assemblée nationale affirme son soutien à l'Ukraine et condamne l'invasion menée par la Russie depuis février 2022. Une résolution exprime une position politique solennelle, mais sans portée juridique contraignante. L'enjeu : marquer le soutien de la France à un pays agressé et à la sécurité de l'Europe.",
     None),
    ("VTANR5L17V456", "europe-international", "Accord UE-Mercosur : déclaration du Gouvernement (2024)",
     "Le Mercosur est un accord de libre-échange en négociation entre l'Union européenne et des pays d'Amérique du Sud (Brésil, Argentine, Uruguay, Paraguay) qui augmenterait les échanges, notamment les importations agricoles (bœuf, volaille, sucre). Sur ce vote, le Gouvernement demandait aux députés d'approuver l'opposition de la France à l'accord en l'état : voter « pour » revenait donc à soutenir ce refus. L'enjeu : les agriculteurs européens redoutent une concurrence de produits soumis à des règles sanitaires et environnementales moins strictes, quand les partisans de l'accord mettent en avant de nouveaux marchés.",
     "Vote au titre de l'article 50-1 de la Constitution : il exprime la position formelle de l'Assemblée, sans effet législatif direct."),
    ("VTANR5L17V988", "europe-international", "Renforcement du soutien à l'Ukraine (2025)",
     "Résolution appelant à renforcer le soutien à l'Ukraine, notamment en utilisant les avoirs russes gelés en Europe pour la financer, et à faciliter le processus d'adhésion de l'Ukraine à l'Union européenne. Comme toute résolution, elle exprime une position sans créer d'obligation juridique. L'enjeu : l'ampleur et les moyens du soutien européen à l'Ukraine dans la durée.",
     None),

    # ── Extension 14e législature (2012-2017), validée le 24/07/2026 ────────
    ("VTANR5L14V511", "societe", "Mariage pour tous (2013)",
     "Ouvre le mariage civil et l'adoption aux couples de personnes de même sexe, jusque-là réservés aux couples femme-homme. L'enjeu : l'égalité des droits entre couples hétérosexuels et homosexuels, un texte qui a donné lieu à d'importantes mobilisations, pour comme contre.",
     "Deuxième lecture du 23 avril 2013 — dernier vote d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V1070", "societe", "Fin de vie : loi Claeys-Leonetti (2015)",
     "Crée un droit à la « sédation profonde et continue » jusqu'au décès pour les malades en phase terminale dont les souffrances ne peuvent être soulagées, et rend contraignantes les « directives anticipées » (les volontés écrites à l'avance sur sa propre fin de vie, que les médecins doivent alors respecter). Le texte n'autorise ni l'euthanasie ni le suicide assisté. L'enjeu : mieux accompagner la fin de vie sans légaliser l'aide active à mourir.",
     "Première lecture ; le texte a été définitivement adopté début 2016. C'est le cadre que la loi sur l'aide à mourir de 2026 est venue compléter."),
    ("VTANR5L14V726", "pouvoir-achat-fiscalite", "Réforme des retraites Touraine (2013)",
     "Allonge progressivement la durée de cotisation nécessaire pour une retraite à taux plein, jusqu'à 43 ans (172 trimestres) pour les générations nées à partir de 1973, et crée un compte permettant de partir plus tôt après un métier pénible. L'enjeu : équilibrer le financement des retraites en faisant cotiser plus longtemps, sans toucher à l'âge légal (alors 62 ans).",
     "Nouvelle lecture du 26 novembre 2013 — dernier scrutin public d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V1270", "pouvoir-achat-fiscalite", "Loi travail (El Khomri) : motion de censure (2016)",
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
    ("VTANR5L14V1237", "immigration", "Déchéance de nationalité — « protection de la Nation » (2016)",
     "Projet de révision de la Constitution qui voulait y inscrire l'état d'urgence et permettre de retirer la nationalité française à des personnes condamnées pour terrorisme, y compris à des Français de naissance disposant d'une autre nationalité. L'enjeu portait sur la réponse à apporter au terrorisme après les attentats de 2015 et sur l'égalité entre Français selon qu'ils possèdent une ou deux nationalités.",
     "Première lecture. La révision a été abandonnée en mars 2016 faute d'accord entre l'Assemblée et le Sénat : le Congrès n'a jamais été réuni."),
    ("VTANR5L14V1120", "ecologie-agriculture", "Transition énergétique (2015)",
     "Fixe les grands objectifs énergétiques de la France : ramener la part du nucléaire à 50 % de l'électricité (contre environ 75 %), diviser par deux la consommation d'énergie d'ici 2050, développer les renouvelables et interdire les sacs plastique à usage unique. L'enjeu : engager la transition vers une énergie moins carbonée et moins gaspilleuse, en fixant des caps de long terme dont dépendront les politiques suivantes.",
     "Nouvelle lecture du 26 mai 2015 — dernier scrutin public d'ensemble à l'Assemblée sur ce texte."),
    ("VTANR5L14V30", "europe-international", "Ratification du traité budgétaire européen (TSCG, 2012)",
     "Autorise la ratification du traité budgétaire européen (TSCG), négocié après la crise de la zone euro, qui engage les États à limiter strictement leurs déficits — la « règle d'or » des finances publiques. L'enjeu : la discipline budgétaire commune en Europe, mise en balance avec la marge de manœuvre des États pour mener leur propre politique économique.",
     None),
    ("VTANR5L14V594", "institutions", "Transparence de la vie publique (2013)",
     "Crée la Haute Autorité pour la transparence de la vie publique (HATVP) et oblige les membres du Gouvernement et de nombreux élus à déclarer publiquement leur patrimoine et leurs intérêts (activités, revenus, liens pouvant créer des conflits d'intérêts). L'enjeu : prévenir la corruption et les conflits d'intérêts, et renforcer la confiance envers les responsables politiques.",
     "Adoptée après l'affaire Cahuzac (lecture définitive). Ce sont ces déclarations HATVP que le présent site utilise pour la partie « parcours » des candidats."),

    # ── Parlement européen (uid PE-HTV-<vote_id>, importés par ingestion/pe) ────
    # Pour la plupart des candidats, aucun vote personnel n'est disponible (mandat
    # européen achevé avant 2019) : c'est la position de la DÉLÉGATION de leur parti
    # qui s'affiche, clairement étiquetée « n'y siégeait pas ». Sélection symétrique.
    ("PE-HTV-147342", "pouvoir-achat-fiscalite", "Salaire minimum européen (2022)",
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
    ("PE-HTV-168573", "societe", "Lutte contre les violences faites aux femmes (2024)",
     "Première directive européenne dédiée à la lutte contre les violences faites aux femmes et les violences domestiques : elle harmonise certaines infractions et sanctions (notamment les cyberviolences) et renforce la protection, l'accompagnement et l'accès à la justice des victimes dans toute l'Union. L'enjeu : un socle commun de protection, le débat ayant porté sur le périmètre des infractions harmonisées.",
     "Directive sur la lutte contre la violence à l'égard des femmes et la violence domestique, vote d'avril 2024."),
    ("PE-HTV-167531", "immigration", "Pacte européen sur l'asile et la migration (2024)",
     "Pièce centrale du Pacte sur la migration et l'asile : le règlement sur la gestion de l'asile et de la migration réforme la répartition des demandeurs entre États membres et instaure un mécanisme dit de solidarité (accueil de demandeurs ou contribution financière). L'enjeu : répartir la charge de l'asile entre les pays de l'Union — un compromis critiqué à la fois comme trop contraignant et comme insuffisamment protecteur.",
     "Volet « gestion de l'asile et de la migration » du Pacte, vote d'avril 2024."),
    ("PE-HTV-164536", "europe-international", "Facilité pour l'Ukraine — 50 milliards (2024)",
     "Crée la « facilité pour l'Ukraine » : un soutien financier de l'Union doté de 50 milliards d'euros sur 2024-2027 (prêts et subventions) pour le fonctionnement de l'État ukrainien, sa reconstruction et ses réformes. L'enjeu : assurer à l'Ukraine en guerre un financement européen pluriannuel et prévisible.",
     "Établissement de la facilité pour l'Ukraine, vote de février 2024."),
    ("PE-HTV-169362", "europe-international", "Soutien continu à l'Ukraine (2024)",
     "Résolution appelant l'Union et les États membres à maintenir et renforcer leur soutien financier et militaire à l'Ukraine face à l'invasion russe. Une résolution exprime une position politique, sans portée juridiquement contraignante. L'enjeu : la constance et l'ampleur du soutien européen dans la durée.",
     "Résolution sur la nécessité d'un soutien continu de l'UE à l'Ukraine, vote de juillet 2024 (10e législature)."),
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


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

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

    ajout = 0
    for uid, theme, titre, resume, contexte in VOTES:
        scrutin = cur.execute(
            "SELECT id, legislature, numero, chambre FROM scrutins WHERE uid_officiel = ?",
            (uid,)).fetchone()
        if scrutin is None:
            sys.exit(f"Scrutin {uid} introuvable en base — la sélection doit pointer des scrutins importés.")
        sid, leg, numero, chambre = scrutin
        if cur.execute("SELECT 1 FROM votes_cles WHERE scrutin_id=?", (sid,)).fetchone():
            continue  # déjà en base
        if chambre == "congres":
            url = URL_CONGRES_IVG
        elif chambre == "pe":
            url = f"https://howtheyvote.eu/votes/{numero}"
        else:
            url = f"https://www.assemblee-nationale.fr/dyn/{leg}/scrutins/{numero}"
        tid = ids_theme[theme]
        ordre_par_theme[tid] = ordre_par_theme.get(tid, 0) + 1
        sid_senat = None
        if uid in EQUIV_SENAT:
            r = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (EQUIV_SENAT[uid],)).fetchone()
            if r is None:
                sys.exit(f"Équivalent Sénat {EQUIV_SENAT[uid]} introuvable — collecter le Sénat d'abord.")
            sid_senat = r[0]
        cur.execute(
            "INSERT INTO votes_cles (scrutin_id, thematique_id, titre, resume, source_resume, contexte, "
            "ordre, scrutin_senat_id) VALUES (?,?,?,?,?,?,?,?)",
            (sid, tid, titre, resume, url, contexte, ordre_par_theme[tid], sid_senat))
        ajout += 1

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM votes_cles").fetchone()[0]
    couv = cur.execute("SELECT COUNT(*) FROM couverture").fetchone()[0]
    print(f"Semé : {len(THEMES)} thématiques, +{ajout} vote(s) clé(s) ajouté(s) ({n} au total). "
          f"Vue couverture : {couv} états calculés.")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

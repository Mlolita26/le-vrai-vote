"""Justifications éditoriales PAR GROUPE parlementaire : pourquoi chaque parti
a voté comme il l'a fait sur un scrutin clé. Chacune est ATTRIBUÉE et SOURCÉE
(règle absolue : un fait sans source ne s'affiche pas) et rapporte la position
déclarée : elle décrit, elle ne juge pas (CLAUDE.md §4).

Complète les décomptes bruts de `positions_groupes` (miroir des dumps, jamais
édités) par le « pourquoi » éditorial, parti par parti. Sert surtout les lois
où les familles politiques divergent nettement (ex. LFI vs RN).

Garde-fou : une justification n'est écrite que si le groupe a réellement un
décompte en base pour ce scrutin (sinon on refuse : pas de parti fantôme).

Usage : python ingestion/seed_justifications_groupes.py [chemin_base]
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"

# clé -> (url, détail). URLs vérifiées le 25/07/2026.
SOURCES = {
    "lcp_nucleaire": ("https://lcp.fr/actualites/acceleration-du-nucleaire-le-projet-de-loi-definitivement-adopte-par-le-parlement-188296",
                      "LCP, mai 2023 : adoption définitive de la loi d'accélération du nucléaire, positions des groupes"),
    "lcp_indverte": ("https://lcp.fr/actualites/assemblee-nationale-adoption-du-projet-de-loi-industrie-verte-fin-de-la-session",
                     "LCP, juillet 2023 : adoption du projet de loi industrie verte, explications et critiques des groupes"),
    "lcp_mineurs": ("https://lcp.fr/actualites/delinquance-des-mineurs-que-contient-la-proposition-de-loi-de-gabriel-attal-que-le",
                    "LCP, 2025 : contenu et débats de la proposition de loi Attal sur la justice des mineurs"),
    "lcp_bienvieillir": ("https://lcp.fr/actualites/bien-vieillir-assemblee-nationale-adopte-texte-premiere-lecture-241649",
                         "LCP, 23/11/2023 : adoption en première lecture de la loi « bien vieillir », positions des groupes"),
    "lcp_corse": ("https://lcp.fr/actualites/l-assemblee-nationale-vote-en-faveur-de-l-autonomie-de-la-corse-437977",
                  "LCP, juin 2026 : vote de l'Assemblée sur l'autonomie de la Corse, positions du RN et de LFI"),
    "lcp_caledonie": ("https://lcp.fr/actualites/nouvelle-caledonie-le-projet-de-loi-constitutionnelle-sur-le-degel-du-corps-electoral",
                      "LCP, mai 2024 : adoption du dégel du corps électoral calédonien, débats des groupes"),
    "lcp_municipales": ("https://lcp.fr/actualites/municipales-le-parlement-etend-le-scrutin-de-liste-paritaire-aux-petites-communes-a",
                        "LCP, avril 2025 : extension du scrutin de liste paritaire aux petites communes, débat RN / gauche"),
    # Sources des justifications de groupe au Parlement européen (+ loi immigration 2023).
    "aubry_seqe": ("https://manonaubry.eu/mes-combats/vote/revision-du-systeme-dechange-de-quotas-demission-de-gaz-effet-de-serre-dans-lunion",
                   "manonaubry.eu : fiche de vote de Manon Aubry (LFI/The Left) sur la révision du marché carbone"),
    "lfi_electricite": ("https://lafranceinsoumise.fr/2024/04/11/le-parlement-europeen-vote-la-catastrophique-reforme-du-marche-de-lelectricite-seul-le-groupe-lfi-sy-oppose/",
                        "lafranceinsoumise.fr, 11/04/2024 : opposition de LFI à la réforme du marché de l'électricité"),
    "rn_pacte_migration": ("https://rassemblementnational.fr/communiques/communique-de-presse-de-jordan-bardella",
                           "rassemblementnational.fr : communiqué de Jordan Bardella (RN) contre le « pacte de submersion » (avril 2024)"),
    "rn_ecologie_punitive": ("https://rassemblementnational.fr/communiques/mondial-de-lauto-2024-le-rassemblement-national-se-tient-aux-cotes-des-automobilistes-et-constructeurs-automobiles-francais-victimes-expiatoires-de-lecologie-punitive",
                             "rassemblementnational.fr : communiqué RN (oct. 2024) contre « l'écologie punitive », défense des automobilistes"),
    "hayer_pacte": ("https://www.lopinion.fr/international/avec-le-pacte-asile-et-migration-leurope-a-repondu-presente-par-valerie-hayer",
                    "L'Opinion, tribune de Valérie Hayer (Renaissance) défendant le pacte : « fermeté, humanité et efficacité »"),
    "hayer_greendeal": ("https://www.touteleurope.eu/vie-politique-des-etats-membres/elections-europeennes-2024-le-programme-de-valerie-hayer-et-de-renaissance/",
                        "Touteleurope.eu, programme de Valérie Hayer (Renaissance) : compléter le Pacte vert, cap sur la neutralité 2050"),
    "toussaint_pacte": ("https://www.marietoussaint.eu/actualites/pacte-asile-migration",
                        "marietoussaint.eu, communiqué de Marie Toussaint (Les Écologistes) contre le pacte : « les pires idées de l'extrême droite »"),
    "toussaint_nature": ("https://www.marietoussaint.eu/actualites/vote-loi-restauration-nature",
                         "marietoussaint.eu, 27/02/2024, Marie Toussaint : « une victoire pour le vivant »"),
    "glucksmann_pacte": ("https://www.franceinfo.fr/elections/europeennes/pacte-europeen-sur-la-migration-et-l-asile-je-vais-voter-contre-la-majorite-des-textes-previent-raphael-glucksmann_6455306.html",
                         "franceinfo, Raphaël Glucksmann (PS/Place publique) : voter contre la majorité des textes, pacte « pas assez équilibré »"),
    "bellamy_co2_2035": ("https://www.fxbellamy.fr/2023/02/14/ppe-contre-l-interdiction-de-la-vente-de-vehicules-a-moteurs-thermiques-en-2035/",
                         "fxbellamy.fr, 14/02/2023, F.-X. Bellamy (LR/PPE) : « erreur historique », « désastreuse pour l'industrie », « la grande gagnante est la Chine »"),
    "lfi_immigration_2023": ("https://lafranceinsoumise.fr/2023/12/15/stop-a-la-loi-immigration/",
                             "lafranceinsoumise.fr, 15/12/2023 : LFI appelle à rejeter la loi immigration (« xénophobie et racisme »)"),
    "ps_immigration_2023": ("https://www.parti-socialiste.paris/communique_loi_immigration_2023",
                            "Parti socialiste : communiqué contre la loi immigration 2023 (« populisme de la droite et de l'extrême droite »)"),
    "lcp_pouvoir_achat": ("https://lcp.fr/actualites/pouvoir-d-achat-le-parlement-adopte-definitivement-le-texte-133297",
                          "LCP, 03/08/2022 : adoption définitive du paquet pouvoir d'achat, explications des groupes"),
    "lfi_mercosur": ("https://lafranceinsoumise.fr/2024/11/26/nous-votons-contre-laccord-de-libre-echange-ue-mercosur/",
                     "lafranceinsoumise.fr, 26/11/2024, LFI vote contre la déclaration : refuse l'accord « tout court », pas seulement « en l'état »"),
    # Lot 2 de justifications (recherche du 25/07/2026). URLs vérifiées.
    "te_zucman": ("https://www.touteleurope.eu/economie-et-social/budget-2026-l-assemblee-nationale-rejette-la-taxe-zucman-tous-les-regards-braques-a-gauche/",
                  "Touteleurope.eu, débat sur la taxe Zucman : la gauche y voit un « minimum » fiscal, le bloc central un « mirage » inconstitutionnel"),
    "ddd_legitime": ("https://www.defenseurdesdroits.fr/avis-sur-la-proposition-de-loi-visant-reconnaitre-une-presomption-de-legitime-defense-pour-les-1199",
                     "Défenseur des droits, juin 2026, avis : la présomption de légitime défense risque de porter atteinte au droit à la vie"),
    "tc_legitime": ("https://theconversation.com/presomption-de-legitime-defense-pour-les-policiers-une-proposition-de-loi-qui-pose-probleme-287244",
                    "The Conversation, 2026 : origine (droite/extrême droite, PPL du LR Éric Pauget), soutien du ministre de l'Intérieur"),
    "fi_orban": ("https://www.franceinfo.fr/politique/front-national/defaite-de-viktor-orban-en-hongrie-le-rassemblement-national-perd-son-principal-allie-europeen_7934591.html",
                 "franceinfo : le Rassemblement national, principal allié de Viktor Orbán au Parlement européen"),
    "basta_rn_salaire": ("https://basta.media/parlement-europeen-RN-oppose-droits-des-femmes-salaire-minimum-Bardella-LePen-Elections-UE",
                         "Basta!, 2024 : récapitulatif des votes du RN au Parlement européen, dont l'opposition au salaire minimum européen"),
    # Éducation
    "lfi_antisem_sup": ("https://lafranceinsoumise.fr/2025/07/02/instrumentalisation-de-la-lutte-contre-lantisemitisme-une-loi-adoptee-pour-reprimer-les-mobilisations-etudiantes/",
                        "lafranceinsoumise.fr, 02/07/2025 : LFI dénonce une « instrumentalisation » de la lutte contre l'antisémitisme"),
    # Santé : lot de justifications (recherche 25/07/2026)
    "wiki_sante_touraine": ("https://fr.wikipedia.org/wiki/Loi_de_modernisation_du_syst%C3%A8me_de_sant%C3%A9",
                            "Wikipédia, loi de modernisation du système de santé : opposition de la droite et des syndicats de médecins au tiers payant généralisé"),
    "lcp_deserts": ("https://lcp.fr/actualites/deserts-medicaux-l-assemblee-nationale-vote-en-faveur-d-une-regulation-de-l-installation",
                    "LCP, mai 2025 : l'Assemblée vote la régulation de l'installation des médecins (loi Garot)"),
    "ps_ratios": ("https://www.publicsenat.fr/actualites/sante/hopital-adoption-definitive-de-la-proposition-de-loi-pour-un-nombre-minimal-de-soignants-par-patients",
                  "Public Sénat, janvier 2025 : adoption définitive des ratios de soignants par patient, soutien unanime de la gauche"),
    "lcp_ivg14": ("https://lcp.fr/actualites/allongement-des-delais-de-l-ivg-apres-un-parcours-seme-d-embuches-la-loi-definitivement",
                  "LCP, février 2022 : adoption définitive de l'allongement du délai d'IVG, opposition de Les Républicains"),
    "gouv_ore": ("https://www.enseignementsup-recherche.gouv.fr/fr/la-loi-ore-en-bref-49643",
                 "enseignementsup-recherche.gouv.fr, loi ORE : orientation, « attendus » et fin du tirage au sort à l'université"),
    "lfi_lpr": ("https://lafranceinsoumise.fr/2020/09/23/loi-programmation-recherche-autre-projet-est-possible/",
                "lafranceinsoumise.fr, 23/09/2020 : LFI dénonce une loi recherche qui « institutionnalise la précarité »"),
    "wiki_lpr": ("https://fr.wikipedia.org/wiki/Loi_de_programmation_de_la_recherche_pour_les_ann%C3%A9es_2021_%C3%A0_2030",
                 "Wikipédia, loi de programmation de la recherche 2021-2030 : trajectoire budgétaire et débats"),
    "lfi_ecole_inclusive": ("https://lafranceinsoumise.fr/2025/05/06/projet-de-loi-relatif-a-lecole-inclusive/",
                            "lafranceinsoumise.fr, 06/05/2025, LFI vote contre : amendement gouvernemental sur les « pôles d'appui », précarisation des AESH"),
    "lcp_egalite_chances": ("https://lcp.fr/actualites/egalite-des-chances-les-deputes-se-prononcent-en-faveur-de-la-prolongation-du-dispositif",
                            "LCP, février 2025 : prolongation du « concours Talents » ; opposition du RN (Bryan Masson) à la « discrimination positive »"),
    # Taxe/impôts et Travail
    "europe1_isf": ("https://www.europe1.fr/politique/lassemblee-a-vote-la-transformation-de-lisf-en-impot-sur-la-fortune-immobiliere-3470117",
                    "Europe 1, 2017, transformation de l'ISF en IFI : majorité + LR pour, gauche contre ; 150 M€ d'impôts en moins pour les 100 plus grandes fortunes"),
    "wiki_ordonnances2017": ("https://fr.wikipedia.org/wiki/R%C3%A9forme_du_code_du_travail_en_2017",
                             "Wikipédia, réforme du code du travail par ordonnances (2017) : accords d'entreprise, encadrement des prud'hommes ; votes des groupes"),
    "lcp_france_travail": ("https://lcp.fr/actualites/reforme-du-rsa-france-travail-l-assemblee-nationale-adopte-le-projet-de-loi-pour-le",
                           "LCP, octobre 2023 : adoption du projet de loi « plein emploi » (RSA conditionné) ; RN et Nupes contre, majorité + LR pour"),
    "lcp_partage_valeur": ("https://lcp.fr/actualites/interessement-primes-participation-l-assemblee-a-adopte-le-projet-de-loi-sur-le-partage",
                           "LCP, juin 2023, partage de la valeur : seuls LFI et le communiste de son groupe contre (Marianne Maximi)"),
    # Ajouts (cancer, transports, femmes)
    "carenews_cancer": ("https://www.carenews.com/grandir-sans-cancer/news/medicaments-contre-les-cancers-et-maladies-rares-de-l-enfant-la-loi-votee",
                        "Grandir Sans Cancer / Carenews, mai 2026 : loi médicaments cancers de l'enfant votée par tous les groupes sauf le RN (opposé à la taxe sur les laboratoires)"),
    # ── Ajouts (recherche web sourcée, 26/07/2026) ──
    "lcp_antisquat": ("https://lcp.fr/actualites/loi-anti-squat-les-deputes-adoptent-le-texte-en-deuxieme-lecture-178239",
                      "LCP, avril 2023 : adoption en deuxième lecture de la loi anti-squat, votes et oppositions des groupes"),
    "fi_pacte": ("https://lafranceinsoumise.fr/2019/03/13/privatisations-votre-modele-est-fini/",
                 "lafranceinsoumise.fr, 13/03/2019 : opposition de LFI aux privatisations de la loi PACTE (ADP, FDJ)"),
    "france24_pacte": ("https://www.france24.com/fr/20190411-france-adoption-loi-pacte-privatisation-aeroport-paris-adp",
                       "France 24, 11/04/2019 : adoption définitive de la loi PACTE et privatisation d'Aéroports de Paris"),
    "lcp_jo_vsa": ("https://lcp.fr/actualites/jeux-olympiques-l-assemblee-valide-le-recours-a-la-videosurveillance-algorithmique",
                   "LCP, mars 2023 : l'Assemblée valide la vidéosurveillance algorithmique pour les JO, défense du gouvernement"),
    "lcp_lpm": ("https://lcp.fr/actualites/la-loi-de-programmation-militaire-definitivement-adoptee-par-le-parlement-203997",
                "LCP, juillet 2023 : adoption définitive de la loi de programmation militaire 2024-2030, positions des groupes"),
    "lcp_palestine": ("https://lcp.fr/actualites/en-2014-l-assemblee-se-prononcait-en-faveur-d-une-reconnaissance-de-l-etat-de-palestine",
                      "LCP, vote du 2 décembre 2014 : l'Assemblée en faveur de la reconnaissance de l'État de Palestine (PS pour, UMP contre)"),
    # ── Justifications LFI en écologie/agriculture (ajout 26/07/2026) ──
    "an_egalim_lfi": ("https://www.assemblee-nationale.fr/dyn/15/comptes-rendus/seance/2e-session-extraordinaire-de-2017-2018/deuxieme-seance-du-mercredi-12-septembre-2018",
                      "Compte rendu AN, 12/09/2018 : LFI juge la loi EGalim insuffisante sur le revenu agricole et demande son renvoi en commission"),
    "f24_climat_lfi": ("https://www.france24.com/fr/info-en-continu/20210329-m%C3%A9lenchon-rejette-la-loi-climat-et-ses-manques-dangereux-dans-un-h%C3%A9micycle-agit%C3%A9",
                       "France 24, 29/03/2021 : J.-L. Mélenchon rejette la loi Climat, jugée « inutile » voire « dangereuse » et très en deçà de la Convention citoyenne"),
    "reporterre_enr_lfi": ("https://reporterre.net/Clemence-Guette-Le-projet-de-loi-sur-les-energies-renouvelables-manque-de-logique",
                           "Reporterre : Clémence Guetté (LFI) explique l'opposition du groupe à la loi d'accélération des EnR (marché libéralisé, veto des maires, pôle public)"),
    # ── Loi d'urgence agricole, 2026 (L17) ────────────────────────────────────
    "basta_urgence_agricole": ("https://basta.media/Adoption-loi-urgence-agricole-quels-deputes-vote-pour-reintroduire-des-pesticides-dangereux",
                               "Basta!, juillet 2026 : détail du vote par groupe sur la loi d'urgence agricole, citation d'Aurélie Trouvé (LFI) interpellant Attal, Philippe et Le Pen"),
    "maireinfo_urgence_agricole": ("https://www.maire-info.com/agriculture/l'assemblee-nationale-adopte-le-projet-de-loi-d'urgence-agricole-dans-l'agitation-et-la-division-article-31002",
                                   "Maire-Info, juillet 2026 : citation de Gabriel Attal (« sentiment de gâchis ») et division du groupe EPR"),

    # ── Corrections d'audit (26/07/2026) : sources de remplacement ou complémentaires,
    # vérifiées une à une par WebFetch après qu'une citation s'est révélée absente,
    # mal attribuée ou insuffisamment précise dans la source d'origine. ──
    "rn_nucleaire": ("https://deputes-rn.fr/article/loi-energie-climat-la-victoire-politique-du-rassemblement-national-montre-que-la-prosperite-de-la-france-et-linteret",
                     "deputes-rn.fr : le RN revendique le nucléaire comme énergie permettant de « retrouver sa souveraineté énergétique », décarbonée et pilotable"),
    "cf_indverte": ("https://charlesfournier.fr/retour-sur-une-loi-industrie-verte-qui-na-de-verte-que-le-nom/",
                    "charlesfournier.fr, le député écologiste Charles Fournier : « une terrible occasion manquée »"),
    "lcp_zfe_vote": ("https://lcp.fr/actualites/la-suppression-des-zfe-confirmee-lors-de-l-ultime-vote-sur-la-loi-de-simplification-a-l",
                     "LCP, vote final loi de simplification : RN et Union des droites pour, EPR divisé en trois blocs (30 contre, 25 pour, 19 abstentions)"),
    "lcp_mineurs_rn": ("https://lcp.fr/actualites/delinquance-des-mineurs-la-proposition-de-loi-de-gabriel-attal-pour-restaurer-l-autorite",
                       "LCP : la députée RN Sylvie Josserand vote le texte comme un « signal », tout en le jugeant insuffisant"),
    "an_cr_mineurs_soc": ("https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/session-ordinaire-de-2024-2025/deuxieme-seance-du-mercredi-12-fevrier-2025",
                          "Compte rendu intégral AN, 12/02/2025, Hervé Saulignac (SOC) : texte « injuste, régressif et, sans aucun doute, aussi incomplet qu'inefficace »"),
    "theconv_rn_climat": ("https://theconversation.com/elections-legislatives-et-climat-avec-le-rn-une-triple-sortie-de-route-233000",
                          "The Conversation : le RN rejette les normes « punitives » de l'UE (dont l'interdiction des thermiques 2035) et met en avant la souveraineté énergétique"),
    "datan_vote2957": ("https://datan.fr/votes/legislature-17/vote_2957",
                       "datan.fr : décompte par groupe du scrutin sur la loi Duplomb (2025)"),
    "franceinfo_duplomb": ("https://www.franceinfo.fr/politique/parlement-francais/assemblee-nationale/infographies-loi-duplomb-decouvrez-si-votre-depute-a-vote-pour-ou-contre-ce-texte-souhaite-par-les-agriculteurs-et-critique-par-les-ecologistes_7365096.html",
                           "franceinfo : loi Duplomb, un texte « souhaité par les agriculteurs et critiqué par les écologistes »"),
    "jss_zucman_sas": ("https://jss.fr/post/projet-taxe-zucman-largement-rejete-assemblee-nationale",
                       "JSS : Éva Sas (EcoS), auteure de l'amendement sur l'impôt plancher, dénonce l'optimisation fiscale des grandes fortunes"),
    "publicsenat_zucman_constit": ("https://www.publicsenat.fr/actualites/parlementaire/rejet-de-la-taxe-zucman-a-lassemblee-nationale-est-elle-inconstitutionnelle",
                                   "Public Sénat : la ministre Amélie de Montchalin invoque l'avis du Conseil d'État sur la constitutionnalité de la taxe Zucman"),
    "an_dossier_legitime": ("https://www.assemblee-nationale.fr/dyn/17/dossiers/presomption_legitime_defense_forces_ordre",
                            "Assemblée nationale, dossier législatif : proposition de loi du député Éric Pauget (LR/DR) sur la présomption de légitime défense"),
    "cncdh_rsa": ("https://www.cncdh.fr/actualite/le-rsa-conditionne-une-atteinte-aux-droits-humains",
                  "CNCDH : le RSA conditionné à des heures d'activité, « une atteinte aux droits humains »"),
    "releve_peste_cancer_rn": ("https://lareleveetlapeste.fr/le-rn-a-vote-contre-la-taxe-permettant-de-financer-la-recherche-contre-les-cancers-pediatriques/",
                               "La Relève et La Peste : le RN justifie son vote contre en disant préférer un crédit d'impôt pour les groupes pharmaceutiques"),
    "an_scrutin_619": ("https://www.assemblee-nationale.fr/dyn/15/scrutins/619",
                       "Assemblée nationale, décompte officiel du scrutin n°619 (loi Schiappa) : LaREM 101 pour, FI 14 contre, Nouvelle Gauche 10 contre, LR abstention"),
    "europe1_separatisme_melenchon": ("https://www.europe1.fr/societe/le-parlement-adopte-definitivement-le-projet-de-loi-contre-le-separatisme-4059275",
                                      "Europe 1 : Jean-Luc Mélenchon dénonce une loi « antirépublicaine » à « vocation anti-musulmane »"),
    "europe1_separatisme_vote": ("https://www.europe1.fr/politique/separatisme-lassemblee-nationale-adopte-le-projet-de-loi-en-premiere-lecture-4025693",
                                 "Europe 1 : adoption en première lecture du projet de loi contre le séparatisme (16/02/2021)"),
    "placegrenet_jo_martin": ("https://www.placegrenet.fr/2023/03/08/jo-de-paris-2024-elisa-martin-et-les-deputes-lfi-denoncent-un-projet-de-loi-olympique-liberticide-et-climaticide/595632",
                              "Place Gre'net : Elisa Martin (LFI) dénonce le « sacrifice de nos libertés fondamentales et de notre État de droit »"),
    "lejdd_jo_regol": ("https://www.lejdd.fr/politique/videosurveillance-aux-jo-2024-est-en-train-de-franchir-un-cap-denonce-la-deputee-sandra-regol-133970",
                       "Le JDD, Sandra Regol (Écologiste) : la vidéosurveillance algorithmique permettrait « de cibler les gens sur leur couleur de peau, leurs habits »"),
    "franceinfo_trouve_criminelle": ("https://www.franceinfo.fr/environnement/loi-duplomb/loi-d-urgence-agricole-c-est-une-loi-criminelle-estime-aurelie-trouve-deputee-lfi-de-seine-saint-denis_8111291.html",
                                     "franceinfo, Aurélie Trouvé (LFI) : « une loi criminelle », les responsables « en rendront compte à tous les Français »"),
    "datan_vote600": ("https://datan.fr/votes/legislature-17/vote_600",
                      "datan.fr : décompte par groupe du scrutin sur les ratios de soignants par patient (2025)"),
    "lcp_ratios_ouvert": ("https://lcp.fr/actualites/hopital-les-deputes-adoptent-un-texte-visant-a-instaurer-un-nombre-minimum-de-soignants",
                          "LCP : adoption des ratios de soignants ; le groupe Ensemble juge le texte « inopérant » et voit son amendement de report rejeté"),
    "an_scrutin_2760": ("https://www.assemblee-nationale.fr/dyn/15/scrutins/2760",
                        "Assemblée nationale, décompte officiel du scrutin n°2760 : GDR et FI unanimement pour, SOC pour, LaREM contre"),
    "gdr_bruneel_segur": ("https://groupe-communiste.assemblee-nationale.fr/interventions/discussions-ge%CC%81ne%CC%81rales/article/loi-de-programmation-pour-l-hopital-public-et-les-etablissements-d-hebergement",
                          "Groupe GDR : Alain Bruneel reproche au Gouvernement de renvoyer au « Ségur de la santé » plutôt que de voter cette programmation"),
    "lqm_ivg_difilippo": ("https://www.lequotidiendumedecin.fr/actus-medicales/sante-publique/lassemblee-vote-lallongement-des-delais-dacces-livg-jusqua-14-semaines-de-grossesse-sans-toucher-la",
                          "Le Quotidien du médecin, Fabien Di Filippo (LR) : l'acte d'IVG « change de nature, avec des conséquences gynécologiques qui peuvent être graves »"),
    "datan_vote5845": ("https://datan.fr/votes/legislature-17/vote_5845",
                       "datan.fr : décompte par groupe du scrutin sur l'enseignement de la défense nationale à l'école (2026)"),
    "an_cr_defense_ecole": ("https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance/session-ordinaire-de-2025-2026/troisieme-seance-du-jeudi-26-mars-2026",
                            "Compte rendu intégral AN, 26/03/2026 : Emmanuel Fernandes (LFI-NFP) chiffre à environ 1 000 le nombre d'enseignants nécessaires"),
    "an_scrutin_1550": ("https://www.assemblee-nationale.fr/dyn/17/scrutins/1550",
                        "Assemblée nationale : décompte officiel du scrutin n°1550 (école inclusive, première lecture)"),
    "an_scrutin_2880": ("https://www.assemblee-nationale.fr/dyn/17/scrutins/2880",
                        "Assemblée nationale : décompte officiel du scrutin n°2880 (antisémitisme dans l'enseignement supérieur)"),
    "an_scrutin_351": ("https://www.assemblee-nationale.fr/dyn/15/scrutins/351",
                       "Assemblée nationale : décompte officiel du scrutin n°351 (loi ORE/Parcoursup, 2018)"),
    "ps_sante_touraine": ("https://www.parti-socialiste.fr/projet-de-loi-sante-la-modernisation-du-systeme-au-coeur-de-la-reforme/",
                          "Parti socialiste : position officielle sur la loi de modernisation du système de santé (tiers payant généralisé)"),
}

# (uid scrutin, groupe_abrege EXACT tel qu'en base, texte de la justification, clé source)
# Les abrégés diffèrent par législature : L16 « LFI - NUPES » / « GDR - NUPES » /
# « Ecolo - NUPES » ; L17 « LFI-NFP » / « GDR » / « EcoS » / « EPR » / « DR ».
JUSTIFS = [
    # ── Relance du nucléaire, 2023 (L16) ──────────────────────────────────────
    ("VTANR5L16V1533", "RN",
     "A voté pour : le RN soutient une relance du nucléaire, qu'il présente comme une énergie souveraine, pilotable et bas-carbone.",
     "rn_nucleaire"),
    ("VTANR5L16V1533", "LFI - NUPES",
     "A voté contre, par hostilité à une relance du nucléaire : le groupe lui préfère un scénario reposant sur les énergies renouvelables et la sobriété.",
     "lcp_nucleaire"),
    ("VTANR5L16V1533", "Ecolo - NUPES",
     "A voté contre, opposé au principe d'une relance du nucléaire (coût, déchets, sûreté), au profit des renouvelables.",
     "lcp_nucleaire"),

    # ── Loi industrie verte, 2023 (L16) ──────────────────────────────────────
    ("VTANR5L16V2721", "RN",
     "A voté pour, en soutien à la réindustrialisation, tout en jugeant le texte insuffisant : « la montagne accouche d'une souris » (Alexandre Loubet).",
     "lcp_indverte"),
    ("VTANR5L16V2721", "LFI - NUPES",
     "A voté contre : le groupe jugeait les moyens de l'État très inférieurs à l'effort d'autres pays (le plan américain IRA) et le texte trop peu contraignant sur l'environnement.",
     "lcp_indverte"),
    ("VTANR5L16V2721", "Ecolo - NUPES",
     "A voté contre, qualifiant le texte de « terrible occasion manquée » et jugeant ses ambitions environnementales insuffisantes (Charles Fournier).",
     "cf_indverte"),

    # ── Simplification de la vie économique, 2026 (L17) ──────────────────────
    ("VTANR5L17V6184", "RN",
     "A voté pour, avec l'Union des droites, en soutien à l'allègement des contraintes sur les entreprises et à la suppression des zones à faibles émissions (ZFE).",
     "lcp_zfe_vote"),
    ("VTANR5L17V6184", "LFI-NFP",
     "A voté contre l'ensemble du texte, jugé porteur de régressions, tout en étant, de longue date, favorable à la suppression des ZFE qu'il contient.",
     "lcp_zfe_vote"),
    ("VTANR5L17V6184", "EPR",
     "Le groupe s'est divisé en trois blocs (30 contre, 25 pour, 19 abstentions) après l'échec, en séance, du compromis du Gouvernement qui laissait aux collectivités le choix de maintenir ou non les ZFE.",
     "lcp_zfe_vote"),

    # ── Justice des mineurs (loi Attal), 2025 (L17) ──────────────────────────
    ("VTANR5L17V1624", "RN",
     "A voté pour : la députée Sylvie Josserand a voté le texte comme un « signal », tout en le jugeant insuffisant face à la délinquance des mineurs.",
     "lcp_mineurs_rn"),
    ("VTANR5L17V1624", "LFI-NFP",
     "A voté contre, avec toute la gauche, estimant que le texte remet en cause le principe fondateur de la justice des mineurs : la primauté de l'éducation sur la répression.",
     "lcp_mineurs"),
    ("VTANR5L17V1624", "SOC",
     "A voté contre, son orateur Hervé Saulignac qualifiant le texte d'« injuste, régressif et, sans aucun doute, aussi incomplet qu'inefficace ».",
     "an_cr_mineurs_soc"),

    # ── Société du bien vieillir, 2023 (L16) ─────────────────────────────────
    ("VTANR5L16V3045", "RN",
     "A voté pour, malgré des critiques : sa porte-parole Sandrine Dogor-Such a dénoncé un texte « à mille lieues des problématiques du grand âge » et une « volonté politique insuffisante ».",
     "lcp_bienvieillir"),
    ("VTANR5L16V3045", "LFI - NUPES",
     "A voté contre, Martine Étienne y voyant « la quintessence de ce que fait la macronie au quotidien » : des annonces sans les moyens de la « loi grand âge » attendue.",
     "lcp_bienvieillir"),
    ("VTANR5L16V3045", "GDR - NUPES",
     "A voté contre, avec LFI, jugeant le texte très en deçà des besoins du grand âge et du financement de l'autonomie.",
     "lcp_bienvieillir"),

    # ── Autonomie de la Corse, 2026 (L17), rôles inversés ───────────────────
    ("VTANR5L17V7454", "RN",
     "A voté contre : le RN s'oppose à une autonomie normative de la Corse, qu'il juge contraire à l'unité de la République.",
     "lcp_corse"),
    ("VTANR5L17V7454", "LFI-NFP",
     "A voté pour : Éric Coquerel y a salué « un signal fort et positif » envoyé à la Corse, le groupe étant favorable à la reconnaissance de ses spécificités.",
     "lcp_corse"),

    # ── Corps électoral en Nouvelle-Calédonie, 2024 (L16) ────────────────────
    ("VTANR5L16V3725", "RN",
     "A voté pour le dégel, favorable à l'ouverture du corps électoral aux résidents installés de longue date dans l'archipel.",
     "lcp_caledonie"),
    ("VTANR5L16V3725", "LFI - NUPES",
     "A voté contre, refusant un dégel unilatéral et partiel hors d'un accord global avec les forces calédoniennes ; Alexis Corbière a averti que le texte « mettra l'archipel dans une tension où l'irréparable risque d'avoir lieu ».",
     "lcp_caledonie"),

    # ── Parité dans les petites communes, 2025 (L17), rôles inversés ────────
    ("VTANR5L17V1303", "RN",
     "A voté contre : Jordan Guitton a fait valoir que, dans beaucoup de petites communes, « il n'y aura qu'une liste, donc il n'y aura aucun choix pour les électeurs », jugeant difficile d'y constituer des listes paritaires.",
     "lcp_municipales"),
    ("VTANR5L17V1303", "LFI-NFP",
     "A voté pour, en soutien à la parité ; la gauche a fustigé des « discours réactionnaires » comparables, selon elle, aux arguments opposés à la parité au début des années 2000.",
     "lcp_municipales"),

    # ── Parlement européen ────────────────────────────────────────────────────
    ("PE-HTV-154173", "LFI",
     "A voté contre : LFI rejette le marché carbone, fondé selon elle sur des « logiques spéculatives » et l'échange de « droits à polluer », et dénonçait un texte affaibli par « l'alliance des droites » : un désaccord sur le mécanisme, pas sur l'objectif climatique.",
     "aubry_seqe"),
    ("PE-HTV-167334", "LFI",
     "A voté contre, dénonçant la fin des tarifs réglementés, le maintien de l'indexation de l'électricité sur le gaz et un risque de privatisation ; le groupe défend un contrôle public des prix de l'énergie.",
     "lfi_electricite"),
    ("PE-HTV-167531", "RN",
     "A voté contre, qualifiant le texte de « pacte de submersion » : le mécanisme « accueil ou contribution financière » y est présenté comme « la submersion ou la punition », et le pacte comme un « appel d'air » migratoire.",
     "rn_pacte_migration"),
    ("PE-HTV-152544", "RN",
     "A voté contre, refusant une « écologie punitive » qui ferait des automobilistes et de l'industrie automobile française des « victimes expiatoires » ; le RN met en avant le pouvoir d'achat et l'emploi.",
     "rn_ecologie_punitive"),
    ("PE-HTV-118521", "RN",
     "A voté contre : le RN rejette les normes climatiques jugées « punitives » de l'Union (dont l'interdiction des véhicules thermiques en 2035), leur préférant une « souveraineté énergétique » fondée sur le nucléaire.",
     "theconv_rn_climat"),
    ("PE-HTV-167531", "RE",
     "A voté pour, défendant un pacte fondé sur « fermeté, humanité et efficacité » : réponse européenne coordonnée, maîtrise des frontières et lutte contre l'immigration illégale.",
     "hayer_pacte"),
    ("PE-HTV-118521", "RE",
     "A voté pour, défendant le Pacte vert et l'objectif de neutralité carbone en 2050 comme feuille de route de l'Union.",
     "hayer_greendeal"),
    ("PE-HTV-167531", "VERT",
     "A voté contre, dénonçant un pacte qui « consacre les pires idées de l'extrême droite » : détention généralisée aux frontières, fichage dès six ans et recul des droits fondamentaux des personnes exilées.",
     "toussaint_pacte"),
    ("PE-HTV-164499", "VERT",
     "A voté pour, saluant « une victoire pour le vivant » face aux tentatives de « sabotage » du texte par l'extrême droite.",
     "toussaint_nature"),
    ("PE-HTV-167531", "PS",
     "A voté contre la majorité des textes du pacte, jugé « pas assez équilibré » et insuffisant sur la protection des droits.",
     "glucksmann_pacte"),
    ("PE-HTV-152544", "LR",
     "A voté contre, y voyant une « erreur historique » : une mesure jugée « désastreuse pour l'industrie européenne » et coûteuse pour les citoyens, dont « la grande gagnante est la Chine ».",
     "bellamy_co2_2035"),

    # ── Loi immigration 2023 (Assemblée, L16) : compléter RN (déjà en nuance perso) ──
    ("VTANR5L16V3213", "LFI - NUPES",
     "A voté contre, dénonçant une loi de « xénophobie et de racisme » et une atteinte aux droits.",
     "lfi_immigration_2023"),
    ("VTANR5L16V3213", "SOC",
     "A voté contre, refusant de « sombrer dans le populisme et l'individualisme de la droite et de l'extrême droite » et dénonçant un texte qui « exclut les étrangers sans papiers de l'hébergement d'urgence » et constitue un « recul important des droits humains et des valeurs républicaines ».",
     "ps_immigration_2023"),

    # ── Mesures d'urgence pouvoir d'achat, 2022 (L16) ────────────────────────
    ("VTANR5L16V186", "LFI - NUPES",
     "A voté contre, avec les groupes de la NUPES, jugeant le paquet « insoutenable sur le plan social et environnemental » et lui reprochant d'esquiver la hausse du Smic et des bas salaires.",
     "lcp_pouvoir_achat"),
    ("VTANR5L16V186", "Ecolo - NUPES",
     "A voté contre, avec les groupes de la NUPES, jugeant le paquet « insoutenable sur le plan social et environnemental » et lui reprochant d'esquiver la hausse du Smic et des bas salaires.",
     "lcp_pouvoir_achat"),
    ("VTANR5L16V186", "GDR - NUPES",
     "A voté contre, avec les groupes de la NUPES, jugeant le paquet « insoutenable sur le plan social et environnemental » et lui reprochant d'esquiver la hausse du Smic et des bas salaires.",
     "lcp_pouvoir_achat"),
    ("VTANR5L16V186", "SOC",
     "S'est abstenu : « le compte n'y est pas », sans opposition de principe aux mesures proposées.",
     "lcp_pouvoir_achat"),

    # ── Accord UE-Mercosur, déclaration du Gouvernement, 2024 (L17) ──────────
    # « Contre » ici ne veut PAS dire soutenir l'accord : LFI voulait un rejet
    # plus net que celui du Gouvernement, d'où l'explication, indispensable.
    ("VTANR5L17V456", "LFI-NFP",
     "A voté contre la déclaration du Gouvernement (non pour soutenir l'accord, mais parce qu'elle se bornait à refuser l'accord « en l'état ») : LFI réclamait un rejet « tout court » et reprochait au Gouvernement une « absence de stratégie ».",
     "lfi_mercosur"),

    # ── Loi Duplomb, 2025 (L17) ──────────────────────────────────────────────
    ("VTANR5L17V2957", "EcoS",
     "A voté contre, en raison de la réintroduction d'un néonicotinoïde interdit depuis 2018 et des reculs environnementaux du texte (eau, élevages) : un texte « critiqué par les écologistes ».",
     "franceinfo_duplomb"),
    ("VTANR5L17V2957", "SOC",
     "A voté contre, avec le reste de la gauche, qui a ensuite saisi le Conseil constitutionnel sur ce texte.",
     "datan_vote2957"),
    ("VTANR5L17V2957", "GDR",
     "A voté contre, pour les mêmes motifs environnementaux que le reste de la gauche (néonicotinoïdes, eau).",
     "datan_vote2957"),
    ("VTANR5L17V2957", "RN",
     "A voté pour, en soutien à la levée de contraintes réclamée par une partie de la profession agricole : un texte « souhaité par les agriculteurs ».",
     "franceinfo_duplomb"),
    ("VTANR5L17V2957", "DR",
     "A voté pour ce texte issu d'une proposition de son sénateur Laurent Duplomb, présenté comme un allègement des contraintes pesant sur les agriculteurs.",
     "datan_vote2957"),

    # ── Impôt plancher « taxe Zucman », 2025 (L17) ───────────────────────────
    ("VTANR5L17V881", "LFI-NFP",
     "A voté pour, présentant cet impôt minimum comme un « plancher » corrigeant une injustice : les très hauts patrimoines paient proportionnellement moins d'impôt que le reste de la population.",
     "te_zucman"),
    ("VTANR5L17V881", "EcoS",
     "A voté pour (la proposition émane d'Éva Sas, membre du groupe) pour instaurer un impôt minimum sur les grandes fortunes et lutter contre leur optimisation fiscale.",
     "jss_zucman_sas"),
    ("VTANR5L17V881", "SOC",
     "A voté pour, en soutien à un impôt plancher sur les très hauts patrimoines.",
     "te_zucman"),
    ("VTANR5L17V881", "GDR",
     "A voté pour cet impôt minimum sur les ultra-riches.",
     "te_zucman"),
    ("VTANR5L17V881", "EPR",
     "A voté contre : la ministre Amélie de Montchalin a invoqué l'avis du Conseil d'État sur une constitutionnalité incertaine de la mesure, jugée aussi risquée pour l'investissement : un « mirage » fiscal selon le bloc central.",
     "publicsenat_zucman_constit"),
    ("VTANR5L17V881", "HOR",
     "A voté contre, estimant l'impôt inconstitutionnel et menaçant pour l'investissement.",
     "te_zucman"),

    # ── Présomption de légitime défense des forces de l'ordre, 2026 (L17) ────
    ("VTANR5L17V7987", "LFI-NFP",
     "A voté contre, s'appuyant sur l'alerte du Défenseur des droits : la présomption risquerait de porter atteinte au droit à la vie et au contrôle de l'usage des armes par les forces de l'ordre.",
     "ddd_legitime"),
    ("VTANR5L17V7987", "SOC",
     "A voté contre, au nom des mêmes réserves que celles exprimées par le Défenseur des droits sur le droit à la vie.",
     "ddd_legitime"),
    ("VTANR5L17V7987", "EcoS",
     "A voté contre, jugeant la présomption attentatoire aux garanties entourant l'usage de la force.",
     "ddd_legitime"),
    ("VTANR5L17V7987", "GDR",
     "A voté contre, pour les mêmes motifs (atteinte au contrôle de l'usage de l'arme).",
     "ddd_legitime"),
    ("VTANR5L17V7987", "RN",
     "A voté pour : l'idée, portée de longue date par l'extrême droite, vise à mieux protéger juridiquement les policiers et gendarmes faisant usage de leur arme.",
     "tc_legitime"),
    ("VTANR5L17V7987", "DR",
     "A voté pour ; la proposition a été déposée par le député Éric Pauget (LR/DR), dans un objectif de meilleure protection des forces de l'ordre.",
     "an_dossier_legitime"),
    ("VTANR5L17V7987", "EPR",
     "A voté majoritairement pour ; le ministre de l'Intérieur Laurent Nuñez s'était dit personnellement favorable au texte.",
     "tc_legitime"),

    # ── État de droit en Hongrie, article 7 (Parlement européen, 2024) ───────
    ("PE-HTV-168862", "RN",
     "A voté contre : le RN est le principal allié de Viktor Orbán au Parlement européen, dont la Hongrie est la cible de cette procédure de l'article 7.",
     "fi_orban"),

    # ── Salaire minimum européen (Parlement européen, 2022) ──────────────────
    ("PE-HTV-147342", "RN",
     "A voté contre : le RN s'oppose à un cadre salarial fixé au niveau européen, la question des rémunérations relevant selon lui d'une « compétence exclusivement nationale » (Dominique Bilde).",
     "basta_rn_salaire"),

    # ── Antisémitisme dans l'enseignement supérieur, 2025 (L17), sensible ────
    ("VTANR5L17V2880", "LFI-NFP",
     "A voté contre : LFI dénonce une « instrumentalisation » de la lutte contre l'antisémitisme, y voyant un moyen de « criminaliser le militantisme étudiant » (notamment les mobilisations pro-palestiniennes), tout en affirmant condamner l'antisémitisme.",
     "lfi_antisem_sup"),
    ("VTANR5L17V2880", "RN",
     "A voté pour, avec la majorité et la droite, en soutien au renforcement des mesures contre l'antisémitisme à l'université.",
     "an_scrutin_2880"),

    # ── Santé : modernisation du système de santé, loi Touraine, 2016 (L14) ──
    ("VTANR5L14V1200", "SRC",
     "A voté pour : le groupe socialiste défendait un meilleur accès aux soins, notamment via la généralisation du tiers payant (ne plus avancer les frais chez le médecin).",
     "ps_sante_touraine"),
    ("VTANR5L14V1200", "Les Républicains",
     "A voté contre, dénonçant surtout la généralisation du tiers payant, combattue par les syndicats de médecins (crainte d'une bureaucratisation de la médecine).",
     "wiki_sante_touraine"),

    # ── Santé : déserts médicaux, loi Garot, 2025 (L17) ─────────────────────
    ("VTANR5L17V1607", "LFI-NFP",
     "A voté pour la régulation de l'installation des médecins pour combattre les déserts médicaux.",
     "lcp_deserts"),
    ("VTANR5L17V1607", "SOC",
     "A voté pour, en soutien à une meilleure répartition des médecins sur le territoire.",
     "lcp_deserts"),

    # ── Santé : ratios de soignants par patient, 2025 (L17) ──────────────────
    ("VTANR5L17V600", "LFI-NFP",
     "A voté pour, avec l'ensemble de la gauche, pour garantir un niveau minimum de personnel au chevet des patients.",
     "datan_vote600"),
    ("VTANR5L17V600", "SOC",
     "A voté pour, en soutien à des ratios protégeant patients et soignants : le texte reprend une proposition d'origine sénatoriale socialiste.",
     "ps_ratios"),
    ("VTANR5L17V600", "RN",
     "S'est abstenu : le député Serge Muller, ancien aide-soignant, a dénoncé la pression déjà subie par les soignants, réclamant surtout une revalorisation des métiers.",
     "datan_vote600"),
    ("VTANR5L17V600", "EPR",
     "S'est abstenu : la députée Annie Vidal jugeait le texte « inopérant » et a tenté, en vain, d'en repousser l'échéance.",
     "lcp_ratios_ouvert"),

    # ── Santé : programmation pour l'hôpital public, 2020 (L15), rejetée ─────
    ("VTANR5L15V2760", "GDR",
     "A voté pour cette proposition, d'origine communiste, prévoyant un plan pluriannuel d'investissement et d'embauches pour l'hôpital public et les EHPAD.",
     "an_scrutin_2760"),
    ("VTANR5L15V2760", "FI",
     "A voté pour ce plan d'investissement pour l'hôpital public.",
     "an_scrutin_2760"),
    ("VTANR5L15V2760", "SOC",
     "A voté pour cette programmation pour l'hôpital public.",
     "an_scrutin_2760"),
    ("VTANR5L15V2760", "LaREM",
     "A voté contre : le groupe communiste (Alain Bruneel) a reproché à la majorité de renvoyer au « Ségur de la santé », alors en cours, plutôt que de voter cette programmation.",
     "gdr_bruneel_segur"),

    # ── Santé : allongement du délai d'IVG à 14 semaines, 2022 (L15) ─────────
    ("VTANR5L15V4414", "LR",
     "A voté contre : le député Fabien Di Filippo estimait que l'acte d'IVG « change de nature, avec des conséquences gynécologiques qui peuvent être graves » au-delà de 12 semaines.",
     "lqm_ivg_difilippo"),
    ("VTANR5L15V4414", "LaREM",
     "A voté pour, pour garantir l'accès effectif à l'IVG aux femmes hors délai.",
     "lcp_ivg14"),

    # ── Éducation : Parcoursup / loi ORE, 2018 (L15) ─────────────────────────
    ("VTANR5L15V351", "LaREM",
     "A voté pour, présentant Parcoursup comme un moyen de mieux orienter et de lutter contre l'échec en licence (fin du tirage au sort).",
     "gouv_ore"),
    ("VTANR5L15V351", "FI",
     "A voté contre, dénonçant l'instauration d'une sélection à l'entrée de l'université.",
     "an_scrutin_351"),

    # ── Éducation : programmation de la recherche (LPR), 2020 (L15) ──────────
    ("VTANR5L15V3188", "FI",
     "A voté contre, dénonçant une loi qui « institutionnalise la précarité » dans la recherche (contrats précaires, « chaires de professeur junior ») au lieu de créer des postes pérennes.",
     "lfi_lpr"),
    ("VTANR5L15V3188", "LaREM",
     "A voté pour, défendant une trajectoire budgétaire pluriannuelle en hausse pour la recherche jusqu'en 2030.",
     "wiki_lpr"),

    # ── Éducation : défense nationale à l'école, 2026 (L17) ──────────────────
    ("VTANR5L17V5845", "LFI-NFP",
     "A voté contre : le député Emmanuel Fernandes a jugé le texte sans moyens réels (environ 1 000 enseignants supplémentaires seraient nécessaires, alors que le budget 2026 supprime des postes) et alourdissant des emplois du temps déjà chargés.",
     "an_cr_defense_ecole"),
    ("VTANR5L17V5845", "RN",
     "A voté pour, en soutien au renforcement du lien entre l'armée et la Nation.",
     "datan_vote5845"),

    # ── Éducation : scolarisation des élèves handicapés, 2025 (L17) ──────────
    ("VTANR5L17V1550", "LFI-NFP",
     "A voté contre : texte jugé loin des enjeux (rien sur la précarité des AESH), et un amendement gouvernemental de dernière minute généralisant les « pôles d'appui à la scolarité », « imposé sans concertation », affaiblirait les MDPH et précariserait les accompagnants.",
     "lfi_ecole_inclusive"),
    ("VTANR5L17V1550", "RN",
     "A voté pour en première lecture, en soutien au renforcement de la scolarisation des élèves en situation de handicap.",
     "an_scrutin_1550"),

    # ── Éducation : égalité des chances / écoles de service public, 2025 (L17)
    ("VTANR5L17V840", "RN",
     "A voté contre : Bryan Masson y voit une « discrimination positive » risquant de « rompre l'égalité d'accès à l'emploi public au détriment de tous les Français », et défend la « méritocratie ».",
     "lcp_egalite_chances"),
    ("VTANR5L17V840", "EPR",
     "A voté pour, en soutien à un dispositif diversifiant le recrutement de la haute fonction publique.",
     "lcp_egalite_chances"),

    # ── Taxe : budget 2018 (suppression de l'ISF + flat tax), L15 ────────────
    ("VTANR5L15V272", "LaREM",
     "A voté pour : la majorité présente la suppression de l'ISF et la « flat tax » comme un moyen d'orienter l'épargne vers l'investissement et l'emploi (engagements de campagne d'Emmanuel Macron).",
     "europe1_isf"),
    ("VTANR5L15V272", "LR",
     "A voté pour, en soutien à l'allègement de la fiscalité du capital.",
     "europe1_isf"),
    ("VTANR5L15V272", "FI",
     "A voté contre, dénonçant un budget « pour les riches » : le ministre a reconnu que les 100 plus grandes fortunes paieraient environ 150 millions d'euros d'impôts en moins.",
     "europe1_isf"),
    ("VTANR5L15V272", "NG",
     "A voté contre, avec la gauche, contre la suppression de l'ISF.",
     "europe1_isf"),

    # ── Travail : ordonnances (réforme du code du travail), 2017 (L15) ───────
    ("VTANR5L15V106", "LaREM",
     "A voté pour : donner plus de place aux accords d'entreprise et « sécuriser » les licenciements pour, selon le Gouvernement, favoriser l'embauche.",
     "wiki_ordonnances2017"),
    ("VTANR5L15V106", "LR",
     "A voté pour, en soutien à l'assouplissement du droit du travail.",
     "wiki_ordonnances2017"),
    ("VTANR5L15V106", "FI",
     "A voté contre, dénonçant une régression sociale, notamment le plafonnement des indemnités prud'homales.",
     "wiki_ordonnances2017"),
    ("VTANR5L15V106", "NG",
     "A voté contre, avec la gauche.",
     "wiki_ordonnances2017"),

    # ── Travail : France Travail / RSA conditionné, 2023 (L16) ───────────────
    ("VTANR5L16V2965", "RE",
     "A voté pour : réduire le chômage et mieux accompagner les allocataires du RSA vers l'emploi.",
     "lcp_france_travail"),
    ("VTANR5L16V2965", "LFI - NUPES",
     "A voté contre, dénonçant une « casse sociale » et le principe d'un RSA conditionné à des heures d'activité : la CNCDH y a vu une « atteinte aux droits humains ».",
     "cncdh_rsa"),
    ("VTANR5L16V2965", "RN",
     "A voté contre, s'opposant au conditionnement du RSA prévu par le texte.",
     "lcp_france_travail"),

    # ── Travail : partage de la valeur (ANI), 2023 (L16) ─────────────────────
    ("VTANR5L16V2112", "RE",
     "A voté pour, pour développer l'intéressement, la participation et les primes et associer davantage les salariés aux résultats de l'entreprise.",
     "lcp_partage_valeur"),
    ("VTANR5L16V2112", "LFI - NUPES",
     "A voté contre, avec l'élu communiste de son groupe : LFI dénonce un texte privilégiant des primes ponctuelles plutôt que des hausses de salaire pérennes.",
     "lcp_partage_valeur"),
    ("VTANR5L16V2112", "GDR - NUPES",
     "A voté contre, avec LFI, pour les mêmes raisons.",
     "lcp_partage_valeur"),

    # ── Santé : médicaments cancers de l'enfant, 2026 (L17) ──────────────────
    ("VTANR5L17V6572", "RN",
     "A voté contre (seul groupe à s'y opposer) : le RN refusait la taxe sur les laboratoires pharmaceutiques prévue pour financer le fonds de recherche sur les cancers et maladies rares de l'enfant, lui préférant un crédit d'impôt pour ces groupes.",
     "releve_peste_cancer_rn"),
    ("VTANR5L17V6572", "EPR",
     "A voté pour, avec l'ensemble des autres groupes, ce texte transpartisan salué par les associations de familles.",
     "carenews_cancer"),


    # ── Société : loi Schiappa (violences sexuelles), 2018 (L15) ─────────────
    ("VTANR5L15V619", "LaREM",
     "A voté pour : renforcer la lutte contre les violences sexuelles et sexistes (prescription allongée, outrage sexiste, cyberharcèlement).",
     "an_scrutin_619"),
    ("VTANR5L15V619", "FI",
     "A voté contre en première lecture, jugeant le texte insuffisant et craignant une « correctionnalisation » du viol (jugé comme agression sexuelle) et l'absence d'un seuil d'âge clair de non-consentement.",
     "an_scrutin_619"),
    ("VTANR5L15V619", "NG",
     "A voté contre en première lecture, pour des motifs proches : protection jugée insuffisante des mineurs victimes.",
     "an_scrutin_619"),
    # ── Ajouts (étude base AN, justifications sourcées 26/07/2026) ──
    ("VTANR5L16V1361", "RN",
     "A voté pour, en soutien au durcissement des sanctions contre le squat et à l'accélération des procédures d'expulsion.",
     "lcp_antisquat"),
    ("VTANR5L16V1361", "LFI - NUPES",
     "A voté contre : le groupe dénonce un texte qui protège les propriétaires au détriment des locataires en difficulté et des personnes mal-logées.",
     "lcp_antisquat"),
    ("VTANR5L16V1361", "Ecolo - NUPES",
     "A voté contre, avec la NUPES, jugeant que le texte aggrave la précarité des locataires au lieu de répondre au mal-logement.",
     "lcp_antisquat"),
    ("VTANR5L15V3421", "FI",
     "A voté contre : Jean-Luc Mélenchon a dénoncé une loi « antirépublicaine » à « vocation anti-musulmane » ; le groupe a saisi le Conseil constitutionnel, y voyant une « atteinte manifestement disproportionnée à la liberté d'association ».",
     "europe1_separatisme_melenchon"),
    ("VTANR5L15V3421", "LaREM",
     "A voté pour : la majorité présidentielle défend un texte présenté comme un outil de lutte contre le « séparatisme » islamiste et de renforcement de la laïcité.",
     "europe1_separatisme_vote"),
    ("VTANR5L15V1209", "FI",
     "A voté contre, en opposition frontale aux privatisations d'Aéroports de Paris et de la Française des jeux, dénoncées comme l'abandon de « biens communs ».",
     "fi_pacte"),
    ("VTANR5L15V1209", "LaREM",
     "A voté pour : la majorité défend une loi censée faciliter la croissance et le financement des entreprises et recentrer l'État sur ses missions stratégiques.",
     "france24_pacte"),
    ("VTANR5L16V1305", "LFI - NUPES",
     "A voté contre : Elisa Martin (LFI) a dénoncé le « sacrifice de nos libertés fondamentales et de notre État de droit ».",
     "placegrenet_jo_martin"),
    ("VTANR5L16V1305", "Ecolo - NUPES",
     "A voté contre : Sandra Regol (Écologistes) a averti que cette vidéosurveillance algorithmique « pourrait devenir une norme » permettant de « cibler les gens sur leur couleur de peau, leurs habits ».",
     "lejdd_jo_regol"),
    ("VTANR5L16V1305", "RN",
     "A voté pour, en soutien aux moyens de sécurité déployés pour les Jeux, dont la vidéosurveillance algorithmique.",
     "lcp_jo_vsa"),
    ("VTANR5L16V1305", "RE",
     "A voté pour : la majorité et le gouvernement (Gérald Darmanin) défendent une expérimentation encadrée, excluant la reconnaissance faciale.",
     "lcp_jo_vsa"),
    ("VTANR5L16V2256", "RN",
     "A voté pour, en soutien à la hausse du budget des armées, tout en exprimant des réserves sur plusieurs dispositions (Frank Giletti).",
     "lcp_lpm"),
    ("VTANR5L16V2256", "LFI - NUPES",
     "A voté contre : Bastien Lachaud (LFI) a déploré une « occasion manquée », le groupe contestant les priorités et l'ampleur budgétaire du texte.",
     "lcp_lpm"),
    ("VTANR5L14V981", "SRC",
     "A voté pour : la résolution, déposée par le groupe socialiste, invite le gouvernement à reconnaître l'État de Palestine pour favoriser une solution à deux États.",
     "lcp_palestine"),
    ("VTANR5L14V981", "UMP",
     "A voté contre : le groupe UMP, alors dans l'opposition, s'est opposé à la résolution. Neuf de ses députés ont toutefois voté pour.",
     "lcp_palestine"),
    # ── LFI en écologie/agriculture : votes contre sans justification ──
    ("VTANR5L15V729", "FI",
     "A voté contre : le groupe a jugé la loi très en deçà de son ambition initiale, estimant qu'elle ne garantissait pas un revenu suffisant aux agriculteurs (mécanisme de fixation des prix jugé insatisfaisant), et a demandé le renvoi du texte en commission.",
     "an_egalim_lfi"),
    ("VTANR5L15V3738", "FI",
     "A voté contre : Jean-Luc Mélenchon a rejeté un texte jugé « sans doute inutile », voire « dangereux » et très en deçà de l'urgence climatique et des propositions de la Convention citoyenne (notée 2,5/10 par ses membres), déplorant l'absence de mesures sur les accords de libre-échange, le 100 % renouvelable ou l'interdiction du glyphosate.",
     "f24_climat_lfi"),
    ("VTANR5L16V823", "LFI - NUPES",
     "A voté contre : le groupe (Clémence Guetté) a dénoncé une logique de « marché libéralisé » et le quasi-droit de veto laissé aux maires.",
     "reporterre_enr_lfi"),

    # ── Loi d'urgence pour la protection et la souveraineté agricoles, 2026 (L17) ──
    ("VTANR5L17V8427", "LFI-NFP",
     "A voté contre à l'unanimité : Aurélie Trouvé a dénoncé « une loi criminelle qui empoisonne nos enfants », avertissant les responsables qu'ils en « rendront compte à tous les Français ».",
     "franceinfo_trouve_criminelle"),
    ("VTANR5L17V8427", "EPR",
     "Groupe divisé (51 pour, 15 contre) : son président Gabriel Attal a voté pour tout en exprimant un « sentiment de gâchis » et en critiquant la méthode du Gouvernement sur les amendements de suppression.",
     "maireinfo_urgence_agricole"),
    ("VTANR5L17V8427", "RN",
     "A voté pour à l'unanimité, en soutien à un texte présenté comme une réponse aux difficultés de la profession agricole face à la concurrence et aux aléas climatiques.",
     "basta_urgence_agricole"),
    ("VTANR5L17V8427", "DR",
     "A voté pour à l'unanimité, en soutien à l'allègement des contraintes réclamé par une partie de la profession agricole.",
     "basta_urgence_agricole"),
    ("VTANR5L17V8427", "SOC",
     "A voté contre, avec le reste de la gauche, dénonçant des reculs environnementaux jugés majeurs, notamment sur l'eau et les pesticides.",
     "basta_urgence_agricole"),
    ("VTANR5L17V8427", "EcoS",
     "A voté contre à l'unanimité, opposé à la réintroduction de pesticides et aux reculs environnementaux du texte sur la gestion de l'eau.",
     "basta_urgence_agricole"),
    ("VTANR5L17V8427", "GDR",
     "A voté contre, avec le reste de la gauche, pour les mêmes motifs environnementaux (pesticides, gestion de l'eau).",
     "basta_urgence_agricole"),
    ("VTANR5L17V8427", "Dem",
     "Groupe divisé (19 pour, 11 contre, 6 abstentions) : son président Marc Fesneau, qui avait publiquement critiqué les mesures du texte relatives à l'eau, a néanmoins voté pour son adoption.",
     "basta_urgence_agricole"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # Table créée à la demande (idempotent) : permet d'exécuter ce seed sur une
    # base initialisée avant l'ajout de la table au schéma.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS justifications_groupes (
            id            INTEGER PRIMARY KEY,
            scrutin_id    INTEGER NOT NULL REFERENCES scrutins(id),
            groupe_abrege TEXT NOT NULL,
            texte         TEXT NOT NULL,
            source_id     INTEGER NOT NULL REFERENCES sources(id),
            UNIQUE (scrutin_id, groupe_abrege)
        )""")

    # (scrutin_id, groupe) -> (id de la ligne, texte actuel, source_id actuel).
    # Permet de CORRIGER une justification déjà semée (texte ou source changés),
    # pas seulement d'en ajouter (ce qui est indispensable après un audit qui corrige des
    # citations mal sourcées, sans quoi les corrections ne seraient jamais appliquées).
    existantes = {(sid, ab): (id_, texte, source_id) for id_, sid, ab, texte, source_id in cur.execute(
        "SELECT id, scrutin_id, groupe_abrege, texte, source_id FROM justifications_groupes")}

    # Purge les lignes retirées de JUSTIFS (ex. citation abandonnée faute de source
    # fiable) : sans ça, une correction qui SUPPRIME une entrée ne serait jamais
    # appliquée en base, contrairement à celles qui modifient texte/source.
    voulues = {(uid, abrege) for uid, abrege, _, _ in JUSTIFS}
    supprime = 0
    for (sid, ab), (jid, _, _) in list(existantes.items()):
        uid = cur.execute("SELECT uid_officiel FROM scrutins WHERE id=?", (sid,)).fetchone()[0]
        if (uid, ab) not in voulues:
            cur.execute("DELETE FROM justifications_groupes WHERE id=?", (jid,))
            del existantes[(sid, ab)]
            supprime += 1

    ids_source = {}

    def source_id_pour(cle):
        if cle not in ids_source:
            url, detail = SOURCES[cle]
            r = cur.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
            if r:
                ids_source[cle] = r[0]
            else:
                cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?, 'presse', '2026-07-26', ?)",
                            (url, detail))
                ids_source[cle] = cur.lastrowid
        return ids_source[cle]

    ajout = maj = 0
    for uid, abrege, texte, cle_source in JUSTIFS:
        r = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
        if not r:
            sys.exit(f"Justification orpheline : scrutin {uid} introuvable.")
        sid = r[0]
        # Garde-fou : le groupe doit avoir un décompte réel pour ce scrutin.
        if not cur.execute("SELECT 1 FROM positions_groupes WHERE scrutin_id=? AND groupe_abrege=?",
                           (sid, abrege)).fetchone():
            sys.exit(f"Justification refusée : aucun décompte pour {abrege} au scrutin {uid} "
                     f"(exécuter parse_positions_groupes.py après avoir ajouté le vote clé).")
        sid_src = source_id_pour(cle_source)
        cle = (sid, abrege)
        if cle in existantes:
            jid, texte_actuel, source_actuel = existantes[cle]
            if texte_actuel != texte or source_actuel != sid_src:
                cur.execute("UPDATE justifications_groupes SET texte=?, source_id=? WHERE id=?",
                            (texte, sid_src, jid))
                maj += 1
            continue
        cur.execute("INSERT INTO justifications_groupes (scrutin_id, groupe_abrege, texte, source_id) "
                    "VALUES (?,?,?,?)", (sid, abrege, texte, sid_src))
        ajout += 1

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM justifications_groupes").fetchone()[0]
    print(f"Semé : {ajout} ajoutée(s), {maj} corrigée(s), {supprime} supprimée(s) "
          f"({len(ids_source)} source(s) référencées) ; {n} au total.")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

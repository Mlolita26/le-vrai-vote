"""Justifications éditoriales PAR GROUPE parlementaire : pourquoi chaque parti
a voté comme il l'a fait sur un scrutin clé. Chacune est ATTRIBUÉE et SOURCÉE
(règle absolue : un fait sans source ne s'affiche pas) et rapporte la position
déclarée — elle décrit, elle ne juge pas (CLAUDE.md §4).

Complète les décomptes bruts de `positions_groupes` (miroir des dumps, jamais
édités) par le « pourquoi » éditorial, parti par parti. Sert surtout les lois
où les familles politiques divergent nettement (ex. LFI vs RN).

Garde-fou : une justification n'est écrite que si le groupe a réellement un
décompte en base pour ce scrutin (sinon on refuse — pas de parti fantôme).

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
                      "LCP, mai 2023 — adoption définitive de la loi d'accélération du nucléaire, positions des groupes"),
    "bdt_nucleaire": ("https://www.banquedesterritoires.fr/le-parlement-adopte-largement-le-projet-de-loi-de-relance-du-nucleaire",
                      "Banque des Territoires, 2023 — adoption large du projet de loi de relance du nucléaire"),
    "lcp_indverte": ("https://lcp.fr/actualites/assemblee-nationale-adoption-du-projet-de-loi-industrie-verte-fin-de-la-session",
                     "LCP, juillet 2023 — adoption du projet de loi industrie verte, explications et critiques des groupes"),
    "ps_simplification": ("https://www.publicsenat.fr/actualites/politique/le-parlement-adopte-definitivement-la-loi-sur-la-simplification-de-la-vie-economique-et-enterine-la-suppression-des-zfe",
                          "Public Sénat, avril 2026 — adoption définitive de la loi de simplification (suppression des ZFE), votes des groupes"),
    "lcp_mineurs": ("https://lcp.fr/actualites/delinquance-des-mineurs-que-contient-la-proposition-de-loi-de-gabriel-attal-que-le",
                    "LCP, 2025 — contenu et débats de la proposition de loi Attal sur la justice des mineurs"),
    "bdt_mineurs": ("https://www.banquedesterritoires.fr/la-proposition-de-loi-attal-sur-la-justice-des-mineurs-definitivement-adoptee",
                    "Banque des Territoires, 2025 — adoption définitive de la loi Attal, oppositions de la gauche"),
    "lcp_bienvieillir": ("https://lcp.fr/actualites/bien-vieillir-assemblee-nationale-adopte-texte-premiere-lecture-241649",
                         "LCP, 23/11/2023 — adoption en première lecture de la loi « bien vieillir », positions des groupes"),
    "lcp_corse": ("https://lcp.fr/actualites/l-assemblee-nationale-vote-en-faveur-de-l-autonomie-de-la-corse-437977",
                  "LCP, juin 2026 — vote de l'Assemblée sur l'autonomie de la Corse, positions du RN et de LFI"),
    "maireinfo_corse": ("https://www.maire-info.com/corse/autonomie-de-la-corse-le-projet-de-loi-adopte-en-premiere-lecture-mais-les-incertitudes-demeurent-sur-son-avenir-article-30919",
                        "Maire-Info, juin 2026 — adoption en première lecture du projet de loi Corse autonome"),
    "lcp_caledonie": ("https://lcp.fr/actualites/nouvelle-caledonie-le-projet-de-loi-constitutionnelle-sur-le-degel-du-corps-electoral",
                      "LCP, mai 2024 — adoption du dégel du corps électoral calédonien, débats des groupes"),
    "lcp_municipales": ("https://lcp.fr/actualites/municipales-le-parlement-etend-le-scrutin-de-liste-paritaire-aux-petites-communes-a",
                        "LCP, avril 2025 — extension du scrutin de liste paritaire aux petites communes, débat RN / gauche"),
    # Sources des justifications de groupe au Parlement européen (+ loi immigration 2023).
    "aubry_seqe": ("https://manonaubry.eu/mes-combats/vote/revision-du-systeme-dechange-de-quotas-demission-de-gaz-effet-de-serre-dans-lunion",
                   "manonaubry.eu — fiche de vote de Manon Aubry (LFI/The Left) sur la révision du marché carbone"),
    "lfi_electricite": ("https://lafranceinsoumise.fr/2024/04/11/le-parlement-europeen-vote-la-catastrophique-reforme-du-marche-de-lelectricite-seul-le-groupe-lfi-sy-oppose/",
                        "lafranceinsoumise.fr, 11/04/2024 — opposition de LFI à la réforme du marché de l'électricité"),
    "rn_pacte_migration": ("https://rassemblementnational.fr/communiques/communique-de-presse-de-jordan-bardella",
                           "rassemblementnational.fr — communiqué de Jordan Bardella (RN) contre le « pacte de submersion » (avril 2024)"),
    "rn_ecologie_punitive": ("https://rassemblementnational.fr/communiques/mondial-de-lauto-2024-le-rassemblement-national-se-tient-aux-cotes-des-automobilistes-et-constructeurs-automobiles-francais-victimes-expiatoires-de-lecologie-punitive",
                             "rassemblementnational.fr — communiqué RN (oct. 2024) contre « l'écologie punitive », défense des automobilistes"),
    "lm_rn_climat": ("https://www.lemonde.fr/politique/article/2024/11/24/l-inaction-climatique-ligne-de-conduite-assumee-du-rassemblement-national",
                     "Le Monde, 24/11/2024 — « L'inaction climatique, ligne de conduite assumée du Rassemblement national »"),
    "hayer_pacte": ("https://www.lopinion.fr/international/avec-le-pacte-asile-et-migration-leurope-a-repondu-presente-par-valerie-hayer",
                    "L'Opinion — tribune de Valérie Hayer (Renaissance) défendant le pacte : « fermeté, humanité et efficacité »"),
    "hayer_greendeal": ("https://www.touteleurope.eu/vie-politique-des-etats-membres/elections-europeennes-2024-le-programme-de-valerie-hayer-et-de-renaissance/",
                        "Touteleurope.eu — programme de Valérie Hayer (Renaissance) : compléter le Pacte vert, cap sur la neutralité 2050"),
    "toussaint_pacte": ("https://www.marietoussaint.eu/actualites/pacte-asile-migration",
                        "marietoussaint.eu — communiqué de Marie Toussaint (Les Écologistes) contre le pacte : « les pires idées de l'extrême droite »"),
    "toussaint_nature": ("https://www.marietoussaint.eu/actualites/vote-loi-restauration-nature",
                         "marietoussaint.eu, 27/02/2024 — Marie Toussaint : « une victoire pour le vivant »"),
    "glucksmann_pacte": ("https://www.franceinfo.fr/elections/europeennes/pacte-europeen-sur-la-migration-et-l-asile-je-vais-voter-contre-la-majorite-des-textes-previent-raphael-glucksmann_6455306.html",
                         "franceinfo — Raphaël Glucksmann (PS/Place publique) : voter contre la majorité des textes, pacte « pas assez équilibré »"),
    "bellamy_co2_2035": ("https://www.fxbellamy.fr/2023/02/14/ppe-contre-l-interdiction-de-la-vente-de-vehicules-a-moteurs-thermiques-en-2035/",
                         "fxbellamy.fr, 14/02/2023 — F.-X. Bellamy (LR/PPE) : « erreur historique », « désastreuse pour l'industrie », « la grande gagnante est la Chine »"),
    "lfi_immigration_2023": ("https://lafranceinsoumise.fr/2023/12/15/stop-a-la-loi-immigration/",
                             "lafranceinsoumise.fr, 15/12/2023 — LFI appelle à rejeter la loi immigration (« xénophobie et racisme »)"),
    "ps_immigration_2023": ("https://www.parti-socialiste.paris/communique_loi_immigration_2023",
                            "Parti socialiste — communiqué contre la loi immigration 2023 (« populisme de la droite et de l'extrême droite »)"),
    "lcp_pouvoir_achat": ("https://lcp.fr/actualites/pouvoir-d-achat-le-parlement-adopte-definitivement-le-texte-133297",
                          "LCP, 03/08/2022 — adoption définitive du paquet pouvoir d'achat, explications des groupes"),
    "lfi_mercosur": ("https://lafranceinsoumise.fr/2024/11/26/nous-votons-contre-laccord-de-libre-echange-ue-mercosur/",
                     "lafranceinsoumise.fr, 26/11/2024 — LFI vote contre la déclaration : refuse l'accord « tout court », pas seulement « en l'état »"),
    # Lot 2 de justifications (recherche du 25/07/2026). URLs vérifiées.
    "maire_duplomb": ("https://www.maire-info.com/agriculture/le-parlement-adopte-definitivement-la-loi-duplomb-article-29875",
                      "Maire-Info, juillet 2025 — adoption définitive de la loi Duplomb, camps pour/contre et acétamipride"),
    "te_zucman": ("https://www.touteleurope.eu/economie-et-social/budget-2026-l-assemblee-nationale-rejette-la-taxe-zucman-tous-les-regards-braques-a-gauche/",
                  "Touteleurope.eu — débat sur la taxe Zucman : la gauche y voit un « minimum » fiscal, le bloc central un « mirage » inconstitutionnel"),
    "ddd_legitime": ("https://www.defenseurdesdroits.fr/avis-sur-la-proposition-de-loi-visant-reconnaitre-une-presomption-de-legitime-defense-pour-les-1199",
                     "Défenseur des droits, juin 2026 — avis : la présomption de légitime défense risque de porter atteinte au droit à la vie"),
    "tc_legitime": ("https://theconversation.com/presomption-de-legitime-defense-pour-les-policiers-une-proposition-de-loi-qui-pose-probleme-287244",
                    "The Conversation, 2026 — origine (droite/extrême droite, PPL du LR Éric Pauget), soutien du ministre de l'Intérieur"),
    "fi_orban": ("https://www.franceinfo.fr/politique/front-national/defaite-de-viktor-orban-en-hongrie-le-rassemblement-national-perd-son-principal-allie-europeen_7934591.html",
                 "franceinfo — le Rassemblement national, principal allié de Viktor Orbán au Parlement européen"),
    "basta_rn_salaire": ("https://basta.media/parlement-europeen-RN-oppose-droits-des-femmes-salaire-minimum-Bardella-LePen-Elections-UE",
                         "Basta!, 2024 — récapitulatif des votes du RN au Parlement européen, dont l'opposition au salaire minimum européen"),
    # Éducation
    "lfi_antisem_sup": ("https://lafranceinsoumise.fr/2025/07/02/instrumentalisation-de-la-lutte-contre-lantisemitisme-une-loi-adoptee-pour-reprimer-les-mobilisations-etudiantes/",
                        "lafranceinsoumise.fr, 02/07/2025 — LFI dénonce une « instrumentalisation » de la lutte contre l'antisémitisme"),
    "lcp_antisem_sup": ("https://lcp.fr/actualites/lutte-contre-l-antisemitisme-dans-l-enseignement-superieur-l-examen-d-une-proposition-de",
                        "LCP, 2025 — examen de la PPL antisémitisme dans l'enseignement supérieur, positions des groupes"),
    # Santé — lot de justifications (recherche 25/07/2026)
    "vp_sante_touraine": ("https://www.vie-publique.fr/loi/20733-loi-de-modernisation-de-notre-systeme-de-sante-tiers-payant-medecin-t",
                          "vie-publique.fr — loi de modernisation du système de santé (2016) : tiers payant généralisé, mesure phare"),
    "wiki_sante_touraine": ("https://fr.wikipedia.org/wiki/Loi_de_modernisation_du_syst%C3%A8me_de_sant%C3%A9",
                            "Wikipédia — loi de modernisation du système de santé : opposition de la droite et des syndicats de médecins au tiers payant généralisé"),
    "lcp_deserts": ("https://lcp.fr/actualites/deserts-medicaux-l-assemblee-nationale-vote-en-faveur-d-une-regulation-de-l-installation",
                    "LCP, mai 2025 — l'Assemblée vote la régulation de l'installation des médecins (loi Garot)"),
    "medscape_ratios": ("https://francais.medscape.com/voirarticle/3612430",
                        "Medscape, janvier 2025 — adoption de la loi ratios soignants/patients : abstentions du RN (Serge Muller) et d'Ensemble (Annie Vidal)"),
    "ps_ratios": ("https://www.publicsenat.fr/actualites/sante/hopital-adoption-definitive-de-la-proposition-de-loi-pour-un-nombre-minimal-de-soignants-par-patients",
                  "Public Sénat, janvier 2025 — adoption définitive des ratios de soignants par patient, soutien unanime de la gauche"),
    "qdm_hopital2020": ("https://www.lequotidiendumedecin.fr/actus-medicales/politique-de-sante/lassemblee-rejette-une-proposition-de-loi-communiste-visant-financer-les-hopitaux-et-les-ehpad-pour",
                        "Le Quotidien du médecin, juin 2020 — rejet de la PPL communiste de programmation pour l'hôpital public ; la majorité renvoie au Ségur"),
    "lcp_ivg14": ("https://lcp.fr/actualites/allongement-des-delais-de-l-ivg-apres-un-parcours-seme-d-embuches-la-loi-definitivement",
                  "LCP, février 2022 — adoption définitive de l'allongement du délai d'IVG, opposition de Les Républicains"),
    "gouv_ore": ("https://www.enseignementsup-recherche.gouv.fr/fr/la-loi-ore-en-bref-49643",
                 "enseignementsup-recherche.gouv.fr — loi ORE : orientation, « attendus » et fin du tirage au sort à l'université"),
    "politis_parcoursup": ("https://www.politis.fr/articles/2018/04/parcoursup-et-loi-ore-une-mauvaise-reponse-a-un-vrai-probleme-38717/",
                           "Politis, avril 2018 — critique de la sélection instaurée par Parcoursup / la loi ORE"),
    "lfi_lpr": ("https://lafranceinsoumise.fr/2020/09/23/loi-programmation-recherche-autre-projet-est-possible/",
                "lafranceinsoumise.fr, 23/09/2020 — LFI dénonce une loi recherche qui « institutionnalise la précarité »"),
    "wiki_lpr": ("https://fr.wikipedia.org/wiki/Loi_de_programmation_de_la_recherche_pour_les_ann%C3%A9es_2021_%C3%A0_2030",
                 "Wikipédia — loi de programmation de la recherche 2021-2030 : trajectoire budgétaire et débats"),
    "lcp_defense_ecole": ("https://lcp.fr/actualites/vote-sur-la-defense-nationale-a-l-assemblee-ce-qu-il-faut-retenir-du-debat-en-6-points",
                          "LCP, mars 2026 — vote sur l'enseignement de la défense nationale à l'école, clivages entre groupes"),
    "lfi_ecole_inclusive": ("https://lafranceinsoumise.fr/2025/05/06/projet-de-loi-relatif-a-lecole-inclusive/",
                            "lafranceinsoumise.fr, 06/05/2025 — LFI vote contre : amendement gouvernemental sur les « pôles d'appui », précarisation des AESH"),
    "an_inclusif": ("https://www.assemblee-nationale.fr/dyn/actualites-accueil-hub/renforcer-le-parcours-inclusif-des-eleves-en-situation-de-handicap-adoption-de-la-proposition-de-loi",
                    "Assemblée nationale — adoption de la PPL renforçant le parcours inclusif des élèves en situation de handicap"),
    "lcp_egalite_chances": ("https://lcp.fr/actualites/egalite-des-chances-les-deputes-se-prononcent-en-faveur-de-la-prolongation-du-dispositif",
                            "LCP, février 2025 — prolongation du « concours Talents » ; opposition du RN (Bryan Masson) à la « discrimination positive »"),
}

# (uid scrutin, groupe_abrege EXACT tel qu'en base, texte de la justification, clé source)
# Les abrégés diffèrent par législature : L16 « LFI - NUPES » / « GDR - NUPES » /
# « Ecolo - NUPES » ; L17 « LFI-NFP » / « GDR » / « EcoS » / « EPR » / « DR ».
JUSTIFS = [
    # ── Relance du nucléaire, 2023 (L16) ──────────────────────────────────────
    ("VTANR5L16V1533", "RN",
     "A voté pour : le RN soutient une relance du nucléaire, qu'il présente comme une énergie souveraine, pilotable et bas-carbone.",
     "bdt_nucleaire"),
    ("VTANR5L16V1533", "LFI - NUPES",
     "A voté contre, par hostilité à une relance du nucléaire : le groupe lui préfère un scénario reposant sur les énergies renouvelables et la sobriété.",
     "lcp_nucleaire"),
    ("VTANR5L16V1533", "Ecolo - NUPES",
     "A voté contre, opposé au principe d'une relance du nucléaire (coût, déchets, sûreté), au profit des renouvelables.",
     "lcp_nucleaire"),

    # ── Loi industrie verte, 2023 (L16) ──────────────────────────────────────
    ("VTANR5L16V2721", "RN",
     "A voté pour, en soutien à la réindustrialisation, tout en jugeant le texte insuffisant — « la montagne accouche d'une souris » (Alexandre Loubet).",
     "lcp_indverte"),
    ("VTANR5L16V2721", "LFI - NUPES",
     "A voté contre : le groupe jugeait les moyens de l'État très inférieurs à l'effort d'autres pays (le plan américain IRA) et le texte trop peu contraignant sur l'environnement.",
     "lcp_indverte"),
    ("VTANR5L16V2721", "Ecolo - NUPES",
     "A voté contre, qualifiant le texte d'« occasion manquée » et jugeant ses ambitions environnementales insuffisantes (Charles Fournier).",
     "lcp_indverte"),

    # ── Simplification de la vie économique, 2026 (L17) ──────────────────────
    ("VTANR5L17V6184", "RN",
     "A voté pour, en soutien à l'allègement des contraintes sur les entreprises et à la suppression des zones à faibles émissions (ZFE).",
     "ps_simplification"),
    ("VTANR5L17V6184", "LFI-NFP",
     "A voté contre l'ensemble du texte, jugé porteur de régressions — tout en étant, de longue date, favorable à la suppression des ZFE qu'il contient.",
     "ps_simplification"),
    ("VTANR5L17V6184", "EPR",
     "Une partie du groupe macroniste a voté contre le texte final : le compromis du Gouvernement, qui laissait aux collectivités le choix de maintenir ou non les ZFE, avait été repoussé.",
     "ps_simplification"),

    # ── Justice des mineurs (loi Attal), 2025 (L17) ──────────────────────────
    ("VTANR5L17V1624", "RN",
     "A voté pour, en soutien à un durcissement de la réponse pénale à la délinquance des mineurs.",
     "bdt_mineurs"),
    ("VTANR5L17V1624", "LFI-NFP",
     "A voté contre, avec toute la gauche, estimant que le texte remet en cause le principe fondateur de la justice des mineurs : la primauté de l'éducation sur la répression.",
     "lcp_mineurs"),
    ("VTANR5L17V1624", "SOC",
     "A voté contre, son orateur Hervé Saulignac qualifiant le texte d'« injuste, régressif et aussi complet qu'inefficace ».",
     "bdt_mineurs"),

    # ── Société du bien vieillir, 2023 (L16) ─────────────────────────────────
    ("VTANR5L16V3045", "RN",
     "A voté pour, malgré des critiques : sa porte-parole Sandrine Dogor-Such a dénoncé un texte « à mille lieues des problèmes de la vieillesse » et un « manque de volonté politique ».",
     "lcp_bienvieillir"),
    ("VTANR5L16V3045", "LFI - NUPES",
     "A voté contre, Martine Étienne y voyant « la quintessence de ce que fait le macronisme au quotidien » : des annonces sans les moyens de la « loi grand âge » attendue.",
     "lcp_bienvieillir"),
    ("VTANR5L16V3045", "GDR - NUPES",
     "A voté contre, avec LFI, jugeant le texte très en deçà des besoins du grand âge et du financement de l'autonomie.",
     "lcp_bienvieillir"),

    # ── Autonomie de la Corse, 2026 (L17) — rôles inversés ───────────────────
    ("VTANR5L17V7454", "RN",
     "A voté contre : le RN s'oppose à une autonomie normative de la Corse, qu'il juge contraire à l'unité de la République, et a dénoncé un amendement porté par LFI.",
     "lcp_corse"),
    ("VTANR5L17V7454", "LFI-NFP",
     "A voté pour : Éric Coquerel y a salué « un signal fort et positif » envoyé à la Corse, le groupe étant favorable à la reconnaissance de ses spécificités.",
     "lcp_corse"),

    # ── Corps électoral en Nouvelle-Calédonie, 2024 (L16) ────────────────────
    ("VTANR5L16V3725", "RN",
     "A voté pour le dégel, favorable à l'ouverture du corps électoral aux résidents installés de longue date dans l'archipel.",
     "lcp_caledonie"),
    ("VTANR5L16V3725", "LFI - NUPES",
     "A voté contre, refusant un dégel unilatéral et partiel hors d'un accord global avec les forces calédoniennes ; Alexis Corbière a averti qu'il placerait l'archipel « sous tension ».",
     "lcp_caledonie"),

    # ── Parité dans les petites communes, 2025 (L17) — rôles inversés ────────
    ("VTANR5L17V1303", "RN",
     "A voté contre : Jordan Guitton a fait valoir que, dans beaucoup de petites communes, « il n'y aura qu'une seule liste, il n'y aura pas de choix pour les électeurs », jugeant difficile d'y constituer des listes paritaires.",
     "lcp_municipales"),
    ("VTANR5L17V1303", "LFI-NFP",
     "A voté pour, en soutien à la parité ; la gauche a fustigé des « discours réactionnaires » comparables, selon elle, aux arguments opposés à la parité au début des années 2000.",
     "lcp_municipales"),

    # ── Parlement européen ────────────────────────────────────────────────────
    ("PE-HTV-154173", "LFI",
     "A voté contre : LFI rejette le marché carbone comme une « fausse solution » fondée sur des « logiques spéculatives » et l'échange de « droits à polluer », et dénonçait un texte affaibli par « l'alliance des droites » — un désaccord sur le mécanisme, pas sur l'objectif climatique.",
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
     "A voté contre : le RN assume une opposition aux objectifs climatiques contraignants de l'Union, jugés coûteux pour les ménages et attentatoires à la souveraineté.",
     "lm_rn_climat"),
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
     "A voté contre, dénonçant une loi de « xénophobie et de racisme » et une atteinte aux droits ; le groupe a ensuite saisi le Conseil constitutionnel, qui a censuré une large partie du texte.",
     "lfi_immigration_2023"),
    ("VTANR5L16V3213", "SOC",
     "A voté contre, refusant de « sombrer dans le populisme de la droite et de l'extrême droite » et jugeant le texte contraire à l'accueil des personnes forcées de fuir.",
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
     "S'est abstenu — « le compte n'y est pas » : des revalorisations jugées inférieures à l'inflation, sans opposition de principe aux mesures.",
     "lcp_pouvoir_achat"),

    # ── Accord UE-Mercosur, déclaration du Gouvernement, 2024 (L17) ──────────
    # « Contre » ici ne veut PAS dire soutenir l'accord : LFI voulait un rejet
    # plus net que celui du Gouvernement — d'où l'explication, indispensable.
    ("VTANR5L17V456", "LFI-NFP",
     "A voté contre la déclaration du Gouvernement — non pour soutenir l'accord, mais parce qu'elle se bornait à refuser l'accord « en l'état » : LFI réclamait un rejet « tout court » et reprochait au Gouvernement une « absence de stratégie ».",
     "lfi_mercosur"),

    # ── Loi Duplomb, 2025 (L17) ──────────────────────────────────────────────
    ("VTANR5L17V2957", "LFI-NFP",
     "A voté contre, dénonçant la réautorisation de l'acétamipride — un néonicotinoïde interdit en France depuis 2018, jugé dangereux pour les abeilles — et les atteintes à la ressource en eau. Les groupes de gauche ont saisi le Conseil constitutionnel.",
     "maire_duplomb"),
    ("VTANR5L17V2957", "EcoS",
     "A voté contre, en raison de la réintroduction d'un néonicotinoïde interdit depuis 2018 et des reculs environnementaux du texte (eau, élevages).",
     "maire_duplomb"),
    ("VTANR5L17V2957", "SOC",
     "A voté contre, refusant la réautorisation de l'acétamipride et les dérogations environnementales du texte.",
     "maire_duplomb"),
    ("VTANR5L17V2957", "GDR",
     "A voté contre, pour les mêmes motifs environnementaux que le reste de la gauche (néonicotinoïdes, eau).",
     "maire_duplomb"),
    ("VTANR5L17V2957", "RN",
     "A voté pour, en soutien à la levée de contraintes réclamée par une partie de la profession agricole face à la concurrence européenne.",
     "maire_duplomb"),
    ("VTANR5L17V2957", "DR",
     "A voté pour ce texte issu d'une proposition de son sénateur Laurent Duplomb, présenté comme un allègement des contraintes pesant sur les agriculteurs.",
     "maire_duplomb"),

    # ── Impôt plancher « taxe Zucman », 2025 (L17) ───────────────────────────
    ("VTANR5L17V881", "LFI-NFP",
     "A voté pour, présentant cet impôt minimum comme un « plancher » corrigeant une injustice : les très hauts patrimoines paient proportionnellement moins d'impôt que le reste de la population.",
     "te_zucman"),
    ("VTANR5L17V881", "EcoS",
     "A voté pour — la proposition émane du groupe (Éva Sas) — pour instaurer un impôt minimum de 2 % sur les patrimoines de plus de 100 millions d'euros.",
     "te_zucman"),
    ("VTANR5L17V881", "SOC",
     "A voté pour, en soutien à un impôt plancher sur les très hauts patrimoines.",
     "te_zucman"),
    ("VTANR5L17V881", "GDR",
     "A voté pour cet impôt minimum sur les ultra-riches.",
     "te_zucman"),
    ("VTANR5L17V881", "EPR",
     "A voté contre, jugeant la mesure d'une constitutionnalité incertaine et risquée pour l'investissement — un « mirage » fiscal selon le bloc central.",
     "te_zucman"),
    ("VTANR5L17V881", "HOR",
     "A voté contre, estimant l'impôt inconstitutionnel et menaçant pour l'investissement (Emmanuel Capus).",
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
     "A voté pour : l'idée, portée de longue date par la droite et l'extrême droite, vise à mieux protéger juridiquement les policiers et gendarmes faisant usage de leur arme.",
     "tc_legitime"),
    ("VTANR5L17V7987", "DR",
     "A voté pour ; la proposition a été reprise par le député LR Éric Pauget, dans un objectif de meilleure protection des forces de l'ordre.",
     "tc_legitime"),
    ("VTANR5L17V7987", "EPR",
     "A voté majoritairement pour ; le ministre de l'Intérieur Laurent Nuñez s'était dit personnellement favorable au texte.",
     "tc_legitime"),

    # ── État de droit en Hongrie, article 7 (Parlement européen, 2024) ───────
    ("PE-HTV-168862", "RN",
     "A voté contre : le RN est le principal allié de Viktor Orbán au Parlement européen, dont la Hongrie est la cible de cette procédure de l'article 7.",
     "fi_orban"),

    # ── Salaire minimum européen (Parlement européen, 2022) ──────────────────
    ("PE-HTV-147342", "RN",
     "A voté contre : le RN s'oppose à un cadre salarial fixé au niveau européen, y préférant des leviers nationaux (baisses de cotisations pour les employeurs).",
     "basta_rn_salaire"),

    # ── Antisémitisme dans l'enseignement supérieur, 2025 (L17) — sensible ────
    ("VTANR5L17V2880", "LFI-NFP",
     "A voté contre : LFI dénonce une « instrumentalisation » de la lutte contre l'antisémitisme, y voyant un moyen de « criminaliser le militantisme étudiant » (notamment les mobilisations pro-palestiniennes), tout en affirmant condamner l'antisémitisme.",
     "lfi_antisem_sup"),
    ("VTANR5L17V2880", "RN",
     "A voté pour, avec la majorité et la droite, en soutien au renforcement des mesures contre l'antisémitisme à l'université.",
     "lcp_antisem_sup"),

    # ── Santé : modernisation du système de santé — loi Touraine, 2016 (L14) ──
    ("VTANR5L14V1200", "SRC",
     "A voté pour : le groupe socialiste défendait un meilleur accès aux soins, notamment via la généralisation du tiers payant (ne plus avancer les frais chez le médecin).",
     "vp_sante_touraine"),
    ("VTANR5L14V1200", "Les Républicains",
     "A voté contre, dénonçant surtout la généralisation du tiers payant — combattue par les syndicats de médecins (bureaucratisation, « étatisation » de la médecine).",
     "wiki_sante_touraine"),
    ("VTANR5L14V1200", "UDI",
     "A voté contre, pour les mêmes raisons que la droite : rejet du tiers payant généralisé.",
     "wiki_sante_touraine"),

    # ── Santé : déserts médicaux — loi Garot, 2025 (L17) ─────────────────────
    ("VTANR5L17V1607", "LFI-NFP",
     "A voté pour la régulation de l'installation des médecins pour combattre les déserts médicaux.",
     "lcp_deserts"),
    ("VTANR5L17V1607", "SOC",
     "A voté pour, en soutien à une meilleure répartition des médecins sur le territoire.",
     "lcp_deserts"),

    # ── Santé : ratios de soignants par patient, 2025 (L17) ──────────────────
    ("VTANR5L17V600", "LFI-NFP",
     "A voté pour, avec l'ensemble de la gauche, pour garantir un niveau minimum de personnel au chevet des patients.",
     "ps_ratios"),
    ("VTANR5L17V600", "SOC",
     "A voté pour, en soutien à des ratios protégeant patients et soignants.",
     "ps_ratios"),
    ("VTANR5L17V600", "RN",
     "S'est abstenu : le RN juge le texte « pas fondé sur des bases scientifiques solides » et « loin d'être suffisant », réclamant surtout une revalorisation des métiers (Serge Muller).",
     "medscape_ratios"),
    ("VTANR5L17V600", "EPR",
     "S'est abstenu : la députée Annie Vidal jugeait le texte « inapplicable » et a tenté, en vain, d'en réduire la portée.",
     "medscape_ratios"),

    # ── Santé : programmation pour l'hôpital public, 2020 (L15) — rejetée ─────
    ("VTANR5L15V2760", "GDR",
     "A voté pour cette proposition, d'origine communiste, prévoyant un plan pluriannuel d'investissement et d'embauches pour l'hôpital public et les EHPAD.",
     "qdm_hopital2020"),
    ("VTANR5L15V2760", "FI",
     "A voté pour ce plan d'investissement pour l'hôpital public.",
     "qdm_hopital2020"),
    ("VTANR5L15V2760", "SOC",
     "A voté pour cette programmation pour l'hôpital public.",
     "qdm_hopital2020"),
    ("VTANR5L15V2760", "LaREM",
     "A voté contre : la majorité a renvoyé au « Ségur de la santé », alors en cours, présenté comme la réponse du Gouvernement.",
     "qdm_hopital2020"),

    # ── Santé : allongement du délai d'IVG à 14 semaines, 2022 (L15) ─────────
    ("VTANR5L15V4414", "LR",
     "A voté contre, invoquant des objections médicales (avis de l'Académie de médecine et du Collège des gynécologues) et craignant que moins de médecins acceptent un acte plus tardif (Fabien Di Filippo).",
     "lcp_ivg14"),
    ("VTANR5L15V4414", "LaREM",
     "A voté pour, pour garantir l'accès effectif à l'IVG aux femmes hors délai, contraintes jusque-là de se rendre à l'étranger.",
     "lcp_ivg14"),

    # ── Éducation : Parcoursup / loi ORE, 2018 (L15) ─────────────────────────
    ("VTANR5L15V351", "LaREM",
     "A voté pour, présentant Parcoursup comme un moyen de mieux orienter et de lutter contre l'échec en licence (fin du tirage au sort).",
     "gouv_ore"),
    ("VTANR5L15V351", "FI",
     "A voté contre, dénonçant l'instauration d'une sélection à l'entrée de l'université.",
     "politis_parcoursup"),

    # ── Éducation : programmation de la recherche (LPR), 2020 (L15) ──────────
    ("VTANR5L15V3188", "FI",
     "A voté contre, dénonçant une loi qui « institutionnalise la précarité » dans la recherche (contrats précaires, « chaires de professeur junior ») au lieu de créer des postes pérennes.",
     "lfi_lpr"),
    ("VTANR5L15V3188", "LaREM",
     "A voté pour, défendant une trajectoire budgétaire pluriannuelle en hausse pour la recherche jusqu'en 2030.",
     "wiki_lpr"),

    # ── Éducation : défense nationale à l'école, 2026 (L17) ──────────────────
    ("VTANR5L17V5845", "LFI-NFP",
     "A voté contre : LFI juge le texte sans moyens (environ 1 000 enseignants seraient nécessaires, alors que le budget 2026 supprime des milliers de postes) et alourdissant des emplois du temps déjà chargés (Louis Boyard).",
     "lcp_defense_ecole"),
    ("VTANR5L17V5845", "RN",
     "A voté pour, tout en réclamant « plus d'ambition » pour renforcer le lien entre l'armée et la Nation.",
     "lcp_defense_ecole"),

    # ── Éducation : scolarisation des élèves handicapés, 2025 (L17) ──────────
    ("VTANR5L17V1550", "LFI-NFP",
     "A voté contre : texte jugé loin des enjeux (rien sur la précarité des AESH), et un amendement gouvernemental de dernière minute généralisant les « pôles d'appui à la scolarité », « imposé sans concertation », affaiblirait les MDPH et précariserait les accompagnants (Murielle Lepvraud).",
     "lfi_ecole_inclusive"),
    ("VTANR5L17V1550", "RN",
     "A voté pour en première lecture, en soutien au renforcement de la scolarisation des élèves en situation de handicap.",
     "an_inclusif"),

    # ── Éducation : égalité des chances / écoles de service public, 2025 (L17)
    ("VTANR5L17V840", "RN",
     "A voté contre : Bryan Masson y voit une « discrimination positive » risquant de « rompre l'égalité d'accès à l'emploi public au détriment de tous les Français », et défend la « méritocratie ».",
     "lcp_egalite_chances"),
    ("VTANR5L17V840", "EPR",
     "A voté pour, en soutien à un dispositif diversifiant le recrutement de la haute fonction publique.",
     "lcp_egalite_chances"),
]


def seed(base: Path) -> None:
    con = sqlite3.connect(base)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    # Table créée à la demande (idempotent) — permet d'exécuter ce seed sur une
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

    existantes = {(sid, ab) for sid, ab in cur.execute(
        "SELECT scrutin_id, groupe_abrege FROM justifications_groupes")}

    a_inserer = []
    for uid, abrege, texte, cle_source in JUSTIFS:
        r = cur.execute("SELECT id FROM scrutins WHERE uid_officiel=?", (uid,)).fetchone()
        if not r:
            sys.exit(f"Justification orpheline : scrutin {uid} introuvable.")
        sid = r[0]
        if (sid, abrege) in existantes:
            continue  # idempotent
        # Garde-fou : le groupe doit avoir un décompte réel pour ce scrutin.
        if not cur.execute("SELECT 1 FROM positions_groupes WHERE scrutin_id=? AND groupe_abrege=?",
                           (sid, abrege)).fetchone():
            sys.exit(f"Justification refusée : aucun décompte pour {abrege} au scrutin {uid} "
                     f"(exécuter parse_positions_groupes.py après avoir ajouté le vote clé).")
        a_inserer.append((sid, abrege, texte, cle_source))

    if not a_inserer:
        print("justifications de groupe : déjà à jour, rien à ajouter.")
        con.close()
        return

    ids_source = {}
    for cle in {item[3] for item in a_inserer}:
        url, detail = SOURCES[cle]
        cur.execute("INSERT INTO sources (url, type, collecte, detail) VALUES (?, 'presse', '2026-07-25', ?)",
                    (url, detail))
        ids_source[cle] = cur.lastrowid

    for sid, abrege, texte, cle_source in a_inserer:
        cur.execute("INSERT INTO justifications_groupes (scrutin_id, groupe_abrege, texte, source_id) "
                    "VALUES (?,?,?,?)", (sid, abrege, texte, ids_source[cle_source]))

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM justifications_groupes").fetchone()[0]
    print(f"Semé : {len(a_inserer)} justification(s) de groupe ajoutée(s) "
          f"({len(ids_source)} source(s)) ; {n} au total.")
    con.close()


if __name__ == "__main__":
    seed(Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT)

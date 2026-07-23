# Plan d'acquisition des données — Site de transparence 2027

Ce document décrit, table par table, comment obtenir chaque donnée du projet : la source, le format, la méthode de collecte, la fréquence de mise à jour, et si l'opération est automatisable ou manuelle.

Principe directeur : séparer strictement les **tables brutes** (miroir fidèle des sources officielles, jamais modifiées à la main) des **tables éditoriales** (curation humaine). En cas de contestation, on peut prouver que les données brutes sont un import automatique reproductible.

---

## 1. Inventaire des sources

| Source | Contenu | Format | Accès | Automatisable |
|---|---|---|---|---|
| data.assemblee-nationale.fr | Scrutins, votes individuels, comptes rendus, questions | JSON / XML | Téléchargement direct | Oui |
| data.senat.fr | Sénateurs, scrutins, comptes rendus, dispositifs | Dumps PostgreSQL / XML (Akoma Ntoso) | Téléchargement direct | Oui |
| Parlement européen (open data portal) | Votes par appel nominal (roll-call) | XML | API REST | Oui |
| HowTheyVote.eu / VoteWatch | Votes PE pré-structurés (alternative plus simple) | CSV / API | API REST | Oui |
| Répertoire National des Élus (data.gouv.fr) | Mandats locaux (maires, conseillers) | CSV | Téléchargement direct | Oui |
| API PISTE / Légifrance (DILA) | Décrets de nomination (JO), textes promulgués | JSON | API REST (inscription gratuite) | Oui |
| HATVP (hatvp.fr, open data) | Déclarations d'intérêts et de patrimoine | XML / CSV | Téléchargement direct | Oui |
| vie-publique.fr (DILA) | Discours publics des responsables | API / HTML | API REST | Oui (partiel) |
| Wikidata | Squelette biographique (dates, mandats, partis) | SPARQL | API SPARQL | Oui (à recouper) |
| État civil AN / Sénat | Identité officielle des parlementaires | JSON / XML | Téléchargement direct | Oui |
| Sites de campagne | Programmes des candidats | HTML hétérogène | Scraping / saisie | Partiel |
| Presse + communiqués de parquet | Affaires judiciaires | HTML | Lecture manuelle | Non (manuel) |

APIs tierces utiles pour prototyper (à ne pas mettre en dépendance de production) : NosDéputés.fr / NosSénateurs.fr (Regards Citoyens), CIVIX, Eutyn. Elles simplifient le parsing mais introduisent une dépendance ; la production doit s'appuyer sur les sources officielles.

Licence : les données parlementaires publiques sont sous Licence Ouverte (réutilisation libre avec mention de la source).

---

## 2. Pipeline par table

### Tables brutes (import automatique)

**personnes** — l'identité pivot.
- Sources : Wikidata (SPARQL) + état civil AN/Sénat.
- Méthode : import initial via requête SPARQL, complété par les fichiers d'état civil ; déduplication sur nom + date de naissance.
- Cadence : hebdomadaire.
- Note : chaque personne est unique et porte tous ses rôles dans le temps via `mandats`.

**mandats** — tous les rôles datés (député, sénateur, eurodéputé, ministre, maire, conseiller).
- Sources : open data AN/Sénat (parlementaires), RNE (locaux), API PISTE/JO (décrets ministériels).
- Méthode : téléchargement + normalisation vers une table unique `(personne_id, type, début, fin)`.
- Cadence : hebdomadaire.

**scrutins** — chaque vote public (objet, date, chambre).
- Sources : data.assemblee-nationale.fr, data.senat.fr, PE.
- Méthode : script planifié téléchargeant les JSON/XML, détectant les nouveaux scrutins.
- Cadence : quotidienne (nuit).

**positions_vote** — jointure personne × scrutin (pour/contre/abstention/absent).
- Sources : mêmes fichiers que `scrutins`.
- Méthode : parsing des positions individuelles, insertion en masse.
- Cadence : quotidienne. Volume élevé (centaines de milliers de lignes).

**presence** — événements de présence (scrutin, commission, séance).
- Sources : fichiers de votes (absence aux scrutins) + comptes rendus de commission AN/Sénat.
- Méthode : dérivée des scrutins pour l'absence ; parsing des comptes rendus pour les commissions (présents / excusés).
- Cadence : quotidienne (scrutins) ; hebdomadaire (commissions).

**declarations** — déclarations d'intérêts/patrimoine + discours.
- Sources : HATVP (XML/CSV), vie-publique.fr (discours).
- Méthode : téléchargement HATVP ; API vie-publique pour les discours datés.
- Cadence : mensuelle.

### Tables éditoriales (curation humaine)

**thematiques** — les ~10 grands thèmes.
- Source : définition interne, stable.
- Méthode : saisie unique.

**votes_cles** — couche éditoriale au-dessus des scrutins.
- Champs : `scrutin_id` (pointe vers un scrutin brut), `thematique_id`, `resume` (phrase neutre décrivant le texte), `source_resume` (URL du dossier législatif officiel), `nuance` (optionnel, par position).
- Méthode : sélection selon la grille de critères objectifs (voir §4) ; rédaction des résumés relus et sourcés sur le dossier législatif.
- Cadence : au fil des scrutins marquants + revue périodique.

**affaires_judiciaires** — entièrement manuelle.
- Source : presse et communiqués de parquet, sourcés fait par fait.
- Champs : `statut` (mise en examen / condamnation définitive / relaxe…), `date`, `detail`, `presomption` (booléen), `source`.
- Méthode : saisie manuelle avec double vérification. Aucune automatisation (le casier n'est pas public ; les décisions en open data sont pseudonymisées).
- Cadence : au fil de l'actualité.

**sources** — registre transverse.
- Chaque ligne de fait pointe vers `(url, type, date_collecte)`. Alimenté automatiquement par les scripts d'import et manuellement pour les affaires.

### Tables calculées (dérivées, régénérées)

**couverture** — par personne et par thématique.
- Calcul : à partir de `mandats` + `positions_vote`, détermine pour chaque candidat et chaque vote clé l'état à afficher : *position connue* / *non concerné* (pas en poste à la date du vote) / *indisponible* (jamais parlementaire).
- Cadence : recalcul à chaque import.

**agrégats_presence** — taux par période, comparés à la médiane de l'assemblée.
- Calcul : moyennes glissantes sur `presence`, avec médiane de référence et prise en compte des fonctions (ministre, président de groupe) et congés légitimes.
- Cadence : recalcul hebdomadaire.

---

## 3. Ordre de construction (phases)

**Phase 0 — Infrastructure.** Base PostgreSQL, schéma des tables, dépôt de code, planificateur (cron ou GitHub Actions), stockage des dumps bruts horodatés.

**Phase 1 — Identités et mandats.** `personnes` + `mandats`. C'est le socle : sans le pivot personnes daté, rien ne se relie. Permet déjà la logique « en poste ou non à telle date ».

**Phase 2 — Données parlementaires brutes.** `scrutins`, `positions_vote`, `presence`. Le gros du volume et la valeur centrale du site. Commencer par l'Assemblée (format le mieux documenté), puis Sénat, puis PE.

**Phase 3 — Déclarations.** `declarations` (HATVP + discours). Complète les profils, notamment des non-parlementaires.

**Phase 4 — Couche éditoriale.** `thematiques`, `votes_cles` avec résumés et sources. Nécessite la grille de sélection finalisée.

**Phase 5 — Volet judiciaire.** `affaires_judiciaires`, saisie manuelle sourcée, avec relecture juridique.

**Phase 6 — Couche calculée.** `couverture` et `agrégats_presence`, qui alimentent l'affichage à trois états et les indicateurs comparés à la médiane.

**Phase 7 — Maintenance.** Automatisation des rafraîchissements et supervision (alertes en cas d'échec d'import ou de changement de format d'une source).

---

## 4. Grille de sélection des votes clés (à finaliser)

Pour se prémunir du cherry-picking, la sélection doit suivre des critères objectifs et publics, appliqués identiquement à tous :
- scrutins solennels (par nature les plus significatifs) ;
- textes ayant fait l'objet d'un large débat public (couverture presse, pétition, mobilisation) ;
- votes ayant divisé au sein des groupes (dissidences internes) ;
- amendements ou votes ciblés révélateurs même s'ils sont peu médiatisés.

Chaque vote clé doit être documenté (contexte neutre, résumé sourcé) et la grille elle-même publiée sur la page Méthode.

---

## 5. Cadence de rafraîchissement (récapitulatif)

| Fréquence | Tables concernées |
|---|---|
| Quotidienne (nuit) | scrutins, positions_vote, presence (scrutins) |
| Hebdomadaire | personnes, mandats, presence (commissions), agrégats_presence |
| Mensuelle | declarations |
| Au fil de l'eau | votes_cles, affaires_judiciaires |
| À chaque import | couverture (recalcul), sources (alimentation) |

Afficher publiquement la date de dernière mise à jour de chaque catégorie de données.

---

## 6. Points juridiques à sécuriser avant lancement

- **RGPD** : les opinions politiques (art. 9) et les données relatives aux condamnations (art. 10) sont des catégories sensibles. Consulter la CNIL ou un juriste ; documenter la base légale (mission d'intérêt public / exception journalistique).
- **Présomption d'innocence** (art. 9-1 du Code civil) : toute procédure en cours formulée de façon neutre, sourcée, avec mention explicite.
- **Diffamation** : chaque fait judiciaire renvoie à un document officiel ou un article de presse fiable.
- **Licence Ouverte** : mention de la source pour les données réutilisées.
- **Accessibilité (RGAA)** : information jamais codée par la couleur seule ; navigation clavier ; contrastes.

---

## 7. Ce qui est automatisable, en résumé

Environ 80 % de la base peut être alimentée automatiquement : identités, mandats, scrutins, votes individuels, présence aux scrutins, déclarations HATVP. Les 20 % restants relèvent du travail humain et font la crédibilité du site : sélection et résumé des votes clés, parsing fin des commissions, volet judiciaire, analyse programme vs votes.

Contrainte technique : la collecte de masse s'effectue sur un serveur disposant d'un accès réseau ouvert vers les domaines de données publiques. Les scripts peuvent être écrits et testés à part, mais s'exécutent dans cet environnement.

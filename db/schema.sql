-- Schéma SQLite — « Le Vrai Vote »
-- Traduction de docs/modele-donnees.md.
-- Écarts assumés par rapport au document (justifiés par CLAUDE.md, règle 3
-- « tout fait porte une source ») :
--   - mandats.source_id est obligatoire (le doc ne le mentionnait pas) ;
--   - mandats.precision indique la granularité de la date fournie par la
--     source (les DIA HATVP donnent le mois, pas le jour) ;
--   - table imports_journal pour la traçabilité de chaque import ;
--   - table identifiants_externes : identifiants officiels (UID AN « PAxxxx »,
--     MEP ID du Parlement européen, matricule Sénat) ;
--   - scrutins.legislature : la numérotation AN recommence à 1 à chaque
--     législature, l'unicité est donc (chambre, legislature, numero) ;
--   - position 'non_votant' : à l'AN, « non votant » signifie présent mais ne
--     prenant pas part au vote (ex. président de séance) — ce n'est PAS une
--     absence. L'absence, elle, est inférée : mandat actif à la date du
--     scrutin et aucune mention dans le fichier officiel.

PRAGMA foreign_keys = ON;

-- ── Transverse ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sources (
    id       INTEGER PRIMARY KEY,
    url      TEXT NOT NULL,            -- URL officielle de la source
    type     TEXT NOT NULL,            -- dataset | declaration_hatvp | scrutin_officiel | presse | autre
    collecte TEXT NOT NULL,            -- date de collecte (ISO 8601)
    detail   TEXT                      -- ex. chemin du fichier local archivé
);

CREATE TABLE IF NOT EXISTS imports_journal (
    id         INTEGER PRIMARY KEY,
    source_id  INTEGER NOT NULL REFERENCES sources(id),
    script     TEXT NOT NULL,          -- script d'ingestion exécuté
    lignes     INTEGER NOT NULL,       -- nombre de lignes écrites
    execute_le TEXT NOT NULL           -- horodatage ISO 8601
);

-- ── Brut (miroir des sources officielles, jamais édité à la main) ───────────

CREATE TABLE IF NOT EXISTS personnes (
    id                  INTEGER PRIMARY KEY,
    nom                 TEXT NOT NULL,
    prenom              TEXT NOT NULL,
    naissance           TEXT,          -- NULL = à importer (jamais de valeur plausible)
    naissance_source_id INTEGER REFERENCES sources(id),
    slug                TEXT NOT NULL UNIQUE,
    CHECK (naissance IS NULL OR naissance_source_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS mandats (
    id          INTEGER PRIMARY KEY,
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    type        TEXT NOT NULL CHECK (type IN (
                    'depute','senateur','eurodepute',
                    'ministre','premier_ministre','secretaire_etat',
                    'maire','conseiller_municipal','conseiller_regional',
                    'autre')),
    debut       TEXT NOT NULL,
    fin         TEXT,                  -- NULL = en cours (ou fin non renseignée par la source)
    detail      TEXT,
    precision   TEXT NOT NULL DEFAULT 'jour' CHECK (precision IN ('jour','mois','annee')),
    source_id   INTEGER NOT NULL REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS identifiants_externes (
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    systeme     TEXT NOT NULL CHECK (systeme IN ('an_uid','pe_mep_id','senat_matricule')),
    identifiant TEXT NOT NULL,
    source_id   INTEGER NOT NULL REFERENCES sources(id),
    PRIMARY KEY (personne_id, systeme),
    UNIQUE (systeme, identifiant)
);

-- chambre 'congres' : Congrès de Versailles (députés et sénateurs réunis) —
-- présent dans les dumps AN avec sa propre numérotation (uid VTCGR…).
-- uid_officiel : identifiant du producteur de la donnée (ex. VTANR5L16V1),
-- clé d'unicité fiable ; la numérotation seule se répète (AN vs Congrès).
CREATE TABLE IF NOT EXISTS scrutins (
    id               INTEGER PRIMARY KEY,
    chambre          TEXT NOT NULL CHECK (chambre IN ('an','senat','pe','congres')),
    legislature      TEXT,             -- AN/Congrès : 14/15/16/17 ; NULL si sans objet
    numero           TEXT NOT NULL,
    uid_officiel     TEXT UNIQUE,      -- NULL si la source n'en fournit pas
    objet            TEXT NOT NULL,
    type_vote        TEXT,             -- ex. « scrutin public solennel »
    date             TEXT NOT NULL,
    sort             TEXT,             -- résultat officiel : adopté | rejeté (sort.code de la source)
    total_pour       INTEGER,          -- décompte de synthèse publié
    total_contre     INTEGER,
    total_abstention INTEGER,
    suffrages_requis INTEGER,          -- majorité requise (utile pour les motions de censure)
    source_id        INTEGER NOT NULL REFERENCES sources(id)
);
CREATE INDEX IF NOT EXISTS idx_scrutins_chambre_leg ON scrutins (chambre, legislature, numero);

CREATE TABLE IF NOT EXISTS positions_vote (
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    scrutin_id  INTEGER NOT NULL REFERENCES scrutins(id),
    position    TEXT NOT NULL CHECK (position IN ('pour','contre','abstention','non_votant','absent')),
    PRIMARY KEY (personne_id, scrutin_id)
);

CREATE TABLE IF NOT EXISTS presence (
    id          INTEGER PRIMARY KEY,
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    type        TEXT NOT NULL CHECK (type IN ('scrutin','commission','seance')),
    date        TEXT NOT NULL,
    statut      TEXT NOT NULL CHECK (statut IN ('present','absent','excuse')),
    source_id   INTEGER NOT NULL REFERENCES sources(id)
);

-- ── Mixte ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS declarations (
    id          INTEGER PRIMARY KEY,
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    type        TEXT NOT NULL CHECK (type IN ('interets','patrimoine','discours','programme')),
    contenu     TEXT NOT NULL,
    date        TEXT NOT NULL,
    source_id   INTEGER NOT NULL REFERENCES sources(id)
);

-- ── Éditorial (curation humaine, jamais rempli par un script) ───────────────

CREATE TABLE IF NOT EXISTS thematiques (
    id      INTEGER PRIMARY KEY,
    libelle TEXT NOT NULL UNIQUE,
    ordre   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS votes_cles (
    id            INTEGER PRIMARY KEY,
    scrutin_id    INTEGER NOT NULL UNIQUE REFERENCES scrutins(id),
    thematique_id INTEGER NOT NULL REFERENCES thematiques(id),
    titre         TEXT NOT NULL,       -- intitulé court affiché (écart assumé vs doc : l'UI l'exige)
    resume        TEXT NOT NULL,       -- phrase neutre : décrit, ne juge pas
    source_resume TEXT NOT NULL,       -- URL de la page officielle du scrutin ou du dossier
    contexte      TEXT,
    ordre         INTEGER NOT NULL DEFAULT 0,
    -- Scrutin équivalent au Sénat sur le MÊME texte (autre chambre) : permet
    -- d'afficher la position d'un sénateur (Retailleau) sur une loi clé sans
    -- fusionner les deux votes, qui restent distincts. NULL si sans équivalent.
    scrutin_senat_id INTEGER REFERENCES scrutins(id)
);

-- Déclarations publiques de candidature (saisie éditoriale sourcée).
-- La liste officielle n'existe qu'après validation des parrainages par le
-- Conseil constitutionnel (mars 2027) : statut 'officielle' réservé à ce moment.
CREATE TABLE IF NOT EXISTS candidatures (
    id          INTEGER PRIMARY KEY,
    personne_id INTEGER NOT NULL UNIQUE REFERENCES personnes(id),
    statut      TEXT NOT NULL CHECK (statut IN ('declaree','primaire','retiree','officielle')),
    date        TEXT,                  -- date de la déclaration publique (NULL si non datée par la source)
    detail      TEXT NOT NULL,         -- parti / cadre (ex. « primaire de la gauche unitaire »)
    source_id   INTEGER NOT NULL REFERENCES sources(id)
);

-- Positions des groupes parlementaires sur les scrutins des votes clés
-- (brut : décomptes officiels par groupe, extraits des mêmes dumps).
CREATE TABLE IF NOT EXISTS positions_groupes (
    id             INTEGER PRIMARY KEY,
    scrutin_id     INTEGER NOT NULL REFERENCES scrutins(id),
    organe_ref     TEXT NOT NULL,      -- identifiant officiel du groupe (POxxxxxx)
    groupe_abrege  TEXT,               -- ex. EPR, RN, LFI-NFP (NULL si réf. inconnue du référentiel)
    groupe_libelle TEXT,
    pour           INTEGER NOT NULL,
    contre         INTEGER NOT NULL,
    abstention     INTEGER NOT NULL,
    non_votant     INTEGER NOT NULL,
    source_id      INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE (scrutin_id, organe_ref)
);

-- Rattachement éditorial candidat → groupe parlementaire de son parti,
-- par législature. Seuls les rattachements nets sont saisis ; l'absence
-- de ligne signifie « pas de groupe rattachable » et s'affiche comme telle.
CREATE TABLE IF NOT EXISTS groupes_reference (
    id            INTEGER PRIMARY KEY,
    personne_id   INTEGER NOT NULL REFERENCES personnes(id),
    legislature   TEXT NOT NULL,
    groupe_abrege TEXT NOT NULL,
    detail        TEXT NOT NULL,       -- justification du rattachement
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE (personne_id, legislature)
);

-- Nuances (éditorial) : explication d'un vote contre-intuitif, toujours
-- attribuée et sourcée (explication de vote en séance, communiqué, presse).
-- Une nuance décrit la justification déclarée — elle ne juge pas.
CREATE TABLE IF NOT EXISTS nuances (
    id          INTEGER PRIMARY KEY,
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    scrutin_id  INTEGER NOT NULL REFERENCES scrutins(id),
    texte       TEXT NOT NULL,
    source_id   INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE (personne_id, scrutin_id)
);

-- Justifications de GROUPE (éditorial) : pourquoi un groupe parlementaire a
-- voté comme il l'a fait sur un scrutin, telle que la justification a été
-- déclarée publiquement (explication de vote en séance, communiqué, presse).
-- Complète positions_groupes (le décompte brut, jamais édité) par le « pourquoi »
-- éditorial, parti par parti. Toujours attribuée et SOURCÉE — une justification
-- sans source ne s'affiche pas. Elle rapporte la position déclarée : décrit, ne juge pas.
CREATE TABLE IF NOT EXISTS justifications_groupes (
    id            INTEGER PRIMARY KEY,
    scrutin_id    INTEGER NOT NULL REFERENCES scrutins(id),
    groupe_abrege TEXT NOT NULL,      -- doit correspondre à un groupe présent dans positions_groupes
    texte         TEXT NOT NULL,
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE (scrutin_id, groupe_abrege)
);

CREATE TABLE IF NOT EXISTS affaires_judiciaires (
    id          INTEGER PRIMARY KEY,
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    statut      TEXT NOT NULL CHECK (statut IN (
                    'enquete','mise_en_examen',
                    'condamnation_premiere_instance','condamnation_definitive',
                    'relaxe','classement_sans_suite','autre')),
    date        TEXT NOT NULL,
    detail      TEXT NOT NULL,
    presomption INTEGER NOT NULL CHECK (presomption IN (0,1)),  -- 1 = procédure en cours, mention obligatoire
    source_id   INTEGER NOT NULL REFERENCES sources(id),
    -- Toute procédure non définitivement jugée porte la présomption d'innocence.
    CHECK (statut IN ('condamnation_definitive','relaxe','classement_sans_suite') OR presomption = 1)
);

-- ── Calculé (régénéré, jamais stocké à la main) ─────────────────────────────
-- Logique des trois états (docs/modele-donnees.md, § couverture) :
--   indisponible : la personne n'a jamais eu de mandat parlementaire pertinent
--   non_concerne : aucun mandat de la chambre du scrutin actif à la date du scrutin
--   pour/contre/abstention/absent : position réellement importée
--   a_importer   : en poste à la date du scrutin mais position pas encore chargée

CREATE VIEW IF NOT EXISTS couverture AS
SELECT
    p.id  AS personne_id,
    p.slug AS personne_slug,
    vc.id AS vote_cle_id,
    s.id  AS scrutin_id,
    s.chambre,
    s.date AS date_scrutin,
    CASE
        WHEN NOT EXISTS (
            SELECT 1 FROM mandats m
            WHERE m.personne_id = p.id
              AND m.type IN ('depute','senateur','eurodepute'))
        THEN 'indisponible'
        WHEN NOT EXISTS (
            SELECT 1 FROM mandats m
            WHERE m.personne_id = p.id
              AND ((s.chambre = 'an'      AND m.type = 'depute')
                OR (s.chambre = 'senat'   AND m.type = 'senateur')
                OR (s.chambre = 'pe'      AND m.type = 'eurodepute')
                OR (s.chambre = 'congres' AND m.type IN ('depute','senateur')))
              AND m.debut <= s.date
              AND (m.fin IS NULL OR m.fin >= s.date))
        THEN 'non_concerne'
        WHEN pv.position IS NOT NULL
        THEN pv.position
        ELSE 'a_importer'
    END AS etat
FROM personnes p
CROSS JOIN votes_cles vc
JOIN scrutins s ON s.id = vc.scrutin_id
LEFT JOIN positions_vote pv
       ON pv.personne_id = p.id AND pv.scrutin_id = s.id;

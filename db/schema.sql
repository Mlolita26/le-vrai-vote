-- Schéma SQLite — « Le Vrai Vote »
-- Traduction de docs/modele-donnees.md.
-- Écarts assumés par rapport au document (justifiés par CLAUDE.md, règle 3
-- « tout fait porte une source ») :
--   - mandats.source_id est obligatoire (le doc ne le mentionnait pas) ;
--   - mandats.precision indique la granularité de la date fournie par la
--     source (les DIA HATVP donnent le mois, pas le jour) ;
--   - table imports_journal pour la traçabilité de chaque import.

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

CREATE TABLE IF NOT EXISTS scrutins (
    id        INTEGER PRIMARY KEY,
    chambre   TEXT NOT NULL CHECK (chambre IN ('an','senat','pe')),
    numero    TEXT NOT NULL,
    objet     TEXT NOT NULL,
    date      TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE (chambre, numero)
);

CREATE TABLE IF NOT EXISTS positions_vote (
    personne_id INTEGER NOT NULL REFERENCES personnes(id),
    scrutin_id  INTEGER NOT NULL REFERENCES scrutins(id),
    position    TEXT NOT NULL CHECK (position IN ('pour','contre','abstention','absent')),
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
    resume        TEXT NOT NULL,       -- phrase neutre : décrit, ne juge pas
    source_resume TEXT NOT NULL,       -- URL du dossier législatif officiel
    contexte      TEXT,
    ordre         INTEGER NOT NULL DEFAULT 0
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
              AND m.type = CASE s.chambre
                               WHEN 'an'    THEN 'depute'
                               WHEN 'senat' THEN 'senateur'
                               WHEN 'pe'    THEN 'eurodepute'
                           END
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

-- Base D1 du service « Communauté » : un compteur d'utilité par vote clé.
CREATE TABLE IF NOT EXISTS votes (
    uid   TEXT PRIMARY KEY,          -- uid officiel du scrutin (ex. PE-HTV-154173, VTANR5L16V3213)
    count INTEGER NOT NULL DEFAULT 0
);

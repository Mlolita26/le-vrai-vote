"""Crée (ou recrée le schéma de) la base SQLite locale.

Usage : python ingestion/init_db.py [chemin_base]
Par défaut : data/levraivote.sqlite à la racine du dépôt.
"""
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SCHEMA = RACINE / "db" / "schema.sql"
BASE_DEFAUT = RACINE / "data" / "levraivote.sqlite"


def init_db(chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(chemin)
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        con.commit()
    finally:
        con.close()
    print(f"Base initialisée : {chemin}")


if __name__ == "__main__":
    cible = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DEFAUT
    init_db(cible)

# imports
import pytest
import pandas as pd
from sqlalchemy import create_engine, text

# ── Fixture : données brutes simulées (comme si elles venaient de l'API) ──────
@pytest.fixture
def produits_raw():
    # Simule ce que l'API Open Food Facts renvoie.
    # Contient volontairement des cas limites :
    # - produit sans code-barres
    # - produit sans nom
    # - nutriments aberrants
    # - statuts manquants

    return [
        {
            "code": "3017620422003",
            "product_name": "Nutella",
            "brands": "Ferrero",
            "categories": "Pâtes à tartiner, Petit-déjeuner",
            "quantity": "400g",
            "countries_tags": ["en:france"],
            "nutriscore_grade": "e",
            "ecoscore_grade": "c",
            "nutriments": {
                "energy-kcal_100g": 539,
                "proteins_100g": 6.3,
                "carbohydrates_100g": 57.5,
                "sugars_100g": 56.3,
                "fat_100g": 30.9,
                "salt_100g": 0.107,
                "fiber_100g": 0.0,
            },
        },
        {
            "code": "5000112548822",
            "product_name": "Coca-Cola",
            "brands": "Coca-Cola",
            "categories": "Boissons gazeuses",
            "quantity": "330ml",
            "countries_tags": ["en:united-kingdom"],
            "nutriscore_grade": "e",
            "ecoscore_grade": "",
            "nutriments": {
                "energy-kcal_100g": 42,
                "sugars_100g": 10.6,
                "fat_100g": 0.0,
                "salt_100g": 0.0,
            },
        },
        {
            # sans code-barres : doit être exclu
            "code": "",
            "product_name": "Produit sans code",
            "brands": "Marque",
            "categories": "Test",
            "nutriments": {},
        },
        {
            # sans nom : doit être exclu
            "code": "1234567890123",
            "product_name": "",
            "brands": "Marque",
            "categories": "Test",
            "nutriments": {},
        },
        {
            # nutriments aberrants : doivent être mis à None
            "code": "9999999999999",
            "product_name": "Produit bizarre",
            "brands": "Test",
            "categories": "Test",
            "nutriments": {
                "energy-kcal_100g": 99999,  # impossible
                "fat_100g": -5,             # impossible
            },
        },
    ]

# ── Fixture : DataFrame propre (après transformation) ─────────────────────────
@pytest.fixture
def df_propre(produits_raw):
    # DataFrame déjà transformé — pour tester la couche load.
    from src.transform import normaliser_produits
    return normaliser_produits(produits_raw)

# ── Fixture : base de données SQLite en mémoire ───────────────────────────────
@pytest.fixture
def engine_test():
    # BDD SQLite en mémoire — créée et détruite pour chaque test.
    # Pas besoin de PostgreSQL pour les tests.

    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE dim_produit (
                produit_sk   INTEGER PRIMARY KEY AUTOINCREMENT,
                code_barres  TEXT UNIQUE NOT NULL,
                nom          TEXT,
                marque       TEXT,
                categorie    TEXT,
                quantite     TEXT,
                pays         TEXT,
                nutriscore   TEXT,
                ecoscore     TEXT,
                energie_kcal REAL,
                proteines_g  REAL,
                glucides_g   REAL,
                sucres_g     REAL,
                graisses_g   REAL,
                sel_g        REAL,
                fibres_g     REAL,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE pipeline_runs (
                run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date      TEXT,
                categorie     TEXT,
                nb_extraits   INTEGER,
                nb_inseres    INTEGER,
                nb_mis_a_jour INTEGER,
                duree_sec     REAL,
                statut        TEXT
            )
        """))
        conn.commit()
    yield engine
    engine.dispose()


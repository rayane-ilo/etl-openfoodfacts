# imports
import os
import logging
import pandas as pd
from datetime import date
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
logger = logging.getLogger(__name__)


def get_engine():
    """Crée la connexion PostgreSQL depuis les variables d'environnement."""
    url = (
        f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    )
    return create_engine(url, pool_pre_ping=True)


@contextmanager
def get_conn(engine):
    """Gère les transactions : commit si OK, rollback si erreur."""
    conn = engine.connect()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction annulée : {e}")
        raise
    finally:
        conn.close()


def initialiser_schema(engine):
    """Crée les tables si elles n'existent pas."""
    with get_conn(engine) as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_produit (
                produit_sk          SERIAL PRIMARY KEY,
                code_barres         TEXT UNIQUE NOT NULL,
                nom                 TEXT,
                marque              TEXT,
                categorie           TEXT,
                quantite            TEXT,
                pays                TEXT,
                nutriscore          CHAR(1),
                ecoscore            CHAR(1),
                energie_kcal        NUMERIC(8,2),
                proteines_g         NUMERIC(6,2),
                glucides_g          NUMERIC(6,2),
                sucres_g            NUMERIC(6,2),
                graisses_g          NUMERIC(6,2),
                sel_g               NUMERIC(6,2),
                fibres_g            NUMERIC(6,2),
                created_at          TIMESTAMP DEFAULT NOW(),
                updated_at          TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id          SERIAL PRIMARY KEY,
                run_date        DATE NOT NULL,
                categorie       TEXT,
                nb_extraits     INTEGER,
                nb_inseres      INTEGER,
                nb_mis_a_jour   INTEGER,
                duree_sec       NUMERIC(8,3),
                statut          TEXT,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """))
    logger.info("Schéma vérifié : dim_produit + pipeline_runs")


def upsert_produits(df: pd.DataFrame, engine) -> dict:
    """Insert si nouveau produit, Update si existant (basé sur code_barres)."""
    if df.empty:
        logger.info("DataFrame vide — rien à charger")
        return {"inseres": 0, "mis_a_jour": 0}

    inseres = mis_a_jour = 0

    with get_conn(engine) as conn:
        for _, row in df.iterrows():
            # Convertir NaN → None (PostgreSQL accepte None, pas NaN)
            data = {k: (None if pd.isna(v) else v) for k, v in row.items()}

            existing = conn.execute(
                text("SELECT produit_sk FROM dim_produit WHERE code_barres = :code"),
                {"code": data["code_barres"]}
            ).fetchone()

            if existing:
                conn.execute(text("""
                    UPDATE dim_produit SET
                        nom=:nom, marque=:marque, categorie=:categorie,
                        nutriscore=:nutriscore, ecoscore=:ecoscore,
                        energie_kcal=:energie_kcal, proteines_g=:proteines_g,
                        glucides_g=:glucides_g, sucres_g=:sucres_g,
                        graisses_g=:graisses_g, sel_g=:sel_g,
                        fibres_g=:fibres_g, updated_at=NOW()
                    WHERE code_barres=:code_barres
                """), data)
                mis_a_jour += 1
            else:
                conn.execute(text("""
                    INSERT INTO dim_produit (
                        code_barres, nom, marque, categorie,
                        quantite, pays, nutriscore, ecoscore,
                        energie_kcal, proteines_g, glucides_g,
                        sucres_g, graisses_g, sel_g, fibres_g
                    ) VALUES (
                        :code_barres, :nom, :marque, :categorie,
                        :quantite, :pays, :nutriscore, :ecoscore,
                        :energie_kcal, :proteines_g, :glucides_g,
                        :sucres_g, :graisses_g, :sel_g, :fibres_g
                    )
                """), data)
                inseres += 1

    logger.info(f"Upsert : {inseres} insérés, {mis_a_jour} mis à jour")
    return {"inseres": inseres, "mis_a_jour": mis_a_jour}


def logger_run(engine, info: dict):
    """Enregistre les métriques du run dans pipeline_runs."""
    with get_conn(engine) as conn:
        conn.execute(text("""
            INSERT INTO pipeline_runs
                (run_date, categorie, nb_extraits, nb_inseres,
                 nb_mis_a_jour, duree_sec, statut)
            VALUES
                (:run_date, :categorie, :nb_extraits, :nb_inseres,
                 :nb_mis_a_jour, :duree_sec, :statut)
        """), info)
    logger.info(f"Run enregistré : {info['statut']}")


# imports
import pytest
import pandas as pd
from sqlalchemy import text
from src.load import upsert_produits, logger_run
from datetime import date


# ── Tests : upsert_produits ───────────────────────────────────────────────────

def test_upsert_insere_nouveaux_produits(df_propre, engine_test):
    """Les nouveaux produits doivent être insérés."""
    result = upsert_produits(df_propre, engine_test)
    assert result["inseres"] == len(df_propre)
    assert result["mis_a_jour"] == 0


def test_upsert_met_a_jour_existants(df_propre, engine_test):
    """Au 2ème run, les mêmes produits doivent être mis à jour, pas dupliqués."""
    upsert_produits(df_propre, engine_test)   # 1er run
    result = upsert_produits(df_propre, engine_test)  # 2ème run
    assert result["inseres"] == 0
    assert result["mis_a_jour"] == len(df_propre)


def test_upsert_pas_de_doublons(df_propre, engine_test):
    """Après 2 runs, le nombre de lignes en base doit rester le même."""
    upsert_produits(df_propre, engine_test)
    upsert_produits(df_propre, engine_test)

    with engine_test.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM dim_produit")
        ).scalar()

    assert count == len(df_propre)


def test_upsert_dataframe_vide(engine_test):
    """Un DataFrame vide ne doit rien insérer et ne pas planter."""
    df_vide = pd.DataFrame()
    result = upsert_produits(df_vide, engine_test)
    assert result["inseres"] == 0
    assert result["mis_a_jour"] == 0


def test_upsert_valeurs_correctes_en_base(df_propre, engine_test):
    """Les valeurs insérées doivent correspondre au DataFrame."""
    upsert_produits(df_propre, engine_test)

    with engine_test.connect() as conn:
        rows = conn.execute(
            text("SELECT code_barres, nom FROM dim_produit")
        ).fetchall()

    codes_en_base = {r[0] for r in rows}
    codes_df      = set(df_propre["code_barres"])
    assert codes_en_base == codes_df


# ── Tests : logger_run ────────────────────────────────────────────────────────

def test_logger_run_enregistre_metriques(engine_test):
    """Les métriques du run doivent être enregistrées dans pipeline_runs."""
    info = {
        "run_date":      date.today(),
        "categorie":     "beverages",
        "nb_extraits":   20,
        "nb_inseres":    18,
        "nb_mis_a_jour": 2,
        "duree_sec":     5.3,
        "statut":        "succes",
    }
    logger_run(engine_test, info)

    with engine_test.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM pipeline_runs")
        ).scalar()

    assert count == 1


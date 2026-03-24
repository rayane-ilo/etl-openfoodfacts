# imports
import pytest
import pandas as pd
from src.transform import normaliser_produits, calculer_stats_par_nutriscore

# ── Tests : normaliser_produits ───────────────────────────────────────────────
def test_retourne_dataframe(produits_raw):
    # Le résultat doit toujours être un DataFrame
    result = normaliser_produits(produits_raw)
    assert isinstance(result, pd.DataFrame)

def test_exclut_produits_sans_code_barres(produits_raw):
    # Un produit avec code_barres vide doit être exclu
    result = normaliser_produits(produits_raw)
    assert (result["code_barres"].str.len() > 0).all()

def test_exclut_produits_sans_nom(produits_raw):
    # Un produit avec nom vide doit être exclu
    result = normaliser_produits(produits_raw)
    assert (result["nom"].str.len() > 0).all()

def test_nombre_produits_valides(produits_raw):
    # Sur 5 produits raw, 3 sont valides (2 exclus : sans code, sans nom)
    result = normaliser_produits(produits_raw)
    assert len(result) == 3

def test_nutriments_aberrants_mis_a_none(produits_raw):
    # Les nutriments impossibles (>900 kcal ou négatifs) doivent être None
    result = normaliser_produits(produits_raw)
    produit_bizarre = result[result["code_barres"] == "9999999999999"]
    assert len(produit_bizarre) == 1
    assert pd.isna(produit_bizarre["energie_kcal"].iloc[0])
    assert pd.isna(produit_bizarre["graisses_g"].iloc[0])

def test_nutriscore_en_majuscule(produits_raw):
    # Le nutriscore doit être en majuscule (A, B, C, D, E)
    result = normaliser_produits(produits_raw)
    scores = result["nutriscore"].dropna()
    assert scores.str.isupper().all()

def test_nutriscore_valeurs_valides(produits_raw):
    # Seules les valeurs A B C D E sont acceptées."""
    result = normaliser_produits(produits_raw)
    scores_valides = {"A", "B", "C", "D", "E"}
    for score in result["nutriscore"].dropna():
        assert score in scores_valides

def test_ecoscore_vide_devient_none(produits_raw):
    # Un ecoscore vide doit devenir None, pas une chaîne vide
    result = normaliser_produits(produits_raw)
    coca = result[result["code_barres"] == "5000112548822"]
    assert pd.isna(coca["ecoscore"].iloc[0])

def test_colonnes_attendues(produits_raw):
    # Le DataFrame doit contenir exactement les colonnes attendues
    result = normaliser_produits(produits_raw)
    colonnes_attendues = {
        "code_barres", "nom", "marque", "categorie",
        "quantite", "pays", "nutriscore", "ecoscore",
        "energie_kcal", "proteines_g", "glucides_g",
        "sucres_g", "graisses_g", "sel_g", "fibres_g",
    }
    assert colonnes_attendues.issubset(set(result.columns))

def test_liste_vide_retourne_dataframe_vide():
    # Une liste vide doit retourner un DataFrame vide sans planter
    result = normaliser_produits([])
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0

def test_pays_extrait_correctement(produits_raw):
    # Le pays doit être extrait du premier tag (sans préfixe 'en:')
    result = normaliser_produits(produits_raw)
    nutella = result[result["code_barres"] == "3017620422003"]
    assert nutella["pays"].iloc[0] == "france"

def test_energie_nutella(produits_raw):
    # Les calories du Nutella doivent être correctement extraites
    result = normaliser_produits(produits_raw)
    nutella = result[result["code_barres"] == "3017620422003"]
    assert nutella["energie_kcal"].iloc[0] == 539.0

# ── Tests : calculer_stats_par_nutriscore ─────────────────────────────────────
def test_stats_retourne_dataframe(df_propre):
    result = calculer_stats_par_nutriscore(df_propre)
    assert isinstance(result, pd.DataFrame)

def test_stats_dataframe_vide():
    # Un DataFrame vide ne doit pas faire planter la fonction
    result = calculer_stats_par_nutriscore(pd.DataFrame())
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0

def test_stats_contient_colonne_nutriscore(df_propre):
    result = calculer_stats_par_nutriscore(df_propre)
    assert "nutriscore" in result.columns
    assert "nb_produits" in result.columns


# imports
import pytest
from unittest.mock import patch, MagicMock
from src.extract import fetch_products, extraire_nutriment

# ── Tests : extraire_nutriment ────────────────────────────────────────────────
def test_extraire_nutriment_avec_suffixe_100g():
    # Doit trouver la valeur avec le suffixe _100g
    nutriments = {"energy-kcal_100g": 539.0}
    assert extraire_nutriment(nutriments, "energy-kcal") == 539.0

def test_extraire_nutriment_sans_suffixe():
    # Doit trouver la valeur sans suffixe si _100g absent
    nutriments = {"proteins": 6.3}
    assert extraire_nutriment(nutriments, "proteins") == 6.3

def test_extraire_nutriment_absent():
    # Doit retourner None si la clé n'existe pas
    assert extraire_nutriment({}, "energy-kcal") is None

def test_extraire_nutriment_valeur_non_numerique():
    # Doit retourner None si la valeur n'est pas convertible en float
    nutriments = {"energy-kcal_100g": "non-numerique"}
    assert extraire_nutriment(nutriments, "energy-kcal") is None

def test_extraire_nutriment_retourne_float():
    # La valeur retournée doit être un float
    nutriments = {"fat_100g": 30}
    result = extraire_nutriment(nutriments, "fat")
    assert isinstance(result, float)

# ── Tests : fetch_products avec mock ─────────────────────────────────────────
def test_fetch_products_retourne_liste():
    # fetch_products doit retourner une liste
    reponse_simulee = MagicMock()
    reponse_simulee.json.return_value = {
        "products": [
            {"code": "123", "product_name": "Test"},
            {"code": "456", "product_name": "Test 2"},
        ]
    }
    reponse_simulee.raise_for_status = MagicMock()

    with patch("src.extract.requests.get", return_value=reponse_simulee):
        result = fetch_products(page_size=2, max_pages=1)

    assert isinstance(result, list)
    assert len(result) == 2

def test_fetch_products_page_vide_arrete_pagination():
    # Si l'API renvoie une page vide, la pagination doit s'arrêter
    reponse_simulee = MagicMock()
    reponse_simulee.json.return_value = {"products": []}
    reponse_simulee.raise_for_status = MagicMock()

    with patch("src.extract.requests.get", return_value=reponse_simulee):
        result = fetch_products(page_size=10, max_pages=5)

    assert result == []

def test_fetch_products_timeout_skip():
    # Un timeout ne doit pas faire planter le pipeline — juste skip la page
    import requests as req

    with patch("src.extract.requests.get", side_effect=req.exceptions.Timeout):
        result = fetch_products(page_size=10, max_pages=2)

    assert result == []


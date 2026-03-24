# imports
import requests
import logging
import time
from typing import Optional

# Créer un logger pour ce module — permet de savoir d'où vient le log
logger = logging.getLogger(__name__)

# L'URL de base de l'API
OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2"

def fetch_products(
    categorie: str = "beverages",
    page_size: int = 100,
    max_pages: int = 3,
) -> list[dict]:
    # Extrait des produits depuis l'API Open Food Facts.
    # L'API ne renvoie pas tout d'un coup, elle pagine par blocs.
    # page_size=100, max_pages=3 → 300 produits maximum.
    # Args:
    #     categorie : catégorie de produits ('beverages', 'dairy', 'snacks'...)
    #     page_size : produits par page (max 200 selon l'API)
    #     max_pages : nombre de pages à récupérer
    # Returns:
    #     Liste de dicts — chaque dict = un produit brut de l'API

    tous_les_produits = []

    for page in range(1, max_pages + 1):
        logger.info(f"Extraction page {page}/{max_pages} — catégorie : {categorie}")

        try:
            response = requests.get(
                f"{OFF_BASE_URL}/search",
                params={
                    "categories_tags": categorie,
                    # On ne demande QUE les champs dont on a besoin
                    # Moins de données = plus rapide = moins de mémoire
                    "fields": (
                        "code,product_name,brands,categories,"
                        "nutriscore_grade,ecoscore_grade,"
                        "nutriments,countries_tags,quantity"
                    ),
                    "page_size": page_size,
                    "page":      page,
                    "json":      1,
                },
                timeout=60,  # si l'API ne répond pas en 60s → erreur
                # Obligatoire : identifier notre client auprès de l'API
                headers={"User-Agent": "ETL-Portfolio/1.0"},
            )
            # raise_for_status() lève une exception si code HTTP >= 400
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.Timeout:
            # L'API est lente → on skip cette page, on continue
            logger.warning(f"Timeout sur la page {page} — skip")
            continue

        except requests.exceptions.HTTPError as e:
            # Erreur HTTP (404, 500...) → on arrête tout
            logger.error(f"Erreur HTTP page {page} : {e}")
            raise

        produits = data.get("products", [])

        # Si la page est vide → plus de données → arrêt
        if not produits:
            logger.info(f"Page {page} vide — fin de la pagination")
            break

        tous_les_produits.extend(produits)
        logger.info(f"Page {page} : {len(produits)} produits récupérés")

        # Pause de 0.5 seconde entre les pages
        time.sleep(0.5)

    logger.info(f"Extraction terminée : {len(tous_les_produits)} produits")
    return tous_les_produits

def extraire_nutriment(nutriments: dict, cle: str) -> Optional[float]:
    # Extrait la valeur d'un nutriment depuis le dict de l'API.
    # Pourquoi cette fonction ?
    # L'API renvoie les nutriments avec le suffixe '_100g' :
    #    nutriments['energy-kcal_100g'] = 539
    # Mais parfois le suffixe est absent. Cette fonction essaie les deux.
    # Returns:
    #   float si trouvé et valide, None sinon

    for suffixe in ["_100g", ""]:
        valeur = nutriments.get(f"{cle}{suffixe}")
        if valeur is not None:
            try:
                return float(valeur)
            except (ValueError, TypeError):
                continue
    return None


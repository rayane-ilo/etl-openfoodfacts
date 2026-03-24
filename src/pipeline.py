# imports
import logging
import time
from datetime import date
from dotenv import load_dotenv
from src.extract import fetch_products
from src.transform import normaliser_produits, calculer_stats_par_nutriscore
from src.load import get_engine, initialiser_schema, upsert_produits, logger_run

load_dotenv()

# ── Configuration des logs ────────────────────────────────────────────────────
# On log à la fois dans le terminal ET dans un fichier
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),                              # terminal
        logging.FileHandler(f"logs/pipeline_{date.today()}.log"),  # fichier
    ],
)
logger = logging.getLogger("pipeline")

def run_pipeline(
    categorie: str = "beverages",
    page_size: int = 100,
    max_pages: int = 3,
) -> dict:
    # Orchestre le pipeline ETL complet.
    # Args:
    #     categorie  : catégorie Open Food Facts à extraire
    #     page_size  : produits par page API
    #     max_pages  : nombre de pages à récupérer
    # Returns:
    #     dict avec les métriques du run

    logger.info(f"=== PIPELINE DÉMARRÉ — catégorie={categorie} ===")
    debut = time.perf_counter()

    # Préparer le dict de métriques — sera rempli au fur et à mesure
    metriques = {
        "run_date":     date.today(),
        "categorie":    categorie,
        "nb_extraits":  0,
        "nb_inseres":   0,
        "nb_mis_a_jour": 0,
        "duree_sec":    0,
        "statut":       "echec",  # par défaut — changé en "succes" à la fin
    }

    engine = get_engine()
    initialiser_schema(engine)

    try:
        # ── EXTRACT ───────────────────────────────────────────────────────
        logger.info("Étape 1/3 : Extraction")
        produits_raw = fetch_products(
            categorie=categorie,
            page_size=page_size,
            max_pages=max_pages,
        )
        metriques["nb_extraits"] = len(produits_raw)

        if not produits_raw:
            logger.warning("Aucun produit extrait — arrêt du pipeline")
            return metriques

        # ── TRANSFORM ─────────────────────────────────────────────────────
        logger.info("Étape 2/3 : Transformation")
        df = normaliser_produits(produits_raw)

        # ── LOAD ──────────────────────────────────────────────────────────
        logger.info("Étape 3/3 : Chargement")
        result = upsert_produits(df, engine)
        metriques["nb_inseres"]    = result["inseres"]
        metriques["nb_mis_a_jour"] = result["mis_a_jour"]

        # ── RAPPORT ───────────────────────────────────────────────────────
        stats = calculer_stats_par_nutriscore(df)
        logger.info(f"Rapport nutritionnel :\n{stats.to_string(index=False)}")

        # Tout s'est bien passé
        metriques["statut"] = "succes"

    except Exception as e:
        # En cas d'erreur — on log et on re-lève l'exception
        logger.error(f"Pipeline échoué : {e}", exc_info=True)
        metriques["statut"] = "echec"
        raise

    finally:
        # Ce bloc s'exécute TOUJOURS — succès ou échec
        # On enregistre les métriques en base dans tous les cas
        metriques["duree_sec"] = round(time.perf_counter() - debut, 3)
        logger_run(engine, metriques)
        logger.info(
            f"=== PIPELINE TERMINÉ en {metriques['duree_sec']}s — "
            f"{metriques['nb_inseres']} insérés, "
            f"{metriques['nb_mis_a_jour']} mis à jour ==="
        )

    return metriques

# ── Point d'entrée ────────────────────────────────────────────────────────────
# Ce bloc ne s'exécute QUE si vous lancez directement :
# python -m src.pipeline
# Il ne s'exécute PAS si ce fichier est importé dans les tests
if __name__ == "__main__":
    run_pipeline(
        categorie="beverages",
        page_size=50,
        max_pages=2,
    )


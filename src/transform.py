# imports
import pandas as pd
import logging
from src.extract import extraire_nutriment

logger = logging.getLogger(__name__)

def normaliser_produits(produits_raw: list[dict]) -> pd.DataFrame:
    # Transforme la liste brute de l'API en DataFrame structuré et propre.
    # Le processus en 3 temps :
    # 1. Aplatir  : passer de dicts imbriqués à un DataFrame colonnaire
    # 2. Nettoyer : supprimer les invalides, dédupliquer
    # 3. Valider  : vérifier que les valeurs sont cohérentes

    if not produits_raw:
        logger.warning("Liste vide — retourne DataFrame vide")
        return pd.DataFrame()

    # ── 1. APLATIR ────────────────────────────────────────────────────────
    # On construit une liste de dicts plats (1 dict = 1 ligne du DataFrame)
    lignes = []
    for p in produits_raw:
        nutriments = p.get("nutriments", {})
        lignes.append({
            "code_barres":  p.get("code", "").strip(),
            "nom":          p.get("product_name", "").strip(),
            "marque":       p.get("brands", "").strip(),
            "categorie":    p.get("categories", "").split(",")[0].strip(),
            "quantite":     p.get("quantity", ""),
            "pays":         _premier_tag(p.get("countries_tags", [])),
            "nutriscore":   (p.get("nutriscore_grade") or "").upper() or None,
            "ecoscore":     (p.get("ecoscore_grade") or "").upper() or None,
            # Nutriments pour 100g
            "energie_kcal": extraire_nutriment(nutriments, "energy-kcal"),
            "proteines_g":  extraire_nutriment(nutriments, "proteins"),
            "glucides_g":   extraire_nutriment(nutriments, "carbohydrates"),
            "sucres_g":     extraire_nutriment(nutriments, "sugars"),
            "graisses_g":   extraire_nutriment(nutriments, "fat"),
            "sel_g":        extraire_nutriment(nutriments, "salt"),
            "fibres_g":     extraire_nutriment(nutriments, "fiber"),
        })

    df = pd.DataFrame(lignes)
    n_initial = len(df)
    logger.info(f"Aplatissage terminé : {n_initial} lignes")

    # ── 2. NETTOYER ───────────────────────────────────────────────────────
    # Supprimer les produits sans code-barres (inutilisables en BDD)
    df = df[df["code_barres"].str.len() > 0]

    # Supprimer les produits sans nom (inutilisables pour l'analyse)
    df = df[df["nom"].str.len() > 0]

    # Dédupliquer sur le code-barres
    # (l'API peut renvoyer le même produit sur plusieurs catégories)
    df = df.drop_duplicates(subset=["code_barres"], keep="first")

    # ── 3. VALIDER ────────────────────────────────────────────────────────
    # Nutriments : remplacer les valeurs impossibles par None
    # (calories > 900 kcal/100g c'est physiquement impossible)
    bornes = {
        "energie_kcal": (0, 900),
        "proteines_g":  (0, 100),
        "glucides_g":   (0, 100),
        "sucres_g":     (0, 100),
        "graisses_g":   (0, 100),
        "sel_g":        (0, 100),
        "fibres_g":     (0, 100),
    }
    for col, (mini, maxi) in bornes.items():
        df[col] = df[col].where(
            (df[col] >= mini) & (df[col] <= maxi),
            other=None
        )

    # Nutriscore/Ecoscore : seulement A B C D E
    for col in ["nutriscore", "ecoscore"]:
        df[col] = df[col].where(
            df[col].isin(["A", "B", "C", "D", "E"]),
            other=None
        )

    n_final = len(df)
    logger.info(
        f"Nettoyage terminé : {n_initial} → {n_final} lignes "
        f"({n_initial - n_final} exclues)"
    )
    return df.reset_index(drop=True)

def calculer_stats_par_nutriscore(df: pd.DataFrame) -> pd.DataFrame:
    # Calcule des statistiques par nutriscore.
    # Utile pour vérifier la qualité des données et créer un rapport.
    
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby("nutriscore", dropna=False)
        .agg(
            nb_produits  = ("code_barres", "count"),
            energie_moy  = ("energie_kcal", "mean"),
            sucres_moy   = ("sucres_g", "mean"),
            graisses_moy = ("graisses_g", "mean"),
        )
        .round(1)
        .reset_index()
    )

def _premier_tag(tags: list) -> str:
    # Fonction utilitaire privée (préfixe _).
    # Extrait le premier tag d'une liste et supprime le préfixe de langue.
    # Exemple : ['en:france', 'en:germany'] → 'france'

    if not tags or not isinstance(tags, list):
        return ""
    return tags[0].split(":")[-1].replace("-", " ").strip()


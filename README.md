# ETL Open Food Facts
Pipeline ETL complet qui extrait des données produits depuis l'API Open Food Facts,
les nettoie et les charge dans PostgreSQL.

Projet réalisé dans le cadre d'une formation Data Engineer — Phase 1 Fondations.

---

## Stack technique
- Python 3.12
- Pandas — transformation et nettoyage
- SQLAlchemy — connexion et chargement PostgreSQL
- PostgreSQL — stockage final
- pytest — tests unitaires (29 tests, couverture > 80%)
- python-dotenv — gestion des variables d'environnement

---

## Architecture
```
API Open Food Facts
        |
        v
   extract.py        # Appel API avec pagination et gestion des erreurs
        |
        v
  transform.py       # Nettoyage, validation, deduplication
        |
        v
    load.py          # Upsert PostgreSQL
        |
        v
  pipeline.py        # Orchestrateur — lance les 3 etapes
        |
        v
  PostgreSQL
  dim_produit        # Table des produits nettoyes
  pipeline_runs      # Historique des executions
```

---

## Structure du projet
```
etl-openfoodfacts/
├── src/
│   ├── extract.py      # Extraction API Open Food Facts
│   ├── transform.py    # Nettoyage et validation des donnees
│   ├── load.py         # Chargement PostgreSQL avec upsert
│   └── pipeline.py     # Orchestrateur ETL
├── tests/
│   ├── conftest.py     # Fixtures partagees
│   ├── test_extract.py # Tests extraction et nutriments
│   ├── test_transform.py # Tests nettoyage et validation
│   └── test_load.py    # Tests upsert et metriques
├── logs/               # Logs d'execution (gitignore)
├── data/               # Donnees brutes et traitees (gitignore)
├── .env.example        # Template des variables d'environnement
├── requirements.txt    # Dependances Python
└── README.md
```

---

## Installation

### Prerequis
- Python 3.12+
- PostgreSQL 15+ (Postgres.app sur Mac)
- pyenv (recommande pour la gestion des versions Python)

### Etapes
```bash
# Cloner le repo
git clone https://github.com/rayane-ilo/etl-openfoodfacts.git
cd etl-openfoodfacts

# Creer et activer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Installer les dependances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Editer .env avec vos identifiants PostgreSQL
```

### Configuration PostgreSQL
```sql
CREATE DATABASE openfoodfacts_dw;
CREATE USER etl_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL ON SCHEMA public TO etl_user;
GRANT CREATE ON SCHEMA public TO etl_user;
```

---

## Configuration
Creez un fichier `.env` a la racine :
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=openfoodfacts_dw
DB_USER=etl_user
DB_PASSWORD=votre_mot_de_passe
```

Un fichier `.env.example` est fourni comme template.

---

## Utilisation

### Lancer le pipeline complet
```bash
python -m src.pipeline
```

### Exemple de sortie
```
2024-03-15 10:00:00 | INFO | pipeline | === PIPELINE DEMARRE — categorie=beverages ===
2024-03-15 10:00:01 | INFO | pipeline | Etape 1/3 : Extraction
2024-03-15 10:00:08 | INFO | src.extract | Page 1 : 50 produits recuperes
2024-03-15 10:00:08 | INFO | pipeline | Etape 2/3 : Transformation
2024-03-15 10:00:08 | INFO | pipeline | Etape 3/3 : Chargement
2024-03-15 10:00:10 | INFO | src.load | Upsert : 47 inseres, 0 mis a jour
2024-03-15 10:00:10 | INFO | pipeline | === PIPELINE TERMINE en 10.3s ===
```

### Lancer les tests
```bash
# Tous les tests
python -m pytest tests/ -v

# Avec rapport de couverture
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## Schema de la base de donnees

### dim_produit
| Colonne | Type | Description |
|---|---|---|
| produit_sk | SERIAL | Cle primaire |
| code_barres | TEXT | Code-barres unique (EAN) |
| nom | TEXT | Nom du produit |
| marque | TEXT | Marque |
| categorie | TEXT | Categorie principale |
| nutriscore | CHAR(1) | Score nutritionnel (A a E) |
| ecoscore | CHAR(1) | Score environnemental (A a E) |
| energie_kcal | NUMERIC | Energie pour 100g |
| proteines_g | NUMERIC | Proteines pour 100g |
| sucres_g | NUMERIC | Sucres pour 100g |
| graisses_g | NUMERIC | Graisses pour 100g |
| sel_g | NUMERIC | Sel pour 100g |
| created_at | TIMESTAMP | Date d'insertion |
| updated_at | TIMESTAMP | Date de mise a jour |

### pipeline_runs
| Colonne | Type | Description |
|---|---|---|
| run_id | SERIAL | Cle primaire |
| run_date | DATE | Date du run |
| categorie | TEXT | Categorie extraite |
| nb_extraits | INTEGER | Produits extraits de l'API |
| nb_inseres | INTEGER | Nouveaux produits inseres |
| nb_mis_a_jour | INTEGER | Produits mis a jour |
| duree_sec | NUMERIC | Duree d'execution en secondes |
| statut | TEXT | succes ou echec |

---

## Choix techniques

**Upsert plutot que INSERT** : l'API renvoie les memes produits a chaque run.
Un simple INSERT creerait des doublons. L'upsert insere les nouveaux
et met a jour les existants sans duplication.

**SQLite en mémoire pour les tests** : les tests ne dependent pas de PostgreSQL.
Chaque test repart d'une base vide — isolation garantie, execution rapide.

**Variables d'environnement** : aucun identifiant dans le code.
Le fichier .env ne va jamais sur Git.

**Pagination API** : Open Food Facts limite les reponses a 200 produits par page.
Le pipeline gere automatiquement la pagination et s'arrete si une page est vide.

---

## Axes d'amelioration
- Ajout d'Apache Airflow pour orchestrer le pipeline (Phase 2)
- Deploiement sur AWS S3 + Glue (Phase 3)
- Tests d'integration avec une vraie base PostgreSQL de test
- Normalisation des noms de marques multilingues

---

## Auteur
Rayane-ilo

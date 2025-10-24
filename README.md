# Scraper d'Arrêtés de Paris - Voirie et Déplacements

Ce projet scrape automatiquement les arrêtés de la catégorie "Voirie et déplacements" depuis le [Bulletin Officiel de la Ville de Paris (BOVP)](https://bovp.apps.paris.fr/).

## 📊 Fonctionnalités

- **Scraping automatique** : Collecte quotidienne des nouveaux arrêtés via GitHub Actions
- **Détection des nouveaux arrêtés** : Basée sur le numéro unique d'arrêté (ex: 2025 T 17858)
- **Métadonnées complètes** : Titre, dates, signataires, autorité responsable
- **Stockage des PDFs** : Upload automatique vers S3
- **Export CSV** : Métadonnées exportées dans `data/arretes.csv`
- **Scraping asynchrone** : Parallélisation des requêtes pour optimiser la vitesse

## 🏗️ Architecture

```
scrapearretesparis/
├── .github/workflows/
│   └── daily_scrape.yml          # GitHub Action (exécution quotidienne)
├── src/
│   ├── scraper.py                # Script principal avec Playwright
│   ├── s3_uploader.py            # Gestion upload S3
│   └── config.py                 # Configuration
├── data/
│   └── arretes.csv               # Métadonnées des arrêtés
├── requirements.txt              # Dépendances Python
├── .env.example                  # Template des variables d'environnement
└── README.md
```

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone https://github.com/VOTRE_USERNAME/scrapearretesparis.git
cd scrapearretesparis
```

### 2. Installer les dépendances

**Option A - Avec uv (recommandé, 10-100x plus rapide)** :

```bash
# Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances système (Linux)
sudo apt-get install -y libxml2-dev libxslt-dev

# Installer les dépendances Python
uv pip install --system -r requirements.txt

# Installer les navigateurs Playwright
playwright install chromium
```

**Option B - Avec pip (méthode classique)** :

```bash
# Installer les dépendances système (Linux)
sudo apt-get install -y libxml2-dev libxslt-dev

# Installer les dépendances Python
pip install -r requirements.txt

# Installer les navigateurs Playwright
playwright install chromium
```

### 3. Configurer les variables d'environnement

Copier `.env.example` vers `.env` et remplir les valeurs :

```bash
cp .env.example .env
```

Éditer `.env` :

```bash
# Configuration S3 / MinIO pour le stockage des PDFs
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=your_bucket_name_here

# Pour MinIO ou autre S3-compatible: spécifier l'URL
# Exemples: http://localhost:9000 ou https://minio.example.com
# Laisser vide pour AWS S3 standard
S3_ENDPOINT_URL=https://minio.example.com

# Configuration du scraper
SCRAPE_DELAY_SECONDS=2
MAX_CONCURRENT_PAGES=5
MAX_PAGES_TO_SCRAPE=0  # 0 = toutes les pages
```

### 4. Configurer GitHub Secrets (pour l'automatisation)

**Option A - Secrets au niveau du repository (recommandé pour débuter)** :

Dans votre repository GitHub, aller dans `Settings > Secrets and variables > Actions > Repository secrets` et ajouter :

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `S3_ENDPOINT_URL` (laisser vide pour AWS S3, ou votre URL MinIO, ex: `https://minio.example.com`)

**Option B - Créer un Environment (recommandé pour la production)** :

1. Dans votre repository : `Settings > Environments > New environment`
2. Nommez-le `production`
3. Ajoutez les mêmes 5 secrets dans cet environnement
4. Dans `.github/workflows/daily_scrape.yml`, décommentez la ligne `# environment: production`
5. (Optionnel) Configurez des protections : approbation manuelle, restrictions de branches, etc.

**Note pour MinIO** : Le scraper supporte nativement MinIO et autres services compatibles S3. Il suffit de spécifier votre endpoint dans `S3_ENDPOINT_URL`. Consultez [MINIO_SETUP.md](MINIO_SETUP.md) pour un guide complet de configuration MinIO.

## 💻 Utilisation

> 📖 **Guide complet de test** : Consultez [TESTING.md](TESTING.md) pour un guide détaillé des différentes méthodes de test

### Exécution manuelle

```bash
cd src
python scraper.py
```

### Mode test (DRY_RUN)

Pour tester le scraper sans uploader vers S3 :

```bash
export DRY_RUN=true
export MAX_PAGES_TO_SCRAPE=1  # Limiter à 1 page pour les tests
cd src
python scraper.py
```

Le mode DRY_RUN :
- Ne nécessite pas de credentials S3
- Simule l'upload des PDFs
- Enregistre quand même les métadonnées dans le CSV
- Affiche `[DRY_RUN]` dans les logs

### Exécution automatique

Le GitHub Action s'exécute automatiquement tous les jours à 6h du matin (heure de Paris).

### Test avec GitHub Actions (mode dry-run)

Pour tester le scraper sans uploader vers S3 :

1. Allez dans l'onglet **Actions** de votre repo GitHub
2. Sélectionnez **"Test Scraper (Dry Run)"** dans la liste des workflows
3. Cliquez sur **"Run workflow"**
4. Configurez les paramètres :
   - **max_pages** : `1` (nombre de pages à scraper)
   - **dry_run** : `true` (pas d'upload S3 réel)
   - **max_concurrent** : `3` (pages en parallèle)
5. Cliquez sur **"Run workflow"** (bouton vert)

Le workflow va :
- ✅ Scraper 1 page de résultats
- ✅ Simuler l'upload des PDFs (pas d'upload réel)
- ✅ Afficher un résumé dans l'interface GitHub
- ✅ Uploader les logs et le CSV comme artefacts (téléchargeables pendant 7 jours)

### Lancement manuel du scraping complet

Vous pouvez aussi lancer manuellement le scraping complet depuis l'interface GitHub :
1. Aller dans l'onglet `Actions`
2. Sélectionner `Daily Scrape of Paris Arrêtés`
3. Cliquer sur `Run workflow`

## 📁 Structure des données

### CSV (`data/arretes.csv`)

Colonnes :
- `numero_arrete` : Numéro unique (ex: "2025 T 17858")
- `titre` : Titre complet de l'arrêté
- `autorite_responsable` : Ex: "Direction de la Voirie et des Déplacements"
- `signataire` : Nom du signataire
- `date_publication` : Date de publication au BOVP
- `date_signature` : Date de signature de l'arrêté
- `poids_pdf_ko` : Taille du PDF en Ko
- `explnum_id` : ID interne du document dans le système BOVP
- `pdf_s3_url` : URL S3 du PDF (`s3://bucket/arretes/2025/2025_T_17858_abc12345.pdf`)
- `date_scrape` : Date et heure du scraping (ISO 8601)

### S3

Les PDFs sont organisés par année :
```
s3://your-bucket/arretes/
├── 2025/
│   ├── 2025_T_17858_a1b2c3d4.pdf
│   ├── 2025_T_17859_b2c3d4e5.pdf
│   └── ...
├── 2024/
│   └── ...
```

Le hash MD5 (8 premiers caractères) est ajouté au nom de fichier pour éviter les duplicatas.

## ⚙️ Configuration avancée

### Limiter le scraping

Pour tester ou limiter le nombre de pages scrapées :

```bash
export MAX_PAGES_TO_SCRAPE=5  # Scraper seulement les 5 premières pages
python src/scraper.py
```

### Ajuster la vitesse

Le site BOVP est lent. Les délais par défaut sont :

- `SCRAPE_DELAY_SECONDS=2` : Délai entre chaque requête
- `MAX_CONCURRENT_PAGES=5` : Nombre de pages ouvertes en parallèle

Vous pouvez augmenter ces valeurs si vous rencontrez des timeouts.

### Logs

Les logs sont disponibles :
- En console pendant l'exécution
- Dans `src/scraper.log`
- Dans les artifacts GitHub Actions (conservés 30 jours)

## 🔧 Dépendances

- **Python 3.11+**
- **uv** : Gestionnaire de paquets ultra-rapide (recommandé) - [Pourquoi uv ?](docs/UV.md)
- **Playwright** : Navigateur headless pour JavaScript
- **BeautifulSoup4** : Parsing HTML
- **Pandas** : Gestion CSV
- **Boto3** : Upload S3
- **python-dotenv** : Variables d'environnement

## 📊 Statistiques

Au 24 octobre 2025, le site BOVP contient environ **22 420 arrêtés** dans la catégorie "Voirie et déplacements".

## 🐛 Problèmes connus

1. **Site lent** : Le site BOVP peut être très lent. Les timeouts sont configurés à 60 secondes.
2. **Téléchargement PDF** : Certains PDFs peuvent être inaccessibles (document retiré, erreur serveur). Dans ce cas, le scraper enregistre `ERROR: PDF non téléchargé` dans le CSV.
3. **Rate limiting** : Si trop de requêtes sont faites rapidement, le site peut bloquer temporairement. Ajustez `SCRAPE_DELAY_SECONDS`.

## 📝 Licence

Ce projet est sous licence MIT.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## ⚠️ Avertissement

Ce scraper est conçu pour un usage éducatif et de recherche. Assurez-vous de respecter les conditions d'utilisation du site BOVP et les lois en vigueur concernant le scraping de données publiques.

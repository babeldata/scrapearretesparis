# Guide de Test du Scraper

Ce guide explique comment tester le scraper en toute sécurité avant de le déployer en production.

## 🧪 Méthodes de test disponibles

### 1. Test local avec DRY_RUN (recommandé pour débuter)

**Avantages** :
- ✅ Pas besoin de credentials S3/MinIO
- ✅ Rapide et sûr
- ✅ Voir les logs en temps réel

**Comment faire** :

```bash
# 1. Configurer les variables
export DRY_RUN=true
export MAX_PAGES_TO_SCRAPE=1

# 2. Lancer le scraper
cd src
python scraper.py

# 3. Vérifier les résultats
cat ../data/arretes.csv
cat scraper.log
```

**Ce qui se passe** :
- Le scraper va scraper 1 page (environ 50 arrêtés)
- Les PDFs seront "téléchargés" mais pas uploadés
- Les métadonnées seront enregistrées dans `data/arretes.csv`
- Les logs montreront `[DRY_RUN]` pour les uploads simulés

---

### 2. Test avec GitHub Actions (sans toucher à MinIO)

**Avantages** :
- ✅ Teste l'environnement de production
- ✅ Pas besoin d'installer localement
- ✅ Logs et artifacts téléchargeables
- ✅ Mode DRY_RUN activé par défaut

**Comment faire** :

#### Étape 1 : Configurer les secrets (minimum)

Dans `Settings > Secrets > Actions`, ajoutez au minimum :

```
AWS_ACCESS_KEY_ID = dummy_value
AWS_SECRET_ACCESS_KEY = dummy_value
AWS_REGION = us-east-1
S3_BUCKET_NAME = dummy_bucket
S3_ENDPOINT_URL = (laisser vide ou dummy)
```

> ⚠️ En mode DRY_RUN, ces valeurs ne sont pas utilisées mais doivent exister

#### Étape 2 : Lancer le workflow de test

1. Allez sur votre repository GitHub
2. Cliquez sur l'onglet **"Actions"**
3. Dans la liste de gauche, cliquez sur **"Test Scraper (Dry Run)"**
4. Cliquez sur le bouton **"Run workflow"** (à droite)
5. Une popup s'ouvre avec 3 paramètres :

```
┌─────────────────────────────────────────────┐
│ Use workflow from: Branch: main        ▼   │
│                                             │
│ Nombre de pages à scraper (0 = toutes)     │
│ ┌─────┐                                     │
│ │  1  │  ← Commencer par 1 page            │
│ └─────┘                                     │
│                                             │
│ Mode DRY_RUN (pas d'upload S3 réel)        │
│ ☑ true     ← Laisser coché                 │
│                                             │
│ Nombre de pages en parallèle                │
│ ┌─────┐                                     │
│ │  3  │  ← 3 est un bon compromis          │
│ └─────┘                                     │
│                                             │
│        [Run workflow]  (bouton vert)        │
└─────────────────────────────────────────────┘
```

6. Cliquez sur **"Run workflow"** (bouton vert)

#### Étape 3 : Voir les résultats

Le workflow apparaît dans la liste avec un cercle jaune 🟡 (en cours).

Cliquez dessus pour voir :
- Les logs en temps réel
- La progression du scraping
- Les messages `[DRY_RUN]` confirmant qu'aucun upload n'est fait

#### Étape 4 : Télécharger les résultats

Une fois terminé (✅ vert ou ❌ rouge) :

1. Descendez en bas de la page
2. Section **"Artifacts"** :
   - `test-scraper-logs-XXX` : Les logs complets
   - `test-csv-XXX` : Le CSV avec les métadonnées

3. Cliquez sur un artifact pour le télécharger (zip)

#### Étape 5 : Analyser les résultats

**Dans les logs** (`test-scraper-logs-XXX.zip`), cherchez :

```
✅ Bon signe :
- "=== Démarrage du scraper d'arrêtés ==="
- "Lancement du navigateur..."
- "Page 1: X résultats trouvés"
- "[DRY_RUN] Simulation upload: arretes/2025/..."
- "✓ Arrêté 2025 T 17858 traité avec succès"

❌ Problèmes potentiels :
- "TimeoutError" → Le site est trop lent, augmenter les timeouts
- "Impossible de télécharger le PDF" → Problème avec la méthode de download
- "Erreur lors du parsing" → Structure HTML changée
```

**Dans le CSV** (`test-csv-XXX.zip`) :

Ouvrez avec Excel/LibreOffice et vérifiez :
- Les colonnes sont bien remplies
- Les numéros d'arrêtés sont corrects (ex: "2025 T 17858")
- Les URLs S3 sont au bon format (ex: "s3://dummy_bucket/arretes/2025/...")

---

### 3. Test avec upload S3/MinIO réel (avant production)

**Quand utiliser** :
- Après validation du test DRY_RUN
- Pour tester la connexion S3/MinIO
- Pour vérifier les permissions

**Comment faire** :

#### Via GitHub Actions

1. Configurez **vos vrais secrets** S3/MinIO
2. Lancez le workflow **"Test Scraper (Dry Run)"**
3. **Décochez** "Mode DRY_RUN" ❌
4. Gardez **max_pages = 1** (pour ne scraper qu'une page)
5. Lancez

Le scraper va :
- Scraper 1 page réellement
- Télécharger les PDFs
- Les uploader vers votre S3/MinIO
- Enregistrer les métadonnées dans le CSV

#### Via local

```bash
# 1. Configurer avec VOS vrais credentials
cp .env.example .env
nano .env  # Remplir avec vos vrais credentials

# Exemple pour MinIO :
# AWS_ACCESS_KEY_ID=minioadmin
# AWS_SECRET_ACCESS_KEY=minioadmin
# S3_BUCKET_NAME=paris-arretes
# S3_ENDPOINT_URL=https://minio.example.com

# 2. Activer les uploads réels
export DRY_RUN=false
export MAX_PAGES_TO_SCRAPE=1

# 3. Lancer
cd src
python scraper.py

# 4. Vérifier sur MinIO
# Ouvrez l'interface MinIO et vérifiez que les PDFs sont bien uploadés
```

---

## 🐛 Troubleshooting

### Le workflow échoue avec "Configuration invalide"

**Cause** : Les secrets GitHub ne sont pas configurés

**Solution** :
- Allez dans `Settings > Secrets > Actions`
- Ajoutez au minimum les 5 secrets (même avec des valeurs dummy en mode DRY_RUN)

### Erreur Playwright : "Package 'libasound2' has no installation candidate"

**Cause** : Incompatibilité entre Playwright et Ubuntu 24.04 (ubuntu-latest)

**Solution** : Ce problème est déjà corrigé dans les workflows (on utilise `ubuntu-22.04`)

Si vous rencontrez cette erreur sur vos propres workflows :
```yaml
jobs:
  scrape:
    runs-on: ubuntu-22.04  # ← Changer de ubuntu-latest à ubuntu-22.04
```

**Explication** : Playwright n'est pas encore totalement compatible avec Ubuntu 24.04. Les paquets système `libasound2`, `libffi7` et `libx264-163` ont été renommés ou supprimés dans cette version.

### TimeoutError sur le téléchargement PDF

**Cause** : Le site BOVP est lent ou le PDF n'est pas accessible

**Solution** :
- Augmenter les timeouts dans `scraper.py` (ligne ~XXX)
- Vérifier que l'URL de la visionneuse fonctionne manuellement

### Aucun arrêté trouvé

**Cause** : La structure HTML du site a changé

**Solution** :
- Vérifier l'URL de recherche : https://bovp.apps.paris.fr/index.php?lvl=search_segment&id=121
- Vérifier les sélecteurs CSS dans `_parse_arrete_from_element()`
- Ouvrir une issue sur GitHub

### CSV vide après le test

**Cause** : Tous les arrêtés étaient déjà présents

**Solution** :
- Vider le fichier `data/arretes.csv` avant le test
- Ou vérifier les logs pour voir si des doublons ont été détectés

---

## ✅ Checklist avant production

Avant de lancer le scraping complet en production :

- [ ] Test local DRY_RUN réussi (1 page)
- [ ] Test GitHub Actions DRY_RUN réussi (1 page)
- [ ] Test upload S3/MinIO réel réussi (1 page)
- [ ] PDFs visibles dans le bucket S3/MinIO
- [ ] CSV correctement formaté
- [ ] Secrets GitHub configurés (production)
- [ ] Environment GitHub créé (optionnel mais recommandé)
- [ ] Délai entre requêtes adapté (pas de ban du site)
- [ ] Logs lisibles et sans erreur critique

Une fois tous les tests passés, vous pouvez :
- Lancer le workflow complet manuellement (`MAX_PAGES_TO_SCRAPE=0`)
- Ou laisser le workflow quotidien se lancer automatiquement

---

## 📊 Estimation de durée

Pour référence, voici les durées approximatives :

| Pages | Arrêtés | Durée estimée | Mode |
|-------|---------|---------------|------|
| 1 | ~50 | 3-5 min | DRY_RUN |
| 1 | ~50 | 5-10 min | Upload S3 |
| 10 | ~500 | 30-60 min | Upload S3 |
| 100 | ~5000 | 5-10h | Upload S3 |
| Toutes (~450) | ~22,400 | 20-40h | Upload S3 |

> ⚠️ Le scraping complet prendra **très longtemps** en raison du délai entre requêtes et de la lenteur du site BOVP.

**Recommandation** : Commencez par scraper les 50 premières pages (~2500 arrêtés les plus récents) puis augmentez progressivement.

---

## 🔄 Test de mise à jour quotidienne

Pour tester que le système détecte bien les nouveaux arrêtés :

1. Lancez un premier scraping (1 page)
2. Vérifiez le CSV : 50 arrêtés
3. Relancez le scraping (même page)
4. Vérifiez les logs : "Arrêté XXX déjà présent, ignoré"
5. Vérifiez le CSV : toujours 50 arrêtés (pas de doublons)

✅ Si aucun doublon n'est créé, le système fonctionne correctement !

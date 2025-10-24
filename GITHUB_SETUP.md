# Guide de Configuration GitHub

Ce document explique les différentes façons de configurer les secrets pour le scraper.

## 🔐 Option 1 : Secrets au niveau du Repository

**👍 Recommandé pour : Débuter rapidement, projets simples**

### Avantages
- ✅ Configuration rapide (5 minutes)
- ✅ Pas besoin de configuration supplémentaire
- ✅ Fonctionne immédiatement

### Inconvénients
- ❌ Moins de contrôle sur les déploiements
- ❌ Pas de séparation dev/staging/production
- ❌ Tous les workflows ont accès aux secrets

### Comment configurer

1. Allez sur votre repository GitHub
2. `Settings` → `Secrets and variables` → `Actions` → `Repository secrets`
3. Cliquez sur `New repository secret`
4. Ajoutez les 5 secrets :

| Nom du secret | Exemple de valeur | Description |
|---------------|-------------------|-------------|
| `AWS_ACCESS_KEY_ID` | `AKIAIOSFODNN7EXAMPLE` | Clé d'accès AWS/MinIO |
| `AWS_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` | Clé secrète AWS/MinIO |
| `AWS_REGION` | `us-east-1` | Région (us-east-1 pour MinIO) |
| `S3_BUCKET_NAME` | `paris-arretes-prod` | Nom du bucket S3/MinIO |
| `S3_ENDPOINT_URL` | `https://minio.example.com` | Endpoint personnalisé (MinIO). Laisser vide pour AWS S3 |

✅ **C'est tout !** Le workflow va automatiquement utiliser ces secrets.

---

## 🏭 Option 2 : Environment GitHub

**👍 Recommandé pour : Production, meilleur contrôle, équipes**

### Avantages
- ✅ **Séparation des environnements** : dev, staging, production
- ✅ **Protections** : Approbation manuelle avant exécution
- ✅ **Restrictions** : Limiter à certaines branches
- ✅ **Audit trail** : Historique des déploiements
- ✅ **Secrets isolés** : Par environnement

### Inconvénients
- ❌ Configuration un peu plus longue
- ❌ Nécessite de modifier le workflow

### Comment configurer

#### Étape 1 : Créer l'environment

1. Allez sur votre repository GitHub
2. `Settings` → `Environments` → `New environment`
3. Nom : `production`
4. Cliquez sur `Configure environment`

#### Étape 2 : Ajouter les secrets à l'environment

Dans l'environment `production`, section `Environment secrets` :

| Nom du secret | Exemple de valeur |
|---------------|-------------------|
| `AWS_ACCESS_KEY_ID` | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | `us-east-1` |
| `S3_BUCKET_NAME` | `paris-arretes-prod` |
| `S3_ENDPOINT_URL` | `https://minio.example.com` (laisser vide pour AWS S3) |

#### Étape 3 : (Optionnel) Configurer les protections

Dans l'environment `production`, vous pouvez configurer :

**Protection rules** :
- ☑️ **Required reviewers** : Exiger l'approbation d'une personne avant chaque run
- ☑️ **Wait timer** : Attendre X minutes avant d'exécuter (prévenir les runs accidentels)
- ☑️ **Deployment branches** : Restreindre à `main` ou d'autres branches spécifiques

Exemple de configuration :
```
✅ Required reviewers: 1 personne (vous-même)
✅ Deployment branches: Selected branches → main
```

#### Étape 4 : Modifier le workflow

Dans `.github/workflows/daily_scrape.yml`, **décommentez** la ligne 15 :

```yaml
jobs:
  scrape:
    runs-on: ubuntu-latest
    environment: production  # ← Décommentez cette ligne
```

✅ **Terminé !** Le workflow va maintenant utiliser l'environment `production`.

---

## 🔄 Créer un environnement de test (optionnel)

Si vous voulez tester le scraper sans toucher à la production :

### 1. Créer un bucket S3 de test

```
paris-arretes-staging
```

### 2. Créer un environment "staging"

- Nom : `staging`
- Secrets : Mêmes clés AWS, mais `S3_BUCKET_NAME=paris-arretes-staging`
- Pas de protections (pour tester facilement)

### 3. Créer un workflow de test

Créez `.github/workflows/test_scrape.yml` :

```yaml
name: Test Scrape (Staging)

on:
  workflow_dispatch:  # Uniquement manuel

jobs:
  scrape:
    runs-on: ubuntu-latest
    environment: staging  # Utilise l'environment staging

    steps:
      # ... même configuration que daily_scrape.yml ...
      - name: Run scraper
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: ${{ secrets.AWS_REGION }}
          S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
          MAX_PAGES_TO_SCRAPE: 5  # Limiter pour les tests
```

---

## 🤔 Quelle option choisir ?

| Critère | Option 1 (Repository) | Option 2 (Environment) |
|---------|----------------------|------------------------|
| **Vitesse de setup** | ⚡ 5 minutes | 🐌 15 minutes |
| **Simplicité** | 😊 Très simple | 🤓 Moyennement simple |
| **Contrôle** | ⚠️ Basique | ✅ Avancé |
| **Séparation dev/prod** | ❌ Non | ✅ Oui |
| **Approbations manuelles** | ❌ Non | ✅ Oui |
| **Recommandé pour** | Débuter, tests | Production, équipes |

### Ma recommandation

1. **Phase de test** (maintenant) : Utilisez **Option 1** (Repository secrets)
   - Plus rapide pour démarrer
   - Facile à configurer
   - Parfait pour valider que tout fonctionne

2. **Mise en production** (après validation) : Migrez vers **Option 2** (Environment)
   - Meilleure sécurité
   - Contrôle des déploiements
   - Séparation test/production

---

## 📞 Besoin d'aide ?

- **Créer une clé AWS IAM** : [Guide AWS](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html)
- **Créer un bucket S3** : [Guide AWS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html)
- **Permissions IAM nécessaires** :
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:PutObject",
          "s3:GetObject",
          "s3:HeadObject"
        ],
        "Resource": "arn:aws:s3:::votre-bucket/*"
      }
    ]
  }
  ```

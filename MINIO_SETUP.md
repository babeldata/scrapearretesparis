# Configuration MinIO

Ce guide explique comment configurer le scraper pour utiliser MinIO au lieu d'AWS S3.

## 🚀 Qu'est-ce que MinIO ?

[MinIO](https://min.io/) est un serveur de stockage d'objets open-source compatible avec l'API S3 d'Amazon. Vous pouvez l'héberger sur votre propre infrastructure.

## ✅ Avantages de MinIO

- ✅ **Auto-hébergé** : Contrôle total de vos données
- ✅ **Compatible S3** : Fonctionne avec tous les outils S3
- ✅ **Gratuit et open-source**
- ✅ **Performant** : Optimisé pour le stockage d'objets
- ✅ **Pas de coûts AWS** : Économisez sur les frais de stockage

## 🔧 Configuration du scraper pour MinIO

### 1. Variables d'environnement

Dans votre fichier `.env` :

```bash
# Credentials MinIO (créés dans l'interface MinIO)
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# Région (peut être n'importe quoi pour MinIO)
AWS_REGION=us-east-1

# Nom du bucket (doit exister dans MinIO)
S3_BUCKET_NAME=paris-arretes

# URL de votre serveur MinIO
S3_ENDPOINT_URL=https://minio.example.com
```

### 2. Formats d'URL supportés

Le scraper supporte plusieurs formats d'endpoint :

```bash
# HTTP (pour développement local)
S3_ENDPOINT_URL=http://localhost:9000

# HTTPS (production)
S3_ENDPOINT_URL=https://minio.example.com

# Avec port personnalisé
S3_ENDPOINT_URL=https://s3.example.com:9000

# IP directe
S3_ENDPOINT_URL=http://192.168.1.100:9000
```

### 3. Créer un bucket dans MinIO

#### Via l'interface web MinIO :

1. Connectez-vous à l'interface MinIO (généralement sur le port 9001)
2. Allez dans **Buckets** → **Create Bucket**
3. Nom du bucket : `paris-arretes`
4. Laissez les options par défaut
5. Cliquez sur **Create**

#### Via la ligne de commande (mc) :

```bash
# Installer le client MinIO
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configurer l'alias
mc alias set myminio https://minio.example.com minioadmin minioadmin

# Créer le bucket
mc mb myminio/paris-arretes

# Vérifier
mc ls myminio/
```

### 4. Créer des credentials MinIO

Pour la production, créez des credentials dédiés au lieu d'utiliser `minioadmin` :

#### Via l'interface web :

1. **Identity** → **Users** → **Create User**
2. Username : `scraper-paris`
3. Générez un mot de passe fort
4. Créez une **Policy** personnalisée :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:HeadObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::paris-arretes/*",
        "arn:aws:s3:::paris-arretes"
      ]
    }
  ]
}
```

5. Assignez cette policy à l'utilisateur `scraper-paris`

#### Via la ligne de commande :

```bash
# Créer une policy
cat > scraper-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:HeadObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::paris-arretes/*",
        "arn:aws:s3:::paris-arretes"
      ]
    }
  ]
}
EOF

# Ajouter la policy
mc admin policy create myminio scraper-policy scraper-policy.json

# Créer l'utilisateur
mc admin user add myminio scraper-paris STRONG_PASSWORD_HERE

# Assigner la policy
mc admin policy attach myminio scraper-policy --user scraper-paris
```

### 5. Configuration GitHub Actions

Dans GitHub, ajoutez ces secrets :

| Secret | Valeur |
|--------|--------|
| `AWS_ACCESS_KEY_ID` | `scraper-paris` |
| `AWS_SECRET_ACCESS_KEY` | Le mot de passe créé |
| `AWS_REGION` | `us-east-1` |
| `S3_BUCKET_NAME` | `paris-arretes` |
| `S3_ENDPOINT_URL` | `https://minio.example.com` |

**⚠️ Important** : Votre serveur MinIO doit être accessible depuis GitHub Actions (IP publique ou VPN).

## 🔒 Sécurité

### Certificat SSL/TLS

Pour la production, utilisez **HTTPS** avec un certificat valide :

1. **Let's Encrypt** (gratuit) :
   ```bash
   # Avec Certbot
   sudo certbot --nginx -d minio.example.com
   ```

2. **Reverse proxy Nginx** :
   ```nginx
   server {
       listen 443 ssl http2;
       server_name minio.example.com;

       ssl_certificate /etc/letsencrypt/live/minio.example.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/minio.example.com/privkey.pem;

       location / {
           proxy_pass http://localhost:9000;
           proxy_set_header Host $http_host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

### Pare-feu

Si votre MinIO est sur un serveur privé, ouvrez les ports nécessaires :

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 9000/tcp  # API MinIO
sudo ufw allow 9001/tcp  # Console MinIO (optionnel)

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --permanent --add-port=9001/tcp
sudo firewall-cmd --reload
```

## 🧪 Test de connexion

Testez la connexion MinIO avec ce script Python :

```python
import boto3
from botocore.exceptions import ClientError

# Configuration
endpoint_url = "https://minio.example.com"
access_key = "scraper-paris"
secret_key = "YOUR_PASSWORD"
bucket_name = "paris-arretes"

# Créer le client
s3 = boto3.client(
    's3',
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name='us-east-1'
)

try:
    # Lister les buckets
    response = s3.list_buckets()
    print("✅ Connexion réussie!")
    print("Buckets disponibles:")
    for bucket in response['Buckets']:
        print(f"  - {bucket['Name']}")

    # Tester l'upload
    s3.put_object(
        Bucket=bucket_name,
        Key='test.txt',
        Body=b'Test de connexion'
    )
    print(f"✅ Upload dans '{bucket_name}' réussi!")

except ClientError as e:
    print(f"❌ Erreur: {e}")
```

Exécutez :

```bash
python test_minio.py
```

## 📊 Monitoring

Vérifiez l'utilisation du bucket :

```bash
# Via mc
mc du myminio/paris-arretes

# Statistiques
mc admin info myminio
```

## 🐛 Troubleshooting

### Erreur : "Connection refused"

- Vérifiez que MinIO est démarré : `sudo systemctl status minio`
- Vérifiez le pare-feu
- Testez avec `curl http://localhost:9000/minio/health/live`

### Erreur : "Access Denied"

- Vérifiez les credentials
- Vérifiez que la policy est bien attachée à l'utilisateur
- Vérifiez que le bucket existe

### Erreur : "SSL Certificate Verify Failed"

Si vous utilisez un certificat auto-signé en développement :

```python
# NE PAS UTILISER EN PRODUCTION
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Dans config.py, ajouter :
import boto3
from botocore.client import Config

s3 = boto3.client(
    's3',
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version='s3v4'),
    verify=False  # Désactiver la vérification SSL (dev uniquement!)
)
```

## 🔄 Migration AWS S3 → MinIO

Si vous avez déjà des données sur AWS S3 :

```bash
# Configurer les deux endpoints
mc alias set aws-s3 https://s3.amazonaws.com ACCESS_KEY SECRET_KEY
mc alias set myminio https://minio.example.com ACCESS_KEY SECRET_KEY

# Copier les données
mc cp --recursive aws-s3/paris-arretes-prod/ myminio/paris-arretes/

# Vérifier
mc ls myminio/paris-arretes/
```

## 📚 Ressources

- [Documentation MinIO](https://min.io/docs/minio/linux/index.html)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html)
- [Boto3 avec MinIO](https://min.io/docs/minio/linux/integrations/aws-cli-with-minio.html)

#!/usr/bin/env python3
"""Test de connexion MinIO."""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL')
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
REGION = os.getenv('AWS_REGION', 'us-east-1')

print("=== Test de connexion MinIO ===\n")
print(f"Endpoint: {ENDPOINT_URL}")
print(f"Bucket: {BUCKET_NAME}")
print(f"Region: {REGION}")
print(f"Access Key: {ACCESS_KEY[:10]}..." if ACCESS_KEY else "Access Key: None")
print()

# Créer le client S3
try:
    s3 = boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=REGION,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
    )
    print("✅ Client S3 créé avec succès\n")
except Exception as e:
    print(f"❌ Erreur création client S3: {e}\n")
    exit(1)

# Test 1: Lister les buckets
print("Test 1: Lister les buckets...")
try:
    response = s3.list_buckets()
    print(f"✅ Buckets disponibles: {[b['Name'] for b in response['Buckets']]}\n")
except ClientError as e:
    print(f"❌ Erreur: {e}\n")

# Test 2: Vérifier si le bucket existe
print(f"Test 2: Vérifier si le bucket '{BUCKET_NAME}' existe...")
try:
    s3.head_bucket(Bucket=BUCKET_NAME)
    print(f"✅ Le bucket '{BUCKET_NAME}' existe\n")
except ClientError as e:
    if e.response['Error']['Code'] == '404':
        print(f"❌ Le bucket '{BUCKET_NAME}' n'existe pas\n")
    else:
        print(f"❌ Erreur: {e}\n")

# Test 3: Essayer d'uploader un petit fichier de test
print("Test 3: Upload d'un fichier test...")
try:
    test_content = b"Test content from scraper"
    test_key = "test/test_upload.txt"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=test_key,
        Body=test_content,
        ContentType='text/plain'
    )
    print(f"✅ Upload réussi: {test_key}\n")

    # Test 4: Vérifier que le fichier existe
    print("Test 4: Vérifier que le fichier existe...")
    s3.head_object(Bucket=BUCKET_NAME, Key=test_key)
    print(f"✅ Le fichier existe sur MinIO\n")

    # Nettoyage
    print("Nettoyage: Suppression du fichier test...")
    s3.delete_object(Bucket=BUCKET_NAME, Key=test_key)
    print(f"✅ Fichier supprimé\n")

except ClientError as e:
    print(f"❌ Erreur lors de l'upload: {e}\n")
    print(f"Code erreur: {e.response['Error']['Code']}")
    print(f"Message: {e.response['Error']['Message']}\n")

print("=== Fin du test ===")

"""Gestion de l'upload des PDFs vers S3."""
import boto3
import logging
from pathlib import Path
from typing import Optional
import hashlib
from botocore.exceptions import ClientError

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    DRY_RUN
)

logger = logging.getLogger(__name__)


class S3Uploader:
    """Classe pour gérer l'upload des PDFs vers S3."""

    def __init__(self):
        """Initialise le client S3 ou MinIO."""
        self.dry_run = DRY_RUN
        self.bucket_name = S3_BUCKET_NAME or "dry-run-bucket"
        self.endpoint_url = S3_ENDPOINT_URL

        if not self.dry_run:
            # Configuration du client S3/MinIO
            client_config = {
                'aws_access_key_id': AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
                'region_name': AWS_REGION
            }

            # Ajouter l'endpoint_url si spécifié (pour MinIO ou S3 compatible)
            if self.endpoint_url:
                client_config['endpoint_url'] = self.endpoint_url
                logger.info(f"Utilisation de l'endpoint S3 personnalisé: {self.endpoint_url}")
            else:
                logger.info("Utilisation d'AWS S3")

            self.s3_client = boto3.client('s3', **client_config)
        else:
            self.s3_client = None
            logger.info("Mode DRY_RUN activé: aucun upload S3 ne sera effectué")

    def upload_pdf(self, pdf_content: bytes, numero_arrete: str) -> Optional[str]:
        """
        Upload un PDF vers S3.

        Args:
            pdf_content: Contenu binaire du PDF
            numero_arrete: Numéro de l'arrêté (ex: "2025 T 17858")

        Returns:
            URL S3 du fichier uploadé, ou None si erreur
        """
        try:
            # Nettoyer le numéro d'arrêté pour créer un nom de fichier valide
            safe_filename = numero_arrete.replace(" ", "_").replace("/", "-")

            # Créer un hash du contenu pour éviter les duplicatas
            content_hash = hashlib.md5(pdf_content).hexdigest()[:8]

            # Chemin S3: arretes/2025/2025_T_17858_a1b2c3d4.pdf
            year = numero_arrete.split()[0] if " " in numero_arrete else "unknown"
            s3_key = f"arretes/{year}/{safe_filename}_{content_hash}.pdf"

            # Mode DRY_RUN: simuler l'upload
            if self.dry_run:
                logger.info(f"[DRY_RUN] Simulation upload: {s3_key} ({len(pdf_content)} bytes)")
                return self._get_s3_url(s3_key)

            # Vérifier si le fichier existe déjà
            if self._file_exists(s3_key):
                logger.info(f"PDF déjà existant sur S3: {s3_key}")
                return self._get_s3_url(s3_key)

            # Upload vers S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=pdf_content,
                ContentType='application/pdf',
                Metadata={
                    'numero_arrete': numero_arrete,
                    'content_hash': content_hash
                }
            )

            logger.info(f"PDF uploadé avec succès: {s3_key}")
            return self._get_s3_url(s3_key)

        except ClientError as e:
            logger.error(f"Erreur S3 lors de l'upload pour {numero_arrete}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'upload pour {numero_arrete}: {e}")
            return None

    def _file_exists(self, s3_key: str) -> bool:
        """Vérifie si un fichier existe déjà sur S3."""
        if self.dry_run:
            return False

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def _get_s3_url(self, s3_key: str) -> str:
        """Retourne l'URL S3 d'un fichier."""
        return f"s3://{self.bucket_name}/{s3_key}"

    def get_public_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Génère une URL présignée pour accéder temporairement au PDF.

        Args:
            s3_key: Clé S3 du fichier
            expiration: Durée de validité en secondes (défaut: 1h)

        Returns:
            URL présignée ou None si erreur
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Erreur lors de la génération de l'URL présignée: {e}")
            return None

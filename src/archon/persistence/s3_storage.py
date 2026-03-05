"""
S3 Storage - Persistence for generated project artifacts.
"""

import os
import boto3
from pathlib import Path
from typing import Optional, List, Dict, Any
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class S3Storage:
    """
    Handles artifact storage in Amazon S3.
    Organizes files under project_id/artifacts/.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or os.getenv("AWS_ARTIFACT_BUCKET", "archon-artifacts")
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-south-1")

        if not self.bucket_name:
            logger.warning("AWS_ARTIFACT_BUCKET not set. S3 storage disabled.")
            self.client = None
            return

        session_kwargs = {"region_name": self.region_name}
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        try:
            self.client = boto3.client("s3", **session_kwargs)
            # Verify bucket exists
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 Storage initialized with bucket: {self.bucket_name}")
        except Exception:
            logger.info("S3 disabled (local mode)")
            self.client = None

    async def upload_file(
        self, local_path: str, project_id: str, remote_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload a local file to S3.

        Args:
            local_path: Absolute path to the local file
            project_id: ID of the project (folder name in S3)
            remote_name: Optional name for the file in S3 (defaults to local basename)

        Returns:
            S3 URL if successful, None otherwise
        """
        if not self.client:
            return None

        local_file = Path(local_path)
        if not local_file.exists():
            logger.error(f"Local file does not exist: {local_path}")
            return None

        file_name = remote_name or local_file.name
        s3_key = f"{project_id}/artifacts/{file_name}"

        try:
            logger.info(f"Uploading {local_path} to s3://{self.bucket_name}/{s3_key}")

            # Note: boto3 is synchronous, wrapping for consistency
            self.client.upload_file(
                Filename=str(local_file),
                Bucket=self.bucket_name,
                Key=s3_key,
                ExtraArgs={"ACL": "public-read"} if os.getenv("S3_PUBLIC_ARTIFACTS") == "1" else {},
            )

            # Construct URL
            url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{s3_key}"
            return url

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return None

    async def upload_content(self, content: str, project_id: str, file_name: str) -> Optional[str]:
        """
        Upload string content directly to S3, bypassing container filesystem.

        Args:
            content: String content to upload
            project_id: ID of the project (folder name in S3)
            file_name: Name of the file in S3

        Returns:
            S3 URL if successful, None otherwise
        """
        if not self.client:
            return None

        s3_key = f"{project_id}/artifacts/{file_name}"

        try:
            logger.info(f"Uploading content directly to s3://{self.bucket_name}/{s3_key}")

            # Note: boto3 is synchronous, wrapping for consistency
            self.client.put_object(
                Body=content.encode("utf-8") if isinstance(content, str) else content,
                Bucket=self.bucket_name,
                Key=s3_key,
                ACL="public-read" if os.getenv("S3_PUBLIC_ARTIFACTS") == "1" else "private",
            )

            # Construct URL
            url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{s3_key}"
            return url

        except Exception as e:
            logger.error(f"S3 content upload failed: {e}")
            return None

    async def list_artifacts(self, project_id: str) -> List[str]:
        """List all artifacts for a project."""
        if not self.client:
            return []

        prefix = f"{project_id}/artifacts/"
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            artifacts = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    key = obj["Key"]
                    url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{key}"
                    artifacts.append(url)
            return artifacts
        except Exception as e:
            logger.error(f"S3 list failed: {e}")
            return []

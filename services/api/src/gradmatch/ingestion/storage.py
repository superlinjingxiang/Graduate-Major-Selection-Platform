from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import boto3
from botocore.config import Config
from django.conf import settings


class ArtifactStore(Protocol):
    def put(self, storage_key: str, body: bytes, content_type: str) -> None: ...


class S3ArtifactStore:
    def __init__(self) -> None:
        self.client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(retries={"max_attempts": 3}),
        )

    def put(self, storage_key: str, body: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=storage_key,
            Body=body,
            ContentType=content_type,
        )


@dataclass(frozen=True)
class StoredArtifact:
    body: bytes
    content_type: str


class InMemoryArtifactStore:
    def __init__(self) -> None:
        self.objects: dict[str, StoredArtifact] = {}

    def put(self, storage_key: str, body: bytes, content_type: str) -> None:
        self.objects[storage_key] = StoredArtifact(body=body, content_type=content_type)

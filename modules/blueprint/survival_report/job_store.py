"""Short-lived, owner-isolated persistence for preview jobs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import ReportBatch


_JOB_ID = re.compile(r"^[0-9a-f]{32}$")


class JobNotFound(LookupError):
    """Used for both missing and unauthorized jobs to avoid information leaks."""


@dataclass(frozen=True)
class StoredJob:
    job_id: str
    created_at: datetime
    batch: ReportBatch


class JobStore:
    def __init__(self, root: Path | None = None, ttl_seconds: int = 3600):
        self.root = (root or Path(tempfile.gettempdir()) / "cancer_registry_survival_report").resolve()
        self.ttl_seconds = int(ttl_seconds)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _owner_digest(owner_id: str) -> str:
        return hashlib.sha256(str(owner_id).encode("utf-8")).hexdigest()

    def _job_dir(self, job_id: str) -> Path:
        if not _JOB_ID.fullmatch(job_id):
            raise JobNotFound("找不到作業。")
        path = (self.root / job_id).resolve()
        if path.parent != self.root:
            raise JobNotFound("找不到作業。")
        return path

    @staticmethod
    def _atomic_json(path: Path, value: dict) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    def create(self, owner_id: str, batch: ReportBatch) -> str:
        job_id = uuid.uuid4().hex
        job_dir = self._job_dir(job_id)
        job_dir.mkdir(parents=False, exist_ok=False)
        created_at = datetime.now(timezone.utc)
        self._atomic_json(
            job_dir / "meta.json",
            {
                "owner": self._owner_digest(owner_id),
                "created_at": created_at.isoformat(),
            },
        )
        self._atomic_json(job_dir / "batch.json", batch.to_dict())
        return job_id

    def load(self, owner_id: str, job_id: str) -> StoredJob:
        job_dir = self._job_dir(job_id)
        try:
            with (job_dir / "meta.json").open(encoding="utf-8") as stream:
                metadata = json.load(stream)
            if metadata.get("owner") != self._owner_digest(owner_id):
                raise JobNotFound("找不到作業。")
            with (job_dir / "batch.json").open(encoding="utf-8") as stream:
                batch = ReportBatch.from_dict(json.load(stream))
            created_at = datetime.fromisoformat(metadata["created_at"])
        except JobNotFound:
            raise
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
            raise JobNotFound("找不到作業。") from error
        return StoredJob(job_id=job_id, created_at=created_at, batch=batch)

    def save_batch(self, owner_id: str, job_id: str, batch: ReportBatch) -> None:
        stored = self.load(owner_id, job_id)
        self._atomic_json(self._job_dir(stored.job_id) / "batch.json", batch.to_dict())

    @staticmethod
    def _remove_known_files(job_dir: Path) -> None:
        for filename in ("batch.json.tmp", "meta.json.tmp", "batch.json", "meta.json"):
            path = job_dir / filename
            if path.exists():
                path.unlink()
        try:
            job_dir.rmdir()
        except (FileNotFoundError, OSError):
            pass

    def delete(self, owner_id: str, job_id: str) -> None:
        stored = self.load(owner_id, job_id)
        self._remove_known_files(self._job_dir(stored.job_id))

    def cleanup_expired(self, now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        removed = 0
        for job_dir in self.root.iterdir():
            if not job_dir.is_dir() or not _JOB_ID.fullmatch(job_dir.name):
                continue
            try:
                with (job_dir / "meta.json").open(encoding="utf-8") as stream:
                    metadata = json.load(stream)
                created_at = datetime.fromisoformat(metadata["created_at"])
                age = (current - created_at).total_seconds()
            except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
                age = self.ttl_seconds + 1
            if age > self.ttl_seconds:
                self._remove_known_files(job_dir)
                removed += 1
        return removed

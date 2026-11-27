"""Retention sweep for transient output/upload/export files (項目 12).

Dependency-free on purpose (only os/time/pathlib) so it can be unit-tested in
isolation and reused by any module without pulling the app import chain.

Safety: only regular files matching the glob are removed, never directories;
a missing root is a no-op; files modified within the TTL are kept, which is the
in-flight protection — an export/upload still being written has a recent mtime
and is never deleted. Per-file errors (locked/vanished) are skipped, not raised.
"""
from __future__ import annotations

import time
from pathlib import Path


def sweep_expired_files(root, ttl_seconds, *, glob: str = "*", now: float | None = None) -> int:
    """Delete files under ``root`` matching ``glob`` older than ``ttl_seconds``.

    ``glob`` is evaluated relative to ``root`` (e.g. ``"*/*.json"`` for the
    per-owner export-draft layout). ``now`` (epoch seconds) is injectable for
    deterministic tests. Returns the number of files removed.
    """
    root = Path(root)
    if not root.exists():
        return 0
    root_resolved = root.resolve()
    cutoff = (time.time() if now is None else now) - float(ttl_seconds)
    removed = 0
    for path in root.glob(glob):
        try:
            resolved = path.resolve()
            # Containment guard: never touch anything outside root. Defends
            # against a traversal glob ("../*") or a symlink escaping the tree.
            if resolved != root_resolved and root_resolved not in resolved.parents:
                continue
            if resolved.is_file() and resolved.stat().st_mtime < cutoff:
                resolved.unlink()
                removed += 1
        except OSError:
            continue  # locked, vanished, or permission issue — leave it for next sweep
    return removed

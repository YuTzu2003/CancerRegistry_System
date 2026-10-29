"""Create one native report download or a ZIP containing several report decks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

from .models import ReportDeck
from .pptx_exporter import build_presentation


PPTX_MIMETYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
ZIP_MIMETYPE = "application/zip"
_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class DownloadArtifact:
    content: BytesIO
    mimetype: str
    filename: str


def _safe_filename(value: str) -> str:
    cleaned = _INVALID_FILENAME.sub("_", value).strip(" .")
    return cleaned or "存活率報表"


def _filename_hospital_name(name: str) -> str:
    normalized = name.strip()
    return "台大雲林" if normalized == "本院" else normalized


def _deck_filename(deck: ReportDeck, suffix: str) -> str:
    hospital = "、".join(
        _filename_hospital_name(name) for name in deck.hospital_names
    ) or "未命名醫院"
    return _safe_filename(
        f"{deck.period_start}-{deck.period_end}_{hospital}_存活率報表{suffix}"
    )


def _unique_name(name: str, used: set[str]) -> str:
    if name.casefold() not in used:
        used.add(name.casefold())
        return name
    path = Path(name)
    index = 2
    while True:
        candidate = f"{path.stem}_{index}{path.suffix}"
        if candidate.casefold() not in used:
            used.add(candidate.casefold())
            return candidate
        index += 1


def _package(
    decks: Sequence[ReportDeck],
    suffix: str,
    native_mimetype: str,
    archive_name: str,
    builder: Callable[[ReportDeck], BytesIO],
) -> DownloadArtifact:
    selected = list(decks)
    if not selected:
        raise ValueError("沒有已選取的 PPT。")
    if len(selected) == 1:
        deck = selected[0]
        return DownloadArtifact(builder(deck), native_mimetype, _deck_filename(deck, suffix))

    output = BytesIO()
    used: set[str] = set()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for deck in selected:
            name = _unique_name(_deck_filename(deck, suffix), used)
            archive.writestr(name, builder(deck).getvalue())
    output.seek(0)
    return DownloadArtifact(output, ZIP_MIMETYPE, archive_name)


def build_pptx_download(
    decks: Sequence[ReportDeck],
    template_path: Path,
) -> DownloadArtifact:
    return _package(
        decks,
        ".pptx",
        PPTX_MIMETYPE,
        "存活率報表.zip",
        lambda deck: build_presentation(deck, template_path),
    )

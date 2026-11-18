"""Create one native report download or a ZIP containing several report decks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

from .models import ReportBatch, ReportDeck
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


def _comparison_filename(base: ReportDeck, comparison: ReportDeck) -> str:
    hospital = "、".join(
        _filename_hospital_name(name) for name in base.hospital_names
    ) or "未命名醫院"
    return _safe_filename(
        f"{base.period_start}-{base.period_end}_vs_"
        f"{comparison.period_start}-{comparison.period_end}_"
        f"{hospital}_存活率比較報表.pptx"
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
    batch: ReportBatch,
    template_path: Path,
) -> DownloadArtifact:
    if batch.year_comparison.enabled:
        comparison_decks = batch.comparison_decks
        if not comparison_decks:
            raise ValueError("找不到年份比較所需的期間。")
        base, comparison = comparison_decks
        return DownloadArtifact(
            build_presentation(
                base,
                template_path,
                comparison_deck=comparison,
            ),
            PPTX_MIMETYPE,
            _comparison_filename(base, comparison),
        )
    return _package(
        batch.selected_decks,
        ".pptx",
        PPTX_MIMETYPE,
        "存活率報表.zip",
        lambda deck: build_presentation(deck, template_path),
    )

"""Stable, JSON-serializable domain objects for survival reports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SourceFormat(str, Enum):
    OOXML = "ooxml"
    BIFF = "biff"
    HTML = "html"


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


@dataclass(frozen=True)
class ParseIssue:
    code: str
    message: str
    severity: IssueSeverity
    source_file: str = ""
    source_row: int | None = None
    table_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "source_file": self.source_file,
            "source_row": self.source_row,
            "table_id": self.table_id,
        }
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ParseIssue":
        return cls(
            code=value["code"],
            message=value["message"],
            severity=IssueSeverity(value["severity"]),
            source_file=value.get("source_file", ""),
            source_row=value.get("source_row"),
            table_id=value.get("table_id"),
        )


@dataclass(frozen=True)
class SurvivalEstimate:
    rate: Decimal | None = None
    ci_low: Decimal | None = None
    ci_high: Decimal | None = None
    value_status: str = "missing"

    @classmethod
    def unavailable(cls, status: str = "missing") -> "SurvivalEstimate":
        return cls(value_status=status)

    @property
    def available(self) -> bool:
        return self.rate is not None and self.value_status == "available"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rate": str(self.rate) if self.rate is not None else None,
            "ci_low": str(self.ci_low) if self.ci_low is not None else None,
            "ci_high": str(self.ci_high) if self.ci_high is not None else None,
            "value_status": self.value_status,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SurvivalEstimate":
        return cls(
            rate=_decimal(value.get("rate")),
            ci_low=_decimal(value.get("ci_low")),
            ci_high=_decimal(value.get("ci_high")),
            value_status=value.get("value_status", "missing"),
        )


@dataclass(frozen=True)
class AnnualObservation:
    follow_up_year: int
    analyzable_count: int | None
    censored_count: int | None
    death_count: int | None
    observed: SurvivalEstimate
    source_row: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "follow_up_year": self.follow_up_year,
            "analyzable_count": self.analyzable_count,
            "censored_count": self.censored_count,
            "death_count": self.death_count,
            "observed": self.observed.to_dict(),
            "source_row": self.source_row,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AnnualObservation":
        return cls(
            follow_up_year=int(value["follow_up_year"]),
            analyzable_count=value.get("analyzable_count"),
            censored_count=value.get("censored_count"),
            death_count=value.get("death_count"),
            observed=SurvivalEstimate.from_dict(value["observed"]),
            source_row=int(value["source_row"]),
        )


@dataclass(frozen=True)
class StageSeries:
    cancer: str
    staging_system: str
    stage: str
    observations: tuple[AnnualObservation, ...]
    adjusted: SurvivalEstimate
    nationwide: SurvivalEstimate
    medical_center: SurvivalEstimate
    non_medical_center: SurvivalEstimate

    def to_dict(self) -> dict[str, Any]:
        return {
            "cancer": self.cancer,
            "staging_system": self.staging_system,
            "stage": self.stage,
            "observations": [item.to_dict() for item in self.observations],
            "adjusted": self.adjusted.to_dict(),
            "nationwide": self.nationwide.to_dict(),
            "medical_center": self.medical_center.to_dict(),
            "non_medical_center": self.non_medical_center.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StageSeries":
        return cls(
            cancer=value["cancer"],
            staging_system=value["staging_system"],
            stage=value["stage"],
            observations=tuple(AnnualObservation.from_dict(item) for item in value.get("observations", [])),
            adjusted=SurvivalEstimate.from_dict(value["adjusted"]),
            nationwide=SurvivalEstimate.from_dict(value["nationwide"]),
            medical_center=SurvivalEstimate.from_dict(value["medical_center"]),
            non_medical_center=SurvivalEstimate.from_dict(value["non_medical_center"]),
        )


@dataclass(frozen=True)
class ParsedWorkbook:
    source_filename: str
    source_format: SourceFormat
    hospital_name: str
    period_start: int
    period_end: int
    target_years: int
    stage_series: tuple[StageSeries, ...] = ()
    issues: tuple[ParseIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_filename": self.source_filename,
            "source_format": self.source_format.value,
            "hospital_name": self.hospital_name,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "target_years": self.target_years,
            "stage_series": [item.to_dict() for item in self.stage_series],
            "issues": [item.to_dict() for item in self.issues],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ParsedWorkbook":
        return cls(
            source_filename=value["source_filename"],
            source_format=SourceFormat(value["source_format"]),
            hospital_name=value.get("hospital_name", ""),
            period_start=int(value["period_start"]),
            period_end=int(value["period_end"]),
            target_years=int(value["target_years"]),
            stage_series=tuple(StageSeries.from_dict(item) for item in value.get("stage_series", [])),
            issues=tuple(ParseIssue.from_dict(item) for item in value.get("issues", [])),
        )


@dataclass(frozen=True)
class ReportHospital:
    key: str
    display_name: str
    is_local: bool = False
    source_filenames: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "display_name": self.display_name,
            "is_local": self.is_local,
            "source_filenames": list(self.source_filenames),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReportHospital":
        return cls(
            key=value["key"],
            display_name=value.get("display_name", ""),
            is_local=bool(value.get("is_local", False)),
            source_filenames=tuple(value.get("source_filenames", [])),
        )


@dataclass(frozen=True)
class HospitalReportValue:
    hospital_key: str
    estimate: SurvivalEstimate
    value_type: str
    source_rows: tuple[int, ...] = ()

    @classmethod
    def unavailable(cls, hospital_key: str) -> "HospitalReportValue":
        return cls(
            hospital_key=hospital_key,
            estimate=SurvivalEstimate.unavailable("not_available"),
            value_type="unavailable",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hospital_key": self.hospital_key,
            "estimate": self.estimate.to_dict(),
            "value_type": self.value_type,
            "source_rows": list(self.source_rows),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "HospitalReportValue":
        return cls(
            hospital_key=value["hospital_key"],
            estimate=SurvivalEstimate.from_dict(value["estimate"]),
            value_type=value.get("value_type", "unavailable"),
            source_rows=tuple(int(item) for item in value.get("source_rows", [])),
        )


@dataclass(frozen=True)
class ReportRow:
    stage: str
    stage_count: int | None
    death_count: int | None
    hospital_values: tuple[HospitalReportValue, ...]
    nationwide: SurvivalEstimate
    medical_center: SurvivalEstimate
    non_medical_center: SurvivalEstimate
    source_rows: tuple[int, ...] = ()

    @property
    def hospital(self) -> SurvivalEstimate:
        if not self.hospital_values:
            return SurvivalEstimate.unavailable("not_available")
        return self.hospital_values[0].estimate

    @property
    def hospital_value_type(self) -> str:
        if not self.hospital_values:
            return "unavailable"
        return self.hospital_values[0].value_type

    def value_for(self, hospital_key: str) -> HospitalReportValue:
        return next(
            (item for item in self.hospital_values if item.hospital_key == hospital_key),
            HospitalReportValue.unavailable(hospital_key),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "stage_count": self.stage_count,
            "death_count": self.death_count,
            "hospital_values": [item.to_dict() for item in self.hospital_values],
            "hospital": self.hospital.to_dict(),
            "hospital_value_type": self.hospital_value_type,
            "nationwide": self.nationwide.to_dict(),
            "medical_center": self.medical_center.to_dict(),
            "non_medical_center": self.non_medical_center.to_dict(),
            "source_rows": list(self.source_rows),
        }

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
        legacy_hospital_key: str = "legacy",
    ) -> "ReportRow":
        hospital_values = tuple(
            HospitalReportValue.from_dict(item)
            for item in value.get("hospital_values", [])
        )
        if not hospital_values and value.get("hospital") is not None:
            hospital_values = (
                HospitalReportValue(
                    hospital_key=legacy_hospital_key,
                    estimate=SurvivalEstimate.from_dict(value["hospital"]),
                    value_type=value.get("hospital_value_type", "unavailable"),
                    source_rows=tuple(int(item) for item in value.get("source_rows", [])),
                ),
            )
        return cls(
            stage=value["stage"],
            stage_count=value.get("stage_count"),
            death_count=value.get("death_count"),
            hospital_values=hospital_values,
            nationwide=SurvivalEstimate.from_dict(value["nationwide"]),
            medical_center=SurvivalEstimate.from_dict(value["medical_center"]),
            non_medical_center=SurvivalEstimate.from_dict(value["non_medical_center"]),
            source_rows=tuple(int(item) for item in value.get("source_rows", [])),
        )


@dataclass(frozen=True)
class ReportTable:
    table_id: str
    source_filenames: tuple[str, ...]
    period_start: int
    period_end: int
    target_years: int
    hospitals: tuple[ReportHospital, ...]
    primary_hospital_key: str
    cancer: str
    staging_system: str
    display_title: str
    rows: tuple[ReportRow, ...]
    custom_title: bool = False
    issues: tuple[ParseIssue, ...] = ()
    selected: bool = True
    sort_order: int = 0

    @property
    def hospital_name(self) -> str:
        primary = next(
            (item for item in self.hospitals if item.key == self.primary_hospital_key),
            self.hospitals[0] if self.hospitals else None,
        )
        return primary.display_name if primary else ""

    def hospital_value(self, row: ReportRow, hospital_key: str) -> HospitalReportValue:
        return row.value_for(hospital_key)

    @property
    def comparison_banner(self) -> str:
        chinese_years = {
            1: "一",
            2: "二",
            3: "三",
            4: "四",
            5: "五",
            6: "六",
            7: "七",
            8: "八",
            9: "九",
            10: "十",
        }
        target_years = chinese_years.get(self.target_years, str(self.target_years))
        scope = "台大雲林與全國" if any(item.is_local for item in self.hospitals) else "全國"
        return (
            f"{self.period_start}-{self.period_end} 存活率："
            f"{scope}{target_years}年存活率比較（百分比）"
        )

    def with_updates(self, **changes: Any) -> "ReportTable":
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "source_filenames": list(self.source_filenames),
            "period_start": self.period_start,
            "period_end": self.period_end,
            "target_years": self.target_years,
            "hospitals": [item.to_dict() for item in self.hospitals],
            "primary_hospital_key": self.primary_hospital_key,
            "hospital_name": self.hospital_name,
            "cancer": self.cancer,
            "staging_system": self.staging_system,
            "display_title": self.display_title,
            "custom_title": self.custom_title,
            "comparison_banner": self.comparison_banner,
            "rows": [item.to_dict() for item in self.rows],
            "issues": [item.to_dict() for item in self.issues],
            "selected": self.selected,
            "sort_order": self.sort_order,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReportTable":
        hospitals = tuple(
            ReportHospital.from_dict(item) for item in value.get("hospitals", [])
        )
        if not hospitals:
            legacy_name = value.get("hospital_name", "").strip()
            is_local = legacy_name in {
                "本院",
                "國立臺灣大學醫學院附設醫院雲林分院",
            }
            hospitals = (
                ReportHospital(
                    key="local" if is_local else (legacy_name or "legacy"),
                    display_name="本院" if is_local else legacy_name,
                    is_local=is_local,
                    source_filenames=tuple(value.get("source_filenames", [])),
                ),
            )
        primary_hospital_key = value.get("primary_hospital_key") or hospitals[0].key
        return cls(
            table_id=value["table_id"],
            source_filenames=tuple(value.get("source_filenames", [])),
            period_start=int(value["period_start"]),
            period_end=int(value["period_end"]),
            target_years=int(value["target_years"]),
            hospitals=hospitals,
            primary_hospital_key=primary_hospital_key,
            cancer=value["cancer"],
            staging_system=value["staging_system"],
            display_title=value["display_title"],
            rows=tuple(
                ReportRow.from_dict(item, primary_hospital_key)
                for item in value.get("rows", [])
            ),
            custom_title=bool(value.get("custom_title", False)),
            issues=tuple(ParseIssue.from_dict(item) for item in value.get("issues", [])),
            selected=bool(value.get("selected", True)),
            sort_order=int(value.get("sort_order", 0)),
        )


def _legacy_deck_id(key: tuple[int, int, int]) -> str:
    payload = "\x1f".join(str(item) for item in key).encode("utf-8")
    return "deck-" + hashlib.sha256(payload).hexdigest()[:16]


@dataclass(frozen=True)
class ReportDeck:
    deck_id: str
    period_start: int
    period_end: int
    target_years: int
    source_filenames: tuple[str, ...]
    tables: tuple[ReportTable, ...]
    selected: bool = True
    sort_order: int = 0

    @property
    def ordered_tables(self) -> tuple[ReportTable, ...]:
        return tuple(sorted(self.tables, key=lambda table: table.sort_order))

    @property
    def hospital_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for table in sorted(self.tables, key=lambda item: item.sort_order):
            for hospital in table.hospitals:
                if hospital.display_name and hospital.display_name not in names:
                    names.append(hospital.display_name)
        return tuple(names)

    @property
    def warning_count(self) -> int:
        return sum(len(table.issues) for table in self.tables)

    def with_updates(self, **changes: Any) -> "ReportDeck":
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "deck_id": self.deck_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "target_years": self.target_years,
            "source_filenames": list(self.source_filenames),
            "hospital_names": list(self.hospital_names),
            "tables": [item.to_dict() for item in self.tables],
            "selected": self.selected,
            "sort_order": self.sort_order,
            "warning_count": self.warning_count,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReportDeck":
        return cls(
            deck_id=value["deck_id"],
            period_start=int(value["period_start"]),
            period_end=int(value["period_end"]),
            target_years=int(value["target_years"]),
            source_filenames=tuple(value.get("source_filenames", [])),
            tables=tuple(ReportTable.from_dict(item) for item in value.get("tables", [])),
            selected=bool(value.get("selected", True)),
            sort_order=int(value.get("sort_order", 0)),
        )


def _decks_from_tables(tables: tuple[ReportTable, ...]) -> tuple[ReportDeck, ...]:
    groups: dict[tuple[int, int, int], list[ReportTable]] = {}
    for table in tables:
        key = (table.period_start, table.period_end, table.target_years)
        groups.setdefault(key, []).append(table)
    decks: list[ReportDeck] = []
    for deck_order, (key, grouped_tables) in enumerate(groups.items()):
        source_names: list[str] = []
        normalized_tables: list[ReportTable] = []
        for table_order, table in enumerate(sorted(grouped_tables, key=lambda item: item.sort_order)):
            normalized_tables.append(table.with_updates(sort_order=table_order))
            for filename in table.source_filenames:
                if filename not in source_names:
                    source_names.append(filename)
        decks.append(
            ReportDeck(
                deck_id=_legacy_deck_id(key),
                period_start=key[0],
                period_end=key[1],
                target_years=key[2],
                source_filenames=tuple(source_names),
                tables=tuple(normalized_tables),
                selected=any(table.selected for table in grouped_tables),
                sort_order=deck_order,
            )
        )
    return tuple(decks)


@dataclass(frozen=True, init=False)
class ReportBatch:
    sources: tuple[ParsedWorkbook, ...]
    decks: tuple[ReportDeck, ...]
    issues: tuple[ParseIssue, ...]

    def __init__(
        self,
        sources: tuple[ParsedWorkbook, ...] = (),
        decks: tuple[ReportDeck, ...] = (),
        issues: tuple[ParseIssue, ...] = (),
        tables: tuple[ReportTable, ...] | None = None,
    ) -> None:
        if tables is not None:
            decks = _decks_from_tables(tuple(tables))
        object.__setattr__(self, "sources", tuple(sources))
        object.__setattr__(self, "decks", tuple(decks))
        object.__setattr__(self, "issues", tuple(issues))

    @property
    def tables(self) -> tuple[ReportTable, ...]:
        return tuple(
            table
            for deck in sorted(self.decks, key=lambda item: item.sort_order)
            for table in sorted(deck.tables, key=lambda item: item.sort_order)
        )

    @property
    def selected_decks(self) -> tuple[ReportDeck, ...]:
        return tuple(
            sorted(
                (deck for deck in self.decks if deck.selected),
                key=lambda deck: deck.sort_order,
            )
        )

    @property
    def selected_tables(self) -> tuple[ReportTable, ...]:
        return tuple(
            table
            for deck in self.selected_decks
            for table in deck.ordered_tables
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": [item.to_dict() for item in self.sources],
            "decks": [item.to_dict() for item in self.decks],
            "tables": [item.to_dict() for item in self.tables],
            "issues": [item.to_dict() for item in self.issues],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReportBatch":
        decks = tuple(ReportDeck.from_dict(item) for item in value.get("decks", []))
        legacy_tables = tuple(ReportTable.from_dict(item) for item in value.get("tables", []))
        return cls(
            sources=tuple(ParsedWorkbook.from_dict(item) for item in value.get("sources", [])),
            decks=decks,
            tables=None if decks else legacy_tables,
            issues=tuple(ParseIssue.from_dict(item) for item in value.get("issues", [])),
        )

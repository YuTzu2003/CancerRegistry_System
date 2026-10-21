"""Convert parsed workbooks into preview/export report tables."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Sequence

from .models import (
    HospitalReportValue,
    IssueSeverity,
    ParseIssue,
    ParsedWorkbook,
    ReportBatch,
    ReportDeck,
    ReportHospital,
    ReportRow,
    ReportTable,
    StageSeries,
    SurvivalEstimate,
)


@dataclass(frozen=True)
class HospitalDisplayOverride:
    hospital_key: str
    display_name: str

    @classmethod
    def from_dict(cls, value: dict) -> "HospitalDisplayOverride":
        return cls(
            hospital_key=str(value["hospital_key"]),
            display_name=str(value.get("display_name", "")),
        )


@dataclass(frozen=True)
class DisplayOverride:
    table_id: str
    deck_id: str | None = None
    hospital_name: str | None = None
    cancer: str | None = None
    staging_system: str | None = None
    display_title: str | None = None
    custom_title: bool | None = None
    hospitals: tuple[HospitalDisplayOverride, ...] | None = None
    selected: bool | None = None
    sort_order: int | None = None

    @classmethod
    def from_dict(cls, value: dict) -> "DisplayOverride":
        allowed = {
            "table_id",
            "deck_id",
            "hospital_name",
            "cancer",
            "staging_system",
            "display_title",
            "custom_title",
            "hospitals",
            "selected",
            "sort_order",
        }
        cleaned = {key: item for key, item in value.items() if key in allowed}
        if isinstance(cleaned.get("hospitals"), list):
            cleaned["hospitals"] = tuple(
                HospitalDisplayOverride.from_dict(item)
                for item in cleaned["hospitals"]
                if isinstance(item, dict) and "hospital_key" in item
            )
        return cls(**cleaned)


@dataclass(frozen=True)
class DeckOverride:
    deck_id: str
    selected: bool | None = None
    sort_order: int | None = None

    @classmethod
    def from_dict(cls, value: dict) -> "DeckOverride":
        return cls(
            deck_id=str(value["deck_id"]),
            selected=None if "selected" not in value else bool(value["selected"]),
            sort_order=None if "sort_order" not in value else int(value["sort_order"]),
        )


def _table_id(key: tuple[object, ...]) -> str:
    payload = "\x1f".join(str(item) for item in key).encode("utf-8")
    return "survival-" + hashlib.sha256(payload).hexdigest()[:16]


def _deck_id(key: tuple[int, int, int]) -> str:
    payload = "\x1f".join(str(item) for item in key).encode("utf-8")
    return "deck-" + hashlib.sha256(payload).hexdigest()[:16]


def _source_issue(issue: ParseIssue, table_id: str) -> ParseIssue:
    return replace(issue, table_id=table_id)


def _generated_title(cancer: str, staging_system: str) -> str:
    cancer_label = cancer.strip()
    staging_label = staging_system.strip()
    if not staging_label or staging_label.casefold() == "ajcc":
        return f"{cancer_label}存活率"
    if not staging_label.endswith("分期"):
        staging_label = f"{staging_label}分期"
    return f"{cancer_label}{staging_label}存活率"


def _canonical_hospital(name: str) -> tuple[str, str, bool]:
    cleaned = name.strip()
    if cleaned in {"本院", "國立臺灣大學醫學院附設醫院雲林分院"}:
        return "local", "本院", True
    return cleaned, cleaned, False


def _series_signature(series: StageSeries) -> tuple[object, ...]:
    return (
        series.cancer.strip(),
        series.staging_system.strip().casefold(),
        series.stage,
        series.observations,
        series.adjusted,
        series.nationwide,
        series.medical_center,
        series.non_medical_center,
    )


def _build_hospital_value(
    series: StageSeries,
    workbook: ParsedWorkbook,
    table_id: str,
    hospital_key: str,
) -> tuple[
    HospitalReportValue,
    int | None,
    int | None,
    tuple[SurvivalEstimate, SurvivalEstimate, SurvivalEstimate],
    tuple[ParseIssue, ...],
]:
    issues: list[ParseIssue] = []
    first_year = next((item for item in series.observations if item.follow_up_year == 1), None)
    through_target = [
        item for item in series.observations if 1 <= item.follow_up_year <= workbook.target_years
    ]
    target_year = next(
        (item for item in series.observations if item.follow_up_year == workbook.target_years),
        None,
    )
    if first_year is None:
        issues.append(
            ParseIssue(
                "missing_first_year",
                f"{series.stage} 缺少第 1 年資料，無法取得期別人數。",
                IssueSeverity.WARNING,
                workbook.source_filename,
                table_id=table_id,
            )
        )
    missing_deaths = any(item.death_count is None for item in through_target)
    if missing_deaths or not through_target:
        death_count = None
        issues.append(
            ParseIssue(
                "missing_death_count",
                f"{series.stage} 的死亡人數不完整。",
                IssueSeverity.WARNING,
                workbook.source_filename,
                table_id=table_id,
            )
        )
    else:
        death_count = sum(item.death_count or 0 for item in through_target)

    if series.adjusted.available:
        hospital = series.adjusted
        value_type = "age_adjusted"
    elif target_year and target_year.observed.available:
        hospital = target_year.observed
        value_type = "observed"
    else:
        hospital = SurvivalEstimate.unavailable("not_available")
        value_type = "unavailable"
    value = HospitalReportValue(
        hospital_key=hospital_key,
        estimate=hospital,
        value_type=value_type,
        source_rows=tuple(item.source_row for item in series.observations),
    )
    return (
        value,
        first_year.analyzable_count if first_year else None,
        death_count,
        (series.nationwide, series.medical_center, series.non_medical_center),
        tuple(issues),
    )


def _build_tables(workbooks: Sequence[ParsedWorkbook]) -> tuple[ReportTable, ...]:
    groups: dict[
        tuple[int, int, int, str, str],
        list[tuple[ParsedWorkbook, StageSeries]],
    ] = {}
    for workbook in workbooks:
        for series in workbook.stage_series:
            key = (
                workbook.period_start,
                workbook.period_end,
                workbook.target_years,
                series.cancer.strip(),
                series.staging_system.strip().casefold(),
            )
            groups.setdefault(key, []).append((workbook, series))

    tables: list[ReportTable] = []
    for sort_order, (key, items) in enumerate(groups.items()):
        period_start, period_end, target_years, cancer, normalized_staging = key
        staging_system = "AJCC" if normalized_staging == "ajcc" else items[0][1].staging_system.strip()
        table_id = _table_id(key)
        table_issues: list[ParseIssue] = []
        source_names: list[str] = []
        hospital_meta: dict[str, dict[str, object]] = {}
        hospital_order: list[str] = []
        hospital_stages: dict[str, dict[str, tuple[ParsedWorkbook, StageSeries]]] = {}
        for workbook, _ in items:
            if workbook.source_filename not in source_names:
                source_names.append(workbook.source_filename)
                table_issues.extend(_source_issue(issue, table_id) for issue in workbook.issues)
        for workbook, series in items:
            hospital_key, display_name, is_local = _canonical_hospital(workbook.hospital_name)
            if hospital_key not in hospital_meta:
                hospital_order.append(hospital_key)
                hospital_meta[hospital_key] = {
                    "display_name": display_name,
                    "is_local": is_local,
                    "source_filenames": [],
                }
                hospital_stages[hospital_key] = {}
            hospital_sources = hospital_meta[hospital_key]["source_filenames"]
            if workbook.source_filename not in hospital_sources:
                hospital_sources.append(workbook.source_filename)
            stages = hospital_stages[hospital_key]
            existing = stages.get(series.stage)
            if existing is None:
                stages[series.stage] = (workbook, series)
                continue
            if _series_signature(existing[1]) == _series_signature(series):
                table_issues.append(
                    ParseIssue(
                        "duplicate_stage",
                        f"{series.stage} 有完全相同的重複資料，已保留第一筆。",
                        IssueSeverity.WARNING,
                        workbook.source_filename,
                        series.observations[0].source_row if series.observations else None,
                        table_id,
                    )
                )
            else:
                table_issues.append(
                    ParseIssue(
                        "conflicting_stage",
                        f"{series.stage} 出現互相衝突的重複資料，請確認來源。",
                        IssueSeverity.ERROR,
                        workbook.source_filename,
                        series.observations[0].source_row if series.observations else None,
                        table_id,
                    )
                )

        hospital_order = sorted(
            hospital_order,
            key=lambda hospital_key: 0 if hospital_meta[hospital_key]["is_local"] else 1,
        )
        primary_hospital_key = hospital_order[0] if hospital_order else ""
        hospitals = tuple(
            ReportHospital(
                key=hospital_key,
                display_name=str(hospital_meta[hospital_key]["display_name"]),
                is_local=bool(hospital_meta[hospital_key]["is_local"]),
                source_filenames=tuple(hospital_meta[hospital_key]["source_filenames"]),
            )
            for hospital_key in hospital_order
        )

        stage_order: list[str] = []
        for hospital_key in hospital_order:
            for stage in hospital_stages[hospital_key]:
                if stage not in stage_order:
                    stage_order.append(stage)

        report_rows: list[ReportRow] = []
        for stage in stage_order:
            values: list[HospitalReportValue] = []
            built: dict[
                str,
                tuple[
                    HospitalReportValue,
                    int | None,
                    int | None,
                    tuple[SurvivalEstimate, SurvivalEstimate, SurvivalEstimate],
                ],
            ] = {}
            for hospital_key in hospital_order:
                source = hospital_stages[hospital_key].get(stage)
                if source is None:
                    values.append(HospitalReportValue.unavailable(hospital_key))
                    continue
                workbook, series = source
                value, count, deaths, benchmarks, row_issues = _build_hospital_value(
                    series,
                    workbook,
                    table_id,
                    hospital_key,
                )
                values.append(value)
                built[hospital_key] = (value, count, deaths, benchmarks)
                table_issues.extend(row_issues)

            primary = built.get(primary_hospital_key)
            if primary is None:
                counts = deaths = None
                benchmarks = (
                    SurvivalEstimate.unavailable("not_available"),
                    SurvivalEstimate.unavailable("not_available"),
                    SurvivalEstimate.unavailable("not_available"),
                )
            else:
                _, counts, deaths, benchmarks = primary
                for hospital_key, (_, _, _, candidate) in built.items():
                    if hospital_key == primary_hospital_key or candidate == benchmarks:
                        continue
                    source = hospital_stages[hospital_key][stage][0]
                    table_issues.append(
                        ParseIssue(
                            "benchmark_mismatch",
                            f"{stage} 的全國或醫院層級比較值與主要醫院不同，已採用主要醫院資料。",
                            IssueSeverity.WARNING,
                            source.source_filename,
                            table_id=table_id,
                        )
                    )
            all_source_rows = tuple(
                row_number
                for value in values
                for row_number in value.source_rows
            )
            report_rows.append(
                ReportRow(
                    stage=stage,
                    stage_count=counts,
                    death_count=deaths,
                    hospital_values=tuple(values),
                    nationwide=benchmarks[0],
                    medical_center=benchmarks[1],
                    non_medical_center=benchmarks[2],
                    source_rows=all_source_rows,
                )
            )

        tables.append(
            ReportTable(
                table_id=table_id,
                source_filenames=tuple(source_names),
                period_start=period_start,
                period_end=period_end,
                target_years=target_years,
                hospitals=hospitals,
                primary_hospital_key=primary_hospital_key,
                cancer=cancer,
                staging_system=staging_system,
                display_title=_generated_title(cancer, staging_system),
                rows=tuple(report_rows),
                issues=tuple(table_issues),
                selected=True,
                sort_order=sort_order,
            )
        )
    return tuple(tables)


def build_report_batch(workbooks: Sequence[ParsedWorkbook]) -> ReportBatch:
    grouped: dict[tuple[int, int, int], list[ParsedWorkbook]] = {}
    for workbook in workbooks:
        if not workbook.stage_series:
            continue
        key = (workbook.period_start, workbook.period_end, workbook.target_years)
        grouped.setdefault(key, []).append(workbook)

    decks: list[ReportDeck] = []
    for deck_order, (key, deck_workbooks) in enumerate(grouped.items()):
        tables = tuple(
            table.with_updates(sort_order=table_order)
            for table_order, table in enumerate(_build_tables(deck_workbooks))
        )
        source_names = tuple(workbook.source_filename for workbook in deck_workbooks)
        decks.append(
            ReportDeck(
                deck_id=_deck_id(key),
                period_start=key[0],
                period_end=key[1],
                target_years=key[2],
                source_filenames=source_names,
                tables=tables,
                selected=bool(tables),
                sort_order=deck_order,
            )
        )
    batch_issues = tuple(issue for workbook in workbooks for issue in workbook.issues)
    return ReportBatch(sources=tuple(workbooks), decks=tuple(decks), issues=batch_issues)


def apply_display_overrides(
    batch: ReportBatch,
    overrides: Sequence[DisplayOverride],
    deck_overrides: Sequence[DeckOverride] = (),
) -> ReportBatch:
    by_id = {override.table_id: override for override in overrides}
    known_table_ids = {table.table_id for table in batch.tables}
    unknown_table_ids = set(by_id) - known_table_ids
    if unknown_table_ids:
        raise ValueError(f"找不到投影片：{sorted(unknown_table_ids)[0]}")
    deck_by_id = {override.deck_id: override for override in deck_overrides}
    known_deck_ids = {deck.deck_id for deck in batch.decks}
    unknown_deck_ids = set(deck_by_id) - known_deck_ids
    if unknown_deck_ids:
        raise ValueError(f"找不到 PPT：{sorted(unknown_deck_ids)[0]}")

    changed_decks: list[ReportDeck] = []
    for deck in batch.decks:
        changed_tables: list[ReportTable] = []
        for table in deck.tables:
            override = by_id.get(table.table_id)
            if override is not None and override.deck_id is not None and override.deck_id != deck.deck_id:
                raise ValueError(f"投影片 {table.table_id} 不屬於指定的 PPT。")
            changed_tables.append(_apply_table_override(table, override))
        deck_override = deck_by_id.get(deck.deck_id)
        updates = {"tables": tuple(changed_tables)}
        if deck_override is not None:
            if deck_override.sort_order is not None:
                updates["sort_order"] = deck_override.sort_order
            if deck_override.selected is not None:
                updates["selected"] = bool(deck_override.selected)
        changed_decks.append(deck.with_updates(**updates))
    return ReportBatch(sources=batch.sources, decks=tuple(changed_decks), issues=batch.issues)


def _apply_table_override(
    table: ReportTable,
    override: DisplayOverride | None,
) -> ReportTable:
    if override is None:
        return table
    updates = {}
    for field_name in ("cancer", "staging_system"):
        value = getattr(override, field_name)
        if value is not None:
            updates[field_name] = str(value).strip()
    hospital_names = {
        item.hospital_key: item.display_name.strip()
        for item in (override.hospitals or ())
    }
    if override.hospital_name is not None and table.primary_hospital_key not in hospital_names:
        hospital_names[table.primary_hospital_key] = str(override.hospital_name).strip()
    if hospital_names:
        updates["hospitals"] = tuple(
            replace(
                hospital,
                display_name=hospital_names.get(hospital.key, hospital.display_name),
        )
            for hospital in table.hospitals
        )
    custom_title = table.custom_title if override.custom_title is None else bool(override.custom_title)
    updates["custom_title"] = custom_title
    if custom_title:
        if override.display_title is not None:
            updates["display_title"] = str(override.display_title).strip()
    else:
        updates["display_title"] = _generated_title(
            updates.get("cancer", table.cancer),
            updates.get("staging_system", table.staging_system),
        )
    issues = table.issues
    updated_hospitals = updates.get("hospitals", table.hospitals)
    if updated_hospitals and all(item.display_name for item in updated_hospitals):
        issues = tuple(issue for issue in issues if issue.code != "hospital_name_required")
        updates["issues"] = issues
    provisional = table.with_updates(**updates)
    if override.sort_order is not None:
        provisional = provisional.with_updates(sort_order=int(override.sort_order))
    if override.selected is not None:
        provisional = provisional.with_updates(selected=bool(override.selected))
    return provisional

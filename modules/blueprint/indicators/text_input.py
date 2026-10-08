from __future__ import annotations

import os

import pandas as pd


SUPPORTED_FIXED_WIDTH_FORMATS = ("42", "45", "114", "115", "129")
DELIMITERS = ("\t", ",", ";", "|")
TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp950", "big5", "utf-16", "gbk")


def _load_fixed_width_specs(connection_factory):
    if connection_factory is None:
        return {}

    connection = connection_factory()
    try:
        cursor = connection.cursor()
        specs = {}
        for format_id in SUPPORTED_FIXED_WIDTH_FORMATS:
            cursor.execute(
                """
                SELECT [FieldID], [ChineseName], [Start], [End]
                FROM [CancerRegistry_Fields]
                WHERE [fmt]=?
                ORDER BY [Start]
                """,
                (format_id,),
            )
            fields = []
            for field_id, chinese_name, start, end in cursor.fetchall():
                field_id = str(field_id or "").strip().removesuffix(".0")
                chinese_name = str(chinese_name or "").strip()
                fields.append((f"{field_id}{chinese_name}", int(start), int(end)))
            if fields:
                specs[format_id] = fields
        return specs
    finally:
        connection.close()


def _decode_fixed_width_value(value):
    for encoding in ("cp950", "big5"):
        try:
            return value.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return value.decode("cp950", errors="replace").strip()


def _read_fixed_width_txt(input_path, connection_factory):
    specs = _load_fixed_width_specs(connection_factory)
    if not specs:
        return None

    with open(input_path, "rb") as input_file:
        lines = [line.removesuffix(b"\x1a") for line in input_file.read().splitlines() if line]
    if not lines:
        return None

    matching_specs = []
    for format_id, fields in specs.items():
        record_length = max(end for _, _, end in fields)
        if all(len(line) == record_length for line in lines):
            matching_specs.append((format_id, fields))

    if not matching_specs:
        return None
    if len(matching_specs) > 1:
        format_names = "、".join(format_id for format_id, _ in matching_specs)
        raise ValueError(f"TXT 固定欄寬同時符合格式 {format_names}，無法判定應使用的欄位定義。")

    _, fields = matching_specs[0]
    rows = []
    for line in lines:
        rows.append({
            header: _decode_fixed_width_value(line[start - 1:end])
            for header, start, end in fields
        })
    return pd.DataFrame(rows, columns=[header for header, _, _ in fields])


def _read_delimited_txt(input_path):
    for encoding in TEXT_ENCODINGS:
        for delimiter in DELIMITERS:
            try:
                dataframe = pd.read_csv(
                    input_path,
                    sep=delimiter,
                    encoding=encoding,
                    low_memory=False,
                    dtype=str,
                )
            except (UnicodeError, UnicodeDecodeError, pd.errors.ParserError):
                continue
            if dataframe.shape[1] >= 2:
                return dataframe
    return None


def convert_indicator_txt_to_excel(input_path, output_path, connection_factory=None):
    """Convert supported fixed-width or delimited TXT uploads into XLSX."""
    dataframe = _read_fixed_width_txt(input_path, connection_factory)
    if dataframe is None:
        dataframe = _read_delimited_txt(input_path)

    if dataframe is None:
        return None

    if not str(output_path).lower().endswith(".xlsx"):
        output_path = f"{os.path.splitext(output_path)[0]}.xlsx"
    dataframe.to_excel(output_path, index=False)
    return output_path

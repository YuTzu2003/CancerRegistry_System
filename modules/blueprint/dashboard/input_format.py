import os
import re

import pandas as pd
from openpyxl import load_workbook


INPUT_SCHEMES = {
    "original", "field_name_zh", "field_name_en", "ntu_yunlin",
    "ntu_system", "taiwan_cancer_registry", "AI_module",
}
SCHEME_INDEX = {
    "field_name_zh": 1,
    "field_name_en": 2,
    "ntu_yunlin": 3,
    "ntu_system": 4,
    "taiwan_cancer_registry": 5,
    "AI_module": 6,
}
SEQUENCE_PATTERN = re.compile(r"^\d+(?:\.\d+)*$")
SEQUENCE_NAME_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\s*(.+)$")
TEXT_INPUT_ENCODINGS = ("utf-8-sig", "utf-8", "cp950", "big5hkscs", "big5", "gb18030")
FIXED_WIDTH_TEXT_ENCODINGS = ("utf-8-sig", "cp950", "big5hkscs", "big5")
FORMAT_SPECIFIC_FIELD_NAMES = {
    "50": {"7.6": "其他因子6"},
    "114": {"4.2.1.8": "未放射治療原因"},
    "115": {
        "4.2.1.8": "放射治療執行狀態",
        "7.6": "首次治療前生活功能狀態評估",
    },
    "129": {
        "4.2.1.8": "放射治療執行狀態",
        "7.6": "首次治療前生活功能狀態評估",
    },
}


def _text(value):
    return "" if value is None else str(value).strip()


def _normalize_sequence(value):
    text = _text(value)
    return text[:-2] if text.endswith(".0") else text


def _reset_source(file_source):
    """Return a source to its beginning when it is an uploaded binary stream."""
    if hasattr(file_source, "seek"):
        file_source.seek(0)


def _first_line_bytes(file_source):
    if isinstance(file_source, (str, os.PathLike)):
        with open(file_source, "rb") as source:
            return source.readline()

    _reset_source(file_source)
    first_line = file_source.readline()
    _reset_source(file_source)
    return first_line


def _read_delimited_or_fixed_width_text(file_source, extension, nrows=None):
    """Read headered CSV/TXT uploads and preserve their source text encoding.

    TXT may be comma/tab/semicolon delimited or a headered fixed-width export.
    Headerless registry TXT is intentionally not accepted here: the annual report
    importer has no selected registry format with which to split those records.
    """
    first_line = _first_line_bytes(file_source)
    delimiter = next((token for token in (b"\t", b",", b";") if token in first_line), None)
    options = {"dtype": str}
    if nrows is not None:
        options["nrows"] = nrows

    read_errors = []
    for encoding in TEXT_INPUT_ENCODINGS:
        try:
            _reset_source(file_source)
            if delimiter is not None:
                dataframe = pd.read_csv(file_source, sep=delimiter.decode("ascii"), encoding=encoding, **options)
            elif extension == "txt":
                dataframe = pd.read_fwf(file_source, encoding=encoding, **options)
            else:
                dataframe = pd.read_csv(file_source, encoding=encoding, **options)

            if dataframe.shape[1] <= 1:
                raise ValueError("找不到可辨識的欄位分隔方式")
            return dataframe
        except UnicodeDecodeError as error:
            read_errors.append(f"{encoding}: {error}")
        except pd.errors.EmptyDataError as error:
            raise ValueError("上傳檔案沒有可辨識的欄位資料。") from error
        except pd.errors.ParserError as error:
            raise ValueError("文字檔欄位格式無法辨識，請確認欄位以 Tab、逗號、分號或固定寬度排列。") from error

    supported = "、".join(TEXT_INPUT_ENCODINGS)
    raise ValueError(f"無法辨識文字檔編碼，請另存為 {supported} 後再上傳。")


def _read_source_bytes(file_source):
    """Read an uploaded stream or saved file without changing its final position."""
    if isinstance(file_source, (str, os.PathLike)):
        with open(file_source, "rb") as source:
            return source.read()

    _reset_source(file_source)
    content = file_source.read()
    _reset_source(file_source)
    return content


def _load_registry_format_name(connection_factory, format_id):
    if not format_id:
        raise ValueError("請先選擇 TXT 的申報欄位格式。")
    if connection_factory is None:
        raise ValueError("系統無法取得申報欄位格式。")

    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT [FmtName] FROM [DataFormat] WHERE [FmtID] = ?", (format_id,))
        row = cursor.fetchone()
        if not row or not row[0]:
            raise ValueError("找不到所選的申報欄位格式，請重新選擇。")
        return str(row[0]).strip().replace("fmt_", "")
    finally:
        connection.close()


def _format_specific_field_names(fmt_name):
    return FORMAT_SPECIFIC_FIELD_NAMES.get(str(fmt_name).replace("fmt_", ""), {})


def _format_specific_sequence_names(connection_factory, format_id):
    if not format_id:
        return {}
    return _format_specific_field_names(
        _load_registry_format_name(connection_factory, format_id)
    )


def _load_fixed_width_field_spec(connection_factory, fmt_name):
    """Load the same fixed-byte field positions used by the data-cleaning module."""
    if connection_factory is None:
        raise ValueError("系統無法取得申報欄位格式。")

    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT [ChineseName], [Start], [End]
               FROM [CancerRegistry_Fields]
               WHERE [fmt] = ?
               ORDER BY [Start]""",
            (fmt_name,),
        )
        field_rows = cursor.fetchall()
        cursor.execute("SELECT [序號], [中文欄位名稱] FROM [CancerRegistry_FieldMap]")
        map_rows = cursor.fetchall()
    finally:
        connection.close()

    name_to_sequence = {
        _text(row[1]): _normalize_sequence(row[0])
        for row in map_rows
        if _text(row[0]) and _text(row[1])
    }
    format_specific_names = _format_specific_field_names(fmt_name)
    return [
        (
            f"{name_to_sequence.get(_text(name), '')}{format_specific_names.get(name_to_sequence.get(_text(name), ''), _text(name))}",
            int(start),
            int(end),
        )
        for name, start, end in field_rows
    ]


def _decode_error_count(value, encoding):
    return value.decode(encoding, errors="replace").count("\ufffd")


def _detect_fixed_width_encoding(content_bytes):
    if content_bytes.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    return min(
        FIXED_WIDTH_TEXT_ENCODINGS,
        key=lambda encoding: _decode_error_count(content_bytes[:65536], encoding),
    )


def _parse_fixed_width_line(line_bytes, field_spec, encoding):
    return {
        name: line_bytes[start - 1:end].decode(encoding, errors="replace").strip()
        for name, start, end in field_spec
    }


def _read_fixed_width_registry_text(file_source, format_id, connection_factory):
    """Split a headerless registry TXT by the selected byte-position format."""
    fmt_name = _load_registry_format_name(connection_factory, format_id)
    field_spec = _load_fixed_width_field_spec(connection_factory, fmt_name)
    if not field_spec:
        raise ValueError(f"找不到 {fmt_name} 格式的欄位定義。")

    content = _read_source_bytes(file_source)
    lines = [line for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("上傳檔案沒有可辨識的欄位資料。")

    expected_length = field_spec[-1][2]
    mismatches = []
    for line_number, line in enumerate(lines, start=1):
        if len(line) != expected_length:
            mismatches.append(
                f"第 {line_number} 行：實際 {len(line)} bytes，預期 {expected_length} bytes"
            )
            if len(mismatches) == 3:
                break
    if mismatches:
        detail = "；".join(mismatches)
        raise ValueError(f"固定欄位 TXT 長度與所選 {fmt_name} 格式不符：{detail}")

    encoding = _detect_fixed_width_encoding(content)
    records = [_parse_fixed_width_line(line, field_spec, encoding) for line in lines]
    return pd.DataFrame(records, columns=[field[0] for field in field_spec])


def _read_upload_dataframe(
    file_source,
    extension,
    *,
    format_id=None,
    txt_has_header=False,
    connection_factory=None,
    nrows=None,
):
    extension = str(extension or "").lower().lstrip(".")
    if extension == "xlsx":
        return pd.read_excel(file_source, nrows=nrows)
    if extension == "xls":
        return pd.read_excel(file_source, nrows=nrows)
    if extension == "csv":
        return _read_delimited_or_fixed_width_text(file_source, extension, nrows=nrows)
    if extension == "txt":
        if txt_has_header:
            return _read_delimited_or_fixed_width_text(file_source, extension, nrows=nrows)
        return _read_fixed_width_registry_text(file_source, format_id, connection_factory)
    raise ValueError("僅接受 .txt、.csv、.xls 或 .xlsx 格式。")


def _read_headers(file_path, extension, *, format_id=None, txt_has_header=False, connection_factory=None):
    extension = str(extension or "").lower().lstrip(".")
    if extension == "xlsx":
        workbook = load_workbook(file_path, read_only=True, data_only=True)
        try:
            return [_text(cell.value) for cell in workbook.worksheets[0][1]]
        finally:
            workbook.close()
    try:
        return [
            _text(value)
            for value in _read_upload_dataframe(
                file_path,
                extension,
                format_id=format_id,
                txt_has_header=txt_has_header,
                connection_factory=connection_factory,
                nrows=0,
            ).columns
        ]
    except ImportError as error:
        raise ValueError("舊式 .xls 檔案需要額外讀取元件，請先另存為 .xlsx 後再上傳。") from error


def _load_field_map(connection_factory):
    if connection_factory is None:
        raise ValueError("系統無法取得欄位名稱對照資料。")
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT [序號], [中文欄位名稱], [英文欄位名稱], [台大雲林欄位名稱],
                   [台大體系醫整庫欄位名稱], [台灣癌症登記中心], [雲醫癌AI模組]
            FROM [CancerRegistry_FieldMap]
        """)
        rows = []
        for row in cursor.fetchall():
            values = [_text(value) for value in row]
            values[0] = _normalize_sequence(values[0])
            if values[0] and values[1]:
                rows.append(values)
        return rows
    finally:
        connection.close()


def _compact(value):
    return re.sub(r"\s+", "", _text(value)).casefold()


def _maps_for_scheme(rows, input_scheme, format_specific_names=None):
    format_specific_names = format_specific_names or {}
    by_sequence = {
        row[0]: f"{row[0]}{format_specific_names.get(row[0], row[1])}"
        for row in rows
    }
    alias_map = {}
    indexes = range(1, 7) if input_scheme == "original" else (SCHEME_INDEX[input_scheme],)
    for row in rows:
        canonical = by_sequence[row[0]]
        for index in indexes:
            aliases = [_text(row[index])]
            if row[0] in {"4.2.1.8", "7.6"} and "/" in aliases[0]:
                aliases.extend(part.strip() for part in aliases[0].split("/") if part.strip())
            if row[0] in format_specific_names:
                aliases.append(format_specific_names[row[0]])
            for alias in aliases:
                compact_alias = _compact(alias)
                if compact_alias:
                    alias_map.setdefault(compact_alias, canonical)
    return by_sequence, alias_map


def _normalize_headers(headers, input_scheme, rows, format_specific_names=None):
    empty_positions = [str(index + 1) for index, header in enumerate(headers) if not _text(header)]
    if empty_positions:
        raise ValueError(f"第一列表頭不可為空白（第 {', '.join(empty_positions)} 欄）。")

    by_sequence, alias_map = _maps_for_scheme(rows, input_scheme, format_specific_names)
    normalized = []
    unknown_sequences = []
    for header in headers:
        text = _text(header)
        sequence_match = SEQUENCE_NAME_PATTERN.fullmatch(text)

        # 三種輸入形式都會自動辨識：僅序號、序號＋名稱、僅名稱。
        if SEQUENCE_PATTERN.fullmatch(text):
            sequence = _normalize_sequence(text)
            canonical = by_sequence.get(sequence)
            if not canonical:
                unknown_sequences.append(text)
                canonical = text
        elif sequence_match:
            sequence = _normalize_sequence(sequence_match.group(1))
            canonical = by_sequence.get(sequence)
            if not canonical:
                unknown_sequences.append(sequence)
                canonical = text
        else:
            # 未匹配的純名稱視為額外欄位並原樣保留。
            canonical = alias_map.get(_compact(text), text)
        normalized.append(canonical)

    if unknown_sequences:
        shown = ", ".join(dict.fromkeys(unknown_sequences[:5]))
        raise ValueError(f"找不到以下欄位序號的名稱對照：{shown}")
    if len(set(normalized)) != len(normalized):
        raise ValueError("欄位名稱轉換後出現重複欄位，請確認第一列表頭與命名來源。")
    return normalized


def _write_headers(
    file_path,
    extension,
    headers,
    keep_indexes=None,
    *,
    format_id=None,
    txt_has_header=False,
    connection_factory=None,
):
    extension = str(extension or "").lower().lstrip(".")
    if extension == "xlsx":
        workbook = load_workbook(file_path)
        try:
            worksheet = workbook.worksheets[0]
            if keep_indexes is not None:
                keep_set = set(keep_indexes)
                for column_index in range(worksheet.max_column, 0, -1):
                    if column_index - 1 not in keep_set:
                        worksheet.delete_cols(column_index)
            for index, header in enumerate(headers, start=1):
                worksheet.cell(row=1, column=index).value = header
            workbook.save(file_path)
        finally:
            workbook.close()
        return file_path

    dataframe = _read_upload_dataframe(
        file_path,
        extension,
        format_id=format_id,
        txt_has_header=txt_has_header,
        connection_factory=connection_factory,
    )
    if keep_indexes is not None:
        dataframe = dataframe.iloc[:, keep_indexes]
    dataframe.columns = headers
    converted_path = f"{os.path.splitext(file_path)[0]}.xlsx"
    dataframe.to_excel(converted_path, index=False)
    os.remove(file_path)
    return converted_path


def validate_and_normalize_dashboard_upload(
    file_path,
    extension,
    input_scheme,
    connection_factory=None,
    extra_fields=None,
    format_id=None,
    txt_has_header=False,
):
    """Normalize supported annual-report headers to sequence + Chinese field name."""
    if input_scheme not in INPUT_SCHEMES:
        raise ValueError("請選擇正確的輸入欄位命名來源。")
    headers = _read_headers(
        file_path,
        extension,
        format_id=format_id,
        txt_has_header=txt_has_header,
        connection_factory=connection_factory,
    )
    if not headers:
        raise ValueError("第一列沒有可辨識的欄位表頭。")
    rows = _load_field_map(connection_factory)
    format_specific_names = _format_specific_sequence_names(connection_factory, format_id)
    normalized_headers = _normalize_headers(
        headers,
        input_scheme,
        rows,
        format_specific_names,
    )
    keep_indexes = None
    if extra_fields is not None:
        retained_extra_fields = {_text(field) for field in extra_fields}
        canonical_headers = set(
            _maps_for_scheme(rows, input_scheme, format_specific_names)[0].values()
        )
        keep_indexes = [
            index
            for index, (original, normalized) in enumerate(zip(headers, normalized_headers))
            if original != normalized or normalized in canonical_headers or original in retained_extra_fields
        ]
        normalized_headers = [normalized_headers[index] for index in keep_indexes]
        if not normalized_headers:
            raise ValueError("沒有可匯入的欄位，請至少保留一個欄位。")
    return _write_headers(
        file_path,
        extension,
        normalized_headers,
        keep_indexes,
        format_id=format_id,
        txt_has_header=txt_has_header,
        connection_factory=connection_factory,
    )


def preview_dashboard_upload(
    file_source,
    extension,
    input_scheme,
    connection_factory=None,
    format_id=None,
    txt_has_header=False,
):
    """Return a read-only header matching preview without storing or rewriting the file."""
    if input_scheme not in INPUT_SCHEMES:
        raise ValueError("請選擇正確的輸入欄位命名來源。")
    headers = _read_headers(
        file_source,
        extension,
        format_id=format_id,
        txt_has_header=txt_has_header,
        connection_factory=connection_factory,
    )
    if not headers:
        raise ValueError("第一列沒有可辨識的欄位表頭。")
    rows = _load_field_map(connection_factory)
    format_specific_names = _format_specific_sequence_names(connection_factory, format_id)
    normalized_headers = _normalize_headers(
        headers,
        input_scheme,
        rows,
        format_specific_names,
    )
    canonical_headers = set(
        _maps_for_scheme(rows, input_scheme, format_specific_names)[0].values()
    )
    columns = []
    for original, normalized in zip(headers, normalized_headers):
        columns.append({
            "original": original,
            "normalized": normalized,
            "matched": original != normalized or normalized in canonical_headers,
        })
    matched_count = sum(1 for column in columns if column["matched"])
    return {
        "columns": columns,
        "total_count": len(columns),
        "matched_count": matched_count,
        "unmatched_count": len(columns) - matched_count,
    }

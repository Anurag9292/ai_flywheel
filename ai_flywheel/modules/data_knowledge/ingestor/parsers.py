# ruff: noqa: E501
"""Format-specific parsers for the Universal Ingestor.

Each parser converts raw content into a list of ParsedRecord objects.
Uses only stdlib — no pandas, no beautifulsoup.
"""

from __future__ import annotations

import csv
import io
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import structlog

from ai_flywheel.modules.data_knowledge.ingestor.schemas import ParsedRecord

logger = structlog.get_logger()


def _infer_type(value: str) -> str:
    """Infer the Python type of a string value.

    Returns one of: int, float, bool, date, str
    """
    if not value or value.strip() == "":
        return "str"

    stripped = value.strip()

    # Bool
    if stripped.lower() in ("true", "false", "yes", "no", "1", "0"):
        return "bool"

    # Int
    try:
        int(stripped)
        return "int"
    except ValueError:
        pass

    # Float
    try:
        float(stripped)
        return "float"
    except ValueError:
        pass

    # Date — check common formats
    date_patterns = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]
    for pattern in date_patterns:
        try:
            datetime.strptime(stripped, pattern)
            return "date"
        except ValueError:
            continue

    return "str"


def _coerce_value(value: str, inferred_type: str) -> Any:
    """Coerce a string value to its inferred type."""
    if not value or value.strip() == "":
        return None

    stripped = value.strip()

    if inferred_type == "int":
        return int(stripped)
    elif inferred_type == "float":
        return float(stripped)
    elif inferred_type == "bool":
        return stripped.lower() in ("true", "yes", "1")
    elif inferred_type == "date":
        return stripped  # Keep as string for serialization
    return stripped


class BaseParser(ABC):
    """Abstract base class for content parsers."""

    @abstractmethod
    def parse(self, content: str | bytes) -> list[ParsedRecord]:
        """Parse content into a list of ParsedRecord objects."""
        ...


class CSVParser(BaseParser):
    """Parses CSV text with dialect detection and type inference."""

    def parse(self, content: str | bytes) -> list[ParsedRecord]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        # Detect dialect
        sample = content[:8192]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel  # type: ignore[assignment]

        # Detect if there's a header
        has_header = csv.Sniffer().has_header(sample)

        reader = csv.reader(io.StringIO(content), dialect)
        rows = list(reader)

        if not rows:
            return []

        # Extract headers
        if has_header:
            headers = [h.strip() for h in rows[0]]
            data_rows = rows[1:]
        else:
            # Generate column names
            num_cols = len(rows[0]) if rows else 0
            headers = [f"col_{i}" for i in range(num_cols)]
            data_rows = rows

        if not data_rows:
            return []

        # Infer column types from first N rows
        sample_size = min(100, len(data_rows))
        column_types: dict[str, str] = {}
        for col_idx, header in enumerate(headers):
            type_counts: dict[str, int] = {}
            for row in data_rows[:sample_size]:
                if col_idx < len(row):
                    t = _infer_type(row[col_idx])
                    type_counts[t] = type_counts.get(t, 0) + 1
            # Use most common non-str type, or str as fallback
            non_str_types = {k: v for k, v in type_counts.items() if k != "str"}
            if non_str_types:
                column_types[header] = max(non_str_types, key=non_str_types.get)  # type: ignore[arg-type]
            else:
                column_types[header] = "str"

        # Parse all rows
        records: list[ParsedRecord] = []
        for row_idx, row in enumerate(data_rows):
            record_data: dict[str, Any] = {}
            for col_idx, header in enumerate(headers):
                if col_idx < len(row):
                    value = row[col_idx]
                    record_data[header] = _coerce_value(value, column_types[header])
                else:
                    record_data[header] = None

            records.append(
                ParsedRecord(
                    data=record_data,
                    source_field_types=column_types,
                    row_index=row_idx,
                )
            )

        logger.debug(
            "csv_parsed",
            rows=len(records),
            columns=len(headers),
            headers=headers,
        )
        return records


class JSONParser(BaseParser):
    """Parses JSON arrays or single objects, flattening nested structures."""

    def parse(self, content: str | bytes) -> list[ParsedRecord]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        data = json.loads(content)

        # Normalize to list of objects
        if isinstance(data, dict):
            objects = [data]
        elif isinstance(data, list):
            objects = data
        else:
            objects = [{"value": data}]

        records: list[ParsedRecord] = []
        for idx, obj in enumerate(objects):
            if not isinstance(obj, dict):
                obj = {"value": obj}

            flat = self._flatten(obj)
            field_types = {k: _infer_type(str(v)) if v is not None else "str" for k, v in flat.items()}

            records.append(
                ParsedRecord(
                    data=flat,
                    source_field_types=field_types,
                    row_index=idx,
                )
            )

        logger.debug("json_parsed", records=len(records))
        return records

    def _flatten(self, obj: dict, prefix: str = "") -> dict[str, Any]:
        """Flatten nested dicts using dot notation."""
        result: dict[str, Any] = {}
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten(value, full_key))
            elif isinstance(value, list):
                # Store lists as-is (don't flatten arrays)
                result[full_key] = value
            else:
                result[full_key] = value
        return result


class HTMLParser(BaseParser):
    """Extracts text content, tables, and metadata from HTML.

    Uses basic string/regex parsing — no BeautifulSoup dependency.
    """

    def parse(self, content: str | bytes) -> list[ParsedRecord]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        records: list[ParsedRecord] = []

        # Extract tables first
        table_records = self._extract_tables(content)
        records.extend(table_records)

        # Extract text content (paragraphs, headings)
        text_records = self._extract_text_blocks(content)
        records.extend(text_records)

        logger.debug(
            "html_parsed",
            tables=len(table_records),
            text_blocks=len(text_records),
        )
        return records

    def _strip_tags(self, html: str) -> str:
        """Remove HTML tags from a string."""
        clean = re.sub(r"<[^>]+>", "", html)
        clean = re.sub(r"&nbsp;", " ", clean)
        clean = re.sub(r"&amp;", "&", clean)
        clean = re.sub(r"&lt;", "<", clean)
        clean = re.sub(r"&gt;", ">", clean)
        clean = re.sub(r"&quot;", '"', clean)
        clean = re.sub(r"&#\d+;", "", clean)
        return clean.strip()

    def _extract_tables(self, html: str) -> list[ParsedRecord]:
        """Extract table rows as records."""
        records: list[ParsedRecord] = []

        # Find all tables
        table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL | re.IGNORECASE)
        tables = table_pattern.findall(html)

        for table_html in tables:
            # Extract rows
            row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
            rows = row_pattern.findall(table_html)

            if not rows:
                continue

            # First row as headers (th or td)
            cell_pattern = re.compile(
                r"<(?:th|td)[^>]*>(.*?)</(?:th|td)>", re.DOTALL | re.IGNORECASE
            )
            header_cells = cell_pattern.findall(rows[0])
            headers = [self._strip_tags(cell).strip() for cell in header_cells]

            if not headers:
                continue

            # Generate fallback headers if empty
            headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]

            # Parse data rows
            for row_idx, row_html in enumerate(rows[1:]):
                cells = cell_pattern.findall(row_html)
                cell_values = [self._strip_tags(cell).strip() for cell in cells]

                row_data: dict[str, Any] = {}
                field_types: dict[str, str] = {}
                for col_idx, header in enumerate(headers):
                    value = cell_values[col_idx] if col_idx < len(cell_values) else ""
                    row_data[header] = value
                    field_types[header] = _infer_type(value)

                records.append(
                    ParsedRecord(
                        data=row_data,
                        source_field_types=field_types,
                        row_index=row_idx,
                    )
                )

        return records

    def _extract_text_blocks(self, html: str) -> list[ParsedRecord]:
        """Extract text paragraphs and headings as records."""
        records: list[ParsedRecord] = []

        # Remove script and style blocks
        clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)

        # Extract headings and paragraphs
        block_pattern = re.compile(
            r"<(h[1-6]|p|li|div|article|section)[^>]*>(.*?)</\1>",
            re.DOTALL | re.IGNORECASE,
        )
        blocks = block_pattern.findall(clean)

        for idx, (tag, content_html) in enumerate(blocks):
            text = self._strip_tags(content_html).strip()
            if not text or len(text) < 3:
                continue

            records.append(
                ParsedRecord(
                    data={
                        "text": text,
                        "tag": tag.lower(),
                        "char_count": len(text),
                    },
                    source_field_types={
                        "text": "str",
                        "tag": "str",
                        "char_count": "int",
                    },
                    row_index=idx,
                )
            )

        return records


class TextParser(BaseParser):
    """Splits plain text into paragraph/chunk records."""

    def parse(self, content: str | bytes) -> list[ParsedRecord]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        # Split on double newlines (paragraphs) or single newlines for short texts
        paragraphs = re.split(r"\n\s*\n", content)

        # If only one paragraph, split on single newlines
        if len(paragraphs) == 1 and len(content) > 500:
            paragraphs = content.split("\n")

        records: list[ParsedRecord] = []
        for idx, para in enumerate(paragraphs):
            text = para.strip()
            if not text:
                continue

            records.append(
                ParsedRecord(
                    data={
                        "text": text,
                        "char_count": len(text),
                        "word_count": len(text.split()),
                    },
                    source_field_types={
                        "text": "str",
                        "char_count": "int",
                        "word_count": "int",
                    },
                    row_index=idx,
                )
            )

        logger.debug("text_parsed", paragraphs=len(records))
        return records


# Parser registry
_PARSERS: dict[str, type[BaseParser]] = {
    "csv": CSVParser,
    "json": JSONParser,
    "html": HTMLParser,
    "text": TextParser,
}


def get_parser(format: str) -> BaseParser:
    """Factory function to get a parser by format name.

    Args:
        format: One of 'csv', 'json', 'html', 'text'

    Returns:
        An instance of the appropriate parser.

    Raises:
        ValueError: If format is not supported.
    """
    parser_cls = _PARSERS.get(format.lower())
    if parser_cls is None:
        raise ValueError(
            f"Unsupported format: {format!r}. Supported: {list(_PARSERS.keys())}"
        )
    return parser_cls()

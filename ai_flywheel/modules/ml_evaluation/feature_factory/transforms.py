# ruff: noqa: E501
"""Pure Python feature transforms — no numpy/pandas/sklearn required."""

from __future__ import annotations

from typing import Any

from ai_flywheel.modules.ml_evaluation.feature_factory.schemas import FeatureDefResponse


def apply_transform(record: dict[str, Any], definition: FeatureDefResponse) -> Any:
    """Dispatch to the appropriate transform based on definition.transform_type and config."""
    transform_type = definition.transform_type
    config = definition.transform_config
    input_fields = definition.input_fields

    if transform_type == "numeric":
        value = record.get(input_fields[0]) if input_fields else None
        method = config.get("method", "scale")
        if method == "bin":
            return numeric_bin(value, config)
        return numeric_scale(value, config)

    elif transform_type == "categorical":
        value = record.get(input_fields[0]) if input_fields else None
        return categorical_encode(value, config)

    elif transform_type == "text":
        value = record.get(input_fields[0]) if input_fields else None
        method = config.get("method", "length")
        if method == "contains":
            return text_contains(value, config)
        return text_length(value, config)

    elif transform_type == "temporal":
        value = record.get(input_fields[0]) if input_fields else None
        return temporal_extract(value, config)

    elif transform_type == "composite":
        method = config.get("method", "ratio")
        if method == "difference":
            return composite_difference(record, config)
        return composite_ratio(record, config)

    else:
        raise ValueError(f"Unknown transform_type: {transform_type}")


def numeric_scale(value: Any, config: dict[str, Any]) -> float:
    """Min-max or z-score normalization.

    Config:
        mode: "minmax" (default) | "zscore"
        min: float (for minmax)
        max: float (for minmax)
        mean: float (for zscore)
        std: float (for zscore)
    """
    if value is None:
        return 0.0

    val = float(value)
    mode = config.get("mode", "minmax")

    if mode == "zscore":
        mean = float(config.get("mean", 0.0))
        std = float(config.get("std", 1.0))
        if std == 0:
            return 0.0
        return (val - mean) / std
    else:
        # minmax
        min_val = float(config.get("min", 0.0))
        max_val = float(config.get("max", 1.0))
        if max_val == min_val:
            return 0.0
        return (val - min_val) / (max_val - min_val)


def numeric_bin(value: Any, config: dict[str, Any]) -> str:
    """Bin a numeric value into ranges.

    Config:
        bins: list of boundary values, e.g. [0, 10, 50, 100]
        labels: list of bin labels (len = len(bins) - 1), e.g. ["low", "med", "high"]
    """
    if value is None:
        return "unknown"

    val = float(value)
    bins = config.get("bins", [0, 50, 100])
    labels = config.get("labels", None)

    for i in range(len(bins) - 1):
        if bins[i] <= val < bins[i + 1]:
            if labels and i < len(labels):
                return labels[i]
            return f"{bins[i]}-{bins[i + 1]}"

    # Value exceeds all bins
    if val >= bins[-1]:
        if labels and len(labels) == len(bins) - 1:
            return labels[-1]
        return f">={bins[-1]}"

    return "unknown"


def categorical_encode(value: Any, config: dict[str, Any]) -> int | list[int]:
    """Label encoding or one-hot encoding.

    Config:
        mode: "label" (default) | "onehot"
        categories: list of known categories
    """
    categories = config.get("categories", [])
    mode = config.get("mode", "label")
    str_value = str(value) if value is not None else ""

    if mode == "onehot":
        return [1 if cat == str_value else 0 for cat in categories]
    else:
        # label encoding
        if str_value in categories:
            return categories.index(str_value)
        return -1  # unknown category


def text_length(value: Any, config: dict[str, Any]) -> int:
    """Character or word count.

    Config:
        unit: "char" (default) | "word"
    """
    if value is None:
        return 0

    text = str(value)
    unit = config.get("unit", "char")

    if unit == "word":
        return len(text.split())
    return len(text)


def text_contains(value: Any, config: dict[str, Any]) -> bool:
    """Keyword presence check.

    Config:
        keywords: list of keywords to search for
        mode: "any" (default) | "all"
        case_sensitive: bool (default False)
    """
    if value is None:
        return False

    text = str(value)
    keywords = config.get("keywords", [])
    mode = config.get("mode", "any")
    case_sensitive = config.get("case_sensitive", False)

    if not case_sensitive:
        text = text.lower()
        keywords = [k.lower() for k in keywords]

    if mode == "all":
        return all(k in text for k in keywords)
    return any(k in text for k in keywords)


def temporal_extract(value: Any, config: dict[str, Any]) -> int | str:
    """Extract day/month/year/hour/day_of_week from a datetime string or timestamp.

    Config:
        component: "year" | "month" | "day" | "hour" | "day_of_week"
    """
    if value is None:
        return 0

    from datetime import datetime

    component = config.get("component", "year")

    # Try to parse if it's a string
    if isinstance(value, str):
        # Try ISO format first
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        else:
            return 0
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value)
    elif isinstance(value, datetime):
        dt = value
    else:
        return 0

    if component == "year":
        return dt.year
    elif component == "month":
        return dt.month
    elif component == "day":
        return dt.day
    elif component == "hour":
        return dt.hour
    elif component == "day_of_week":
        return dt.strftime("%A")
    else:
        return 0


def composite_ratio(record: dict[str, Any], config: dict[str, Any]) -> float:
    """Compute field_a / field_b.

    Config:
        field_a: str — field name for numerator
        field_b: str — field name for denominator
    """
    field_a = config.get("field_a", "")
    field_b = config.get("field_b", "")

    a = record.get(field_a)
    b = record.get(field_b)

    if a is None or b is None:
        return 0.0

    a_val = float(a)
    b_val = float(b)

    if b_val == 0:
        return 0.0

    return a_val / b_val


def composite_difference(record: dict[str, Any], config: dict[str, Any]) -> float:
    """Compute field_a - field_b.

    Config:
        field_a: str — field name for minuend
        field_b: str — field name for subtrahend
    """
    field_a = config.get("field_a", "")
    field_b = config.get("field_b", "")

    a = record.get(field_a)
    b = record.get(field_b)

    if a is None or b is None:
        return 0.0

    return float(a) - float(b)

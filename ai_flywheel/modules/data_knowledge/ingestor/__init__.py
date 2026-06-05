"""Universal Ingestor — Phase 2, Module #14.

Multi-format data ingestion with automatic format detection,
schema inference, and event-driven orchestration.

Supported formats: CSV, JSON, HTML, plain text.
"""

from .models import DataSource, IngestionRecord
from .parsers import (
    BaseParser,
    CSVParser,
    HTMLParser,
    JSONParser,
    TextParser,
    get_parser,
)
from .schemas import (
    DataSourceCreate,
    DataSourceResponse,
    IngestRequest,
    IngestResult,
    ParsedRecord,
)
from .service import UniversalIngestor

__all__ = [
    # Service
    "UniversalIngestor",
    # Models
    "DataSource",
    "IngestionRecord",
    # Schemas
    "DataSourceCreate",
    "DataSourceResponse",
    "IngestRequest",
    "IngestResult",
    "ParsedRecord",
    # Parsers
    "BaseParser",
    "CSVParser",
    "JSONParser",
    "HTMLParser",
    "TextParser",
    "get_parser",
]

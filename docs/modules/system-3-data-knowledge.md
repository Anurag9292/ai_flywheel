# System 3 — Data & Knowledge

> Ingestion, quality assurance, embeddings, knowledge graph construction, ground truth management, and privacy enforcement for all data flowing through the platform.

---

## Module 14: Universal Ingestor

**PDF, email, CSV, JSON, APIs, audio, images → structured data, schema detection, streaming + batch**

### What It Does

- Accepts data from any format — PDF, email (MIME/EML), CSV, JSON, XML, APIs, audio files, images, HTML, and proprietary formats — normalizing everything into structured, queryable representations
- Implements intelligent schema detection: automatically infers data types, relationships, and hierarchies from raw inputs without requiring user-specified schemas
- Supports both streaming (real-time webhooks, API polling, event streams) and batch (file uploads, scheduled pulls, bulk imports) ingestion modes
- Provides OCR and document understanding for PDFs and images: extracts tables, forms, headings, and semantic structure, not just raw text
- Implements audio transcription with speaker diarization, timestamp alignment, and automatic segmentation into semantic chunks
- Handles incremental ingestion with change detection — only reprocesses modified portions of data sources, with full/partial refresh options
- Provides data preview and validation before committing: shows parsed schema, sample rows, and detected issues for user confirmation
- Tracks data lineage from source through all transformations, maintaining provenance for every structured record produced

### Feedback Loop

Parsing failures and manual corrections train format-specific extractors to handle edge cases. Schema detection accuracy improves from user confirmations and rejections. Sources with frequent format changes get more aggressive re-detection.

### Feeds Into

- **Data Quality Engine (15)** — Raw ingested data flows through quality validation
- **Embedding Engine (16)** — Structured text is embedded for retrieval
- **Knowledge Graph Builder (17)** — Entities and relationships extracted from documents feed the graph
- **Feature Factory (20)** — Ingested data becomes raw material for feature engineering
- **Privacy & PII Engine (19)** — All ingested data passes through PII detection

### Fed By

- **Tool Forge (10)** — API integrations provide data source connections
- **Data Quality Engine (15)** — Quality issues trigger re-ingestion with improved parsing
- **Trace & Observability (5)** — Ingestion failures are traced and analyzed for systemic issues

---

## Module 15: Data Quality Engine

**Validation, anomaly detection, deduplication, entity resolution, lineage tracking**

### What It Does

- Runs configurable validation rules on all ingested data: type checks, range constraints, format patterns, referential integrity, and custom business rules
- Implements statistical anomaly detection: identifies outliers, distribution shifts, sudden volume changes, and unexpected null patterns across all data streams
- Performs deduplication using exact matching, fuzzy matching, and ML-based similarity scoring with configurable merge strategies
- Provides entity resolution: links records referring to the same real-world entity across different data sources using probabilistic matching
- Maintains full data lineage: tracks every transformation, merge, and derivation from raw source to final representation
- Generates data quality scores per source, per field, and per time window — enabling quality-aware downstream processing
- Implements data contracts: formal agreements on schema, quality thresholds, and freshness SLAs between producing and consuming modules
- Provides quarantine workflows for data that fails validation — hold for manual review, auto-fix with rules, or reject with notification

### Feedback Loop

False positive anomaly alerts (flagged but actually normal) refine detection thresholds. Deduplication merge errors (incorrectly merged or missed duplicates) improve matching models. Data contract violations that are waived inform relaxed thresholds.

### Feeds Into

- **Embedding Engine (16)** — Only quality-validated data gets embedded
- **Knowledge Graph Builder (17)** — Clean, deduplicated entities feed graph construction
- **Feature Factory (20)** — Data quality scores weight feature reliability
- **Labeling & Ground Truth (18)** — Quality issues create labeling tasks for ambiguous cases
- **Universal Ingestor (14)** — Quality failures trigger re-ingestion

### Fed By

- **Universal Ingestor (14)** — All raw ingested data flows through quality checks
- **Feedback Collector (33)** — User reports of bad data create quality rules
- **Trace & Observability (5)** — Downstream errors caused by bad data inform new validation rules
- **Model Forge (21)** — Model performance degradation linked to data quality issues

---

## Module 16: Embedding Engine

**Text/image/code embeddings, domain-adapted fine-tuning, vector store management, retrieval quality tracking**

### What It Does

- Generates embeddings for text, images, code, and multimodal content using configurable models (OpenAI, Cohere, open-source) with automatic batching and caching
- Manages vector stores per venture with configurable indexing strategies (HNSW, IVF, flat) optimized for the specific recall/latency tradeoffs needed
- Implements domain-adapted fine-tuning: trains custom embedding models on venture-specific data to improve retrieval relevance for specialized domains
- Tracks retrieval quality metrics: measures precision@k, recall@k, MRR, and NDCG against labeled relevance judgments, alerting on degradation
- Supports hybrid search combining dense embeddings with sparse (BM25) retrieval for best-of-both-worlds ranking
- Provides embedding versioning: when models are updated, manages the migration of all stored vectors with zero-downtime reindexing
- Implements chunking strategies for long documents: sentence, paragraph, semantic, and sliding window with overlap — optimized per content type
- Supports cross-modal retrieval: find images by text description, find code by natural language query, find similar documents by example
- **Versioned collections** — embeddings are stored in namespaced collections, each tied to a specific model and dimension. Never mix vectors from different models in the same similarity search. When upgrading models, the engine creates a v2 collection, routes new data there, and runs a background Temporal workflow to gradually re-embed older documents (querying v1 until migration completes).
- **Model migration workflows** — background Temporal workflow re-embeds documents in batches when switching to a better/cheaper model. System serves from the old collection until new collection is fully populated. Old collection kept for 30-day rollback window.
- **Query routing** — automatically routes similarity searches to the active collection for the venture. Embeds the query with the same model that produced the collection's vectors.

### Feedback Loop

Retrieval quality tracking identifies queries where embedding similarity fails to predict relevance — these become training pairs for fine-tuning. Click-through data and downstream task success rates validate whether retrieved content was actually useful.

### Feeds Into

- **Memory Engine (11)** — Semantic memory retrieval uses embeddings
- **Knowledge Graph Builder (17)** — Embedding similarity helps resolve entities and discover relationships
- **Agent Factory (9)** — RAG (retrieval-augmented generation) uses embeddings for context injection
- **Market & Signal Intelligence (25)** — Semantic search over market data
- **Pattern & Template Library (38)** — Similarity search over patterns

### Fed By

- **Data Quality Engine (15)** — Only clean data gets embedded
- **Labeling & Ground Truth (18)** — Relevance labels train embedding fine-tuning
- **Feedback Collector (33)** — User interactions reveal retrieval quality issues
- **Universal Ingestor (14)** — New content triggers embedding generation

---

## Module 17: Knowledge Graph Builder

**Entity extraction, relationships, ontology construction, domain knowledge, temporal facts, multi-source fusion, reasoning — absorbs old Domain Knowledge Extractor**

### What It Does

- Extracts entities (people, companies, products, concepts, events) and relationships from unstructured text using NER, relation extraction, and LLM-powered analysis
- Constructs domain-specific ontologies: identifies entity types, relationship types, and hierarchies relevant to each venture's domain
- Manages temporal facts: relationships and attributes have valid-from/valid-to timestamps, enabling point-in-time queries and change tracking
- Implements multi-source fusion: reconciles conflicting information from different sources using confidence scoring, recency weighting, and source reliability
- Provides graph reasoning: traverses relationships to infer implicit knowledge, detect contradictions, and answer complex multi-hop questions
- Supports graph versioning with full change history, enabling comparison of knowledge state across time periods
- Implements automatic knowledge maintenance: detects stale facts, validates against new data, and flags contradictions for review
- Exposes a query API supporting SPARQL-like graph queries, natural language questions, and path-finding between entities

### Feedback Loop

Query failures (questions the graph can't answer) identify knowledge gaps that drive targeted extraction. User corrections of incorrect facts improve extraction accuracy. Stale fact detection refines temporal validity heuristics.

### Feeds Into

- **Agent Factory (9)** — Agents query the knowledge graph for domain context
- **Memory Engine (11)** — Graph facts feed semantic memory
- **Venture Thesis Engine (27)** — Market entities and relationships inform hypotheses
- **Customer Discovery Engine (26)** — Customer/market knowledge supports interview analysis
- **Feature Factory (20)** — Graph features (degree, centrality, paths) become ML features

### Fed By

- **Universal Ingestor (14)** — Documents provide raw text for entity extraction
- **Data Quality Engine (15)** — Clean, deduplicated records feed reliable graph construction
- **Embedding Engine (16)** — Similarity helps entity resolution and relationship discovery
- **Labeling & Ground Truth (18)** — Labeled entity/relation data trains extraction models
- **Market & Signal Intelligence (25)** — Market data provides entities and relationships

---

## Module 18: Labeling & Ground Truth

**Annotation tasks, gold datasets, multi-annotator, disagreement resolution, benchmark versioning, production errors → eval cases**

### What It Does

- Creates and manages annotation tasks: routing items to annotators with task-specific interfaces, instructions, and quality controls
- Maintains gold datasets: curated, version-controlled sets of labeled examples that serve as ground truth for evaluation and training
- Supports multi-annotator workflows with configurable overlap, measuring inter-annotator agreement (Cohen's kappa, Fleiss' kappa, Krippendorff's alpha)
- Implements disagreement resolution: escalation to expert annotators, majority voting, adjudication queues, and consensus protocols
- Provides benchmark versioning: track how gold datasets evolve over time, enabling fair comparison of models trained/evaluated at different points
- Converts production errors into evaluation cases: when agents fail in production and humans correct them, those corrections become labeled examples
- Supports active learning: prioritizes annotation of examples where models are most uncertain, maximizing label efficiency
- Implements annotation quality assurance: gold-standard checks, annotator calibration, and consistency monitoring with feedback loops

### Feedback Loop

Annotator disagreement patterns reveal ambiguous label definitions that need clarification. Production error rates per category identify where gold datasets need expansion. Model performance gaps between benchmarks and production indicate benchmark staleness.

### Feeds Into

- **Model Forge (21)** — Labeled data trains and fine-tunes models
- **Evaluation Framework (22)** — Gold datasets define evaluation benchmarks
- **Embedding Engine (16)** — Relevance labels train embedding fine-tuning
- **Knowledge Graph Builder (17)** — Labeled entities/relations train extraction models
- **Prompt Studio (8)** — Labeled examples become few-shot examples in prompts

### Fed By

- **Human Review Engine (12)** — Human corrections become labeled examples
- **Feedback Collector (33)** — User feedback identifies mislabeled or missing cases
- **Agent Factory (9)** — Agent failures in production generate annotation tasks
- **Data Quality Engine (15)** — Ambiguous data cases route to human annotation
- **Synthetic Data Generator (23)** — Synthetic examples bootstrap annotation with pre-labels

---

## Module 19: Privacy & PII Engine

**PII detection, redaction, retention policies, consent management, data residency, prevent leakage into prompts/logs**

### What It Does

- Detects PII across all data flows using pattern matching, ML classifiers, and context-aware analysis — covering names, emails, phones, SSNs, addresses, financial data, health info, and custom entity types
- Implements configurable redaction strategies: masking, tokenization (reversible pseudonymization), generalization, and synthetic replacement
- Enforces retention policies: automatically deletes or anonymizes data after configured retention periods, with legal hold exceptions
- Manages consent records: tracks per-user consent for data processing, with granular purpose-based permissions and revocation support
- Prevents PII leakage into LLM prompts: scans all context injected into prompts and redacts PII before it reaches external model providers
- Prevents PII leakage into logs and traces: sanitizes observability data to ensure debugging information doesn't contain personal data
- Enforces data residency requirements: ensures data for specific ventures/regions stays within required geographic boundaries
- Provides data subject access request (DSAR) handling: locate, export, or delete all data associated with a specific individual across the platform

### Feedback Loop

False positive PII detections (legitimate data incorrectly redacted) and false negatives (PII that slipped through) continuously improve detection models. Residency violation near-misses strengthen routing rules. DSAR execution gaps reveal untracked data stores.

### Feeds Into

- **All modules** — Privacy rules are enforced upstream of all data processing
- **LLM Gateway (7)** — PII scrubbing happens before prompts are sent to external providers
- **Trace & Observability (5)** — Sanitized logs prevent PII in debugging data
- **Identity & Tenancy (2)** — Data isolation is enforced at the privacy layer
- **Policy Engine (13)** — Privacy rules are a subset of the policy framework

### Fed By

- **Universal Ingestor (14)** — All ingested data passes through PII detection
- **Identity & Tenancy (2)** — Consent and residency requirements come from user/venture config
- **Feedback Collector (33)** — User reports of exposed PII improve detection
- **Reliability & Incident Engine (37)** — Privacy incidents trigger rule tightening

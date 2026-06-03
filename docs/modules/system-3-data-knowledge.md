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

**A configurable multi-agent pipeline for constructing, maintaining, and exporting structured knowledge representations — not a single agent, but a deep pipeline where each step has independent evaluation and experimentation.**

### The KG Construction Pipeline

The Knowledge Graph Builder is composed of specialized sub-agents, each handling a distinct phase:

**ANALYSIS PHASE:**
- **Structure Inferrer** — Analyzes document structure (headings, sections, tables, lists) to understand organizational hierarchy before extraction
- **Visual Analyzer** — Processes images, tables, diagrams, and charts to extract structured information that text-only approaches miss
- **Summarizer** — Produces section-level and document-level summaries used as context during extraction

**EXTRACTION PHASE:**
- **Ontology Extractor** — Infers what TYPES of entities exist in this customer's domain (Person, Product, Process, Team, Policy, etc.) and defines the schema before entity extraction begins. This is the foundation — getting the ontology wrong means everything downstream is wrong.
- **Relationship Extractor** — Identifies what relationship TYPES exist (owns, reports_to, depends_on, contradicts, supersedes, etc.) and defines the edge schema

**TRANSFORMATION PHASE:**
- **Entity Extractor** — Finds all instances of each entity type across all documents. Uses the ontology as a constraint.
- **Entity Resolver** — Deduplicates and merges entities that refer to the same real-world thing ("John Smith" = "J. Smith" = "the VP of Engineering"). This is one of the hardest sub-problems.
- **Relationship Mapper** — Connects resolved entities with typed edges. Validates that relationships conform to the defined schema.
- **KG Builder** — Assembles the final graph structure from resolved entities and validated relationships.

**EXPORT PHASE:**
- **Schema Exporter** — Exports the typed schema (entity types, relationship types, constraints) for use at query time. This schema is what constrains the LLM to prevent hallucination.

### Schema-Constrained Generation (Anti-Hallucination)

The graph schema is used at query time to prevent hallucination:
- The schema defines what entities and relationships EXIST in this customer's knowledge base
- When a user asks a question, the system first queries the graph for factual grounding
- The synthesis agent is constrained to ONLY reference entities that actually exist in the graph
- If the LLM tries to invent an entity not in the graph, the constraint catches it
- Example: User asks "What products does Acme make?" → Graph lookup returns [WidgetPro, DataSync] → LLM can ONLY reference these two, cannot hallucinate a third product

### Per-Step Evaluation

Each pipeline step has independent evaluation metrics:

| Step | Metric | What it measures |
|------|--------|-----------------|
| Ontology Extraction | Coverage score | % of real entity types captured |
| Ontology Extraction | Precision | Are extracted types real (not noise)? |
| Entity Extraction | Recall | % of all entities found |
| Entity Extraction | Precision | % of extracted entities that are real |
| Entity Resolution | F1 score | Correct merges vs. incorrect merges vs. missed merges |
| Relationship Extraction | Accuracy | % of edges that are factually correct |
| Relationship Extraction | Coverage | % of real relationships captured |
| Schema Export | Constraint effectiveness | How much does schema reduce hallucination rate? |
| End-to-end | Graph utility | Do answers improve when using the graph vs. not? |

### Per-Step Experimentation

Each step is independently A/B testable via the Experiment Tracker:
- Test different ontology extraction prompts (zero-shot vs few-shot vs iterative refinement)
- Test different entity resolution strategies (embedding similarity vs fuzzy matching vs LLM-based)
- Test different relationship extraction approaches (per-document vs cross-document vs hybrid)
- Test schema injection strategies at query time (full schema vs relevant sub-schema vs graph traversal results only)
- Each experiment runs independently without affecting other steps

### The Research Imperative

Building a production-grade knowledge graph is NOT a wrapper problem. It requires:
- Reading academic papers on ontology learning, entity resolution, and relationship extraction
- Understanding which approaches work for which data types
- When the system doesn't know how to solve a sub-problem: surface it to the founder, suggest papers, ask for sample implementations
- The Academic Radar capabilities of Market & Signal Intelligence should be actively finding new KG construction techniques

### Feedback Loop

- Query-time failures (hallucinated entities, wrong relationships cited) trace back to specific pipeline steps
- Entity resolution errors are detected when users correct an answer referencing the wrong entity
- Ontology gaps are detected when queries can't be answered because the entity type wasn't extracted
- Schema effectiveness is measured by comparing hallucination rates with/without schema constraint
- Each improvement at any step compounds with improvements at other steps (multiplicative quality)

### Feeds Into

- **Agent Factory (9)** — graph schema constrains agent generation at query time
- **Embedding Engine (16)** — graph entities enrich embedding metadata for filtered retrieval
- **Evaluation Framework (22)** — graph accuracy is a core evaluation dimension
- **Memory Engine (11)** — graph provides semantic memory (facts) to agents

### Fed By

- **Universal Ingestor (14)** — raw documents to process
- **Data Quality Engine (15)** — clean, deduplicated source data
- **Feedback Collector (33)** — user corrections reveal graph errors
- **Experiment Tracker (31)** — experiment results improve each pipeline step
- **Labeling & Ground Truth (18)** — gold-standard entity/relationship labels for evaluation

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

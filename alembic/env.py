"""Alembic environment configuration for async migrations."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from ai_flywheel.core.config import settings

# Import all models so Alembic can detect them
from ai_flywheel.core.models import (  # noqa: F401
    CostRecord,
    PersistedEvent,
    TraceSpan,
    Venture,
)
from ai_flywheel.core.models.base import Base
from ai_flywheel.modules.agent_runtime.agent_factory.models import AgentBlueprint  # noqa: F401
from ai_flywheel.modules.agent_runtime.human_review.models import (  # noqa: F401
    ReviewItem,
    ReviewPolicy,
)
from ai_flywheel.modules.agent_runtime.memory_engine.models import MemoryEntry  # noqa: F401
from ai_flywheel.modules.agent_runtime.policy_engine.models import (  # noqa: F401
    Policy,
    PolicyViolation,
)
from ai_flywheel.modules.agent_runtime.prompt_studio.models import (  # noqa: F401
    PromptTemplate,
    PromptVersion,
)
from ai_flywheel.modules.agent_runtime.tool_forge.models import (  # noqa: F401
    ToolDefinition,
    ToolExecution,
)
from ai_flywheel.modules.cross_venture.meta_learning.models import (  # noqa: F401
    CrossVentureInsight,
    FlywheelMetric,
)
from ai_flywheel.modules.cross_venture.pattern_library.models import (  # noqa: F401
    Pattern,
    PatternApplication,
)
from ai_flywheel.modules.data_knowledge.embeddings.models import (  # noqa: F401
    EmbeddingCollection,
    EmbeddingDocument,
)
from ai_flywheel.modules.data_knowledge.ingestor.models import (  # noqa: F401
    DataSource,
    IngestionRecord,
)
from ai_flywheel.modules.data_knowledge.knowledge_graph.models import (  # noqa: F401
    Entity,
    KnowledgeGraph,
    Relationship,
)
from ai_flywheel.modules.data_knowledge.labeling.models import LabelingTask, LabelItem  # noqa: F401
from ai_flywheel.modules.data_knowledge.privacy.models import (  # noqa: F401
    PIIDetection,
    RetentionPolicy,
)
from ai_flywheel.modules.data_knowledge.quality.models import (  # noqa: F401
    QualityReport,
    QualityRule,
)
from ai_flywheel.modules.deployment.deployment_engine.models import (  # noqa: F401
    Deployment,
    DeploymentEvent,
)
from ai_flywheel.modules.deployment.reliability.models import HealthMetric, Incident  # noqa: F401
from ai_flywheel.modules.experimentation.ab_testing.models import (  # noqa: F401
    Experiment,
    ExperimentObservation,
)
from ai_flywheel.modules.experimentation.cost_optimizer.models import (  # noqa: F401
    Budget,
    CostAlert,
)
from ai_flywheel.modules.experimentation.feedback.models import FeedbackItem  # noqa: F401
from ai_flywheel.modules.ml_evaluation.evaluation.models import EvalRun, EvalSuite  # noqa: F401
from ai_flywheel.modules.ml_evaluation.feature_factory.models import (  # noqa: F401
    FeatureDefinition,
    FeatureSet,
)
from ai_flywheel.modules.ml_evaluation.model_forge.models import (  # noqa: F401
    ModelDefinition,
    TrainingRun,
)
from ai_flywheel.modules.ml_evaluation.simulation.models import Simulation  # noqa: F401
from ai_flywheel.modules.ml_evaluation.synthetic_data.models import SyntheticDataset  # noqa: F401
from ai_flywheel.modules.product_intelligence.customer_discovery.models import (  # noqa: F401
    Assumption,
    DiscoveryProject,
    Interview,
)
from ai_flywheel.modules.product_intelligence.market_intelligence.models import (  # noqa: F401
    MarketReport,
    MarketSignal,
    SignalSource,
)
from ai_flywheel.modules.product_intelligence.offer_design.models import (  # noqa: F401
    MessagingVariant,
    Offer,
)
from ai_flywheel.modules.product_intelligence.product_experience.models import (
    ProductSpec,  # noqa: F401
)
from ai_flywheel.modules.product_intelligence.venture_thesis.models import (  # noqa: F401
    EvidenceItem,
    Thesis,
    ThesisAssumption,
)
from ai_flywheel.modules.product_intelligence.workflow_blueprint.models import (
    WorkflowBlueprint,  # noqa: F401
)
from alembic import context

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in async mode."""
    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

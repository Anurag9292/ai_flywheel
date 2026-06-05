"""Unit tests for PromptStudio service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.agent_runtime.prompt_studio.schemas import (
    PromptRenderRequest,
    PromptTemplateCreate,
    PromptTemplateUpdate,
)
from ai_flywheel.modules.agent_runtime.prompt_studio.service import (
    PromptStudio,
    RenderError,
)


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def fake_template():
    """Create a fake PromptTemplate ORM object with model_validate support."""
    template = MagicMock()
    template.id = "tpl-001"
    template.venture_id = "ven-001"
    template.name = "greeting_template"
    template.description = "A greeting template"
    template.template_text = "Hello, {{ name }}! Welcome to {{ service }}."
    template.input_variables = ["name", "service"]
    template.tags = ["onboarding"]
    template.category = "user-facing"
    template.is_active = True
    template.current_version = 1
    template.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    template.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    template.deleted_at = None
    template.versions = []
    return template


@pytest.fixture
def fake_version():
    """Create a fake PromptVersion ORM object."""
    version = MagicMock()
    version.id = "ver-001"
    version.template_id = "tpl-001"
    version.venture_id = "ven-001"
    version.version_number = 1
    version.template_text = "Hello, {{ name }}! Welcome to {{ service }}."
    version.input_variables = ["name", "service"]
    version.change_description = "Initial version"
    version.created_by = None
    version.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return version


@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_session")
async def test_create_template_stores_and_emits_event(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_template
):
    """create_template should persist template + version and emit prompt.created."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # Mock flush to simulate ID assignment
    call_count = [0]

    def flush_side_effect():
        call_count[0] += 1

    mock_session.flush.side_effect = flush_side_effect

    # Patch model_validate to return a response object
    with patch(
        "ai_flywheel.modules.agent_runtime.prompt_studio.service.PromptTemplateResponse"
    ) as MockResponse:
        mock_response = MagicMock()
        mock_response.id = "tpl-001"
        mock_response.name = "greeting_template"
        mock_response.category = "user-facing"
        mock_response.current_version = 1
        MockResponse.model_validate.return_value = mock_response

        studio = PromptStudio()
        data = PromptTemplateCreate(
            name="greeting_template",
            description="A greeting template",
            template_text="Hello, {{ name }}!",
            input_variables=["name"],
            tags=["onboarding"],
            category="user-facing",
        )
        result = await studio.create_template("ven-001", data)

    # Template and version were added
    assert mock_session.add.call_count == 2
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "prompt.created"
    assert publish_kwargs["venture_id"] == "ven-001"


@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_session")
async def test_render_with_valid_variables(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_template
):
    """render should return rendered text when all variables are provided."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # Mock get_template to return our fake template response
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_template
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_flywheel.modules.agent_runtime.prompt_studio.service.PromptTemplateResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "tpl-001"
        mock_resp.name = "greeting_template"
        mock_resp.template_text = "Hello, {{ name }}! Welcome to {{ service }}."
        mock_resp.current_version = 1
        MockResponse.model_validate.return_value = mock_resp

        studio = PromptStudio()
        request = PromptRenderRequest(
            template_id="tpl-001",
            variables={"name": "Alice", "service": "Flywheel"},
        )
        result = await studio.render("ven-001", request)

    assert result.rendered_text == "Hello, Alice! Welcome to Flywheel."
    assert result.template_id == "tpl-001"
    assert result.version_used == 1


@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_session")
async def test_render_with_missing_variables_raises(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_template
):
    """render should raise RenderError when required variables are missing."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_template
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_flywheel.modules.agent_runtime.prompt_studio.service.PromptTemplateResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "tpl-001"
        mock_resp.name = "greeting_template"
        mock_resp.template_text = "Hello, {{ name }}! Welcome to {{ service }}."
        mock_resp.current_version = 1
        MockResponse.model_validate.return_value = mock_resp

        studio = PromptStudio()
        request = PromptRenderRequest(
            template_id="tpl-001",
            variables={"name": "Alice"},  # Missing 'service'
        )

        with pytest.raises(RenderError, match="Missing variable"):
            await studio.render("ven-001", request)


@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_session")
async def test_update_template_creates_new_version(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_template
):
    """update_template with new template_text should increment version."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_template
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_flywheel.modules.agent_runtime.prompt_studio.service.PromptTemplateResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "tpl-001"
        mock_resp.name = "greeting_template"
        mock_resp.current_version = 2
        MockResponse.model_validate.return_value = mock_resp

        studio = PromptStudio()
        # Patch _extract_variables to avoid jinja2.meta import issue
        studio._extract_variables = MagicMock(return_value=["name"])

        data = PromptTemplateUpdate(
            template_text="Hi {{ name }}, glad you're here!",
            change_description="Simplified greeting",
        )
        result = await studio.update_template("ven-001", "tpl-001", data)

    # Version should be incremented on the template object
    assert fake_template.current_version == 2
    # A new version record should be added
    assert mock_session.add.called
    mock_event_bus.publish.assert_awaited_once()
    publish_kwargs = mock_event_bus.publish.call_args[1]
    assert publish_kwargs["event_type"] == "prompt.updated"
    assert publish_kwargs["payload"]["text_changed"] is True


@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_session")
async def test_rollback_template_restores_old_text(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_template, fake_version
):
    """rollback_template should restore template_text from target version."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # rollback_template does two execute calls in one session block:
    # 1. Fetch the template (scalar_one_or_none)
    # 2. Fetch the target version (scalar_one_or_none)
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # First execute: fetch template
            result.scalar_one_or_none.return_value = fake_template
        else:
            # Second execute: fetch target version
            result.scalar_one_or_none.return_value = fake_version
        return result

    mock_session.execute.side_effect = execute_side_effect

    # Modify template to be at version 3 with different text
    fake_template.current_version = 3
    fake_template.template_text = "Version 3 text: {{ name }}"

    with patch(
        "ai_flywheel.modules.agent_runtime.prompt_studio.service.PromptTemplateResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "tpl-001"
        mock_resp.name = "greeting_template"
        mock_resp.current_version = 4
        MockResponse.model_validate.return_value = mock_resp

        studio = PromptStudio()
        result = await studio.rollback_template("ven-001", "tpl-001", version_number=1)

    # Template text should be restored from version 1
    assert fake_template.template_text == fake_version.template_text
    assert fake_template.current_version == 4  # incremented from 3
    mock_event_bus.publish.assert_awaited()
    # Find the rollback event
    for call in mock_event_bus.publish.call_args_list:
        kwargs = call[1]
        if kwargs.get("event_type") == "prompt.rolled_back":
            assert kwargs["payload"]["rolled_back_to"] == 1
            break


@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_event_bus")
@patch("ai_flywheel.modules.agent_runtime.prompt_studio.service.get_session")
async def test_get_version_history_returns_versions(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus, fake_template, fake_version
):
    """get_version_history should return versions in order."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # First execute for get_template, second for version list
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = fake_template
        else:
            result.scalars.return_value.all.return_value = [fake_version]
        return result

    mock_session.execute.side_effect = execute_side_effect

    with patch(
        "ai_flywheel.modules.agent_runtime.prompt_studio.service.PromptTemplateResponse"
    ) as MockResponse:
        mock_resp = MagicMock()
        mock_resp.id = "tpl-001"
        MockResponse.model_validate.return_value = mock_resp

        with patch(
            "ai_flywheel.modules.agent_runtime.prompt_studio.service.PromptVersionResponse"
        ) as MockVersionResponse:
            mock_ver_resp = MagicMock()
            mock_ver_resp.version_number = 1
            MockVersionResponse.model_validate.return_value = mock_ver_resp

            studio = PromptStudio()
            result = await studio.get_version_history("ven-001", "tpl-001")

    assert len(result) == 1
    assert result[0].version_number == 1

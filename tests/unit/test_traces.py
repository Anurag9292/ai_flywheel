"""Tests for distributed tracing."""

import pytest

from ai_flywheel.core.traces import Tracer, get_tracer, traced


@pytest.fixture
def tracer():
    return Tracer()


async def test_span_creates_trace(tracer: Tracer):
    """A span should create trace data."""
    async with tracer.span("test_module", "test_op") as span:
        span.output_data = {"result": "ok"}

    spans = tracer.get_pending_spans()
    assert len(spans) == 1
    assert spans[0].module_name == "test_module"
    assert spans[0].operation == "test_op"
    assert spans[0].status == "ok"
    assert spans[0].duration_ms is not None
    assert spans[0].duration_ms >= 0


async def test_span_records_cost(tracer: Tracer):
    """Cost should be recordable on a span."""
    async with tracer.span("llm_gateway", "complete") as span:
        span.set_cost(cost_usd=0.03, tokens_input=150, tokens_output=50, model="gpt-4o")

    spans = tracer.get_pending_spans()
    assert spans[0].cost_usd == 0.03
    assert spans[0].tokens_input == 150
    assert spans[0].tokens_output == 50
    assert spans[0].model_name == "gpt-4o"


async def test_span_records_error(tracer: Tracer):
    """Errors should be captured on the span."""
    with pytest.raises(ValueError):
        async with tracer.span("module", "failing_op") as span:
            raise ValueError("something broke")

    spans = tracer.get_pending_spans()
    assert spans[0].status == "error"
    assert "ValueError: something broke" in spans[0].error_message


async def test_nested_spans_propagate_trace_id(tracer: Tracer):
    """Nested spans should share the same trace_id."""
    async with tracer.span("parent_module", "parent_op") as parent:
        async with tracer.span("child_module", "child_op") as child:
            pass

    spans = tracer.get_pending_spans()
    assert len(spans) == 2
    # Both should have same trace_id
    assert spans[0].trace_id == spans[1].trace_id
    # Child's parent should be the outer span
    assert spans[0].parent_span_id == spans[1].span_id


async def test_span_to_dict(tracer: Tracer):
    """Span should serialize to dict for persistence."""
    async with tracer.span("mod", "op") as span:
        span.set_cost(0.01, 100, 50, "gpt-4o-mini")

    spans = tracer.get_pending_spans()
    d = spans[0].to_dict()
    assert d["module_name"] == "mod"
    assert d["operation"] == "op"
    assert d["cost_usd"] == 0.01
    assert d["model_name"] == "gpt-4o-mini"
    assert "started_at" in d
    assert "ended_at" in d


async def test_venture_context(tracer: Tracer):
    """Venture context should be propagated to spans."""
    tracer.set_venture_context("venture-123")
    async with tracer.span("mod", "op"):
        pass

    spans = tracer.get_pending_spans()
    assert spans[0].venture_id == "venture-123"

from fastapi.testclient import TestClient

from flywheel.devserver.app import app

client = TestClient(app)


def setup_function() -> None:
    # Each test starts from a clean in-memory trace state.
    client.post("/api/reset")


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_venture_endpoint_returns_functions_and_lint() -> None:
    r = client.get("/api/venture")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "postlineai"
    fn_names = {f["name"] for f in body["functions"]}
    assert {"market-exploration", "gtm", "customer-success"} <= fn_names
    # The venture composition is clean against the live graph.
    assert body["lint"]["unknown_nodes"] == []
    assert body["lint"]["inactive_nodes"] == []


def test_topology_endpoint_returns_describe_shape() -> None:
    r = client.get("/api/topology")
    assert r.status_code == 200
    topo = r.json()
    names = {n["name"] for n in topo["nodes"]}
    # Steps 1–4 nodes are all registered in the dev runtime.
    assert {
        "thesis-tracker",
        "market-scanner",
        "pain-extractor",
        "ad-campaign-runner",
        "ad-analytics-collector",
        "signal-analyzer",
        "founder-notifier",
    } <= names
    assert "llm-gateway" in topo["libraries"]
    assert topo["substrate"]["name"] == "trace-recorder"


def test_publish_triggers_real_multistep_run() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "research.requested",
            "venture_id": "postlineai",
            "payload": {
                "thesis": "B2B founders pay $499/mo",
                "keywords": ["linkedin ghostwriter"],
                "competitor_query": "AI LinkedIn ghostwriting competitors",
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    chain = body["chain"]
    nodes = [s["node"] for s in chain["steps"]]
    # The real chain: market-scanner -> thesis-tracker (reacting to the
    # landscape) -> founder-notifier (reacting to the thesis update). The chain
    # growing as nodes subscribe is the event-driven reuse payoff.
    assert nodes == ["market-scanner", "thesis-tracker", "founder-notifier"]
    assert chain["steps"][0]["is_start"] is True
    assert chain["steps"][-1]["is_end"] is True


def test_publish_transcript_runs_step3_chain() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "transcript.captured",
            "venture_id": "postlineai",
            "payload": {"transcript": "no time, posts flop", "speaker": "Founder A"},
        },
    )
    assert r.status_code == 200
    nodes = [s["node"] for s in r.json()["chain"]["steps"]]
    # pain-extractor -> thesis-tracker -> founder-notifier (reuse by subscription).
    assert nodes == ["pain-extractor", "thesis-tracker", "founder-notifier"]


def test_publish_campaign_runs_step4_decision_loop() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "campaign.requested",
            "venture_id": "postlineai",
            "payload": {
                "platform": "linkedin",
                "name": "ghostwriting waitlist",
                "budget_usd": 200,
                "landing_page": "/postlineai",
                "rubric": "would pay $499/mo",
            },
        },
    )
    assert r.status_code == 200
    steps = r.json()["chain"]["steps"]
    nodes = [s["node"] for s in steps]
    # The full ads -> analyze -> decide loop the architecture exists to prove.
    # signal.verdict fans out to BOTH thesis-tracker and founder-notifier, and
    # the resulting thesis.state.updated notifies the founder again — so
    # founder-notifier legitimately appears twice. Assert the loop, not a brittle
    # exact sequence.
    assert nodes[:3] == ["ad-campaign-runner", "ad-analytics-collector", "signal-analyzer"]
    assert "thesis-tracker" in nodes
    assert nodes.count("founder-notifier") == 2
    # Causal: first step is the trigger, last step is terminal.
    assert steps[0]["is_start"] is True
    assert steps[-1]["is_end"] is True


def test_traces_reflects_published_runs_and_reset() -> None:
    client.post("/api/publish", json={"type": "research.requested", "payload": {}})
    body = client.get("/api/traces").json()
    assert body["count"] >= 1
    assert len(body["chains"]) >= 1

    client.post("/api/reset")
    assert client.get("/api/traces").json()["count"] == 0


def test_evidence_event_runs_thesis_tracker_only() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "evidence.collected",
            "payload": {"assumption": "willing_to_pay_499", "supports": True},
        },
    )
    nodes = [s["node"] for s in r.json()["chain"]["steps"]]
    # thesis-tracker reacts, then founder-notifier reacts to its update.
    assert nodes == ["thesis-tracker", "founder-notifier"]


def test_wizard_of_oz_park_then_approve_resume() -> None:
    # Run 1: customer input is drafted (human) and parked for review.
    r1 = client.post(
        "/api/publish",
        json={
            "type": "inbound.received",
            "venture_id": "postlineai",
            "payload": {"customer_id": "c1", "kind": "text", "content": "talk about hiring"},
        },
    )
    nodes1 = [s["node"] for s in r1.json()["chain"]["steps"]]
    # input-intake -> post-drafter -> human-review-queue (parks, emits nothing).
    assert nodes1 == ["input-intake", "post-drafter", "human-review-queue"]

    # The draft is now visible as a pending review item.
    pending = client.get("/api/review").json()["pending"]
    mine = [p for p in pending if p["payload"].get("customer_id") == "c1"]
    assert len(mine) == 1
    parked_id = mine[0]["event_id"]

    parked_correlation = mine[0]["correlation_id"]
    # The park run and the resume run share one correlation id.
    assert r1.json()["correlation_id"] == parked_correlation

    # Run 2: founder approves with the real text -> chain resumes and publishes.
    r2 = client.post(
        "/api/review/approve",
        json={"event_id": parked_id, "draft": "The real ghostwritten post."},
    )
    body2 = r2.json()
    # The approval reuses the parked correlation id so the two runs are stitched.
    assert body2["correlation_id"] == parked_correlation
    nodes2 = [s["node"] for s in body2["chain"]["steps"]]
    # The merged chain shows the full draft->park->approve->publish story, then
    # (Step 6) the published post flows into engagement analytics -> signal ->
    # thesis + founder. The first five steps are the Wizard-of-Oz spine:
    assert nodes2[:5] == [
        "input-intake",
        "post-drafter",
        "human-review-queue",
        "human-review-queue",
        "post-scheduler",
    ]
    # Step-6 reuse: publishing triggers analytics + signal-analyzer downstream.
    assert "post-analytics-collector" in nodes2
    assert "signal-analyzer" in nodes2

    # /api/traces groups it as a SINGLE chain (one correlation id), not two.
    chains = client.get("/api/traces").json()["chains"]
    matching = [c for c in chains if c["correlation_id"] == parked_correlation]
    assert len(matching) == 1
    assert len(matching[0]["steps"]) == len(nodes2)

    # Item is no longer pending after approval.
    still = [p for p in client.get("/api/review").json()["pending"] if p["event_id"] == parked_id]
    assert still == []


def test_survey_request_runs_step6_chain() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "survey.requested",
            "venture_id": "postlineai",
            "payload": {"customer_id": "c1", "nps": 9, "rubric": "happy to renew?"},
        },
    )
    nodes = [s["node"] for s in r.json()["chain"]["steps"]]
    # customer-survey -> survey.responded fans out to signal-analyzer AND
    # thesis-tracker; the verdict + thesis update then reach founder-notifier.
    assert nodes[0] == "customer-survey"
    assert "signal-analyzer" in nodes
    assert "thesis-tracker" in nodes


def test_subscription_request_activates_and_charges() -> None:
    r = client.post(
        "/api/publish",
        json={
            "type": "subscription.requested",
            "venture_id": "postlineai",
            "payload": {"customer_id": "c9", "plan": "trial", "amount_usd": 299},
        },
    )
    nodes = [s["node"] for s in r.json()["chain"]["steps"]]
    assert nodes == ["subscription-manager"]


def test_build_chain_orders_and_links_causally() -> None:
    from flywheel.devserver.app import _build_chain

    # Two steps in one run: scanner emits e1, which triggers tracker.
    steps = [
        {
            "captured_at": "2026-01-01T00:00:00.002+00:00",
            "node": "thesis-tracker",
            "trigger_event_id": "e1",
            "trigger_type": "market.landscape.summarized",
            "emitted_event_ids": ["e2"],
        },
        {
            "captured_at": "2026-01-01T00:00:00.001+00:00",
            "node": "market-scanner",
            "trigger_event_id": "root",
            "trigger_type": "research.requested",
            "emitted_event_ids": ["e1"],
        },
    ]
    chain = _build_chain("c1", steps)
    s = chain["steps"]

    # Sorted chronologically: scanner first.
    assert [x["node"] for x in s] == ["market-scanner", "thesis-tracker"]
    assert s[0]["seq"] == 0 and s[1]["seq"] == 1
    # Causality: tracker's parent is the scanner step.
    assert s[0]["parent_step"] is None and s[0]["is_start"] is True
    assert s[1]["parent_step"] == 0
    # Start is consumed downstream (not end); tracker is the end.
    assert s[0]["is_end"] is False
    assert s[1]["is_end"] is True

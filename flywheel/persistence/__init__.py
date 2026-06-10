"""Persistence — the first *durable* substrate in the system.

Derived in the **public-data ingestion** step (see ``new_docs/layer1-nodes.md``):
the ``source-registry`` / ``source-scraper`` / ``knowledge-builder`` nodes need
to remember sources, the records they've ingested, a per-source cursor that
survives restarts, and the knowledge graph / materialized views built from
those records. That durable state is the concrete trigger ``new_docs/stack.md``
names for **Postgres (Neon)**.

Per the repo's fake/real Protocol seam, every store is a ``Protocol`` with:

  - an **in-memory fake** (``InMemory*Store``) — zero-infra, used by unit tests
    and the dev demo, exactly like ``FakeLLMGateway`` / ``FakeJobBoardClient``;
  - a **real SQLAlchemy** impl (``Sql*Store``) targeting Neon Postgres, swapped
    in behind the identical interface when ``DB_URL`` is set.

Nothing here imports a venture (Layer 1 dependency rule). Nodes depend only on
the Protocols, never on a concrete store — so swapping Neon for any other
Postgres (or back to a fake) never touches node code.
"""

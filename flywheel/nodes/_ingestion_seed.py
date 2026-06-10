"""Seed data for the public-data ingestion demo (canned, offline).

These are **small, shape-faithful samples** of the six public ATS job boards the
user pointed at — used only as canned fixtures so the ``source-scraper`` +
``knowledge-builder`` run end-to-end with zero network in the dev demo and
tests. They are deliberately *not* encoded as provider adapters: the agentic
scraper infers each source's schema generically (Lever array-at-root with
``createdAt`` epoch-ms; Greenhouse ``{jobs, meta}`` with ISO ``updated_at``;
Ashby ``{jobs, apiVersion}`` with ISO ``publishedAt``).

Each body is stamped with a ``_company`` field by the seed so the deterministic
``StructuralExtractor`` can attribute jobs to a company even when the provider
encodes the company only in the URL path.
"""

from __future__ import annotations

from typing import Any

# (source_id, url, canned_body)
SEED_SOURCES: list[dict[str, Any]] = [
    {
        "id": "lever-mindtickle",
        "url": "https://api.lever.co/v0/postings/mindtickle?mode=json",
        "company": "Mindtickle",
        "body": [
            {
                "id": "mt-1",
                "text": "Content Marketing Manager",
                "createdAt": 1776772338840,
                "categories": {"department": "Marketing", "location": "Pune"},
                "_company": "Mindtickle",
            },
            {
                "id": "mt-2",
                "text": "Brand Designer",
                "createdAt": 1776772300000,
                "categories": {"department": "Design", "location": "Remote"},
                "_company": "Mindtickle",
            },
        ],
    },
    {
        "id": "lever-nium",
        "url": "https://api.lever.co/v0/postings/nium?mode=json",
        "company": "Nium",
        "body": [
            {
                "id": "ni-1",
                "text": "Head of Content",
                "createdAt": 1776700000000,
                "categories": {"department": "Marketing", "location": "Singapore"},
                "_company": "Nium",
            },
        ],
    },
    {
        "id": "lever-scaleway",
        "url": "https://api.lever.co/v0/postings/scaleway?mode=json",
        "company": "Scaleway",
        "body": [
            {
                "id": "sc-1",
                "text": "Content Strategist",
                "createdAt": 1776600000000,
                "categories": {"department": "Marketing", "location": "Paris"},
                "_company": "Scaleway",
            },
        ],
    },
    {
        "id": "greenhouse-webflow",
        "url": "https://boards-api.greenhouse.io/v1/boards/webflow/jobs?content=true",
        "company": "Webflow",
        "body": {
            "jobs": [
                {"id": 7951428, "title": "Founder Brand Lead", "company_name": "Webflow",
                 "updated_at": "2026-06-09T12:55:09-04:00",
                 "location": {"name": "London (Hybrid)"}},
            ],
            "meta": {"total": 1},
        },
    },
    {
        "id": "ashby-posthog",
        "url": "https://api.ashbyhq.com/posting-api/job-board/posthog",
        "company": "PostHog",
        "body": {
            "apiVersion": "1",
            "jobs": [
                {"id": "ph-1", "title": "Content Engineer", "department": "Marketing",
                 "location": "Remote (EMEA)", "publishedAt": "2026-04-21T06:53:22.089+00:00",
                 "_company": "PostHog"},
            ],
        },
    },
    {
        "id": "ashby-vercel",
        "url": "https://api.ashbyhq.com/posting-api/job-board/vercel",
        "company": "Vercel",
        "body": {
            "apiVersion": "1",
            "jobs": [
                {"id": "vc-1", "title": "Head of Brand", "department": "Marketing",
                 "location": "Remote (US)", "publishedAt": "2026-03-10T10:00:00.000+00:00",
                 "_company": "Vercel"},
            ],
        },
    },
]


def seed_bodies() -> dict[str, Any]:
    """``{url: canned_body}`` for the ``FakeApiFetchClient``."""
    return {s["url"]: s["body"] for s in SEED_SOURCES}


def seed_register_payload() -> dict[str, Any]:
    """Payload for a ``source.register.requested`` event registering all seeds.

    Each source is stamped with an ``enrichment.company`` so downstream views
    can group by company even before the graph is built.
    """
    return {
        "sources": [
            {
                "id": s["id"],
                "url": s["url"],
                "enrichment": {"company": s["company"], "kind": "ats-job-board"},
                "tags": ["ats", "hiring-signal"],
            }
            for s in SEED_SOURCES
        ]
    }

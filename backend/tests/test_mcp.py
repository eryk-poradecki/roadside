import asyncio

import httpx
import pytest
from fastapi import FastAPI
from mcp.shared.memory import create_connected_server_and_client_session

from app.mcp import create_server
from app.settings import Settings
from tests.fakes import FakePlaceSource, ScriptedProvider, osm_node, report_json


async def test_mcp_exposes_only_the_four_allowed_tools(settings: Settings) -> None:
    async with create_connected_server_and_client_session(create_server(settings)) as client:
        tools = (await client.list_tools()).tools
        assert {tool.name for tool in tools} == {
            "list_incidents",
            "get_incident",
            "find_nearby",
            "draft_damage_report",
        }
        result = await client.call_tool("delete_incident", {"incident_id": 1})
        assert result.isError


async def test_client_reads_existing_incidents_and_validates_inputs(
    settings: Settings, client: httpx.AsyncClient
) -> None:
    created = (await client.post("/api/v1/incidents", json={"problem_type": "flat_tyre"})).json()
    async with create_connected_server_and_client_session(create_server(settings)) as mcp:
        page = await mcp.call_tool("list_incidents", {"status": "open"})
        assert not page.isError
        assert page.structuredContent is not None
        assert page.structuredContent["total"] == 1
        assert page.structuredContent["items"][0]["id"] == created["id"]
        detail = await mcp.call_tool("get_incident", {"incident_id": created["id"]})
        assert not detail.isError
        assert detail.structuredContent == created
        for tool, args in (
            ("get_incident", {"incident_id": 999}),
            ("get_incident", {"incident_id": 0}),
            ("list_incidents", {"limit": 101}),
            ("list_incidents", {"status": "deleted"}),
        ):
            assert (await mcp.call_tool(tool, args)).isError


async def test_nearby_lookup_does_not_change_the_incident(
    settings: Settings, app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = FakePlaceSource([osm_node(1, 52.23, 21.01, shop="tyres", name="Tyres")])
    app.state.place_source = source
    monkeypatch.setattr("app.mcp.create_app", lambda _: app)
    created = (
        await client.post(
            "/api/v1/incidents",
            json={"problem_type": "flat_tyre", "location": {"lat": 52.23, "lon": 21.01}},
        )
    ).json()
    async with create_connected_server_and_client_session(create_server(settings)) as mcp:
        result = await mcp.call_tool("find_nearby", {"incident_id": created["id"]})
        assert not result.isError
        assert result.structuredContent is not None
        assert result.structuredContent["places"][0]["name"] == "Tyres"
        assert source.calls == [(52.23, 21.01, 5000)]
        after = await mcp.call_tool("get_incident", {"incident_id": created["id"]})
        assert after.structuredContent == created


async def test_draft_is_created_but_never_replaced_or_sent(
    settings: Settings, app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = ScriptedProvider(report_json())
    app.state.llm_provider = provider
    monkeypatch.setattr("app.mcp.create_app", lambda _: app)
    pothole = (
        await client.post("/api/v1/incidents", json={"problem_type": "pothole_damage"})
    ).json()
    other = (await client.post("/api/v1/incidents", json={"problem_type": "flat_tyre"})).json()
    async with create_connected_server_and_client_session(create_server(settings)) as mcp:
        rejected = await mcp.call_tool("draft_damage_report", {"incident_id": other["id"]})
        assert rejected.isError
        assert "not_pothole_damage" in str(rejected.content)
        draft = await mcp.call_tool("draft_damage_report", {"incident_id": pothole["id"]})
        assert not draft.isError
        assert draft.structuredContent is not None
        assert draft.structuredContent["status"] == "draft"
        assert draft.structuredContent["locale"] == "pl"
        assert "The front right tyre is cut and the rim is bent." in draft.structuredContent["body"]
        url = f"/api/v1/incidents/{pothole['id']}/damage-report"
        sent = (
            await client.patch(url, json={"body": "Driver's edited letter", "status": "sent"})
        ).json()
        again = await mcp.call_tool("draft_damage_report", {"incident_id": pothole["id"]})
        assert again.isError
        assert "damage_report_exists" in str(again.content)
        assert (await client.get(url)).json() == sent


async def test_api_and_mcp_cannot_generate_for_the_same_incident_at_once(
    settings: Settings, app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()

    async def generate() -> str:
        entered.set()
        await release.wait()
        return report_json()

    provider = ScriptedProvider(generate)
    app.state.llm_provider = provider
    monkeypatch.setattr("app.main.build_provider", lambda _: provider)
    incident = (
        await client.post("/api/v1/incidents", json={"problem_type": "pothole_damage"})
    ).json()
    async with create_connected_server_and_client_session(create_server(settings)) as mcp:
        pending = asyncio.create_task(
            client.post(f"/api/v1/incidents/{incident['id']}/damage-report", json={})
        )
        try:
            await asyncio.wait_for(entered.wait(), timeout=5)
            result = await mcp.call_tool("draft_damage_report", {"incident_id": incident["id"]})
            assert result.isError
            assert "turn_in_progress" in str(result.content)
        finally:
            release.set()
            assert (await pending).status_code == 201

"""Local stdio entry point: the existing services, with a deliberately small tool surface."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import FastAPI
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.session import ServerSession
from mcp.types import ToolAnnotations
from pydantic import Field

from app.db.connection import connect
from app.deps import (
    get_damage_report_service,
    get_incident_service,
    get_location_resolver,
    get_nearby_service,
    get_photo_files,
)
from app.domain.ai_turn import Locale
from app.domain.incident import IncidentStatus
from app.errors import AppError
from app.main import create_app
from app.schemas.damage_report import DamageReportRead
from app.schemas.incident import IncidentPage, IncidentRead, IncidentSummary
from app.schemas.nearby import NearbyRead
from app.services.damage_reports import DamageReportService
from app.services.incidents import IncidentService
from app.services.nearby import NearbyService
from app.settings import Settings

IncidentId = Annotated[int, Field(ge=1, le=2**63 - 1)]
McpContext = Context[ServerSession, FastAPI]


@dataclass
class Services:
    incidents: IncidentService
    nearby: NearbyService
    reports: DamageReportService


@asynccontextmanager
async def services(ctx: McpContext) -> AsyncIterator[Services]:
    # Share the API's composition and lifecycle, not its HTTP transport or routers.
    state = ctx.request_context.lifespan_context.state
    settings = state.settings
    location = get_location_resolver(
        settings, state.geocoder, state.place_recordings, state.place_recorder
    )
    conn = await connect(settings.database_path)
    try:
        yield Services(
            get_incident_service(conn, location, get_photo_files(settings)),
            get_nearby_service(
                conn, state.place_source, state.place_recordings, state.place_recorder
            ),
            get_damage_report_service(
                conn, settings, state.llm_provider, state.turn_locks, location
            ),
        )
    except AppError as exc:
        raise ToolError(f"{exc.reason}: {exc.detail or exc.reason}") from exc
    finally:
        await conn.close()


def create_server(settings: Settings | None = None) -> FastMCP:
    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[FastAPI]:
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            yield app

    server = FastMCP("Roadside", lifespan=lifespan)
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False)

    @server.tool(annotations=read_only)
    async def list_incidents(
        ctx: McpContext,
        status: IncidentStatus | None = None,
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        offset: Annotated[int, Field(ge=0, le=2**63 - 1)] = 0,
    ) -> IncidentPage:
        """List incidents newest first, optionally filtered by open/resolved status."""
        async with services(ctx) as svc:
            items, total, reports = await svc.incidents.list(status, None, limit, offset)
            return IncidentPage(
                items=[IncidentSummary.from_domain(i, reports.get(i.id)) for i in items],
                total=total,
                limit=limit,
                offset=offset,
            )

    @server.tool(annotations=read_only)
    async def get_incident(incident_id: IncidentId, ctx: McpContext) -> IncidentRead:
        """Read an incident and its stored AI answer, photos and nearby snapshot."""
        async with services(ctx) as svc:
            return IncidentRead.from_domain(await svc.incidents.detail(incident_id))

    @server.tool(annotations=read_only)
    async def find_nearby(
        incident_id: IncidentId,
        ctx: McpContext,
        radius_km: Annotated[int, Field(ge=1, le=25)] = 5,
    ) -> NearbyRead:
        """Find real OSM places around an incident without changing its saved snapshot."""
        async with services(ctx) as svc:
            return NearbyRead.from_domain(
                await svc.nearby.lookup(incident_id, radius_km, persist=False)
            )

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
    async def draft_damage_report(
        incident_id: IncidentId, ctx: McpContext, locale: Locale = "pl"
    ) -> DamageReportRead:
        """Create a draft for a pothole incident. Never overwrite an existing report or send it."""
        async with services(ctx) as svc:
            report, _ = await svc.reports.generate(incident_id, locale, replace=False)
            return DamageReportRead.from_domain(report)

    return server


if __name__ == "__main__":
    create_server().run(transport="stdio")
